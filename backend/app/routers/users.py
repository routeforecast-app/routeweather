from __future__ import annotations

from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import add_role_grant, get_user_by_email, remove_role_grant, sync_user_access_state
from app.config import get_settings
from app.database import get_session
from app.dependencies import get_current_active_admin, get_current_active_user, get_current_system_manager, get_current_user
from app.models import AdminEmail, SavedGpxFile, SavedRoute, User
from app.roles import ADMINISTRATION_USER, has_role, normalize_role, role_label
from app.schemas import (
    AdminStatsRead,
    GenericMessageResponse,
    PasswordChangeRequest,
    RoleGrantRead,
    RoleGrantRequest,
    UserPreferencesUpdate,
    UserProfileUpdate,
    UserRead,
)
from app.services.account_lifecycle_service import (
    ACCOUNT_STATUS_USER_DEACTIVATED,
    USER_DELETION_GRACE_PERIOD,
    deactivate_user,
    touch_user_activity,
    utc_now,
)
from app.services.support_service import normalize_name
from app.utils.security import (
    ADMIN_PASSWORD_POLICY_MESSAGE,
    decrypt_sensitive_value,
    encrypt_sensitive_value,
    get_password_hash,
    hash_lookup_value,
    normalize_phone_number,
    password_meets_admin_policy,
    verify_password,
)


router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


def _needs_support_profile(user: User) -> bool:
    return not bool(user.first_name and user.last_name and user.phone_number_encrypted and user.phone_number_hash)


def _serialize_user(user: User) -> UserRead:
    normalized_role = normalize_role(user.role)
    return UserRead(
        id=user.id,
        email=user.email,
        role=normalized_role,
        role_label=role_label(normalized_role),
        is_admin=has_role(normalized_role, ADMINISTRATION_USER),
        must_change_password=user.must_change_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=decrypt_sensitive_value(user.phone_number_encrypted),
        needs_support_profile=_needs_support_profile(user),
        distance_unit=user.distance_unit,
        temperature_unit=user.temperature_unit,
        time_format=user.time_format,
        account_status=user.account_status,
        last_login_at=user.last_login_at,
        last_active_at=user.last_active_at,
        deactivated_at=user.deactivated_at,
        scheduled_deletion_at=user.scheduled_deletion_at,
        deactivation_reason=user.deactivation_reason,
        created_at=user.created_at,
    )


def _seeded_role_for_email(email: str) -> str | None:
    normalized_email = email.strip().lower()
    if normalized_email in settings.normalized_system_manager_emails:
        return "system_manager"
    if normalized_email in settings.normalized_administration_user_emails:
        return "administration_user"
    if normalized_email in settings.normalized_senior_support_user_emails:
        return "senior_support_user"
    if normalized_email in settings.normalized_support_user_emails:
        return "support_user"
    return None


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return _serialize_user(current_user)


@router.patch("/me/preferences", response_model=UserRead)
def update_preferences(
    payload: UserPreferencesUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> UserRead:
    current_user.distance_unit = payload.distance_unit
    current_user.temperature_unit = payload.temperature_unit
    current_user.time_format = payload.time_format
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return _serialize_user(current_user)


@router.patch("/me/profile", response_model=UserRead)
def update_profile(
    payload: UserProfileUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> UserRead:
    try:
        normalized_phone_number = normalize_phone_number(payload.phone_number)
        normalized_first_name = normalize_name(payload.first_name)
        normalized_last_name = normalize_name(payload.last_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    current_user.first_name = normalized_first_name
    current_user.last_name = normalized_last_name
    current_user.phone_number_encrypted = encrypt_sensitive_value(normalized_phone_number)
    current_user.phone_number_hash = hash_lookup_value(normalized_phone_number)
    touch_user_activity(session, current_user, force=True, commit=False)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return _serialize_user(current_user)


@router.post("/me/change-password", response_model=GenericMessageResponse)
def change_password(
    payload: PasswordChangeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> GenericMessageResponse:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )
    if has_role(current_user.role, ADMINISTRATION_USER) and not password_meets_admin_policy(payload.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ADMIN_PASSWORD_POLICY_MESSAGE)

    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.admin_password_compliant = password_meets_admin_policy(payload.new_password)
    current_user.must_change_password = False
    touch_user_activity(session, current_user, force=True, commit=False)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return GenericMessageResponse(message="Password updated successfully.")


@router.post("/me/deactivate", response_model=GenericMessageResponse)
def deactivate_own_account(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> GenericMessageResponse:
    deactivate_user(
        session,
        current_user,
        status_value=ACCOUNT_STATUS_USER_DEACTIVATED,
        reason="User requested account deactivation.",
        grace_period=USER_DELETION_GRACE_PERIOD,
        when=utc_now(),
    )
    return GenericMessageResponse(
        message="Your account has been deactivated and is scheduled for deletion in 60 days unless you sign in again."
    )


@router.get("/admin/stats", response_model=AdminStatsRead)
def get_admin_stats(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_active_admin),
) -> AdminStatsRead:
    total_users = session.exec(select(func.count()).select_from(User)).one()
    total_routes = session.exec(select(func.count()).select_from(SavedRoute)).one()
    total_saved_gpx_files = session.exec(select(func.count()).select_from(SavedGpxFile)).one()
    total_admin_users = session.exec(
        select(func.count()).select_from(User).where(User.role.in_(["administration_user", "system_manager"]))
    ).one()
    return AdminStatsRead(
        total_users=total_users,
        total_routes=total_routes,
        total_saved_gpx_files=total_saved_gpx_files,
        total_admin_users=total_admin_users,
    )


@router.get("/admin/role-grants", response_model=list[RoleGrantRead])
def list_role_grants(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_active_admin),
) -> list[RoleGrantRead]:
    grants = session.exec(select(AdminEmail).order_by(AdminEmail.email.asc())).all()
    role_grants: list[RoleGrantRead] = []
    for grant in grants:
        role_grants.append(
            RoleGrantRead(
                id=grant.id,
                email=grant.email,
                role=normalize_role(grant.role),
                role_label=role_label(grant.role),
                created_at=grant.created_at,
                is_seeded=_seeded_role_for_email(grant.email) is not None,
            )
        )
    return role_grants


@router.post("/admin/role-grants", response_model=RoleGrantRead, status_code=status.HTTP_201_CREATED)
def create_role_grant(
    payload: RoleGrantRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_system_manager),
) -> RoleGrantRead:
    role_grant = add_role_grant(session, payload.email, payload.role)
    user = get_user_by_email(session, payload.email)
    if user:
        sync_user_access_state(session, user)
    return RoleGrantRead(
        id=role_grant.id,
        email=role_grant.email,
        role=normalize_role(role_grant.role),
        role_label=role_label(role_grant.role),
        created_at=role_grant.created_at,
        is_seeded=_seeded_role_for_email(role_grant.email) is not None,
    )


@router.delete("/admin/role-grants/{role_grant_id}", response_model=GenericMessageResponse)
def delete_role_grant(
    role_grant_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_system_manager),
) -> GenericMessageResponse:
    role_grant = session.get(AdminEmail, role_grant_id)
    if not role_grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role grant not found.")
    if _seeded_role_for_email(role_grant.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seeded access roles cannot be removed from the panel.",
        )

    email = role_grant.email
    remove_role_grant(session, email)
    user = get_user_by_email(session, email)
    if user:
        sync_user_access_state(session, user)
    return GenericMessageResponse(message=f"{email} has been removed from privileged access.")
