"""Helix Agent API (FastAPI).

Run:   uvicorn app.main:app --reload
Docs:  http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config, db, repository
from app.routers import agent, answers, dashboard, faqs, tickets
from app.services import knowledge, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = db.connect()
    db.migrate(conn)
    db.ensure_domain(conn)
    db.seed_reference_data(conn)
    knowledge.load_from_csv(conn)
    repository.seed_tickets_from_csv(conn)
    conn.close()
    yield


app = FastAPI(
    title="Helix Agent — AI Customer Support & Ticket Management",
    version=system.VERSION,
    description="Ticket triage, FAQ-grounded answers with citations, guardrails and human approval.\n\n"
                "**[Agent workspace](/agent)** · **[Dashboard](/dashboard)** · **[Backend](/agent#/backend)**",
    lifespan=lifespan,
)
app.include_router(tickets.router)
app.include_router(answers.router)
app.include_router(faqs.router)
app.include_router(dashboard.router)
app.include_router(agent.router)


@app.get("/health", tags=["system"])
def health():
    d = config.domain()
    return {"status": "ok", "version": app.version, "domain": d.name, "domain_title": d.title}


@app.get("/", include_in_schema=False)
def home():
    """Opening http://127.0.0.1:8000/ goes to the dashboard (API docs: /docs)."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")
