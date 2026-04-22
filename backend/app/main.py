from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth import seed_admin_emails
from app.content import seed_legal_documents
from app.config import get_settings
from app.database import engine
from app.database import create_db_and_tables
from app.routers import analytics, auth, content, gpx_files, routes, support, users
from app.services.account_lifecycle_service import process_account_lifecycle
from sqlmodel import Session


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.email_outbox_dir).mkdir(parents=True, exist_ok=True)
    create_db_and_tables()
    with Session(engine) as session:
        seed_admin_emails(session)
        seed_legal_documents(session)
        process_account_lifecycle(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(support.router)
app.include_router(analytics.router)
app.include_router(content.router)
app.include_router(gpx_files.router)
app.include_router(routes.router)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
