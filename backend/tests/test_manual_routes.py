from __future__ import annotations

from app.routers import routes as routes_router
from app.services.gpx_service import build_route_points_from_coordinates


async def _fake_manual_route(*_, **__):
    return build_route_points_from_coordinates(
        [
            (51.5000, -0.1200),
            (51.5050, -0.1150),
            (51.5100, -0.1100),
            (51.5200, -0.1000),
        ]
    )


async def _fake_enrich_sampled_points(sampled_points):
    return [
        {
            **point,
            "weather": {
                "temperature_c": 12.34,
                "precipitation_probability": 15.67,
                "precipitation_mm": 0.12,
                "wind_speed_kph": 8.91,
                "cloud_cover_percent": 21.23,
                "weather_code": 1,
                "summary": "Mostly clear",
            },
        }
        for point in sampled_points
    ]


async def _fake_build_key_points_from_specs(specs):
    return [
        {
            **spec,
            "forecast_24h": [
                {
                    "timestamp": spec["arrival_time"],
                    "temperature_c": 10.56,
                    "precipitation_probability": 20.22,
                    "precipitation_mm": 0.34,
                    "wind_speed_kph": 12.34,
                    "cloud_cover_percent": 45.67,
                    "weather_code": 1,
                    "summary": "Mostly clear",
                }
            ],
        }
        for spec in specs
    ]


def _register_user(client, email: str = "manual@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Manual",
            "last_name": "User",
            "phone_number": "+447700900123",
            "email": email,
            "password": "supersecure123",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_manual_route_preview_and_create(client, monkeypatch):
    monkeypatch.setattr(routes_router.routing_service, "build_walking_route", _fake_manual_route)
    monkeypatch.setattr(routes_router.weather_service, "enrich_sampled_points", _fake_enrich_sampled_points)
    monkeypatch.setattr(routes_router.weather_service, "build_key_points_from_specs", _fake_build_key_points_from_specs)

    headers = _register_user(client)

    preview_response = client.post(
        "/routes/manual-preview",
        headers=headers,
        json={
            "mode": "endpoints",
            "waypoints": [
                {"latitude": 51.5, "longitude": -0.12},
                {"latitude": 51.52, "longitude": -0.10},
            ],
        },
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["route_geojson"]["geometry"]["type"] == "LineString"
    assert preview_payload["point_count"] == 4

    create_response = client.post(
        "/routes/manual",
        headers=headers,
        json={
            "name": "Manual route",
            "start_time": "2026-04-22T08:00:00+00:00",
            "speed_kmh": 5,
            "sample_interval_minutes": 30,
            "mode": "waypoints",
            "waypoints": [
                {"latitude": 51.5, "longitude": -0.12},
                {"latitude": 51.505, "longitude": -0.115},
                {"latitude": 51.52, "longitude": -0.10},
            ],
        },
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["name"] == "Manual route"
    assert payload["route_geojson"]["geometry"]["type"] == "LineString"
    assert payload["sampled_points"][0]["weather"]["temperature_c"] == 12.3
    assert payload["key_points"][0]["forecast_24h"][0]["temperature_c"] == 10.6
