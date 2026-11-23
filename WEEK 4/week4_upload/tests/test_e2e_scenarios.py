"""Week 4 — the 20 end-to-end ticket scenarios (data/kgit/e2e_scenarios.json) must all pass their workflow checks.
AI misses are reported in docs/kgit/week4_e2e_results.md (python -m ml.run_e2e), not failed here."""
import pytest

from ml import run_e2e


@pytest.fixture(scope="module")
def results():
    return run_e2e.run_all()


def test_there_are_twenty_scenarios():
    assert len(run_e2e.load_scenarios()) == 20


def test_every_scenario_passes_its_workflow_checks(results):
    failed = {r["id"]: r["failed_checks"] for r in results if r["result"] != "PASS"}
    assert not failed


def test_no_reply_without_a_person(results):
    for r in results:
        if r["reply_sent"]:
            assert r["human_reply"] in ("approved", "edited")
