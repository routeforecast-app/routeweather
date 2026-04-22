from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "RouteForcast API"
    api_prefix: str = ""
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    password_reset_token_expire_minutes: int = 60 * 2
    database_url: str = "sqlite:///./routeweather.db"
    upload_dir: str = str(BASE_DIR / "app" / "static_uploads")
    frontend_app_url: str = "http://127.0.0.1:5173"
    email_outbox_dir: str = str(BASE_DIR / "app" / "static_uploads" / "email_outbox")
    support_user_emails: list[str] = Field(default_factory=list)
    senior_support_user_emails: list[str] = Field(default_factory=list)
    administration_user_emails: list[str] = Field(default_factory=list)
    system_manager_emails: list[str] = Field(default_factory=lambda: ["jack.s.steele2007@icloud.com"])
    admin_emails: list[str] = Field(default_factory=list)
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    routing_base_url: str = "https://router.project-osrm.org"
    routing_profile: str = "foot"
    routing_timeout_seconds: float = 20.0
    manual_route_max_waypoints: int = 25
    stored_route_max_geometry_points: int = 500
    weather_cache_ttl_minutes: int = 30
    forecast_match_tolerance_minutes: int = 90

    def _normalize_emails(self, emails: list[str]) -> set[str]:
        return {email.strip().lower() for email in emails if email.strip()}

    @property
    def normalized_support_user_emails(self) -> set[str]:
        return self._normalize_emails(self.support_user_emails)

    @property
    def normalized_senior_support_user_emails(self) -> set[str]:
        return self._normalize_emails(self.senior_support_user_emails)

    @property
    def normalized_administration_user_emails(self) -> set[str]:
        return self._normalize_emails(self.administration_user_emails) | self._normalize_emails(self.admin_emails)

    @property
    def normalized_system_manager_emails(self) -> set[str]:
        return self._normalize_emails(self.system_manager_emails)


@lru_cache
def get_settings() -> Settings:
    return Settings()
