"""What-if sweeps and the risk heat map. Pure functions over the prototype risk model."""

from __future__ import annotations

from app.risk.assumptions import ENVELOPE
from app.risk.model import assess
from app.schemas import HeatmapOut, ScenarioIn, SweepOut

AXES = {"oxygen_percent": (15.0, 25.0), "airflow_cm_s": (0.0, 40.0)}


def _with(s: ScenarioIn, **kw: float) -> ScenarioIn:
    return s.model_copy(update=kw)


def sweep(s: ScenarioIn, axis: str, observed=None, points: int = 41) -> SweepOut:
    lo, hi = AXES[axis]
    xs = [round(lo + (hi - lo) * i / (points - 1), 3) for i in range(points)]
    scores = [float(assess(_with(s, **{axis: x}), observed=observed)[0].score) for x in xs]
    cur = float(assess(s, observed=observed)[0].score)
    return SweepOut(
        axis=axis,
        xs=xs,
        scores=scores,
        current=float(getattr(s, axis)),
        current_score=cur,
        envelope=[float(ENVELOPE[axis][0]), float(ENVELOPE[axis][1])],
    )


def heatmap(s: ScenarioIn, observed=None, n: int = 21) -> HeatmapOut:
    ox = [round(15 + 10 * i / (n - 1), 3) for i in range(n)]
    fl = [round(40 * i / (n - 1), 3) for i in range(n)]
    grid = [
        [float(assess(_with(s, oxygen_percent=o, airflow_cm_s=f), observed=observed)[0].score) for o in ox]
        for f in fl
    ]
    return HeatmapOut(
        oxygen=ox, airflow=fl, scores=grid, current={"oxygen": s.oxygen_percent, "airflow": s.airflow_cm_s}
    )
