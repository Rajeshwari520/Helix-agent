"""Agent workspace (Week 4): the React UI and the data behind it.

The React source is in frontend/; `npm run build` writes app/static/ui/app.js + app.css.
The built files are committed, so the app runs without Node.js.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from app import config
from app.deps import get_db
from app.schemas import Status
from app.services import audit, dashboard, system

router = APIRouter(tags=["agent workspace"])
UI_DIR = config.ROOT / "app" / "static" / "ui"
UI_FILES = {"app.js": "text/javascript", "app.css": "text/css"}  # nothing else is served from disk


def ui_index() -> HTMLResponse:
    return HTMLResponse((UI_DIR / "index.html").read_text(encoding="utf-8"))


@router.get("/agent", response_class=HTMLResponse, include_in_schema=False)
def agent_page():
    """Open http://127.0.0.1:8000/agent: ticket queue, ticket detail, approve / edit / reject (React)."""
    return ui_index()


@router.get("/ui/{name}", include_in_schema=False)
def ui_file(name: str):
    """The built React bundle (app.js, app.css)."""
    if name not in UI_FILES or not (UI_DIR / name).exists():
        raise HTTPException(status_code=404, detail="Not found")
    return Response((UI_DIR / name).read_bytes(), media_type=UI_FILES[name],
                    headers={"Cache-Control": "no-cache"})


@router.get("/queue")
def agent_queue(clock: Literal["now", "demo"] = "now", include_closed: bool = False, conn=Depends(get_db)):
    """Queue rows for the agent page: SLA state, AI confidence and how many AI suggestions wait for a decision."""
    return dashboard.queue(conn, clock=clock, include_closed=include_closed)


@router.get("/meta")
def meta():
    """Lists for drop-downs: categories, default team per category, teams, priorities, statuses, SLA hours."""
    teams = config.domain().teams
    return {
        "domain": config.domain().name,
        "categories": config.domain().categories,
        "category_team": teams,
        "teams": sorted(set(teams.values()) | {config.ESCALATION_TEAM}),
        "priorities": list(reversed(config.PRIORITIES)),
        "statuses": list(Status.__args__),
        "sla_hours": {k: {"first_response": v[0], "resolution": v[1]} for k, v in config.SLA_HOURS.items()},
    }


@router.get("/audit")
def recent_audit(limit: int = Query(100, ge=1, le=500), event: Optional[str] = None, conn=Depends(get_db)):
    """Newest audit events across all tickets (filter with event=suggestion_rejected, reply_sent, ...)."""
    return audit.recent(conn, limit=limit, event=event)


@router.get("/system")
def system_info(conn=Depends(get_db)):
    """Backend facts: version, database engine, migrations, row counts, AI model / retriever / FAQ versions,
    thresholds, AI latency and SLA hours. Read-only; no secrets."""
    return system.info(conn)
