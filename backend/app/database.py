from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


settings = get_settings()

# This stays intentionally simple so swapping to Postgres later is mostly an
# environment-variable change plus installing a Postgres driver.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    _apply_lightweight_migrations()


def _apply_lightweight_migrations() -> None:
    """Keep local SQLite development databases usable without a full migration tool."""

    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "user" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("user")}
    statements: list[str] = []
    if "distance_unit" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN distance_unit VARCHAR NOT NULL DEFAULT 'km'")
    if "temperature_unit" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN temperature_unit VARCHAR NOT NULL DEFAULT 'c'")
    if "time_format" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN time_format VARCHAR NOT NULL DEFAULT '24h'")
    if "is_admin" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
    if "role" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN role VARCHAR NOT NULL DEFAULT 'general_user'")
    if "must_change_password" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0")
    if "admin_password_compliant" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN admin_password_compliant BOOLEAN NOT NULL DEFAULT 0")
    if "first_name" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN first_name VARCHAR NULL")
    if "last_name" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN last_name VARCHAR NULL")
    if "phone_number_encrypted" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN phone_number_encrypted VARCHAR NULL")
    if "phone_number_hash" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN phone_number_hash VARCHAR NULL")
    if "account_status" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN account_status VARCHAR NOT NULL DEFAULT 'active'")
    if "last_login_at" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN last_login_at TIMESTAMP NULL")
    if "last_active_at" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN last_active_at TIMESTAMP NULL")
    if "deactivated_at" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN deactivated_at TIMESTAMP NULL")
    if "scheduled_deletion_at" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN scheduled_deletion_at TIMESTAMP NULL")
    if "deactivation_reason" not in existing_columns:
        statements.append("ALTER TABLE user ADD COLUMN deactivation_reason VARCHAR NULL")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    if "adminemail" in table_names:
        admin_email_columns = {column["name"] for column in inspector.get_columns("adminemail")}
        admin_email_statements: list[str] = []
        if "role" not in admin_email_columns:
            admin_email_statements.append(
                "ALTER TABLE adminemail ADD COLUMN role VARCHAR NOT NULL DEFAULT 'administration_user'"
            )
        if admin_email_statements:
            with engine.begin() as connection:
                for statement in admin_email_statements:
                    connection.execute(text(statement))


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
