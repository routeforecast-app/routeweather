from __future__ import annotations

from bisect import bisect_left
from datetime import datetime, timedelta
from math import floor

from app.services.gpx_service import RoutePoint
from app.config import get_settings
from app.utils.datetime_utils import ensure_aware_datetime


settings = get_settings()


def _interpolate_value(start: float, end: float, fraction: float) -> float:
    return start + (end - start) * fraction


def interpolate_point(points: list[RoutePoint], distance_km: float) -> tuple[float, float]:
    """Find the latitude and longitude at a cumulative route distance."""

    distances = [point.cumulative_distance_km for point in points]
    position = bisect_left(distances, distance_km)

    if position <= 0:
        return points[0].latitude, points[0].longitude
    if position >= len(points):
        return points[-1].latitude, points[-1].longitude

    start = points[position - 1]
    end = points[position]
    segment_distance = end.cumulative_distance_km - start.cumulative_distance_km
    if segment_distance <= 0:
        return start.latitude, start.longitude

    fraction = (distance_km - start.cumulative_distance_km) / segment_distance
    latitude = _interpolate_value(start.latitude, end.latitude, fraction)
    longitude = _interpolate_value(start.longitude, end.longitude, fraction)
    return latitude, longitude


def sample_route(
    points: list[RoutePoint],
    start_time: datetime,
    speed_kmh: float,
    sample_interval_minutes: int,
) -> list[dict]:
    """Sample route positions at regular intervals using a constant travel speed."""

    if speed_kmh <= 0:
        raise ValueError("Average movement speed must be greater than zero.")
    if sample_interval_minutes <= 0:
        raise ValueError("Sampling interval must be greater than zero minutes.")

    start_time = ensure_aware_datetime(start_time)
    total_distance_km = points[-1].cumulative_distance_km
    total_hours = total_distance_km / speed_kmh
    total_minutes = total_hours * 60

    sample_offsets: list[float] = []
    current_offset = 0.0
    while current_offset < total_minutes:
        sample_offsets.append(round(current_offset, 6))
        current_offset += sample_interval_minutes

    if not sample_offsets or abs(sample_offsets[-1] - total_minutes) > 0.001:
        sample_offsets.append(round(total_minutes, 6))

    sampled_points: list[dict] = []
    for index, offset_minutes in enumerate(sample_offsets):
        distance_km = min(total_distance_km, speed_kmh * (offset_minutes / 60))
        latitude, longitude = interpolate_point(points, distance_km)
        sampled_points.append(
            {
                "index": index,
                "timestamp": (start_time + timedelta(minutes=offset_minutes)).isoformat(),
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "distance_from_start_km": round(distance_km, 3),
                "weather": None,
            }
        )

    return sampled_points


def build_route_geojson(points: list[RoutePoint], extra_properties: dict | None = None) -> dict:
    display_points = _downsample_route_points(points, settings.stored_route_max_geometry_points)
    properties = {
        "total_distance_km": round(points[-1].cumulative_distance_km, 2),
        "point_count": len(points),
    }
    if extra_properties:
        properties.update(extra_properties)

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [round(point.longitude, 5), round(point.latitude, 5)]
                for point in display_points
            ],
        },
        "properties": properties,
    }


def compact_sampled_points(sampled_points: list[dict]) -> list[dict]:
    return [
        {
            "index": point["index"],
            "timestamp": point["timestamp"],
            "latitude": round(float(point["latitude"]), 5),
            "longitude": round(float(point["longitude"]), 5),
            "distance_from_start_km": round(float(point["distance_from_start_km"]), 2),
            "weather": _compact_weather(point.get("weather")),
        }
        for point in sampled_points
    ]


def compact_key_points(key_points: list[dict]) -> list[dict]:
    compacted: list[dict] = []
    for point in key_points:
        compacted.append(
            {
                "label": point["label"],
                "category": point.get("category", "custom"),
                "sample_index": point["sample_index"],
                "latitude": round(float(point["latitude"]), 5),
                "longitude": round(float(point["longitude"]), 5),
                "arrival_time": point["arrival_time"],
                "distance_from_start_km": (
                    round(float(point["distance_from_start_km"]), 2)
                    if point.get("distance_from_start_km") is not None
                    else None
                ),
                "details": point.get("details", {}),
                "forecast_24h": [
                    {
                        "timestamp": forecast["timestamp"],
                        **_compact_weather(forecast),
                    }
                    for forecast in point.get("forecast_24h", [])
                ],
            }
        )
    return compacted


def _downsample_route_points(points: list[RoutePoint], max_points: int) -> list[RoutePoint]:
    if max_points <= 0 or len(points) <= max_points:
        return points

    if max_points == 1:
        return [points[0]]

    step = (len(points) - 1) / (max_points - 1)
    indices = {0, len(points) - 1}
    for item_index in range(1, max_points - 1):
        indices.add(floor(item_index * step))
    return [points[index] for index in sorted(indices)]


def _compact_weather(weather: dict | None) -> dict | None:
    if not weather:
        return weather

    compacted = dict(weather)
    for field in [
        "temperature_c",
        "precipitation_probability",
        "precipitation_mm",
        "wind_speed_kph",
        "cloud_cover_percent",
    ]:
        value = compacted.get(field)
        if value is not None:
            compacted[field] = round(float(value), 1)
    return compacted
