from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlmodel import Session, delete, select

from app.config import get_settings
from app.models import AdminEmail, DeletedAccountRecord, SavedGpxFile, SavedRoute, SiteVisit, User


ACCOUNT_STATUS_ACTIVE = "active"
ACCOUNT_STATUS_INACTIVE_DEACTIVATED = "inactive_deactivated"
ACCOUNT_STATUS_USER_DEACTIVATED = "user_deactivated"
ACCOUNT_STATUS_ADMIN_DEACTIVATED = "admin_deactivated"

INACTIVITY_DEACTIVATION_AFTER = timedelta(days=365)
INACTIVITY_WARNING_WINDOW = timedelta(days=60)
USER_DELETION_GRACE_PERIOD = timedelta(days=60)
ADMIN_DELETION_GRACE_PERIOD = timedelta(days=90)
DELETION_IMMINENT_WINDOW = timedelta(days=14)
DELETED_AUDIT_RETENTION = timedelta(days=7)
ACTIVITY_WRITE_THROTTLE = timedelta(minutes=5)

settings = get_settings()


@dataclass
class InactiveAccountSummary:
    email: str
    account_status: str
    status_label: str
    deletion_phase: str | None
    created_at: datetime
    last_login_at: datetime | None
    last_active_at: datetime | None
    deactivated_at: datetime | None
    scheduled_deletion_at: datetime | None
    deletion_reason: str | None
    deleted_at: datetime | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_user_lifecycle_fields(user: User) -> bool:
    changed = False
    if not user.account_status:
        user.account_status = ACCOUNT_STATUS_ACTIVE
        changed = True

    created_at = as_utc(user.created_at) or utc_now()
    if user.created_at != created_at:
        user.created_at = created_at
        changed = True

    if user.last_active_at is None:
        user.last_active_at = created_at
        changed = True
    else:
        normalized_last_active = as_utc(user.last_active_at)
        if user.last_active_at != normalized_last_active:
            user.last_active_at = normalized_last_active
            changed = True

    if user.last_login_at is not None:
        normalized_last_login = as_utc(user.last_login_at)
        if user.last_login_at != normalized_last_login:
            user.last_login_at = normalized_last_login
            changed = True

    if user.deactivated_at is not None:
        normalized_deactivated_at = as_utc(user.deactivated_at)
        if user.deactivated_at != normalized_deactivated_at:
            user.deactivated_at = normalized_deactivated_at
            changed = True

    if user.scheduled_deletion_at is not None:
        normalized_scheduled_deletion_at = as_utc(user.scheduled_deletion_at)
        if user.scheduled_deletion_at != normalized_scheduled_deletion_at:
            user.scheduled_deletion_at = normalized_scheduled_deletion_at
            changed = True

    return changed


def touch_user_activity(
    session: Session,
    user: User,
    when: datetime | None = None,
    *,
    force: bool = False,
    commit: bool = True,
) -> User:
    when = as_utc(when) or utc_now()
    changed = normalize_user_lifecycle_fields(user)
    if force or user.last_active_at is None or when - user.last_active_at >= ACTIVITY_WRITE_THROTTLE:
        user.last_active_at = when
        changed = True

    if changed:
        session.add(user)
        if commit:
            session.commit()
            session.refresh(user)
    return user


def deactivate_user(
    session: Session,
    user: User,
    *,
    status_value: str,
    reason: str | None,
    grace_period: timedelta,
    when: datetime | None = None,
    commit: bool = True,
) -> User:
    when = as_utc(when) or utc_now()
    normalize_user_lifecycle_fields(user)
    user.account_status = status_value
    user.deactivated_at = when
    user.scheduled_deletion_at = when + grace_period
    user.deactivation_reason = reason
    session.add(user)
    if commit:
        session.commit()
        session.refresh(user)
    return user


def reactivate_user(session: Session, user: User, when: datetime | None = None) -> User:
    when = as_utc(when) or utc_now()
    normalize_user_lifecycle_fields(user)
    user.account_status = ACCOUNT_STATUS_ACTIVE
    user.deactivated_at = None
    user.scheduled_deletion_at = None
    user.deactivation_reason = None
    user.last_active_at = when
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def register_login(session: Session, user: User, when: datetime | None = None) -> User:
    when = as_utc(when) or utc_now()
    normalize_user_lifecycle_fields(user)
    user.last_login_at = when
    if user.account_status in {ACCOUNT_STATUS_USER_DEACTIVATED, ACCOUNT_STATUS_INACTIVE_DEACTIVATED}:
        user.account_status = ACCOUNT_STATUS_ACTIVE
        user.deactivated_at = None
        user.scheduled_deletion_at = None
        user.deactivation_reason = None
        user.last_active_at = when
    elif user.account_status == ACCOUNT_STATUS_ACTIVE:
        user.last_active_at = when

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def permanently_delete_user(
    session: Session,
    user: User,
    *,
    deleted_at: datetime | None = None,
    deletion_reason: str | None = None,
) -> None:
    deleted_at = as_utc(deleted_at) or utc_now()
    normalize_user_lifecycle_fields(user)

    route_file_paths = [Path(route.gpx_file_path) for route in session.exec(select(SavedRoute).where(SavedRoute.user_id == user.id)).all()]
    gpx_file_paths = [Path(gpx.file_path) for gpx in session.exec(select(SavedGpxFile).where(SavedGpxFile.user_id == user.id)).all()]

    session.add(
        DeletedAccountRecord(
            email=user.email,
            prior_account_status=user.account_status,
            deletion_reason=deletion_reason or user.deactivation_reason,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            last_active_at=user.last_active_at,
            deleted_at=deleted_at,
        )
    )

    session.exec(delete(SavedRoute).where(SavedRoute.user_id == user.id))
    session.exec(delete(SavedGpxFile).where(SavedGpxFile.user_id == user.id))
    session.exec(delete(SiteVisit).where(SiteVisit.user_id == user.id))
    session.exec(delete(AdminEmail).where(AdminEmail.email == user.email.lower()))
    session.delete(user)
    session.commit()

    for file_path in [*route_file_paths, *gpx_file_paths]:
        file_path.unlink(missing_ok=True)


def process_account_lifecycle(session: Session, *, now: datetime | None = None) -> None:
    now = as_utc(now) or utc_now()
    users = session.exec(select(User)).all()
    changed = False

    for user in users:
        if normalize_user_lifecycle_fields(user):
            session.add(user)
            changed = True

    if changed:
        session.commit()

    users = session.exec(select(User)).all()
    for user in list(users):
        normalize_user_lifecycle_fields(user)
        inactivity_reference = as_utc(user.last_active_at) or as_utc(user.created_at)
        if user.account_status == ACCOUNT_STATUS_ACTIVE and inactivity_reference and now - inactivity_reference >= INACTIVITY_DEACTIVATION_AFTER:
            deactivate_user(
                session,
                user,
                status_value=ACCOUNT_STATUS_INACTIVE_DEACTIVATED,
                reason="Automatically deactivated after 12 months of inactivity.",
                grace_period=USER_DELETION_GRACE_PERIOD,
                when=now,
            )
            continue

        if user.account_status in {
            ACCOUNT_STATUS_INACTIVE_DEACTIVATED,
            ACCOUNT_STATUS_USER_DEACTIVATED,
            ACCOUNT_STATUS_ADMIN_DEACTIVATED,
        } and user.scheduled_deletion_at and as_utc(user.scheduled_deletion_at) <= now:
            permanently_delete_user(session, user, deleted_at=now)

    retention_cutoff = now - DELETED_AUDIT_RETENTION
    expired_records = session.exec(
        select(DeletedAccountRecord).where(DeletedAccountRecord.deleted_at < retention_cutoff)
    ).all()
    if expired_records:
        for record in expired_records:
            session.delete(record)
        session.commit()


def list_inactive_account_summaries(session: Session, *, now: datetime | None = None) -> list[InactiveAccountSummary]:
    now = as_utc(now) or utc_now()
    process_account_lifecycle(session, now=now)
    summaries: list[InactiveAccountSummary] = []

    for user in session.exec(select(User).order_by(User.email.asc())).all():
        normalize_user_lifecycle_fields(user)
        inactivity_reference = as_utc(user.last_active_at) or as_utc(user.created_at)
        deletion_phase = None
        if user.scheduled_deletion_at and as_utc(user.scheduled_deletion_at) - now <= DELETION_IMMINENT_WINDOW:
            deletion_phase = "Deletion imminent"

        if user.account_status == ACCOUNT_STATUS_ACTIVE:
            if inactivity_reference and now - inactivity_reference >= INACTIVITY_DEACTIVATION_AFTER - INACTIVITY_WARNING_WINDOW:
                summaries.append(
                    InactiveAccountSummary(
                        email=user.email,
                        account_status=user.account_status,
                        status_label="Deactivation imminent",
                        deletion_phase=None,
                        created_at=as_utc(user.created_at) or utc_now(),
                        last_login_at=as_utc(user.last_login_at),
                        last_active_at=as_utc(user.last_active_at),
                        deactivated_at=None,
                        scheduled_deletion_at=None,
                        deletion_reason=None,
                    )
                )
            continue

        label = {
            ACCOUNT_STATUS_INACTIVE_DEACTIVATED: "Deactivated",
            ACCOUNT_STATUS_USER_DEACTIVATED: "User Deactivated",
            ACCOUNT_STATUS_ADMIN_DEACTIVATED: "Admin Deactivated",
        }.get(user.account_status)
        if not label:
            continue

        summaries.append(
            InactiveAccountSummary(
                email=user.email,
                account_status=user.account_status,
                status_label=label,
                deletion_phase=deletion_phase,
                created_at=as_utc(user.created_at) or utc_now(),
                last_login_at=as_utc(user.last_login_at),
                last_active_at=as_utc(user.last_active_at),
                deactivated_at=as_utc(user.deactivated_at),
                scheduled_deletion_at=as_utc(user.scheduled_deletion_at),
                deletion_reason=user.deactivation_reason,
            )
        )

    for record in session.exec(
        select(DeletedAccountRecord)
        .where(DeletedAccountRecord.deleted_at >= now - DELETED_AUDIT_RETENTION)
        .order_by(DeletedAccountRecord.deleted_at.desc())
    ).all():
        summaries.append(
            InactiveAccountSummary(
                email=record.email,
                account_status="deleted",
                status_label="Deleted",
                deletion_phase=None,
                created_at=as_utc(record.created_at) or utc_now(),
                last_login_at=as_utc(record.last_login_at),
                last_active_at=as_utc(record.last_active_at),
                deactivated_at=None,
                scheduled_deletion_at=None,
                deletion_reason=record.deletion_reason,
                deleted_at=as_utc(record.deleted_at),
            )
        )

    def sort_key(summary: InactiveAccountSummary) -> tuple[datetime, str]:
        primary_date = summary.deleted_at or summary.scheduled_deletion_at or summary.deactivated_at or summary.last_active_at or summary.created_at
        return (primary_date, summary.email.lower())

    return sorted(summaries, key=sort_key, reverse=True)


def get_account_status_detail(user: User) -> str | None:
    if user.account_status == ACCOUNT_STATUS_ADMIN_DEACTIVATED:
        return user.deactivation_reason or "This account has been deactivated by an administrator."
    if user.account_status == ACCOUNT_STATUS_USER_DEACTIVATED:
        return "This account has been deactivated and will be deleted unless you log in again in time."
    if user.account_status == ACCOUNT_STATUS_INACTIVE_DEACTIVATED:
        return "This account has been deactivated after 12 months of inactivity and will be deleted unless you log in again in time."
    return None
