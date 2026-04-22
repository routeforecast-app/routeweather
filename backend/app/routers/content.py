from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.content import update_legal_document
from app.database import get_session
from app.dependencies import get_current_active_admin
from app.models import LegalDocument, User
from app.schemas import LegalDocumentRead, LegalDocumentUpdate


router = APIRouter(prefix="/content", tags=["content"])


@router.get("/legal", response_model=list[LegalDocumentRead])
def list_legal_documents(session: Session = Depends(get_session)) -> list[LegalDocumentRead]:
    documents = session.exec(select(LegalDocument).order_by(LegalDocument.document_type.asc())).all()
    return [LegalDocumentRead.model_validate(document) for document in documents]


@router.get("/legal/{document_type}", response_model=LegalDocumentRead)
def get_legal_document(
    document_type: str,
    session: Session = Depends(get_session),
) -> LegalDocumentRead:
    document = _get_document_or_404(session, document_type)
    return LegalDocumentRead.model_validate(document)


@router.get("/admin/legal", response_model=list[LegalDocumentRead])
def list_admin_legal_documents(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_active_admin),
) -> list[LegalDocumentRead]:
    documents = session.exec(select(LegalDocument).order_by(LegalDocument.document_type.asc())).all()
    return [LegalDocumentRead.model_validate(document) for document in documents]


@router.put("/admin/legal/{document_type}", response_model=LegalDocumentRead)
def save_legal_document(
    document_type: str,
    payload: LegalDocumentUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_active_admin),
) -> LegalDocumentRead:
    document = _get_document_or_404(session, document_type)
    update_legal_document(document, payload.title, payload.body)
    session.add(document)
    session.commit()
    session.refresh(document)
    return LegalDocumentRead.model_validate(document)


def _get_document_or_404(session: Session, document_type: str) -> LegalDocument:
    document = session.exec(
        select(LegalDocument).where(LegalDocument.document_type == document_type.lower())
    ).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal document not found.")
    return document
