from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib

from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session, select

from app.auth import get_user_from_token
from app.database import get_session
from app.dependencies import get_current_active_admin
from app.models import SiteVisit, User
from app.services.account_lifecycle_service import touch_user_activity
from app.schemas import (
    CountryVisitCount,
    DailyVisitCount,
    PathVisitCount,
    RecentVisitRead,
    VisitAnalyticsRead,
    VisitTrackRequest,
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/visit", status_code=status.HTTP_202_ACCEPTED)
def track_visit(
    payload: VisitTrackRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    current_user = _get_optional_user(session, request)
    if current_user:
        touch_user_activity(session, current_user)
    client_ip = _extract_client_ip(request)
    visit = SiteVisit(
        user_id=current_user.id if current_user else None,
        path=_normalize_path(payload.path),
        country_code=_extract_country_code(request),
        visitor_hash=_hash_value(client_ip) if client_ip else None,
        user_agent=request.headers.get("user-agent"),
        referrer=payload.referrer,
        timezone=payload.timezone,
        language=payload.language or request.headers.get("accept-language"),
    )
    session.add(visit)
    session.commit()
    return {"status": "accepted"}


@router.get("/admin/summary", response_model=VisitAnalyticsRead)
def get_visit_analytics(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_active_admin),
) -> VisitAnalyticsRead:
    visits = session.exec(select(SiteVisit).order_by(SiteVisit.visited_at.desc())).all()
    normalized_visits = [_as_utc(visit) for visit in visits]
    now = datetime.now(timezone.utc)
    last_7 = now - timedelta(days=7)
    last_30 = now - timedelta(days=30)

    unique_visitors = {visit.visitor_hash for visit in normalized_visits if visit.visitor_hash}
    top_countries_counter = Counter(visit.country_code for visit in normalized_visits)
    top_paths_counter = Counter(visit.path for visit in normalized_visits)
    daily_counter = Counter(
        visit.visited_at.astimezone(timezone.utc).date().isoformat() for visit in normalized_visits
    )

    user_ids = {visit.user_id for visit in normalized_visits if visit.user_id is not None}
    users_by_id = {}
    if user_ids:
        users = session.exec(select(User).where(User.id.in_(user_ids))).all()
        users_by_id = {user.id: user.email for user in users}

    recent_visits = [
        RecentVisitRead(
            path=visit.path,
            country_code=visit.country_code,
            visited_at=visit.visited_at,
            user_email=users_by_id.get(visit.user_id),
        )
        for visit in normalized_visits[:20]
    ]

    daily_visits = [
        DailyVisitCount(day=day, visits=count)
        for day, count in sorted(daily_counter.items())[-14:]
    ]

    return VisitAnalyticsRead(
        total_visits=len(normalized_visits),
        unique_visitors=len(unique_visitors),
        visits_last_7_days=sum(1 for visit in normalized_visits if visit.visited_at >= last_7),
        visits_last_30_days=sum(1 for visit in normalized_visits if visit.visited_at >= last_30),
        top_countries=[
            CountryVisitCount(country_code=country_code, visits=count)
            for country_code, count in top_countries_counter.most_common(8)
        ],
        top_paths=[
            PathVisitCount(path=path, visits=count)
            for path, count in top_paths_counter.most_common(8)
        ],
        daily_visits=daily_visits,
        recent_visits=recent_visits,
    )


def _get_optional_user(session: Session, request: Request) -> User | None:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    return get_user_from_token(session, token)


def _normalize_path(path: str) -> str:
    normalized = path.strip() or "/"
    return normalized[:256]


def _extract_country_code(request: Request) -> str:
    possible_headers = [
        "cf-ipcountry",
        "x-country-code",
        "x-appengine-country",
        "cloudfront-viewer-country",
    ]
    for header_name in possible_headers:
        value = (request.headers.get(header_name) or "").strip()
        if value:
            return value.upper()[:16]
    return "LOCAL" if request.url.hostname in {"127.0.0.1", "localhost"} else "UNKNOWN"


def _extract_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return None


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _as_utc(visit: SiteVisit) -> SiteVisit:
    if visit.visited_at.tzinfo is None:
        visit.visited_at = visit.visited_at.replace(tzinfo=timezone.utc)
    return visit
