"""Versioned FAQ knowledge store endpoints (Week 3)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_db
from app.schemas import FAQApprove, FAQCreate
from app.services import knowledge

router = APIRouter(prefix="/faqs", tags=["knowledge"])


@router.get("")
def list_faqs(category: Optional[str] = None, conn=Depends(get_db)):
    """Current approved FAQs (what the RAG service can use)."""
    return {"corpus_version": knowledge.corpus_version(conn), "faqs": knowledge.current_faqs(conn, category)}


@router.get("/{faq_id}/history")
def faq_history(faq_id: str, conn=Depends(get_db)):
    rows = knowledge.history(conn, faq_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"{faq_id} not found")
    return rows


@router.post("", status_code=201)
def create_faq(payload: FAQCreate, conn=Depends(get_db)):
    """Propose a NEW FAQ (created as draft; not used until approved)."""
    return knowledge.propose_version(conn, None, payload.category, payload.question, payload.answer)


@router.post("/{faq_id}/versions", status_code=201)
def new_version(faq_id: str, payload: FAQCreate, conn=Depends(get_db)):
    """Propose an edit to an existing FAQ (new draft version)."""
    try:
        return knowledge.propose_version(conn, faq_id, payload.category, payload.question, payload.answer)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"{faq_id} not found")


@router.post("/{faq_id}/approve")
def approve(faq_id: str, payload: FAQApprove, conn=Depends(get_db)):
    """Approve a version: it becomes current and the previous version is retired."""
    try:
        return knowledge.approve(conn, faq_id, payload.version, payload.approved_by)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"{faq_id} v{payload.version} not found")
