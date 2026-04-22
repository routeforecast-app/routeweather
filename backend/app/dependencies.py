from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.auth import get_user_from_token
from app.database import get_session
from app.models import User
from app.roles import ADMINISTRATION_USER, SENIOR_SUPPORT_USER, SUPPORT_USER, SYSTEM_MANAGER, has_role
from app.services.account_lifecycle_service import ACCOUNT_STATUS_ADMIN_DEACTIVATED


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    session: Session = Depends(get_session),
    token: str = Depends(oauth2_scheme),
) -> User:
    user = get_user_from_token(session, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.account_status == ACCOUNT_STATUS_ADMIN_DEACTIVATED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated by an administrator.",
        )
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must change your password before accessing the app.",
        )
    return current_user


def require_minimum_role(minimum_role: str) -> Callable[[User], User]:
    def _dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if not has_role(current_user.role, minimum_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Higher access level required.")
        return current_user

    return _dependency


def get_current_support_user(current_user: User = Depends(require_minimum_role(SUPPORT_USER))) -> User:
    return current_user


def get_current_senior_support_user(current_user: User = Depends(require_minimum_role(SENIOR_SUPPORT_USER))) -> User:
    return current_user


def get_current_active_admin(current_user: User = Depends(require_minimum_role(ADMINISTRATION_USER))) -> User:
    return current_user


def get_current_system_manager(current_user: User = Depends(require_minimum_role(SYSTEM_MANAGER))) -> User:
    return current_user
