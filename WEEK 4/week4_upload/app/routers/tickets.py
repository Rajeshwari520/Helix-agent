"""Ticket CRUD + triage endpoints (Week 2)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app import repository
from app.deps import get_db
from app.schemas import ReviewRequest, Ticket, TicketCreate, TicketUpdate
from app.services import audit, review

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _or_404(ticket, ticket_id: str):
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@router.post("", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate, conn=Depends(get_db)):
    """Create a ticket. It is triaged automatically (category, priority, team, SLA, escalation)."""
    return repository.create_ticket(conn, **payload.model_dump())


@router.get("", response_model=list[Ticket])
def list_tickets(status: Optional[str] = None, priority: Optional[str] = None, team: Optional[str] = None,
                 category: Optional[str] = None, escalated: Optional[bool] = None,
                 limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), conn=Depends(get_db)):
    """Ticket queue, ordered Critical -> Low, then oldest first."""
    return repository.list_tickets(conn, status=status, priority=priority, team=team, category=category,
                                   escalated=escalated, limit=limit, offset=offset)


@router.get("/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: str, conn=Depends(get_db)):
    return _or_404(repository.get_ticket(conn, ticket_id), ticket_id)


@router.patch("/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: str, payload: TicketUpdate, conn=Depends(get_db)):
    """Human override of status / category / priority / team / assignee."""
    changes = payload.model_dump(exclude_none=True)
    actor = changes.pop("changed_by")
    return _or_404(repository.update_ticket(conn, ticket_id, changes, actor=actor), ticket_id)


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: str, deleted_by: str = Query("agent", min_length=2, max_length=80),
                  conn=Depends(get_db)):
    """Soft delete (row kept for audit)."""
    if not repository.delete_ticket(conn, ticket_id, actor=deleted_by):
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")


@router.post("/{ticket_id}/triage")
def triage_ticket(ticket_id: str, conn=Depends(get_db)):
    """Re-run AI triage and return the full explanation (confidence, reasons, SLA)."""
    return _or_404(repository.triage_ticket(conn, ticket_id), ticket_id)


@router.get("/{ticket_id}/suggestions")
def ticket_suggestions(ticket_id: str, conn=Depends(get_db)):
    """All AI suggestions stored for this ticket (triage + answers), each with its human review (or null)."""
    _or_404(repository.get_ticket(conn, ticket_id), ticket_id)
    return repository.list_suggestions(conn, ticket_id)


@router.post("/{ticket_id}/suggestions/{suggestion_id}/review")
def review_suggestion(ticket_id: str, suggestion_id: int, payload: ReviewRequest, conn=Depends(get_db)):
    """Human decision on an AI suggestion: approve, edit or reject (Week 4).

    Triage: edit with category / priority / team. Answer: edit with `reply` (your own text).
    Reject needs a `reason`. Each suggestion can be decided once; the decision is audited.
    Sending a reply is simulated: it is stored and logged, no email is sent.
    """
    try:
        return review.review(conn, ticket_id, suggestion_id, payload.decision, payload.reviewer,
                             category=payload.category, priority=payload.priority, team=payload.team,
                             reply=payload.reply, reason=payload.reason)
    except review.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except review.Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except review.ReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{ticket_id}/audit")
def ticket_audit(ticket_id: str, conn=Depends(get_db)):
    """Audit trail of one ticket: AI suggestions, human decisions and changes, oldest first."""
    _or_404(repository.get_ticket(conn, ticket_id), ticket_id)
    return audit.for_ticket(conn, ticket_id)
