from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

import gpxpy
import gpxpy.gpx


EARTH_RADIUS_KM = 6371.0


@dataclass(slots=True)
class RoutePoint:
    index: int
    latitude: float
    longitude: float
    elevation: float | None
    cumulative_distance_km: float


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in kilometers."""

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    start_lat = radians(lat1)
    end_lat = radians(lat2)

    a = sin(d_lat / 2) ** 2 + cos(start_lat) * cos(end_lat) * sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def parse_gpx_file(file_bytes: bytes) -> list[RoutePoint]:
    """Parse GPX bytes into an ordered route with cumulative distances."""

    try:
        gpx = gpxpy.parse(file_bytes.decode("utf-8-sig"))
    except Exception as exc:  # pragma: no cover - depends on parser internals
        raise ValueError("The uploaded GPX file could not be parsed.") from exc

    raw_points: list[tuple[float, float, float | None]] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                raw_points.append((point.latitude, point.longitude, point.elevation))

    if len(raw_points) < 2:
        raise ValueError("The GPX route must contain at least two track points.")

    parsed_points: list[RoutePoint] = []
    cumulative_distance = 0.0

    for index, (latitude, longitude, elevation) in enumerate(raw_points):
        if index > 0:
            previous = raw_points[index - 1]
            cumulative_distance += haversine_distance_km(previous[0], previous[1], latitude, longitude)

        parsed_points.append(
            RoutePoint(
                index=index,
                latitude=latitude,
                longitude=longitude,
                elevation=elevation,
                cumulative_distance_km=round(cumulative_distance, 6),
            )
        )

    if parsed_points[-1].cumulative_distance_km <= 0:
        raise ValueError("The GPX route distance is too short to sample.")

    return parsed_points


def build_route_points_from_coordinates(
    coordinates: list[tuple[float, float]],
    *,
    elevations: list[float | None] | None = None,
) -> list[RoutePoint]:
    """Build RoutePoint objects from a sequence of latitude/longitude coordinates."""

    if len(coordinates) < 2:
        raise ValueError("A route must contain at least two coordinates.")

    parsed_points: list[RoutePoint] = []
    cumulative_distance = 0.0

    for index, (latitude, longitude) in enumerate(coordinates):
        elevation = elevations[index] if elevations and index < len(elevations) else None
        if index > 0:
            previous_latitude, previous_longitude = coordinates[index - 1]
            cumulative_distance += haversine_distance_km(
                previous_latitude,
                previous_longitude,
                latitude,
                longitude,
            )

        parsed_points.append(
            RoutePoint(
                index=index,
                latitude=float(latitude),
                longitude=float(longitude),
                elevation=elevation,
                cumulative_distance_km=round(cumulative_distance, 6),
            )
        )

    if parsed_points[-1].cumulative_distance_km <= 0:
        raise ValueError("The route distance is too short to sample.")

    return parsed_points


def generate_gpx_bytes(points: list[RoutePoint], route_name: str) -> bytes:
    """Generate GPX bytes from route points for export or manual route storage."""

    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack(name=route_name.strip() or "RouteForcast route")
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for point in points:
        segment.points.append(
            gpxpy.gpx.GPXTrackPoint(
                latitude=point.latitude,
                longitude=point.longitude,
                elevation=point.elevation,
            )
        )

    return gpx.to_xml().encode("utf-8")
