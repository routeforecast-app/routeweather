from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session, select

from app.config import get_settings
from app.models import PasswordResetToken, SupportAuditLog, User
from app.roles import GENERAL_USER, role_label
from app.utils.security import decrypt_sensitive_value, hash_lookup_value, normalize_phone_number


settings = get_settings()
email_outbox_dir = Path(settings.email_outbox_dir)
email_outbox_dir.mkdir(parents=True, exist_ok=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_name(value: str) -> str:
    normalized = " ".join(part for part in value.strip().split() if part)
    if not normalized:
        raise ValueError("This field is required.")
    return normalized


def _normalize_stored_name(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(part for part in value.strip().split() if part).casefold()


def build_password_reset_url(token: str) -> str:
    return f"{settings.frontend_app_url.rstrip('/')}/reset-password?token={token}"


def queue_email_file(*, to_email: str, subject: str, body: str) -> Path:
    filename = f"{utc_now().strftime('%Y%m%d-%H%M%S')}-{uuid4()}.json"
    outbox_file = email_outbox_dir / filename
    payload = {
        "to_email": to_email,
        "subject": subject,
        "body": body,
        "queued_at": utc_now().isoformat(),
    }
    outbox_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return outbox_file


def log_support_action(
    session: Session,
    *,
    actor: User,
    action: str,
    target_user: User | None = None,
    target_email: str | None = None,
    details: dict | None = None,
    commit: bool = True,
) -> SupportAuditLog:
    audit_log = SupportAuditLog(
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action=action,
        target_user_id=target_user.id if target_user else None,
        target_email=(target_user.email if target_user else target_email),
        details_json=details or {},
    )
    session.add(audit_log)
    if commit:
        session.commit()
        session.refresh(audit_log)
    return audit_log


def invalidate_active_password_reset_tokens(session: Session, user: User) -> None:
    now = utc_now()
    tokens = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at >= now,
        )
    ).all()
    for token in tokens:
        token.used_at = now
        session.add(token)


def create_password_reset_token(
    session: Session,
    *,
    user: User,
    delivery_email: str,
    requested_by_user: User | None,
    purpose: str = "password_reset",
) -> tuple[str, PasswordResetToken]:
    invalidate_active_password_reset_tokens(session, user)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    reset_token = PasswordResetToken(
        user_id=user.id,
        delivery_email=delivery_email.strip().lower(),
        token_hash=token_hash,
        created_by_user_id=requested_by_user.id if requested_by_user else None,
        created_by_role=requested_by_user.role if requested_by_user else GENERAL_USER,
        purpose=purpose,
        expires_at=utc_now() + timedelta(minutes=settings.password_reset_token_expire_minutes),
    )
    session.add(reset_token)
    session.commit()
    session.refresh(reset_token)
    return raw_token, reset_token


def queue_password_reset_email(
    session: Session,
    *,
    user: User,
    delivery_email: str,
    requested_by_user: User | None,
    reason: str,
) -> None:
    token, _ = create_password_reset_token(
        session,
        user=user,
        delivery_email=delivery_email,
        requested_by_user=requested_by_user,
    )
    reset_url = build_password_reset_url(token)
    subject = "RouteForcast password reset"
    body = (
        f"Hello {user.first_name or 'RouteForcast user'},\n\n"
        f"A password reset has been requested for your RouteForcast account.\n"
        f"Reason: {reason}\n\n"
        f"Use this reset link:\n{reset_url}\n\n"
        f"This link expires in {settings.password_reset_token_expire_minutes} minutes."
    )
    email_file = queue_email_file(to_email=delivery_email, subject=subject, body=body)
    if requested_by_user:
        log_support_action(
            session,
            actor=requested_by_user,
            action="password_reset_email_queued",
            target_user=user,
            details={
                "delivery_email": delivery_email,
                "reason": reason,
                "email_outbox_file": str(email_file),
            },
        )


def get_user_from_password_reset_token(session: Session, raw_token: str) -> User | None:
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    password_reset_token = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).first()
    if not password_reset_token:
        return None
    if password_reset_token.used_at is not None or password_reset_token.expires_at < utc_now():
        return None
    return session.get(User, password_reset_token.user_id)


def consume_password_reset_token(session: Session, raw_token: str) -> PasswordResetToken | None:
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    password_reset_token = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).first()
    if not password_reset_token:
        return None
    if password_reset_token.used_at is not None or password_reset_token.expires_at < utc_now():
        return None
    password_reset_token.used_at = utc_now()
    session.add(password_reset_token)
    session.commit()
    session.refresh(password_reset_token)
    return password_reset_token


def find_users_by_support_identity(
    session: Session,
    *,
    first_name: str,
    last_name: str,
    phone_number: str,
) -> list[User]:
    normalized_first_name = normalize_name(first_name).casefold()
    normalized_last_name = normalize_name(last_name).casefold()
    normalized_phone_number = normalize_phone_number(phone_number)
    phone_hash = hash_lookup_value(normalized_phone_number)
    matches: list[User] = []

    for user in session.exec(select(User).order_by(User.created_at.asc(), User.id.asc())).all():
        if _normalize_stored_name(user.first_name) != normalized_first_name:
            continue
        if _normalize_stored_name(user.last_name) != normalized_last_name:
            continue

        stored_phone_matches = user.phone_number_hash == phone_hash
        if not stored_phone_matches:
            decrypted_phone = decrypt_sensitive_value(user.phone_number_encrypted)
            if decrypted_phone:
                try:
                    stored_phone_matches = normalize_phone_number(decrypted_phone) == normalized_phone_number
                except ValueError:
                    stored_phone_matches = False

        if stored_phone_matches:
            matches.append(user)

    return matches


def format_paid_status(_: User) -> str:
    return "Not paid"


def support_lookup_summary(user: User) -> dict[str, str | int | None]:
    return {
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_paid_member": False,
        "paid_member_status": format_paid_status(user),
        "role": user.role,
        "role_label": role_label(user.role),
        "created_at": user.created_at,
        "last_active_at": user.last_active_at,
    }
