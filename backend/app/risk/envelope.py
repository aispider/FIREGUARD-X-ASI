"""Does the scenario sit inside the conditions the evidence covers?"""

from __future__ import annotations

from app.risk.assumptions import ENVELOPE, GRAVITY_ENVELOPE_PENALTY
from app.schemas import ScenarioIn

LABELS = {
    "oxygen_percent": "oxygen",
    "airflow_cm_s": "airflow",
    "pressure_kpa": "pressure",
    "temperature_k": "temperature",
    "external_heating_kw_m2": "external heating",
}


def penalty(
    s: ScenarioIn, observed: dict[str, tuple[float, float]] | None = None
) -> tuple[float, list[str], str]:
    """Returns (penalty points, out-of-range names, source).

    With real NASA observations loaded, variables that have observations use the observed min/max; the
    rest keep the prototype envelope. The source field says which one was used.
    """
    observed = observed or {}
    used_real = False
    pen = 0.0
    out: list[str] = []
    for key, (lo, hi) in ENVELOPE.items():
        if key in observed:
            lo, hi = observed[key]
            used_real = True
        v = getattr(s, key)
        if v < lo or v > hi:
            out.append(LABELS[key])
            span = max(hi - lo, 1e-9)
            over = (lo - v) if v < lo else (v - hi)
            pen += min(40.0, 6.0 + 24.0 * over / span)
    g = GRAVITY_ENVELOPE_PENALTY[s.gravity]
    if g:
        out.append(f"{s.gravity} gravity")
        pen += g
    return pen, out, ("nasa_observations" if used_real else "prototype_assumption")
