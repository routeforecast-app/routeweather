from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlmodel import Session, select

from app.config import get_settings
from app.models import AdminEmail, User
from app.roles import (
    ADMINISTRATION_USER,
    GENERAL_USER,
    SENIOR_SUPPORT_USER,
    SUPPORT_USER,
    SYSTEM_MANAGER,
    has_role,
    highest_role,
    normalize_role,
)
from app.services.account_lifecycle_service import (
    ACCOUNT_STATUS_ACTIVE,
    process_account_lifecycle,
    register_login,
    touch_user_activity,
)
from app.services.support_service import normalize_name
from app.utils.security import (
    ADMIN_PASSWORD_POLICY_MESSAGE,
    encrypt_sensitive_value,
    get_password_hash,
    hash_lookup_value,
    normalize_phone_number,
    password_meets_admin_policy,
    verify_password,
)


settings = get_settings()


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email.lower())).first()


def _configured_role_from_settings(email: str) -> str:
    normalized_email = email.lower()
    configured_roles: list[str] = [GENERAL_USER]
    if normalized_email in settings.normalized_support_user_emails:
        configured_roles.append(SUPPORT_USER)
    if normalized_email in settings.normalized_senior_support_user_emails:
        configured_roles.append(SENIOR_SUPPORT_USER)
    if normalized_email in settings.normalized_administration_user_emails:
        configured_roles.append(ADMINISTRATION_USER)
    if normalized_email in settings.normalized_system_manager_emails:
        configured_roles.append(SYSTEM_MANAGER)
    return highest_role(*configured_roles)


def get_assigned_role(session: Session, email: str) -> str:
    normalized_email = email.lower()
    configured_role = _configured_role_from_settings(normalized_email)
    role_assignments = session.exec(select(AdminEmail).where(AdminEmail.email == normalized_email)).all()
    assigned_role = highest_role(
        configured_role,
        *(assignment.role for assignment in role_assignments),
    )
    return assigned_role


def add_role_grant(session: Session, email: str, role: str) -> AdminEmail:
    normalized_email = email.lower()
    normalized_role = normalize_role(role)
    existing = session.exec(select(AdminEmail).where(AdminEmail.email == normalized_email)).first()
    if existing:
        existing.role = normalized_role
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    role_grant = AdminEmail(email=normalized_email, role=normalized_role)
    session.add(role_grant)
    session.commit()
    session.refresh(role_grant)
    return role_grant


def remove_role_grant(session: Session, email: str) -> None:
    normalized_email = email.lower()
    role_grant = session.exec(select(AdminEmail).where(AdminEmail.email == normalized_email)).first()
    if not role_grant:
        return
    session.delete(role_grant)
    session.commit()


def seed_role_grants(session: Session) -> None:
    for email in settings.normalized_support_user_emails:
        add_role_grant(session, email, SUPPORT_USER)
    for email in settings.normalized_senior_support_user_emails:
        add_role_grant(session, email, SENIOR_SUPPORT_USER)
    for email in settings.normalized_administration_user_emails:
        add_role_grant(session, email, ADMINISTRATION_USER)
    for email in settings.normalized_system_manager_emails:
        add_role_grant(session, email, SYSTEM_MANAGER)


def seed_admin_emails(session: Session) -> None:
    seed_role_grants(session)


def sync_user_access_state(session: Session, user: User) -> User:
    process_account_lifecycle(session)
    previous_role = normalize_role(user.role)
    assigned_role = get_assigned_role(session, user.email)
    has_changes = False
    if user.role != assigned_role:
        user.role = assigned_role
        has_changes = True

    derived_is_admin = has_role(user.role, ADMINISTRATION_USER)
    if user.is_admin != derived_is_admin:
        user.is_admin = derived_is_admin
        has_changes = True

    promoted_to_admin = has_role(assigned_role, ADMINISTRATION_USER) and not has_role(previous_role, ADMINISTRATION_USER)
    if promoted_to_admin and not user.admin_password_compliant and not user.must_change_password:
        user.must_change_password = True
        has_changes = True

    if has_role(assigned_role, ADMINISTRATION_USER) and user.admin_password_compliant and user.must_change_password:
        user.must_change_password = False
        has_changes = True

    if not has_role(user.role, ADMINISTRATION_USER) and user.must_change_password:
        user.must_change_password = False
        has_changes = True

    if has_changes:
        session.add(user)
        session.commit()
        session.refresh(user)

    return user


def sync_admin_account_state(session: Session, user: User) -> User:
    return sync_user_access_state(session, user)


def register_user(
    session: Session,
    email: str,
    password: str,
    *,
    first_name: str,
    last_name: str,
    phone_number: str,
) -> User:
    normalized_email = email.lower()
    process_account_lifecycle(session)
    assigned_role = get_assigned_role(session, normalized_email)
    admin_password_compliant = password_meets_admin_policy(password)
    if has_role(assigned_role, ADMINISTRATION_USER) and not admin_password_compliant:
        raise ValueError(ADMIN_PASSWORD_POLICY_MESSAGE)

    normalized_phone_number = normalize_phone_number(phone_number)
    user = User(
        email=normalized_email,
        password_hash=get_password_hash(password),
        role=assigned_role,
        is_admin=has_role(assigned_role, ADMINISTRATION_USER),
        must_change_password=False,
        admin_password_compliant=admin_password_compliant,
        first_name=normalize_name(first_name),
        last_name=normalize_name(last_name),
        phone_number_encrypted=encrypt_sensitive_value(normalized_phone_number),
        phone_number_hash=hash_lookup_value(normalized_phone_number),
        distance_unit="km",
        temperature_unit="c",
        time_format="24h",
        account_status="active",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    touch_user_activity(session, user, force=True)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    process_account_lifecycle(session)
    user = get_user_by_email(session, email)
    if not user:
        return None
    user = sync_user_access_state(session, user)
    if not verify_password(password, user.password_hash):
        return None
    return register_login(session, user)


def get_user_from_token(session: Session, token: str) -> User | None:
    try:
        process_account_lifecycle(session)
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if not subject:
            return None
        user = session.get(User, int(subject))
        if not user:
            return None
        user = sync_user_access_state(session, user)
        if user.account_status != ACCOUNT_STATUS_ACTIVE:
            return user
        return touch_user_activity(session, user, commit=True)
    except (JWTError, TypeError, ValueError):
        return None
