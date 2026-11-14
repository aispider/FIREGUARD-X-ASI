from app.risk.model import assess, level_name
from app.schemas import ScenarioIn


def sc(**kw):
    return ScenarioIn(**kw)


def test_oxygen_raises_risk_monotonically():
    scores = [assess(sc(oxygen_percent=o))[0].score for o in (16, 18, 20, 22, 24)]
    assert scores == sorted(scores) and scores[-1] > scores[0]


def test_airflow_is_nonlinear_with_peak_in_the_teens():
    low, mid, high = (assess(sc(airflow_cm_s=f))[0].score for f in (0.5, 13, 60))
    assert mid > low and mid > high


def test_material_ordering():
    nomex = assess(sc(material="Nomex fabric"))[0].score
    pmma = assess(sc(material="PMMA"))[0].score
    cotton = assess(sc(material="Cotton-fiberglass fabric"))[0].score
    assert nomex < pmma < cotton


def test_levels_use_documented_thresholds():
    assert level_name(0.24) == "LOW" and level_name(0.25) == "MEDIUM"
    assert level_name(0.45) == "HIGH" and level_name(0.70) == "CRITICAL"


def test_envelope_flags_extrapolation():
    r, pen, _ = assess(sc(oxygen_percent=24.8, pressure_kpa=140, temperature_k=590, external_heating_kw_m2=25))
    assert not r.in_envelope and pen > 0 and "oxygen" in r.out_of_range
    r2, pen2, _ = assess(sc())
    assert r2.in_envelope and pen2 == 0


def test_suppression_lowers_score():
    base = assess(sc(oxygen_percent=24))[0].score
    assert assess(sc(oxygen_percent=24), suppression=0.8)[0].score < base


def test_score_bounded():
    r = assess(sc(oxygen_percent=40, temperature_k=1500, external_heating_kw_m2=100, material="Cotton-fiberglass fabric", gravity="earth"))[0]
    assert 0 <= r.score <= 100
