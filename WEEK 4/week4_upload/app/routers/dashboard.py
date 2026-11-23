"""Dashboard: the page (React UI, dashboard view) + the JSON numbers behind it (read-only)."""
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.deps import get_db
from app.services import dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page():
    """Open http://127.0.0.1:8000/dashboard: the dashboard view of the React UI."""
    from app.routers.agent import ui_index
    return ui_index()


@router.get("/dashboard/stats")
def dashboard_stats(clock: Literal["now", "demo"] = "now", conn=Depends(get_db)):
    """Numbers for the dashboard. clock=demo measures SLA 1 hour after the newest ticket
    (the seeded demo tickets are from early November, so in real time they are all overdue)."""
    return dashboard.stats(conn, clock=clock)
