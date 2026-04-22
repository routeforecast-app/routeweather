from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone_number: str = Field(min_length=7, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str = "general_user"
    role_label: str = "General User"
    is_admin: bool = False
    must_change_password: bool = False
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    needs_support_profile: bool = False
    distance_unit: str = "km"
    temperature_unit: str = "c"
    time_format: str = "24h"
    account_status: str = "active"
    last_login_at: datetime | None = None
    last_active_at: datetime | None = None
    deactivated_at: datetime | None = None
    scheduled_deletion_at: datetime | None = None
    deactivation_reason: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class GenericMessageResponse(BaseModel):
    message: str


class UserPreferencesUpdate(BaseModel):
    distance_unit: str = Field(pattern="^(km|miles)$")
    temperature_unit: str = Field(pattern="^(c|f)$")
    time_format: str = Field(pattern="^(12h|24h)$")


class UserProfileUpdate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone_number: str = Field(min_length=7, max_length=32)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminStatsRead(BaseModel):
    total_users: int
    total_routes: int
    total_saved_gpx_files: int
    total_admin_users: int


class AdminGrantRequest(BaseModel):
    email: EmailStr


class RoleGrantRequest(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(support_user|senior_support_user|administration_user|system_manager)$")


class RoleGrantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    role_label: str
    created_at: datetime
    is_seeded: bool = False


class AccountLifecycleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    account_status: str
    status_label: str
    deletion_phase: str | None = None
    created_at: datetime
    last_login_at: datetime | None = None
    last_active_at: datetime | None = None
    deactivated_at: datetime | None = None
    scheduled_deletion_at: datetime | None = None
    deletion_reason: str | None = None
    deleted_at: datetime | None = None


class AdminUserEmailAction(BaseModel):
    email: EmailStr
    confirm_email: EmailStr
    reason: str | None = Field(default=None, max_length=500)


class AdminDeleteUserRequest(BaseModel):
    email: EmailStr
    confirm_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)


class FlaggedUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    created_at: datetime
    last_active_at: datetime | None = None
    last_login_at: datetime | None = None
    routes_created_total: int = 0
    routes_created_last_hour: int = 0
    visit_count_last_10_minutes: int = 0
    distinct_paths_last_10_minutes: int = 0
    flag_reasons: list[str] = Field(default_factory=list)


class AdminEmailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime
    is_seeded: bool = False


class SupportPasswordResetRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)


class SupportAccountRecoverySearchRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone_number: str = Field(min_length=7, max_length=32)


class SupportMatchedUserRead(BaseModel):
    user_id: int
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    is_paid_member: bool = False
    paid_member_status: str = "Not paid"
    role: str = "general_user"
    role_label: str = "General User"
    created_at: datetime
    last_active_at: datetime | None = None


class SupportEmailChangeRequest(BaseModel):
    user_id: int
    new_email: EmailStr


class SupportAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_email: EmailStr
    actor_role: str
    actor_role_label: str
    action: str
    target_email: EmailStr | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class VisitTrackRequest(BaseModel):
    path: str = Field(min_length=1, max_length=256)
    referrer: str | None = Field(default=None, max_length=512)
    timezone: str | None = Field(default=None, max_length=128)
    language: str | None = Field(default=None, max_length=64)


class DailyVisitCount(BaseModel):
    day: str
    visits: int


class CountryVisitCount(BaseModel):
    country_code: str
    visits: int


class PathVisitCount(BaseModel):
    path: str
    visits: int


class RecentVisitRead(BaseModel):
    path: str
    country_code: str
    visited_at: datetime
    user_email: EmailStr | None = None


class VisitAnalyticsRead(BaseModel):
    total_visits: int
    unique_visitors: int
    visits_last_7_days: int
    visits_last_30_days: int
    top_countries: list[CountryVisitCount]
    top_paths: list[PathVisitCount]
    daily_visits: list[DailyVisitCount]
    recent_visits: list[RecentVisitRead]


class LegalDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type: str
    title: str
    body: str
    updated_at: datetime


class LegalDocumentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)


class ManualWaypointRead(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ManualRoutePreviewRequest(BaseModel):
    mode: str = Field(pattern="^(endpoints|waypoints)$")
    waypoints: list[ManualWaypointRead] = Field(min_length=2, max_length=25)


class ManualRoutePreviewRead(BaseModel):
    route_geojson: dict[str, Any]
    total_distance_km: float
    point_count: int


class ManualRouteCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    start_time: datetime
    speed_kmh: float = Field(gt=0)
    sample_interval_minutes: int = Field(gt=0)
    overnight_camps_enabled: bool = False
    target_distance_per_day_km: float | None = None
    target_time_to_camp: str | None = None
    target_time_to_destination: str | None = None
    plan_lunch_stops: bool = False
    lunch_rest_minutes: int = 0
    avoid_camp_after_sunset: bool = False
    selected_sample_indices: list[int] = Field(default_factory=list)
    mode: str = Field(pattern="^(endpoints|waypoints)$")
    waypoints: list[ManualWaypointRead] = Field(min_length=2, max_length=25)


class WeatherSnapshot(BaseModel):
    temperature_c: float | None = None
    precipitation_probability: float | None = None
    precipitation_mm: float | None = None
    wind_speed_kph: float | None = None
    cloud_cover_percent: float | None = None
    weather_code: int | None = None
    summary: str


class HourlyForecastItem(BaseModel):
    timestamp: datetime
    temperature_c: float | None = None
    precipitation_probability: float | None = None
    precipitation_mm: float | None = None
    wind_speed_kph: float | None = None
    cloud_cover_percent: float | None = None
    weather_code: int | None = None
    summary: str


class SampledPointRead(BaseModel):
    index: int
    timestamp: datetime
    latitude: float
    longitude: float
    distance_from_start_km: float
    weather: WeatherSnapshot | None = None


class KeyPointRead(BaseModel):
    label: str
    category: str = "custom"
    sample_index: int
    latitude: float
    longitude: float
    arrival_time: datetime
    distance_from_start_km: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    forecast_24h: list[HourlyForecastItem]


class RouteSummaryRead(BaseModel):
    id: int
    name: str
    start_time: datetime
    speed_kmh: float
    sample_interval_minutes: int
    total_distance_km: float
    sampled_points_count: int
    created_at: datetime


class RouteRead(RouteSummaryRead):
    route_geojson: dict[str, Any]
    sampled_points: list[SampledPointRead]
    key_points: list[KeyPointRead]
    trip_plan: dict[str, Any] | None = None


class RefreshWeatherRequest(BaseModel):
    sample_indices: list[int] = Field(default_factory=list)


class SavedGpxFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    original_filename: str
    total_distance_km: float
    point_count: int
    uploaded_at: datetime
