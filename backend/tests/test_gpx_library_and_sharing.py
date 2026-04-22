from __future__ import annotations

from pathlib import Path

from app.routers import routes as routes_router


GPX_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="RouteWeather Test">
  <trk>
    <name>Shared Route</name>
    <trkseg>
      <trkpt lat="51.5000" lon="-0.1200"></trkpt>
      <trkpt lat="51.5200" lon="-0.1000"></trkpt>
      <trkpt lat="51.5400" lon="-0.0800"></trkpt>
    </trkseg>
  </trk>
</gpx>
"""


async def _fake_enrich_sampled_points(sampled_points):
    return [
        {
            **point,
            "weather": {
                "temperature_c": 12.0,
                "precipitation_probability": 10.0,
                "precipitation_mm": 0.0,
                "wind_speed_kph": 8.0,
                "cloud_cover_percent": 20.0,
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
                    "temperature_c": 12.0,
                    "precipitation_probability": 10.0,
                    "precipitation_mm": 0.0,
                    "wind_speed_kph": 8.0,
                    "cloud_cover_percent": 20.0,
                    "weather_code": 1,
                    "summary": "Mostly clear",
                }
            ],
        }
        for spec in specs
    ]


def _register_user(client, email: str = "library@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Library",
            "last_name": "User",
            "phone_number": "+447700900123",
            "email": email,
            "password": "supersecure123",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_gpx_library_upload_download_delete(client):
    headers = _register_user(client)

    upload_response = client.post(
        "/gpx-files/upload",
        headers=headers,
        data={"name": "Weekend trail"},
        files={"gpx_file": ("weekend-trail.gpx", GPX_SAMPLE, "application/gpx+xml")},
    )
    assert upload_response.status_code == 201
    payload = upload_response.json()
    assert payload["name"] == "Weekend trail"
    assert payload["point_count"] == 3

    list_response = client.get("/gpx-files", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    download_response = client.get(f"/gpx-files/{payload['id']}/download", headers=headers)
    assert download_response.status_code == 200
    assert download_response.content == GPX_SAMPLE

    delete_response = client.delete(f"/gpx-files/{payload['id']}", headers=headers)
    assert delete_response.status_code == 204


def test_route_export_and_import_round_trip(client, monkeypatch):
    monkeypatch.setattr(routes_router.weather_service, "enrich_sampled_points", _fake_enrich_sampled_points)
    monkeypatch.setattr(routes_router.weather_service, "build_key_points_from_specs", _fake_build_key_points_from_specs)

    headers = _register_user(client, email="share-owner@example.com")

    create_response = client.post(
        "/routes/upload",
        headers=headers,
        data={
            "name": "Sharable route",
            "start_time": "2026-04-22T08:00:00+00:00",
            "speed_kmh": "5",
            "sample_interval_minutes": "30",
            "overnight_camps_enabled": "false",
            "plan_lunch_stops": "false",
            "avoid_camp_after_sunset": "false",
            "lunch_rest_minutes": "0",
        },
        files={"gpx_file": ("sharable.gpx", GPX_SAMPLE, "application/gpx+xml")},
    )
    assert create_response.status_code == 201
    route_id = create_response.json()["id"]

    export_response = client.get(f"/routes/{route_id}/export", headers=headers)
    assert export_response.status_code == 200
    assert "routeweather-route-package" in export_response.text

    import_headers = _register_user(client, email="receiver@example.com")
    import_response = client.post(
        "/routes/import",
        headers=import_headers,
        files={"route_file": ("shared.routeweather.json", export_response.content, "application/json")},
    )
    assert import_response.status_code == 201
    imported_payload = import_response.json()
    assert imported_payload["name"] == "Sharable route"
    assert imported_payload["route_geojson"]["geometry"]["type"] == "LineString"

    receiver_routes = client.get("/routes", headers=import_headers)
    assert receiver_routes.status_code == 200
    assert len(receiver_routes.json()) == 1
