"""Every number in the prototype risk model, in one place, labelled as an assumption.

None of these values is a NASA result or a NASA-approved threshold. They are transparent modelling choices
made for this prototype. The Mission Command screen shows this list under "Prototype assumptions".
"""

from __future__ import annotations

WEIGHTS = {"oxygen": 0.42, "airflow": 0.26, "temperature": 0.20, "heating": 0.10, "pressure": 0.08}
OXYGEN_EXPONENT = 1.3
AIRFLOW_PEAK_CM_S = 13.0
AIRFLOW_WIDTH = 0.85
AIRFLOW_FLOOR = 0.12
OXYGEN_ENRICHMENT_LIMIT = 23.5
OXYGEN_ENRICHMENT_BONUS = 0.08

MATERIAL_FACTOR = {
    "PMMA": 1.0,
    "Cotton-fiberglass fabric": 1.12,
    "Polyethylene": 0.92,
    "Silicone": 0.6,
    "Nomex fabric": 0.45,
}
GEOMETRY_FACTOR = {"thin_sheet": 1.15, "cylinder": 1.0, "thick_slab": 0.85}
GRAVITY_FACTOR = {"microgravity": 1.0, "lunar": 1.05, "mars": 1.1, "earth": 1.2}
# Gravity levels the prototype envelope was assumed for; others count as extrapolation.
GRAVITY_ENVELOPE_PENALTY = {"microgravity": 0, "lunar": 8, "mars": 10, "earth": 14}
GRAVITY_VISUAL = {"microgravity": 0.0, "lunar": 0.25, "mars": 0.5, "earth": 1.0}

# Relative amount of experimental coverage assumed per material (used only when no real evidence tags exist).
MATERIAL_COVERAGE_HINT = {
    "PMMA": 92,
    "Cotton-fiberglass fabric": 78,
    "Polyethylene": 66,
    "Silicone": 58,
    "Nomex fabric": 74,
}

LEVEL_THRESHOLDS = (0.25, 0.45, 0.70)  # MEDIUM, HIGH, CRITICAL
LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

# Prototype assumption of the conditions the evidence covers.
ENVELOPE = {
    "oxygen_percent": (15.0, 24.0),
    "airflow_cm_s": (0.0, 30.0),
    "pressure_kpa": (60.0, 110.0),
    "temperature_k": (200.0, 500.0),
    "external_heating_kw_m2": (0.0, 20.0),
}

TRUST_WEIGHTS = {
    "evidence_quality": 20,
    "source_relevance": 20,
    "experimental_match": 15,
    "agent_consensus": 15,
    "adversarial": 15,
    "data_integrity": 10,
    "uncertainty": 5,
}
TRUST_LABELS = {
    "evidence_quality": "Evidence quality",
    "source_relevance": "Source relevance",
    "experimental_match": "Experimental match",
    "agent_consensus": "Agent consensus",
    "adversarial": "Adversarial verification",
    "data_integrity": "Data integrity",
    "uncertainty": "Uncertainty",
}
EVIDENCE_QUALITY_WEIGHTS = {"coverage": 0.5, "diversity": 0.3, "authority": 0.2}
SYNTHETIC_AUTHORITY = 0.35  # demo passages count for something, never as much as official documents
TRUST_BANDS = ((85, "TRUSTED"), (70, "REVIEW"), (50, "LOW CONFIDENCE"), (0, "REJECT"))

ASSUMPTION_LINES = [
    "Risk weights: oxygen 0.42, airflow 0.26, temperature 0.20, external heating 0.10, pressure 0.08.",
    "Airflow response peaks near 13 cm/s (log-gaussian bump). The peak location is an assumption.",
    "Material, geometry and gravity multipliers are prototype values, not measured ones.",
    "Risk thresholds 0.25 / 0.45 / 0.70 (MEDIUM / HIGH / CRITICAL) are the FIREGUARD-X policy, not NASA-approved.",
    "Trust score weights: evidence 20, relevance 20, experiment match 15, consensus 15, adversarial 15, integrity 10, uncertainty 5.",
    "Tested envelope: O2 15-24 %, flow 0-30 cm/s, 60-110 kPa, up to 500 K, up to 20 kW/m2, microgravity.",
]
