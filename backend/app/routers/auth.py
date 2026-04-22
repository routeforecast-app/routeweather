from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth import authenticate_user, create_access_token, get_user_by_email, register_user
from app.database import get_session
from app.models import User
from app.roles import ADMINISTRATION_USER, has_role, normalize_role, role_label
from app.schemas import (
    ForgotPasswordRequest,
    GenericMessageResponse,
    PasswordResetConfirmRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services.support_service import consume_password_reset_token, queue_password_reset_email
from app.utils.security import (
    ADMIN_PASSWORD_POLICY_MESSAGE,
    decrypt_sensitive_value,
    get_password_hash,
    password_meets_admin_policy,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _serialize_user(user) -> UserRead:
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
        needs_support_profile=not bool(
            user.first_name and user.last_name and user.phone_number_encrypted and user.phone_number_hash
        ),
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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, session: Session = Depends(get_session)) -> TokenResponse:
    existing_user = get_user_by_email(session, payload.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered.")

    try:
        user = register_user(
            session,
            payload.email,
            payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone_number=payload.phone_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=_serialize_user(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, session: Session = Depends(get_session)) -> TokenResponse:
    user = authenticate_user(session, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=_serialize_user(user))


@router.post("/forgot-password", response_model=GenericMessageResponse)
def forgot_password(payload: ForgotPasswordRequest, session: Session = Depends(get_session)) -> GenericMessageResponse:
    user = get_user_by_email(session, payload.email)
    if user:
        queue_password_reset_email(
            session,
            user=user,
            delivery_email=user.email,
            requested_by_user=None,
            reason="User-initiated forgot password request",
        )
    return GenericMessageResponse(
        message="If the email exists in RouteForcast, a password reset link has been queued for delivery."
    )


@router.post("/reset-password/confirm", response_model=GenericMessageResponse)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    session: Session = Depends(get_session),
) -> GenericMessageResponse:
    password_reset_token = consume_password_reset_token(session, payload.token)
    if not password_reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That password reset link is invalid or expired.")

    user = session.get(User, password_reset_token.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found for that reset link.")
    if has_role(user.role, ADMINISTRATION_USER) and not password_meets_admin_policy(payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ADMIN_PASSWORD_POLICY_MESSAGE,
        )

    user.password_hash = get_password_hash(payload.new_password)
    user.admin_password_compliant = password_meets_admin_policy(payload.new_password)
    user.must_change_password = False
    session.add(user)
    session.commit()
    return GenericMessageResponse(message="Password updated successfully. You can now sign in.")
