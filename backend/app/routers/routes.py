from __future__ import annotations

import base64
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_active_user
from app.models import SavedGpxFile, SavedRoute, User
from app.schemas import (
    ManualRouteCreateRequest,
    ManualRoutePreviewRead,
    ManualRoutePreviewRequest,
    RefreshWeatherRequest,
    RouteRead,
    RouteSummaryRead,
)
from app.services.gpx_service import generate_gpx_bytes, parse_gpx_file
from app.services.route_sampling_service import build_route_geojson, compact_key_points, compact_sampled_points
from app.services.routing_service import ManualWaypoint, routing_service
from app.services.trip_planning_service import TripPlanningOptions, build_trip_plan, parse_time_input
from app.services.weather_service import weather_service
from app.utils.datetime_utils import parse_client_datetime
from app.config import get_settings


router = APIRouter(prefix="/routes", tags=["routes"])
settings = get_settings()
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)


def _serialize_route(route: SavedRoute) -> RouteRead:
    sampled_points = route.sampled_points_json or []
    total_distance = 0.0
    if sampled_points:
        total_distance = sampled_points[-1]["distance_from_start_km"]
    trip_plan = route.route_geojson.get("properties", {}).get("trip_plan")

    return RouteRead(
        id=route.id,
        name=route.name,
        start_time=route.start_time,
        speed_kmh=route.speed_kmh,
        sample_interval_minutes=route.sample_interval_minutes,
        total_distance_km=total_distance,
        sampled_points_count=len(sampled_points),
        created_at=route.created_at,
        route_geojson=route.route_geojson,
        sampled_points=sampled_points,
        key_points=route.key_points_json,
        trip_plan=trip_plan,
    )


def _get_owned_route(session: Session, route_id: int, user_id: int) -> SavedRoute:
    route = session.exec(
        select(SavedRoute).where(SavedRoute.id == route_id, SavedRoute.user_id == user_id)
    ).first()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found.")
    return route


def _build_key_point_indices(sampled_points: list[dict], requested_indices: list[int] | None = None) -> list[int]:
    requested_indices = requested_indices or []
    valid_requested = [index for index in requested_indices if 0 <= index < len(sampled_points)]
    return sorted({0, len(sampled_points) - 1, *valid_requested})


def _build_custom_key_point_specs(sampled_points: list[dict], requested_indices: list[int]) -> list[dict]:
    specs: list[dict] = []
    for sample_index in requested_indices:
        point = sampled_points[sample_index]
        specs.append(
            {
                "label": f"Custom point {sample_index + 1}",
                "category": "custom",
                "sample_index": sample_index,
                "latitude": point["latitude"],
                "longitude": point["longitude"],
                "arrival_time": point["timestamp"],
                "distance_from_start_km": point["distance_from_start_km"],
                "details": {},
            }
        )
    return specs


def _get_owned_gpx_file(session: Session, gpx_file_id: int, user_id: int) -> SavedGpxFile:
    gpx_file = session.exec(
        select(SavedGpxFile).where(SavedGpxFile.id == gpx_file_id, SavedGpxFile.user_id == user_id)
    ).first()
    if not gpx_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved GPX file not found.")
    return gpx_file


def _slugify_filename(value: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "routeweather-route"


def _build_route_export_payload(route: SavedRoute) -> dict:
    gpx_package = None
    gpx_path = Path(route.gpx_file_path)
    if gpx_path.exists():
        gpx_package = {
            "filename": gpx_path.name,
            "content_base64": base64.b64encode(gpx_path.read_bytes()).decode("utf-8"),
        }

    return {
        "format": "routeweather-route-package",
        "version": 1,
        "route": {
            "name": route.name,
            "start_time": route.start_time.isoformat(),
            "speed_kmh": route.speed_kmh,
            "sample_interval_minutes": route.sample_interval_minutes,
            "route_geojson": route.route_geojson,
            "sampled_points": route.sampled_points_json,
            "key_points": route.key_points_json,
            "trip_plan": route.route_geojson.get("properties", {}).get("trip_plan"),
            "gpx_package": gpx_package,
        },
    }


@router.get("", response_model=list[RouteSummaryRead])
def list_routes(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> list[RouteSummaryRead]:
    routes = session.exec(
        select(SavedRoute)
        .where(SavedRoute.user_id == current_user.id)
        .order_by(SavedRoute.created_at.desc())
    ).all()

    return [
        RouteSummaryRead(
            id=route.id,
            name=route.name,
            start_time=route.start_time,
            speed_kmh=route.speed_kmh,
            sample_interval_minutes=route.sample_interval_minutes,
            total_distance_km=(route.sampled_points_json or [{}])[-1].get("distance_from_start_km", 0.0),
            sampled_points_count=len(route.sampled_points_json or []),
            created_at=route.created_at,
        )
        for route in routes
    ]


@router.post("/upload", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
async def upload_route(
    name: str = Form(...),
    start_time: str = Form(...),
    speed_kmh: float = Form(...),
    sample_interval_minutes: int = Form(...),
    overnight_camps_enabled: bool = Form(False),
    target_distance_per_day_km: float | None = Form(default=None),
    target_time_to_camp: str | None = Form(default=None),
    target_time_to_destination: str | None = Form(default=None),
    plan_lunch_stops: bool = Form(False),
    lunch_rest_minutes: int = Form(default=0),
    avoid_camp_after_sunset: bool = Form(False),
    saved_gpx_file_id: int | None = Form(default=None),
    selected_sample_indices: str | None = Form(default=None),
    gpx_file: UploadFile | None = File(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> RouteRead:
    if not name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Route name is required.")

    try:
        parsed_start_time = parse_client_datetime(start_time)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid start time.") from exc

    if not saved_gpx_file_id and not gpx_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please choose a saved GPX file or upload a new GPX file.",
        )

    source_filename = None
    if saved_gpx_file_id:
        saved_gpx = _get_owned_gpx_file(session, saved_gpx_file_id, current_user.id)
        file_bytes = Path(saved_gpx.file_path).read_bytes()
        source_filename = saved_gpx.original_filename
    else:
        if not gpx_file or not (gpx_file.filename or "").lower().endswith(".gpx"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a GPX file.")
        file_bytes = await gpx_file.read()
        source_filename = gpx_file.filename

    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded GPX file is empty.")

    try:
        route_points = parse_gpx_file(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    requested_indices = _parse_selected_sample_indices(selected_sample_indices)
    route_geojson, enriched_points, key_points = await _build_processed_route_payload(
        route_points=route_points,
        start_time=parsed_start_time,
        speed_kmh=speed_kmh,
        sample_interval_minutes=sample_interval_minutes,
        planning_options=TripPlanningOptions(
            overnight_camps_enabled=overnight_camps_enabled,
            target_distance_per_day_km=target_distance_per_day_km,
            target_time_to_camp=parse_time_input(target_time_to_camp),
            target_time_to_destination=parse_time_input(target_time_to_destination),
            plan_lunch_stops=plan_lunch_stops,
            lunch_rest_minutes=lunch_rest_minutes,
            avoid_camp_after_sunset=avoid_camp_after_sunset,
        ),
        requested_indices=requested_indices,
    )

    file_path = upload_dir / f"user-{current_user.id}-route-{uuid4()}.gpx"
    file_path.write_bytes(file_bytes)

    saved_route = SavedRoute(
        user_id=current_user.id,
        name=name.strip(),
        gpx_file_path=str(file_path),
        start_time=parsed_start_time,
        speed_kmh=speed_kmh,
        sample_interval_minutes=sample_interval_minutes,
        route_geojson=route_geojson,
        sampled_points_json=enriched_points,
        key_points_json=key_points,
    )
    session.add(saved_route)
    session.commit()
    session.refresh(saved_route)
    return _serialize_route(saved_route)


@router.post("/manual-preview", response_model=ManualRoutePreviewRead)
async def preview_manual_route(
    payload: ManualRoutePreviewRequest,
    current_user: User = Depends(get_current_active_user),
) -> ManualRoutePreviewRead:
    del current_user
    try:
        route_points = await routing_service.build_walking_route(
            _to_manual_waypoints(payload.waypoints),
            mode=payload.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    route_geojson = build_route_geojson(route_points)
    return ManualRoutePreviewRead(
        route_geojson=route_geojson,
        total_distance_km=route_geojson["properties"]["total_distance_km"],
        point_count=route_geojson["properties"]["point_count"],
    )


@router.post("/manual", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
async def create_manual_route(
    payload: ManualRouteCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> RouteRead:
    try:
        route_points = await routing_service.build_walking_route(
            _to_manual_waypoints(payload.waypoints),
            mode=payload.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    route_geojson, enriched_points, key_points = await _build_processed_route_payload(
        route_points=route_points,
        start_time=payload.start_time,
        speed_kmh=payload.speed_kmh,
        sample_interval_minutes=payload.sample_interval_minutes,
        planning_options=TripPlanningOptions(
            overnight_camps_enabled=payload.overnight_camps_enabled,
            target_distance_per_day_km=payload.target_distance_per_day_km,
            target_time_to_camp=parse_time_input(payload.target_time_to_camp),
            target_time_to_destination=parse_time_input(payload.target_time_to_destination),
            plan_lunch_stops=payload.plan_lunch_stops,
            lunch_rest_minutes=payload.lunch_rest_minutes,
            avoid_camp_after_sunset=payload.avoid_camp_after_sunset,
        ),
        requested_indices=payload.selected_sample_indices,
    )

    file_path = upload_dir / f"user-{current_user.id}-manual-route-{uuid4()}.gpx"
    file_path.write_bytes(generate_gpx_bytes(route_points, payload.name))

    saved_route = SavedRoute(
        user_id=current_user.id,
        name=payload.name.strip(),
        gpx_file_path=str(file_path),
        start_time=payload.start_time,
        speed_kmh=payload.speed_kmh,
        sample_interval_minutes=payload.sample_interval_minutes,
        route_geojson=route_geojson,
        sampled_points_json=enriched_points,
        key_points_json=key_points,
    )
    session.add(saved_route)
    session.commit()
    session.refresh(saved_route)
    return _serialize_route(saved_route)


@router.get("/{route_id}/export")
def export_route(
    route_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    route = _get_owned_route(session, route_id, current_user.id)
    payload = _build_route_export_payload(route)
    filename = f"{_slugify_filename(route.name)}.routeweather.json"
    return Response(
        content=json.dumps(payload, separators=(",", ":")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
async def import_route(
    route_file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> RouteRead:
    file_bytes = await route_file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded route file is empty.")

    try:
        payload = json.loads(file_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid route package file.") from exc

    if payload.get("format") != "routeweather-route-package":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported route package format.")

    route_payload = payload.get("route", {})
    try:
        route_name = str(route_payload["name"]).strip()
        start_time = parse_client_datetime(route_payload["start_time"])
        speed_kmh = float(route_payload["speed_kmh"])
        sample_interval_minutes = int(route_payload["sample_interval_minutes"])
        route_geojson = route_payload["route_geojson"]
        sampled_points = route_payload["sampled_points"]
        key_points = route_payload["key_points"]
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Route package is missing required data.") from exc

    gpx_package = route_payload.get("gpx_package")
    stored_path = upload_dir / f"user-{current_user.id}-imported-route-{uuid4()}.gpx"
    if gpx_package and gpx_package.get("content_base64"):
        try:
            stored_path.write_bytes(base64.b64decode(gpx_package["content_base64"]))
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Route package GPX data is invalid.") from exc
        gpx_file_path = str(stored_path)
    else:
        gpx_file_path = "imported-route-package"

    saved_route = SavedRoute(
        user_id=current_user.id,
        name=route_name or "Imported route",
        gpx_file_path=gpx_file_path,
        start_time=start_time,
        speed_kmh=speed_kmh,
        sample_interval_minutes=sample_interval_minutes,
        route_geojson=route_geojson,
        sampled_points_json=sampled_points,
        key_points_json=key_points,
    )
    session.add(saved_route)
    session.commit()
    session.refresh(saved_route)
    return _serialize_route(saved_route)


@router.get("/{route_id}", response_model=RouteRead)
def get_route(
    route_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> RouteRead:
    route = _get_owned_route(session, route_id, current_user.id)
    return _serialize_route(route)


@router.delete("/{route_id}")
def delete_route(
    route_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    route = _get_owned_route(session, route_id, current_user.id)
    file_path = Path(route.gpx_file_path)
    session.delete(route)
    session.commit()
    file_path.unlink(missing_ok=True)
    return {"status": "deleted"}


@router.post("/{route_id}/refresh-weather", response_model=RouteRead)
async def refresh_weather(
    route_id: int,
    payload: RefreshWeatherRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> RouteRead:
    route = _get_owned_route(session, route_id, current_user.id)
    enriched_points = await weather_service.enrich_sampled_points(route.sampled_points_json)
    trip_plan = route.route_geojson.get("properties", {}).get("trip_plan", {})
    planned_stop_specs = trip_plan.get("planned_stops", [])
    if not planned_stop_specs:
        key_indices = _build_key_point_indices(enriched_points, payload.sample_indices)
        route.sampled_points_json = compact_sampled_points(enriched_points)
        route.key_points_json = compact_key_points(await weather_service.build_key_points(enriched_points, key_indices))
        session.add(route)
        session.commit()
        session.refresh(route)
        return _serialize_route(route)

    custom_indices = {
        point["sample_index"]
        for point in route.key_points_json
        if point.get("category") == "custom"
    }
    custom_indices.update(payload.sample_indices)
    custom_specs = _build_custom_key_point_specs(
        enriched_points,
        [
            index
            for index in sorted(custom_indices)
            if index not in {spec["sample_index"] for spec in planned_stop_specs}
        ],
    )
    route.sampled_points_json = compact_sampled_points(enriched_points)
    route.key_points_json = compact_key_points(
        await weather_service.build_key_points_from_specs([*planned_stop_specs, *custom_specs])
    )
    session.add(route)
    session.commit()
    session.refresh(route)
    return _serialize_route(route)


def _parse_selected_sample_indices(selected_sample_indices: str | None) -> list[int]:
    if not selected_sample_indices:
        return []
    try:
        return [int(index) for index in json.loads(selected_sample_indices)]
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="selected_sample_indices must be a JSON array of integers.",
        ) from exc


async def _build_processed_route_payload(
    *,
    route_points,
    start_time,
    speed_kmh: float,
    sample_interval_minutes: int,
    planning_options: TripPlanningOptions,
    requested_indices: list[int],
) -> tuple[dict, list[dict], list[dict]]:
    try:
        trip_plan_result = await build_trip_plan(
            route_points,
            start_time,
            speed_kmh,
            sample_interval_minutes,
            planning_options,
            sunset_lookup=weather_service.get_sunset_for_date,
        )
        sampled_points = trip_plan_result["sampled_points"]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    enriched_points = await weather_service.enrich_sampled_points(sampled_points)
    trip_plan = {
        "options": trip_plan_result["options"],
        "daily_legs": trip_plan_result["daily_legs"],
        "planned_stops": trip_plan_result["planned_stops"],
    }
    planned_stop_specs = trip_plan["planned_stops"]
    custom_specs = _build_custom_key_point_specs(
        enriched_points,
        [index for index in requested_indices if index not in {spec["sample_index"] for spec in planned_stop_specs}],
    )
    key_points = await weather_service.build_key_points_from_specs([*planned_stop_specs, *custom_specs])
    return (
        build_route_geojson(route_points, {"trip_plan": trip_plan}),
        compact_sampled_points(enriched_points),
        compact_key_points(key_points),
    )


def _to_manual_waypoints(waypoints: list) -> list[ManualWaypoint]:
    return [ManualWaypoint(latitude=point.latitude, longitude=point.longitude) for point in waypoints]
