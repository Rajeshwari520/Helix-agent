"""Ticket CRUD + triage endpoints (Week 2)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app import repository
from app.deps import get_db
from app.schemas import Ticket, TicketCreate, TicketUpdate

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
    return _or_404(repository.update_ticket(conn, ticket_id, payload.model_dump(exclude_none=True)), ticket_id)


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: str, conn=Depends(get_db)):
    """Soft delete (row kept for audit)."""
    if not repository.delete_ticket(conn, ticket_id):
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")


@router.post("/{ticket_id}/triage")
def triage_ticket(ticket_id: str, conn=Depends(get_db)):
    """Re-run AI triage and return the full explanation (confidence, reasons, SLA)."""
    return _or_404(repository.triage_ticket(conn, ticket_id), ticket_id)


@router.get("/{ticket_id}/suggestions")
def ticket_suggestions(ticket_id: str, conn=Depends(get_db)):
    """All AI suggestions stored for this ticket (triage + answers)."""
    _or_404(repository.get_ticket(conn, ticket_id), ticket_id)
    return repository.list_suggestions(conn, ticket_id)
