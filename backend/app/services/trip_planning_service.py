from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Awaitable, Callable

from app.services.gpx_service import RoutePoint
from app.services.route_sampling_service import interpolate_point
from app.utils.datetime_utils import ensure_aware_datetime


SunsetLookup = Callable[[float, float, date], Awaitable[datetime | None]]


@dataclass(slots=True)
class TripPlanningOptions:
    overnight_camps_enabled: bool = False
    target_distance_per_day_km: float | None = None
    target_time_to_camp: time | None = None
    target_time_to_destination: time | None = None
    plan_lunch_stops: bool = False
    lunch_rest_minutes: int = 0
    avoid_camp_after_sunset: bool = False


def parse_time_input(value: str | None) -> time | None:
    if not value:
        return None
    return time.fromisoformat(value)


def validate_trip_planning_options(options: TripPlanningOptions, total_distance_km: float) -> None:
    if options.target_distance_per_day_km is not None and options.target_distance_per_day_km <= 0:
        raise ValueError("Target distance each day must be greater than zero.")

    if options.plan_lunch_stops and options.lunch_rest_minutes <= 0:
        raise ValueError("Lunch rest duration must be greater than zero when lunch stops are enabled.")

    if options.overnight_camps_enabled:
        if not options.target_distance_per_day_km:
            raise ValueError("Target distance each day is required when overnight camps are enabled.")
        if not options.target_time_to_camp:
            raise ValueError("Target time to camp is required when overnight camps are enabled.")
        if not options.target_time_to_destination:
            raise ValueError("Target time to destination is required when overnight camps are enabled.")


def _combine_with_time(reference: datetime, target_time: time) -> datetime:
    reference = ensure_aware_datetime(reference)
    return reference.replace(
        hour=target_time.hour,
        minute=target_time.minute,
        second=target_time.second,
        microsecond=0,
    )


def _next_occurrence_after(reference: datetime, target_time: time) -> datetime:
    candidate = _combine_with_time(reference, target_time)
    if candidate <= reference:
        candidate += timedelta(days=1)
    return candidate


def _travel_minutes(distance_km: float, speed_kmh: float) -> float:
    return (distance_km / speed_kmh) * 60


def _timestamp_for_distance(
    distance_km: float,
    daily_legs: list[dict[str, Any]],
    speed_kmh: float,
) -> datetime:
    for leg in daily_legs:
        start_distance = leg["start_distance_km"]
        end_distance = leg["end_distance_km"]
        if start_distance <= distance_km <= end_distance + 1e-9:
            travel_minutes = _travel_minutes(distance_km - start_distance, speed_kmh)
            timestamp = datetime.fromisoformat(leg["start_time"]) + timedelta(minutes=travel_minutes)
            lunch_distance = leg.get("lunch_distance_km")
            lunch_rest_minutes = leg.get("lunch_rest_minutes", 0)
            if lunch_distance is not None and distance_km > lunch_distance:
                timestamp += timedelta(minutes=lunch_rest_minutes)
            return timestamp

    last_leg = daily_legs[-1]
    return datetime.fromisoformat(last_leg["end_time"])


def _build_sampled_points_with_schedule(
    points: list[RoutePoint],
    daily_legs: list[dict[str, Any]],
    speed_kmh: float,
    sample_interval_minutes: int,
) -> list[dict[str, Any]]:
    total_distance_km = points[-1].cumulative_distance_km
    total_movement_minutes = _travel_minutes(total_distance_km, speed_kmh)

    movement_offsets: list[float] = []
    current_offset = 0.0
    while current_offset < total_movement_minutes:
        movement_offsets.append(round(current_offset, 6))
        current_offset += sample_interval_minutes

    if not movement_offsets or abs(movement_offsets[-1] - total_movement_minutes) > 0.001:
        movement_offsets.append(round(total_movement_minutes, 6))

    sampled_points: list[dict[str, Any]] = []
    for index, movement_minutes in enumerate(movement_offsets):
        distance_km = min(total_distance_km, speed_kmh * (movement_minutes / 60))
        latitude, longitude = interpolate_point(points, distance_km)
        timestamp = _timestamp_for_distance(distance_km, daily_legs, speed_kmh)
        sampled_points.append(
            {
                "index": index,
                "timestamp": timestamp.isoformat(),
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "distance_from_start_km": round(distance_km, 3),
                "weather": None,
            }
        )

    return sampled_points


def _nearest_sample_index(distance_km: float, sampled_points: list[dict[str, Any]]) -> int:
    return min(
        sampled_points,
        key=lambda point: abs(point["distance_from_start_km"] - distance_km),
    )["index"]


async def build_trip_plan(
    points: list[RoutePoint],
    start_time: datetime,
    speed_kmh: float,
    sample_interval_minutes: int,
    options: TripPlanningOptions,
    sunset_lookup: SunsetLookup | None = None,
) -> dict[str, Any]:
    """Build daily legs, planned stops, and sampled timestamps for multi-day route plans."""

    start_time = ensure_aware_datetime(start_time)
    total_distance_km = points[-1].cumulative_distance_km
    validate_trip_planning_options(options, total_distance_km)

    overnight_enabled = options.overnight_camps_enabled
    day_start_clock = start_time.timetz().replace(tzinfo=None)
    daily_target_distance = options.target_distance_per_day_km or total_distance_km
    lunch_enabled = options.plan_lunch_stops and options.lunch_rest_minutes > 0

    daily_legs: list[dict[str, Any]] = []
    planned_stops: list[dict[str, Any]] = []

    current_start_time = start_time
    current_start_distance = 0.0
    day_number = 1

    while current_start_distance < total_distance_km - 1e-6:
        desired_end_distance = min(total_distance_km, current_start_distance + daily_target_distance)
        target_clock = None
        if overnight_enabled:
            target_clock = (
                options.target_time_to_destination if desired_end_distance >= total_distance_km else options.target_time_to_camp
            )

        deadline = _next_occurrence_after(current_start_time, target_clock) if target_clock else None
        lunch_pause = timedelta(minutes=options.lunch_rest_minutes) if lunch_enabled else timedelta(0)
        effective_deadline = deadline
        sunset_time = None

        if options.avoid_camp_after_sunset and overnight_enabled and desired_end_distance < total_distance_km:
            provisional_latitude, provisional_longitude = interpolate_point(points, desired_end_distance)
            if sunset_lookup:
                sunset_time = await sunset_lookup(
                    provisional_latitude,
                    provisional_longitude,
                    current_start_time.date(),
                )
            if sunset_time:
                effective_deadline = min(deadline, sunset_time) if deadline else sunset_time

        actual_end_distance = desired_end_distance
        if effective_deadline:
            available_minutes = (effective_deadline - current_start_time - lunch_pause).total_seconds() / 60
            if available_minutes <= 0:
                raise ValueError("Planning inputs leave no travel time before the target stop deadline.")

            max_distance_by_deadline = current_start_distance + max(0.0, speed_kmh * (available_minutes / 60))
            actual_end_distance = min(desired_end_distance, total_distance_km, max_distance_by_deadline)
            if actual_end_distance <= current_start_distance + 0.01:
                raise ValueError("Planning inputs leave no meaningful progress before the target stop deadline.")

        segment_distance = actual_end_distance - current_start_distance
        lunch_distance = None
        lunch_arrival = None
        if lunch_enabled and segment_distance >= 1:
            lunch_distance = round(current_start_distance + (segment_distance / 2), 3)
            lunch_arrival = current_start_time + timedelta(
                minutes=_travel_minutes(lunch_distance - current_start_distance, speed_kmh)
            )

        end_arrival = current_start_time + timedelta(minutes=_travel_minutes(segment_distance, speed_kmh)) + lunch_pause
        reached_destination = actual_end_distance >= total_distance_km - 1e-6
        stop_category = "destination" if reached_destination else "camp"

        latitude, longitude = interpolate_point(points, actual_end_distance)
        leg_details = {
            "day_number": day_number,
            "start_time": current_start_time.isoformat(),
            "end_time": end_arrival.isoformat(),
            "start_distance_km": round(current_start_distance, 3),
            "end_distance_km": round(actual_end_distance, 3),
            "target_end_time": target_clock.isoformat(timespec="minutes") if target_clock else None,
            "effective_deadline": effective_deadline.isoformat() if effective_deadline else None,
            "end_type": stop_category,
            "lunch_distance_km": lunch_distance,
            "lunch_rest_minutes": options.lunch_rest_minutes if lunch_distance is not None else 0,
            "sunset_time": sunset_time.isoformat() if sunset_time else None,
        }
        daily_legs.append(leg_details)

        if day_number == 1:
            planned_stops.append(
                {
                    "label": "Route start",
                    "category": "start",
                    "latitude": points[0].latitude,
                    "longitude": points[0].longitude,
                    "arrival_time": start_time.isoformat(),
                    "distance_from_start_km": 0.0,
                    "details": {"day_number": 1},
                }
            )

        if lunch_distance is not None and lunch_arrival is not None:
            lunch_latitude, lunch_longitude = interpolate_point(points, lunch_distance)
            planned_stops.append(
                {
                    "label": f"Day {day_number} lunch stop",
                    "category": "lunch",
                    "latitude": round(lunch_latitude, 6),
                    "longitude": round(lunch_longitude, 6),
                    "arrival_time": lunch_arrival.isoformat(),
                    "distance_from_start_km": round(lunch_distance, 3),
                    "details": {
                        "day_number": day_number,
                        "rest_minutes": options.lunch_rest_minutes,
                    },
                }
            )

        planned_stops.append(
            {
                "label": "Route destination" if reached_destination else f"Camp night {day_number}",
                "category": stop_category,
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "arrival_time": end_arrival.isoformat(),
                "distance_from_start_km": round(actual_end_distance, 3),
                "details": {
                    "day_number": day_number,
                    "target_end_time": target_clock.isoformat(timespec="minutes") if target_clock else None,
                    "sunset_time": sunset_time.isoformat() if sunset_time else None,
                },
            }
        )

        current_start_distance = actual_end_distance
        if reached_destination:
            break

        current_start_time = _next_occurrence_after(end_arrival, day_start_clock)
        day_number += 1

    sampled_points = _build_sampled_points_with_schedule(points, daily_legs, speed_kmh, sample_interval_minutes)
    for stop in planned_stops:
        stop["sample_index"] = _nearest_sample_index(stop["distance_from_start_km"], sampled_points)

    return {
        "options": {
            "overnight_camps_enabled": options.overnight_camps_enabled,
            "target_distance_per_day_km": options.target_distance_per_day_km,
            "target_time_to_camp": options.target_time_to_camp.isoformat(timespec="minutes")
            if options.target_time_to_camp
            else None,
            "target_time_to_destination": options.target_time_to_destination.isoformat(timespec="minutes")
            if options.target_time_to_destination
            else None,
            "plan_lunch_stops": options.plan_lunch_stops,
            "lunch_rest_minutes": options.lunch_rest_minutes if options.plan_lunch_stops else 0,
            "avoid_camp_after_sunset": options.avoid_camp_after_sunset,
        },
        "daily_legs": daily_legs,
        "planned_stops": planned_stops,
        "sampled_points": sampled_points,
    }
