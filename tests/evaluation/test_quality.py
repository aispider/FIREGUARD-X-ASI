"""Evaluation: low false positives on benign science, sensible retrieval, trust behaves as designed."""

import pytest

from app.agents.orchestrator import run_council
from app.rag.retriever import retrieve
from app.schemas import ScenarioIn
from app.security.injection import scan

BENIGN = [
    "The flame was extinguished when the oxygen concentration was reduced to 18 percent.",
    "Researchers ran the experiment at several flow velocities and recorded the spread rate.",
    "The command module crew reviewed the system design and previous fire reports.",
    "Previous studies ignored the effect of sample thickness on extinction.",
    "Instructions for the next run were uploaded to the rack after the test.",
    "A high risk of re-ignition was observed in the cotton fabric samples.",
    "The system pressure was set to 101 kPa and the fan speed to 20 cm/s.",
    "Act as a heat sink: the metal backing plate absorbs radiant energy.",
    "The administrator of the facility approved the test schedule.",
    "Safety guidelines were followed during the experiment.",
]


@pytest.mark.parametrize("text", BENIGN)
def test_benign_science_not_flagged(text):
    assert not scan(text).detected, scan(text).flags


@pytest.mark.parametrize("query,expected", [
    ("oxygen concentration and flame spread", "DEMO-oxygen"),
    ("airflow velocity opposed flow", "DEMO-airflow"),
    ("fabric and silicone Nomex material flammability", "DEMO-materials"),
    ("sensor corroboration smoke detector false alarm", "DEMO-detection"),
])
def test_retrieval_finds_expected_doc(db, query, expected):
    top = [c.doc.doc_key for c in retrieve(db, None, query=query, limit=3) if c.status == "used"]
    assert expected in top


def test_trust_falls_when_conditions_leave_envelope(db):
    inside = run_council(db, ScenarioIn())
    outside = run_council(db, ScenarioIn(oxygen_percent=24.8, pressure_kpa=140, temperature_k=590, external_heating_kw_m2=25))
    assert outside.trust.score < inside.trust.score
    assert any(c.category == "extrapolation" and not c.passed for c in outside.challenges)


def test_sensor_disagreement_is_challenged(db):
    r = run_council(db, ScenarioIn(oxygen_percent=24, airflow_cm_s=13, sensor_flags={"smoke_detected": False, "optical_flame_detected": False}))
    assert r.risk.level in ("HIGH", "CRITICAL") and any(c.category == "sensor" and not c.passed for c in r.challenges)


def test_every_citation_exists(db):
    r = run_council(db, ScenarioIn())
    ids = {e.chunk_id for e in r.evidence if e.status == "used"}
    for m in r.council:
        assert {ref.source_id for ref in m.output.evidence} <= ids
