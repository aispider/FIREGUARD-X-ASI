"""Evaluation of the trust logic: it must never hand out TRUSTED on weak ground."""

from __future__ import annotations

from tests.integration.test_api import BEYOND, NOMINAL, run


def test_strict_mode_with_only_synthetic_evidence_is_insufficient(client, admin, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("EVIDENCE_MODE", "strict")
    get_settings.cache_clear()
    try:
        d = run(client, admin, NOMINAL)
        assert d["trust"]["insufficient_evidence"] is True
        assert d["trust"]["verdict"] == "INSUFFICIENT EVIDENCE — HUMAN REVIEW REQUIRED."
        assert d["trust"]["guardian_status"] != "TRUSTED"
        assert d["decision"]["insufficient_evidence"] is True
        assert d["decision"]["summary"] == "INSUFFICIENT EVIDENCE — HUMAN REVIEW REQUIRED."
        g = next(g for g in d["trust"]["gates"] if g["key"] == "nasa_evidence")
        assert g["status"] == "fail"
    finally:
        monkeypatch.delenv("EVIDENCE_MODE", raising=False)
        get_settings.cache_clear()


def test_insufficient_evidence_blocks_approval(client, commander, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("EVIDENCE_MODE", "strict")
    get_settings.cache_clear()
    try:
        a = client.post("/api/risk/assess", json=NOMINAL, headers=commander).json()
        assert a["status"] == "insufficient_evidence"
        r = client.post(
            "/api/approvals",
            json={"assessment_id": a["id"], "decision": "approve", "confirm": True},
            headers=commander,
        ).json()
        assert r["allowed"] is False and r["steps"] == []
    finally:
        monkeypatch.delenv("EVIDENCE_MODE", raising=False)
        get_settings.cache_clear()


def test_out_of_range_never_trusted(client, admin):
    assert run(client, admin, BEYOND)["trust"]["guardian_status"] != "TRUSTED"


def test_no_evidence_returns_insufficient(client, admin, session):
    """A query that retrieves nothing usable must not produce a confident answer."""
    from app.agents.orchestrator import run_council
    from app.models import Document
    from app.schemas import ScenarioIn

    docs = list(session.query(Document))
    for d in docs:
        d.quarantined = True
    session.commit()
    try:
        res = run_council(session, ScenarioIn(), persist=False)
        assert res.trust.insufficient_evidence and res.trust.verdict.startswith("INSUFFICIENT EVIDENCE")
        assert res.council[0].output.finding.startswith("INSUFFICIENT EVIDENCE")
    finally:
        for d in docs:
            d.quarantined = False
        session.commit()
