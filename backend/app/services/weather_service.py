from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.utils.datetime_utils import ceil_to_hour, ensure_aware_datetime, floor_to_hour


WEATHER_CODE_SUMMARIES = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


@dataclass(slots=True)
class HourlyWeather:
    timestamp: datetime
    temperature_c: float | None
    precipitation_probability: float | None
    precipitation_mm: float | None
    wind_speed_kph: float | None
    cloud_cover_percent: float | None
    weather_code: int | None

    @property
    def summary(self) -> str:
        return WEATHER_CODE_SUMMARIES.get(self.weather_code, "Unknown conditions")

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "temperature_c": self.temperature_c,
            "precipitation_probability": self.precipitation_probability,
            "precipitation_mm": self.precipitation_mm,
            "wind_speed_kph": self.wind_speed_kph,
            "cloud_cover_percent": self.cloud_cover_percent,
            "weather_code": self.weather_code,
            "summary": self.summary,
        }


class WeatherService:
    """Encapsulates all Open-Meteo calls and response normalization."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._cache: dict[str, tuple[datetime, list[HourlyWeather]]] = {}
        self._sunset_cache: dict[str, tuple[datetime, datetime | None]] = {}

    def _cache_key(self, latitude: float, longitude: float, start: datetime, end: datetime) -> str:
        return (
            f"{round(latitude, 3)}:{round(longitude, 3)}:"
            f"{start.date().isoformat()}:{end.date().isoformat()}"
        )

    async def _fetch_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
        start: datetime,
        end: datetime,
    ) -> list[HourlyWeather]:
        start = ensure_aware_datetime(start)
        end = ensure_aware_datetime(end)
        cache_key = self._cache_key(latitude, longitude, start, end)
        now = datetime.now(timezone.utc)
        cached = self._cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "precipitation_probability",
                    "precipitation",
                    "wind_speed_10m",
                    "cloud_cover",
                    "weather_code",
                ]
            ),
            "timezone": "UTC",
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(self.settings.open_meteo_base_url, params=params)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError:
                return []

        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        results: list[HourlyWeather] = []
        for index, timestamp in enumerate(times):
            results.append(
                HourlyWeather(
                    timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
                    temperature_c=_maybe_float(hourly.get("temperature_2m"), index),
                    precipitation_probability=_maybe_float(hourly.get("precipitation_probability"), index),
                    precipitation_mm=_maybe_float(hourly.get("precipitation"), index),
                    wind_speed_kph=_maybe_float(hourly.get("wind_speed_10m"), index),
                    cloud_cover_percent=_maybe_float(hourly.get("cloud_cover"), index),
                    weather_code=_maybe_int(hourly.get("weather_code"), index),
                )
            )

        expires_at = now + timedelta(minutes=self.settings.weather_cache_ttl_minutes)
        self._cache[cache_key] = (expires_at, results)
        return results

    async def get_weather_for_time(
        self,
        latitude: float,
        longitude: float,
        target_time: datetime,
    ) -> dict[str, Any]:
        """Return the closest hourly forecast to the requested time."""

        target_time = ensure_aware_datetime(target_time)
        hourly = await self._fetch_hourly_forecast(
            latitude,
            longitude,
            floor_to_hour(target_time - timedelta(hours=1)),
            ceil_to_hour(target_time + timedelta(hours=1)),
        )
        if not hourly:
            return {"summary": "Forecast unavailable"}

        closest = min(hourly, key=lambda item: abs(item.timestamp - target_time))
        tolerance = timedelta(minutes=self.settings.forecast_match_tolerance_minutes)
        if abs(closest.timestamp - target_time) > tolerance:
            return {"summary": "Forecast unavailable"}

        weather = closest.to_dict()
        weather.pop("timestamp", None)
        return weather

    async def get_rolling_24h_forecast(
        self,
        latitude: float,
        longitude: float,
        base_time: datetime,
    ) -> list[dict[str, Any]]:
        """Return the next 24 hourly forecast entries from the provided time."""

        base_time = ensure_aware_datetime(base_time)
        hourly = await self._fetch_hourly_forecast(
            latitude,
            longitude,
            floor_to_hour(base_time),
            ceil_to_hour(base_time + timedelta(hours=30)),
        )
        filtered = [item for item in hourly if item.timestamp >= floor_to_hour(base_time)]
        return [item.to_dict() for item in filtered[:24]]

    async def get_sunset_for_date(
        self,
        latitude: float,
        longitude: float,
        target_date: datetime.date,
    ) -> datetime | None:
        cache_key = f"{round(latitude, 3)}:{round(longitude, 3)}:{target_date.isoformat()}"
        now = datetime.now(timezone.utc)
        cached = self._sunset_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "sunset",
            "timezone": "UTC",
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(self.settings.open_meteo_base_url, params=params)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError:
                return None

        sunsets = payload.get("daily", {}).get("sunset", [])
        sunset = None
        if sunsets:
            sunset = datetime.fromisoformat(sunsets[0]).replace(tzinfo=timezone.utc)

        self._sunset_cache[cache_key] = (
            now + timedelta(minutes=self.settings.weather_cache_ttl_minutes),
            sunset,
        )
        return sunset

    async def enrich_sampled_points(self, sampled_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched_points: list[dict[str, Any]] = []
        for point in sampled_points:
            weather = await self.get_weather_for_time(
                point["latitude"],
                point["longitude"],
                datetime.fromisoformat(point["timestamp"]),
            )
            enriched = {**point, "weather": weather}
            enriched_points.append(enriched)
        return enriched_points

    async def build_key_points(
        self,
        sampled_points: list[dict[str, Any]],
        sample_indices: list[int],
    ) -> list[dict[str, Any]]:
        key_points: list[dict[str, Any]] = []
        for sample_index in sample_indices:
            point = sampled_points[sample_index]
            arrival_time = datetime.fromisoformat(point["timestamp"])
            key_points.append(
                {
                    "label": self._label_for_key_point(sample_index, sampled_points),
                    "sample_index": sample_index,
                    "latitude": point["latitude"],
                    "longitude": point["longitude"],
                    "arrival_time": point["timestamp"],
                    "forecast_24h": await self.get_rolling_24h_forecast(
                        point["latitude"],
                        point["longitude"],
                        arrival_time,
                    ),
                }
            )
        return key_points

    async def build_key_points_from_specs(
        self,
        point_specs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        key_points: list[dict[str, Any]] = []
        for spec in point_specs:
            arrival_time = datetime.fromisoformat(spec["arrival_time"])
            key_points.append(
                {
                    "label": spec["label"],
                    "category": spec.get("category", "custom"),
                    "sample_index": spec["sample_index"],
                    "latitude": spec["latitude"],
                    "longitude": spec["longitude"],
                    "arrival_time": spec["arrival_time"],
                    "distance_from_start_km": spec.get("distance_from_start_km"),
                    "details": spec.get("details", {}),
                    "forecast_24h": await self.get_rolling_24h_forecast(
                        spec["latitude"],
                        spec["longitude"],
                        arrival_time,
                    ),
                }
            )
        return key_points

    @staticmethod
    def _label_for_key_point(sample_index: int, sampled_points: list[dict[str, Any]]) -> str:
        if sample_index == 0:
            return "Route start"
        if sample_index == len(sampled_points) - 1:
            return "Route end"
        return f"Key point {sample_index + 1}"


def _maybe_float(values: Any, index: int) -> float | None:
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    return None if value is None else float(value)


def _maybe_int(values: Any, index: int) -> int | None:
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    return None if value is None else int(value)


weather_service = WeatherService()
