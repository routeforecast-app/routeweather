from __future__ import annotations

from datetime import datetime, timezone

from app.services.gpx_service import build_route_points_from_coordinates, parse_gpx_file
from app.services.route_sampling_service import build_route_geojson, sample_route


GPX_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="RouteWeather Test">
  <trk>
    <name>Test Route</name>
    <trkseg>
      <trkpt lat="51.5000" lon="-0.1200"></trkpt>
      <trkpt lat="51.5010" lon="-0.1185"></trkpt>
      <trkpt lat="51.5020" lon="-0.1170"></trkpt>
      <trkpt lat="51.5030" lon="-0.1155"></trkpt>
    </trkseg>
  </trk>
</gpx>
"""


def test_parse_gpx_and_sample_route():
    route_points = parse_gpx_file(GPX_SAMPLE)
    assert len(route_points) == 4
    assert route_points[-1].cumulative_distance_km > 0

    sampled_points = sample_route(
        route_points,
        datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
        speed_kmh=5.0,
        sample_interval_minutes=15,
    )

    assert sampled_points[0]["distance_from_start_km"] == 0
    assert sampled_points[-1]["distance_from_start_km"] == round(route_points[-1].cumulative_distance_km, 3)
    assert sampled_points[-1]["timestamp"] > sampled_points[0]["timestamp"]


def test_build_geojson_contains_linestring():
    route_points = parse_gpx_file(GPX_SAMPLE)
    geojson = build_route_geojson(route_points)
    assert geojson["geometry"]["type"] == "LineString"
    assert len(geojson["geometry"]["coordinates"]) == len(route_points)


def test_build_geojson_downsamples_large_routes():
    coordinates = [(51.5 + index * 0.0001, -0.12 + index * 0.0001) for index in range(1200)]
    route_points = build_route_points_from_coordinates(coordinates)
    geojson = build_route_geojson(route_points)
    assert geojson["geometry"]["type"] == "LineString"
    assert len(geojson["geometry"]["coordinates"]) <= 500
    assert geojson["properties"]["point_count"] == 1200
