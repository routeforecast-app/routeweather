from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False)
    password_hash: str = Field(nullable=False)
    role: str = Field(default="general_user", nullable=False, index=True)
    is_admin: bool = Field(default=False, nullable=False, index=True)
    must_change_password: bool = Field(default=False, nullable=False)
    admin_password_compliant: bool = Field(default=False, nullable=False)
    first_name: str | None = Field(default=None, nullable=True, index=True)
    last_name: str | None = Field(default=None, nullable=True, index=True)
    phone_number_encrypted: str | None = Field(default=None, nullable=True)
    phone_number_hash: str | None = Field(default=None, nullable=True, index=True)
    distance_unit: str = Field(default="km", nullable=False)
    temperature_unit: str = Field(default="c", nullable=False)
    time_format: str = Field(default="24h", nullable=False)
    account_status: str = Field(default="active", nullable=False, index=True)
    last_login_at: datetime | None = Field(default=None, nullable=True, index=True)
    last_active_at: datetime | None = Field(default=None, nullable=True, index=True)
    deactivated_at: datetime | None = Field(default=None, nullable=True, index=True)
    scheduled_deletion_at: datetime | None = Field(default=None, nullable=True, index=True)
    deactivation_reason: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)

    routes: list["SavedRoute"] = Relationship(back_populates="user")
    gpx_files: list["SavedGpxFile"] = Relationship(back_populates="user")


class AdminEmail(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False)
    role: str = Field(default="administration_user", nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class LegalDocument(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    document_type: str = Field(index=True, unique=True, nullable=False)
    title: str = Field(nullable=False)
    body: str = Field(nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class SiteVisit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    path: str = Field(nullable=False, index=True)
    country_code: str = Field(default="unknown", nullable=False, index=True)
    visitor_hash: str | None = Field(default=None, nullable=True, index=True)
    user_agent: str | None = Field(default=None, nullable=True)
    referrer: str | None = Field(default=None, nullable=True)
    timezone: str | None = Field(default=None, nullable=True)
    language: str | None = Field(default=None, nullable=True)
    visited_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class DeletedAccountRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False)
    prior_account_status: str = Field(nullable=False, index=True)
    deletion_reason: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(nullable=False)
    last_login_at: datetime | None = Field(default=None, nullable=True, index=True)
    last_active_at: datetime | None = Field(default=None, nullable=True, index=True)
    deleted_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class PasswordResetToken(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    delivery_email: str = Field(nullable=False, index=True)
    token_hash: str = Field(nullable=False, unique=True, index=True)
    created_by_user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    created_by_role: str | None = Field(default=None, nullable=True, index=True)
    purpose: str = Field(default="password_reset", nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    expires_at: datetime = Field(nullable=False, index=True)
    used_at: datetime | None = Field(default=None, nullable=True, index=True)


class SupportAuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actor_user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    actor_email: str = Field(nullable=False, index=True)
    actor_role: str = Field(nullable=False, index=True)
    action: str = Field(nullable=False, index=True)
    target_user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    target_email: str | None = Field(default=None, nullable=True, index=True)
    details_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class SavedGpxFile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    name: str = Field(nullable=False, index=True)
    original_filename: str = Field(nullable=False)
    file_path: str = Field(nullable=False)
    total_distance_km: float = Field(nullable=False)
    point_count: int = Field(nullable=False)
    uploaded_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    user: User | None = Relationship(back_populates="gpx_files")


class SavedRoute(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    name: str = Field(nullable=False, index=True)
    gpx_file_path: str = Field(nullable=False)
    start_time: datetime = Field(nullable=False, index=True)
    speed_kmh: float = Field(nullable=False)
    sample_interval_minutes: int = Field(nullable=False)
    route_geojson: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    sampled_points_json: list[dict[str, Any]] = Field(sa_column=Column(JSON, nullable=False))
    key_points_json: list[dict[str, Any]] = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    user: User | None = Relationship(back_populates="routes")
