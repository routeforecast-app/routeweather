from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.services.gpx_service import RoutePoint, build_route_points_from_coordinates


settings = get_settings()


@dataclass(slots=True)
class ManualWaypoint:
    latitude: float
    longitude: float


class RoutingService:
    """Resolve walking routes between user-defined waypoints."""

    def __init__(self) -> None:
        self._cache: dict[str, list[RoutePoint]] = {}

    async def build_walking_route(
        self,
        waypoints: list[ManualWaypoint],
        *,
        mode: str,
    ) -> list[RoutePoint]:
        self._validate_waypoints(waypoints, mode)
        cache_key = self._cache_key(waypoints, mode)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        coordinates = ";".join(f"{point.longitude:.6f},{point.latitude:.6f}" for point in waypoints)
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }
        url = f"{settings.routing_base_url}/route/v1/{settings.routing_profile}/{coordinates}"

        async with httpx.AsyncClient(timeout=settings.routing_timeout_seconds) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as exc:
                raise ValueError("Could not build a walking route for those points right now.") from exc

        routes = payload.get("routes", [])
        if not routes:
            raise ValueError("No walking route could be found for those points.")

        geometry = routes[0].get("geometry", {})
        route_coordinates = geometry.get("coordinates", [])
        if len(route_coordinates) < 2:
            raise ValueError("No walking route could be found for those points.")

        route_points = build_route_points_from_coordinates(
            [(latitude, longitude) for longitude, latitude in route_coordinates]
        )
        self._cache[cache_key] = route_points
        return route_points

    @staticmethod
    def _validate_waypoints(waypoints: list[ManualWaypoint], mode: str) -> None:
        if len(waypoints) < 2:
            raise ValueError("Please provide at least two map points.")
        if len(waypoints) > settings.manual_route_max_waypoints:
            raise ValueError(
                f"Please use no more than {settings.manual_route_max_waypoints} points in one route."
            )
        if mode == "endpoints" and len(waypoints) != 2:
            raise ValueError("Quick walking mode needs exactly two end points.")
        if mode not in {"endpoints", "waypoints"}:
            raise ValueError("Unsupported manual route mode.")

    @staticmethod
    def _cache_key(waypoints: list[ManualWaypoint], mode: str) -> str:
        return "|".join(
            [mode, *[f"{round(point.latitude, 5)}:{round(point.longitude, 5)}" for point in waypoints]]
        )


routing_service = RoutingService()
