"""Command simulator. It models the effect of approved steps on the risk score and sends NOTHING anywhere.

Reached only after the guardian, the policy engine and a human approval (two-step confirm).
"""

from __future__ import annotations

from app.risk.model import assess
from app.schemas import ActionStep, ScenarioIn, SimStep


def simulate(s: ScenarioIn, actions: list[ActionStep]) -> list[SimStep]:
    steps: list[SimStep] = []
    n = max(1, len(actions))
    for i, a in enumerate(actions, start=1):
        after = assess(s, suppression=min(0.9, 0.9 * i / n))[0].score
        steps.append(
            SimStep(index=i, title=a.title, detail="[SIMULATED] " + a.detail, risk_after=float(after))
        )
    return steps
