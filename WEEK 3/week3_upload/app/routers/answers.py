"""Grounded answer endpoints (Week 3)."""
from fastapi import APIRouter, Depends, HTTPException

from app import repository
from app.deps import get_db, get_retriever
from app.schemas import AskRequest
from app.services import rag

router = APIRouter(tags=["answers"])


@router.post("/tickets/{ticket_id}/answer")
def answer_ticket(ticket_id: str, conn=Depends(get_db)):
    """Draft a reply for a ticket from approved FAQs, with citations.

    The draft is NEVER sent automatically: requires_human_approval is always true.
    """
    ticket = repository.get_ticket(conn, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    retriever, corpus_version = get_retriever(conn)
    result = rag.answer(f"{ticket['subject']}. {ticket['body']}", retriever, corpus_version)
    repository.save_suggestion(conn, ticket_id, "answer", result,
                               f"{result['retriever_version']}|{corpus_version}", result["latency_ms"])
    if result["escalate"] and not ticket["needs_escalation"]:
        repository.update_ticket(conn, ticket_id, {"status": "Escalated"})
    return {"ticket_id": ticket_id, **result}


@router.post("/ask")
def ask(payload: AskRequest, conn=Depends(get_db)):
    """Ask a free-text question (agent helper). Same guardrails and citations as ticket answers."""
    retriever, corpus_version = get_retriever(conn)
    return rag.answer(payload.question, retriever, corpus_version)
