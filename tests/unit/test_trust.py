from app.risk import assumptions as A
from app.schemas import INSUFFICIENT_EVIDENCE_TEXT
from app.security.trust import band_for


def test_weights_sum_to_100():
    assert sum(A.TRUST_WEIGHTS.values()) == 100
    assert sum(A.EVIDENCE_QUALITY_WEIGHTS.values()) == 1.0


def test_bands():
    assert [band_for(x) for x in (0, 49, 50, 69, 70, 84, 85, 100)] == [
        "REJECT", "REJECT", "LOW CONFIDENCE", "LOW CONFIDENCE", "REVIEW", "REVIEW", "TRUSTED", "TRUSTED"]


def test_insufficient_text_is_exact():
    assert INSUFFICIENT_EVIDENCE_TEXT == "INSUFFICIENT EVIDENCE — HUMAN REVIEW REQUIRED."
