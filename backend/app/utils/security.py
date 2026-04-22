from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

from app.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ADMIN_PASSWORD_POLICY_MESSAGE = (
    "Administrator passwords must be at least 8 characters and include at least "
    "1 uppercase letter, 1 number, and 1 symbol."
)


@lru_cache
def get_fernet() -> Fernet:
    settings = get_settings()
    derived_key = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived_key))


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def password_meets_admin_policy(password: str) -> bool:
    has_min_length = len(password) >= 8
    has_uppercase = any(character.isupper() for character in password)
    has_number = any(character.isdigit() for character in password)
    has_symbol = any(not character.isalnum() for character in password)
    return has_min_length and has_uppercase and has_number and has_symbol


def encrypt_sensitive_value(value: str | None) -> str | None:
    if not value:
        return None
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_sensitive_value(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def normalize_phone_number(value: str) -> str:
    trimmed = value.strip()
    normalized = "".join(character for character in trimmed if character.isdigit() or character == "+")
    if normalized.startswith("00"):
        normalized = f"+{normalized[2:]}"
    if not normalized:
        raise ValueError("Phone number is required.")
    digits_only = "".join(character for character in normalized if character.isdigit())
    if len(digits_only) < 7:
        raise ValueError("Phone number must include at least 7 digits.")
    if normalized.count("+") > 1 or ("+" in normalized and not normalized.startswith("+")):
        raise ValueError("Phone number format is invalid.")
    return normalized


def hash_lookup_value(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()
