from __future__ import annotations

from datetime import datetime, timedelta, timezone


def ensure_aware_datetime(value: datetime) -> datetime:
    """Normalize datetimes to UTC-aware values."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_client_datetime(value: str) -> datetime:
    """Parse an ISO datetime string from the client and normalize to UTC."""

    return ensure_aware_datetime(datetime.fromisoformat(value))


def floor_to_hour(value: datetime) -> datetime:
    value = ensure_aware_datetime(value)
    return value.replace(minute=0, second=0, microsecond=0)


def ceil_to_hour(value: datetime) -> datetime:
    floored = floor_to_hour(value)
    if floored == ensure_aware_datetime(value):
        return floored
    return floored + timedelta(hours=1)
