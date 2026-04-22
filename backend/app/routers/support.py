from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_user_by_email, sync_user_access_state
from app.database import get_session
from app.dependencies import (
    get_current_active_admin,
    get_current_senior_support_user,
    get_current_support_user,
)
from app.models import AdminEmail, SavedRoute, SiteVisit, SupportAuditLog, User
from app.roles import ADMINISTRATION_USER, has_role, role_label
from app.schemas import (
    AccountLifecycleRead,
    AdminDeleteUserRequest,
    AdminUserEmailAction,
    FlaggedUserRead,
    GenericMessageResponse,
    SupportAccountRecoverySearchRequest,
    SupportAuditLogRead,
    SupportEmailChangeRequest,
    SupportMatchedUserRead,
    SupportPasswordResetRequest,
)
from app.services.account_lifecycle_service import (
    ACCOUNT_STATUS_ACTIVE,
    ACCOUNT_STATUS_ADMIN_DEACTIVATED,
    ADMIN_DELETION_GRACE_PERIOD,
    deactivate_user,
    list_inactive_account_summaries,
    permanently_delete_user,
    reactivate_user,
)
from app.services.support_service import (
    find_users_by_support_identity,
    log_support_action,
    normalize_name,
    queue_email_file,
    queue_password_reset_email,
    support_lookup_summary,
)
from app.utils.security import verify_password


router = APIRouter(prefix="/support", tags=["support"])

SUSPICIOUS_ROUTE_THRESHOLD = 10
SUSPICIOUS_VISIT_THRESHOLD = 20
SUSPICIOUS_PATH_SWITCH_THRESHOLD = 8
SUSPICIOUS_VISIT_WINDOW = timedelta(minutes=10)
SUSPICIOUS_ROUTE_WINDOW = timedelta(hours=1)


def _normalize_confirmed_email(email: str, confirm_email: str) -> str:
    normalized_email = email.strip().lower()
    normalized_confirm_email = confirm_email.strip().lower()
    if not normalized_email or normalized_email != normalized_confirm_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email confirmation does not match.")
    return normalized_email


def _build_flagged_users(session: Session) -> list[FlaggedUserRead]:
    now = datetime.now(timezone.utc)
    visit_window_start = now - SUSPICIOUS_VISIT_WINDOW
    route_window_start = now - SUSPICIOUS_ROUTE_WINDOW

    users = session.exec(select(User).order_by(User.email.asc())).all()
    recent_visits = session.exec(select(SiteVisit).where(SiteVisit.visited_at >= visit_window_start)).all()
    recent_routes = session.exec(select(SavedRoute).where(SavedRoute.created_at >= route_window_start)).all()
    all_routes = session.exec(select(SavedRoute)).all()

    routes_total_by_user: dict[int, int] = {}
    for route in all_routes:
        routes_total_by_user[route.user_id] = routes_total_by_user.get(route.user_id, 0) + 1

    route_counts_last_hour: dict[int, int] = {}
    for route in recent_routes:
        route_counts_last_hour[route.user_id] = route_counts_last_hour.get(route.user_id, 0) + 1

    visit_counts: dict[int, int] = {}
    distinct_paths: dict[int, set[str]] = {}
    for visit in recent_visits:
        if visit.user_id is None:
            continue
        visit_counts[visit.user_id] = visit_counts.get(visit.user_id, 0) + 1
        distinct_paths.setdefault(visit.user_id, set()).add(visit.path)

    flagged_users: list[FlaggedUserRead] = []
    for user in users:
        reasons: list[str] = []
        routes_last_hour = route_counts_last_hour.get(user.id, 0)
        visits_last_10_minutes = visit_counts.get(user.id, 0)
        distinct_paths_last_10_minutes = len(distinct_paths.get(user.id, set()))

        if routes_last_hour >= SUSPICIOUS_ROUTE_THRESHOLD:
            reasons.append(f"{routes_last_hour} routes created within the last hour.")
        if (
            visits_last_10_minutes >= SUSPICIOUS_VISIT_THRESHOLD
            and distinct_paths_last_10_minutes >= SUSPICIOUS_PATH_SWITCH_THRESHOLD
        ):
            reasons.append(
                f"{visits_last_10_minutes} page visits across {distinct_paths_last_10_minutes} paths in 10 minutes."
            )

        if not reasons:
            continue

        flagged_users.append(
            FlaggedUserRead(
                email=user.email,
                created_at=user.created_at,
                last_active_at=user.last_active_at,
                last_login_at=user.last_login_at,
                routes_created_total=routes_total_by_user.get(user.id, 0),
                routes_created_last_hour=routes_last_hour,
                visit_count_last_10_minutes=visits_last_10_minutes,
                distinct_paths_last_10_minutes=distinct_paths_last_10_minutes,
                flag_reasons=reasons,
            )
        )

    return flagged_users


@router.get("/inactive-accounts", response_model=list[AccountLifecycleRead])
def get_inactive_accounts(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_support_user),
) -> list[AccountLifecycleRead]:
    return [AccountLifecycleRead.model_validate(summary) for summary in list_inactive_account_summaries(session)]


@router.get("/flagged-users", response_model=list[FlaggedUserRead])
def get_flagged_users(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_support_user),
) -> list[FlaggedUserRead]:
    return _build_flagged_users(session)


@router.post("/password-reset", response_model=GenericMessageResponse)
def support_password_reset(
    payload: SupportPasswordResetRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_support_user),
) -> GenericMessageResponse:
    user = get_user_by_email(session, payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if normalize_name(payload.first_name).casefold() != (user.first_name or "").casefold():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User details did not match.")
    if normalize_name(payload.last_name).casefold() != (user.last_name or "").casefold():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User details did not match.")

    queue_password_reset_email(
        session,
        user=user,
        delivery_email=user.email,
        requested_by_user=current_user,
        reason="Support-assisted password reset",
    )
    log_support_action(
        session,
        actor=current_user,
        action="support_password_reset_requested",
        target_user=user,
        details={"verification": "email_first_name_last_name"},
    )
    return GenericMessageResponse(message="Password reset link queued for delivery.")


@router.post("/reactivate", response_model=GenericMessageResponse)
def reactivate_account(
    payload: AdminUserEmailAction,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_support_user),
) -> GenericMessageResponse:
    target_email = _normalize_confirmed_email(payload.email, payload.confirm_email)
    user = get_user_by_email(session, target_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.account_status == ACCOUNT_STATUS_ACTIVE:
        return GenericMessageResponse(message=f"{user.email} is already active.")
    if user.account_status == ACCOUNT_STATUS_ADMIN_DEACTIVATED and not has_role(current_user.role, ADMINISTRATION_USER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Administration User or higher can reactivate an admin-deactivated account.",
        )

    reactivate_user(session, user)
    log_support_action(
        session,
        actor=current_user,
        action="account_reactivated",
        target_user=user,
        details={"reason": payload.reason or "Support reactivation"},
    )
    return GenericMessageResponse(message=f"{user.email} has been reactivated.")


@router.post("/account-search", response_model=list[SupportMatchedUserRead])
def search_accounts_for_recovery(
    payload: SupportAccountRecoverySearchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_senior_support_user),
) -> list[SupportMatchedUserRead]:
    users = find_users_by_support_identity(
        session,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
    )
    log_support_action(
        session,
        actor=current_user,
        action="account_recovery_search",
        target_email=None,
        details={
            "searched_first_name": normalize_name(payload.first_name),
            "searched_last_name": normalize_name(payload.last_name),
            "match_count": len(users),
            "matched_emails": [user.email for user in users],
        },
    )
    return [SupportMatchedUserRead(**support_lookup_summary(user)) for user in users]


@router.post("/email-change", response_model=GenericMessageResponse)
def change_user_email_for_recovery(
    payload: SupportEmailChangeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_senior_support_user),
) -> GenericMessageResponse:
    user = session.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if has_role(user.role, ADMINISTRATION_USER) and not has_role(current_user.role, ADMINISTRATION_USER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Administration User or higher can change the email for an elevated account.",
        )

    new_email = payload.new_email.strip().lower()
    if user.email == new_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The new email matches the current email.")
    existing_user = get_user_by_email(session, new_email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That email is already in use.")

    original_email = user.email
    role_grant = session.exec(select(AdminEmail).where(AdminEmail.email == original_email)).first()
    if role_grant:
        role_grant.email = new_email
        session.add(role_grant)

    user.email = new_email
    session.add(user)
    session.commit()
    session.refresh(user)
    user = sync_user_access_state(session, user)

    original_email_notice = queue_email_file(
        to_email=original_email,
        subject="RouteForcast account email changed",
        body=(
            f"Hello {user.first_name or 'RouteForcast user'},\n\n"
            f"Your account email has been changed from {original_email} to {new_email} by RouteForcast support.\n"
            f"If you did not request this, please contact support immediately."
        ),
    )
    queue_password_reset_email(
        session,
        user=user,
        delivery_email=new_email,
        requested_by_user=current_user,
        reason="Support-assisted account recovery after email change",
    )
    log_support_action(
        session,
        actor=current_user,
        action="account_email_changed_for_recovery",
        target_user=user,
        details={
            "original_email": original_email,
            "new_email": new_email,
            "original_email_notice_file": str(original_email_notice),
        },
    )
    return GenericMessageResponse(
        message=f"Email updated for {user.first_name or user.email}. Reset instructions have been queued to the new email."
    )


@router.get("/audit-logs", response_model=list[SupportAuditLogRead])
def list_support_audit_logs(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_senior_support_user),
) -> list[SupportAuditLogRead]:
    logs = session.exec(select(SupportAuditLog).order_by(SupportAuditLog.created_at.desc())).all()
    return [
        SupportAuditLogRead(
            id=log.id,
            actor_email=log.actor_email,
            actor_role=log.actor_role,
            actor_role_label=role_label(log.actor_role),
            action=log.action,
            target_email=log.target_email,
            details=log.details_json or {},
            created_at=log.created_at,
        )
        for log in logs[:100]
    ]


@router.post("/admin-deactivate", response_model=GenericMessageResponse)
def admin_deactivate_user(
    payload: AdminUserEmailAction,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_admin),
) -> GenericMessageResponse:
    target_email = _normalize_confirmed_email(payload.email, payload.confirm_email)
    if target_email == current_user.email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot admin-deactivate your own account.")

    user = get_user_by_email(session, target_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    deactivate_user(
        session,
        user,
        status_value=ACCOUNT_STATUS_ADMIN_DEACTIVATED,
        reason=payload.reason or "This account has been deactivated by an administrator pending appeal review.",
        grace_period=ADMIN_DELETION_GRACE_PERIOD,
    )
    log_support_action(
        session,
        actor=current_user,
        action="admin_deactivate_account",
        target_user=user,
        details={"reason": payload.reason},
    )
    return GenericMessageResponse(
        message=f"{user.email} has been admin-deactivated and now has 90 days to appeal before deletion."
    )


@router.post("/admin-delete", response_model=GenericMessageResponse)
def admin_delete_user(
    payload: AdminDeleteUserRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_admin),
) -> GenericMessageResponse:
    target_email = _normalize_confirmed_email(payload.email, payload.confirm_email)
    if target_email == current_user.email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account from the support panel.")
    if not verify_password(payload.admin_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrator password is incorrect.")

    user = get_user_by_email(session, target_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    log_support_action(
        session,
        actor=current_user,
        action="admin_delete_account_requested",
        target_user=user,
        details={"reason": "Deleted immediately by an administrator."},
        commit=False,
    )
    permanently_delete_user(
        session,
        user,
        deletion_reason="Deleted immediately by an administrator.",
    )
    return GenericMessageResponse(message=f"{target_email} has been permanently deleted.")
