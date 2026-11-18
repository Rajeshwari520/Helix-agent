"""Central settings. Values marked (proposal) need mentor confirmation.

Environment variables
  HELIX_DOMAIN   kgit (default)  -> helpdesk data/categories in data/<domain>/ (one domain today: KGIT)
  DATABASE_URL   postgresql://user:pass@host:5432/db  or  sqlite:///file.db
                 default: sqlite:///helix_<domain>.db
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
MODEL_DIR = ROOT / "models"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
DOMAINS = ["kgit"]   # a new client = a new folder data/<name>/ with domain.json + data


@dataclass
class Domain:
    name: str
    title: str
    description: str
    teams: dict                      # category -> team
    extra_signals: list = field(default_factory=list)   # domain-specific urgency signals

    @property
    def categories(self) -> list[str]:
        return list(self.teams)

    @property
    def data_dir(self) -> Path:
        return DATA_ROOT / self.name

    @property
    def classifier_path(self) -> Path:
        return MODEL_DIR / f"{self.name}_category_classifier.joblib"


def load_domain(name: str) -> Domain:
    if name not in DOMAINS:
        raise ValueError(f"Unknown domain '{name}'. Use one of {DOMAINS}")
    spec = json.loads((DATA_ROOT / name / "domain.json").read_text(encoding="utf-8"))
    return Domain(name=name, title=spec["title"], description=spec["description"],
                  teams=spec["teams"], extra_signals=spec.get("extra_signals", []))


_active = load_domain(os.getenv("HELIX_DOMAIN", "kgit"))


def domain() -> Domain:
    return _active


def set_domain(name: str) -> Domain:
    """Switch the active domain (used by tests and evaluation scripts)."""
    global _active
    _active = load_domain(name)
    return _active


def database_url() -> str:
    return os.getenv("DATABASE_URL") or f"sqlite:///{ROOT / f'helix_{_active.name}.db'}"


# kept as a module attribute so tests can monkeypatch it
DATABASE_URL = os.getenv("DATABASE_URL")

ESCALATION_TEAM = "Team Lead"
PRIORITIES = ["Low", "Medium", "High", "Critical"]
# (proposal) hours: (first response, resolution)
SLA_HOURS = {"Critical": (1, 8), "High": (4, 24), "Medium": (8, 48), "Low": (24, 72)}
STATUSES = ["New", "Triaged", "Assigned", "In Progress", "Waiting on Customer",
            "Escalated", "Resolved", "Closed"]

# (proposal) below this classifier confidence the category must be confirmed by a human
CLASSIFIER_CONFIDENCE_THRESHOLD = float(os.getenv("HELIX_CLS_THRESHOLD", "0.45"))
# minimum retrieval similarity for the RAG answer to be used
RETRIEVAL_MIN_SCORE = float(os.getenv("HELIX_RAG_MIN_SCORE", "0.30"))
RETRIEVAL_TOP_K = 3
