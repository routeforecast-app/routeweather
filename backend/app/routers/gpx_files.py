from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.dependencies import get_current_active_user
from app.models import SavedGpxFile, User
from app.schemas import SavedGpxFileRead
from app.services.gpx_service import parse_gpx_file


router = APIRouter(prefix="/gpx-files", tags=["gpx-files"])
settings = get_settings()
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)


def _get_owned_gpx_file(session: Session, gpx_file_id: int, user_id: int) -> SavedGpxFile:
    gpx_file = session.exec(
        select(SavedGpxFile).where(SavedGpxFile.id == gpx_file_id, SavedGpxFile.user_id == user_id)
    ).first()
    if not gpx_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GPX file not found.")
    return gpx_file


@router.get("", response_model=list[SavedGpxFileRead])
def list_gpx_files(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> list[SavedGpxFileRead]:
    gpx_files = session.exec(
        select(SavedGpxFile)
        .where(SavedGpxFile.user_id == current_user.id)
        .order_by(SavedGpxFile.uploaded_at.desc())
    ).all()
    return [SavedGpxFileRead.model_validate(item) for item in gpx_files]


@router.post("/upload", response_model=SavedGpxFileRead, status_code=status.HTTP_201_CREATED)
async def upload_gpx_file(
    name: str | None = Form(default=None),
    gpx_file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> SavedGpxFileRead:
    filename = gpx_file.filename or ""
    if not filename.lower().endswith(".gpx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a GPX file.")

    file_bytes = await gpx_file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded GPX file is empty.")

    try:
        route_points = parse_gpx_file(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    stored_path = upload_dir / f"user-{current_user.id}-library-{uuid4()}.gpx"
    stored_path.write_bytes(file_bytes)

    saved_file = SavedGpxFile(
        user_id=current_user.id,
        name=(name or Path(filename).stem).strip() or "Saved GPX",
        original_filename=filename,
        file_path=str(stored_path),
        total_distance_km=round(route_points[-1].cumulative_distance_km, 3),
        point_count=len(route_points),
    )
    session.add(saved_file)
    session.commit()
    session.refresh(saved_file)
    return SavedGpxFileRead.model_validate(saved_file)


@router.get("/{gpx_file_id}/download")
def download_gpx_file(
    gpx_file_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    gpx_file = _get_owned_gpx_file(session, gpx_file_id, current_user.id)
    file_path = Path(gpx_file.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored GPX file is missing.")

    return FileResponse(
        path=file_path,
        media_type="application/gpx+xml",
        filename=gpx_file.original_filename or f"{gpx_file.name}.gpx",
    )


@router.delete("/{gpx_file_id}", response_class=Response, status_code=status.HTTP_204_NO_CONTENT)
def delete_gpx_file(
    gpx_file_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    gpx_file = _get_owned_gpx_file(session, gpx_file_id, current_user.id)
    file_path = Path(gpx_file.file_path)
    session.delete(gpx_file)
    session.commit()
    file_path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
