"""Prototype fire-risk model (transparent, deterministic). Not a NASA model.

risk = multiplier * (0.42*oxygen^1.3 + 0.26*airflow_bump + 0.20*temperature + 0.10*heating + 0.08*pressure)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.risk import assumptions as A
from app.risk.envelope import penalty
from app.schemas import Driver, RiskOut, ScenarioIn


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def level_index(x: float) -> int:
    t = A.LEVEL_THRESHOLDS
    return 0 if x < t[0] else 1 if x < t[1] else 2 if x < t[2] else 3


def level_name(x: float) -> str:
    return A.LEVELS[level_index(x)]


@dataclass
class Core:
    raw: float
    terms: dict[str, float]
    multiplier: float


def core(s: ScenarioIn) -> Core:
    o2n = clamp((s.oxygen_percent - 15) / 10, 0, 1.2)
    bump = math.exp(
        -((math.log(s.airflow_cm_s + 1) - math.log(A.AIRFLOW_PEAK_CM_S)) ** 2) / (2 * A.AIRFLOW_WIDTH**2)
    )
    w = A.WEIGHTS
    terms = {
        "oxygen": w["oxygen"] * o2n**A.OXYGEN_EXPONENT,
        "airflow": w["airflow"] * (A.AIRFLOW_FLOOR + (1 - A.AIRFLOW_FLOOR) * bump),
        "temperature": w["temperature"] * clamp((s.temperature_k - 300) / 300, 0, 1),
        "heating": w["heating"] * clamp(s.external_heating_kw_m2 / 30, 0, 1),
        "pressure": w["pressure"] * clamp((s.pressure_kpa - 50) / 100, 0, 1),
    }
    mult = A.MATERIAL_FACTOR[s.material] * A.GEOMETRY_FACTOR[s.fuel_geometry] * A.GRAVITY_FACTOR[s.gravity]
    raw = mult * sum(terms.values())
    if s.oxygen_percent > A.OXYGEN_ENRICHMENT_LIMIT:
        raw += A.OXYGEN_ENRICHMENT_BONUS
    return Core(clamp(raw, 0, 1), terms, mult)


DRIVER_NAMES = {
    "oxygen": "Oxygen level",
    "airflow": "Airflow regime",
    "temperature": "Temperature",
    "heating": "External heating",
    "pressure": "Pressure",
}


def assess(
    s: ScenarioIn,
    *,
    suppression: float = 0.0,
    observed: dict[str, tuple[float, float]] | None = None,
) -> tuple[RiskOut, float, float]:
    """Returns (RiskOut with confidence=0 placeholder, penalty_points, raw score 0..1)."""
    c = core(s)
    score = c.raw * (1 - 0.9 * suppression)
    crew = clamp(score * 0.88 + (0.06 if s.oxygen_percent > A.OXYGEN_ENRICHMENT_LIMIT else 0), 0, 1)
    nonlinear = 4 <= s.airflow_cm_s <= 20 and c.raw >= 0.5
    pen, out_of_range, source = penalty(s, observed)
    total = sum(c.terms.values()) or 1.0
    drivers = [
        Driver(name=DRIVER_NAMES[k], contribution=round(v * c.multiplier, 4), share=round(v / total, 4))
        for k, v in sorted(c.terms.items(), key=lambda kv: -kv[1])
    ]
    out = RiskOut(
        score=round(score * 100),
        level=level_name(score),
        crew_level=level_name(crew),
        flame_growth=level_name(clamp(score + 0.02, 0, 1)),
        spread_potential=level_name(score),
        extinction_probability=round((1 - clamp(score * 1.12, 0, 1)) * 100),
        confidence=0.0,
        drivers=drivers,
        multiplier=round(c.multiplier, 3),
        nonlinear_airflow=nonlinear,
        in_envelope=not out_of_range,
        out_of_range=out_of_range,
        envelope_source=source,
    )
    return out, pen, score
