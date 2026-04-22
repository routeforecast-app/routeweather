from __future__ import annotations

from datetime import date, datetime, time, timezone

import pytest

from app.services.gpx_service import parse_gpx_file
from app.services.trip_planning_service import TripPlanningOptions, build_trip_plan


GPX_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="RouteWeather Test">
  <trk>
    <name>Long Test Route</name>
    <trkseg>
      <trkpt lat="51.5000" lon="-0.1200"></trkpt>
      <trkpt lat="51.5200" lon="-0.1000"></trkpt>
      <trkpt lat="51.5400" lon="-0.0800"></trkpt>
      <trkpt lat="51.5600" lon="-0.0600"></trkpt>
      <trkpt lat="51.5800" lon="-0.0400"></trkpt>
      <trkpt lat="51.6000" lon="-0.0200"></trkpt>
      <trkpt lat="51.6200" lon="0.0000"></trkpt>
    </trkseg>
  </trk>
</gpx>
"""


async def _fixed_sunset(_: float, __: float, target_date: date) -> datetime:
    return datetime.combine(target_date, time(18, 30), tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_build_trip_plan_creates_camps_and_lunch_stops():
    route_points = parse_gpx_file(GPX_SAMPLE)

    trip_plan = await build_trip_plan(
        route_points,
        datetime(2026, 4, 22, 8, 0, tzinfo=timezone.utc),
        speed_kmh=5.0,
        sample_interval_minutes=30,
        options=TripPlanningOptions(
            overnight_camps_enabled=True,
            target_distance_per_day_km=8.0,
            target_time_to_camp=time(17, 0),
            target_time_to_destination=time(15, 0),
            plan_lunch_stops=True,
            lunch_rest_minutes=45,
            avoid_camp_after_sunset=True,
        ),
        sunset_lookup=_fixed_sunset,
    )

    planned_stops = trip_plan["planned_stops"]
    categories = [stop["category"] for stop in planned_stops]

    assert "start" in categories
    assert "lunch" in categories
    assert "camp" in categories
    assert "destination" in categories
    assert len(trip_plan["daily_legs"]) >= 2
    assert trip_plan["sampled_points"][-1]["distance_from_start_km"] == pytest.approx(
        round(route_points[-1].cumulative_distance_km, 3)
    )
