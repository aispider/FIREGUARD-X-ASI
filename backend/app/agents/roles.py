"""The seven agents. Each reads evidence through the permission broker and returns a validated, structured output.

They are deterministic rule-based agents over the retrieved evidence and the prototype risk model. An optional
LLM can rephrase the `finding` sentence only (see llm.py). Agents never execute commands.
"""

from __future__ import annotations

from app.agents.base import Context, refs_for
from app.risk.assumptions import LEVELS
from app.schemas import INSUFFICIENT_EVIDENCE_TEXT, AgentOutput

LIMIT = "Prototype scoring model; not NASA-approved."


def _lims(ctx: Context, *extra: str) -> list[str]:
    out = [LIMIT, *extra]
    if ctx.stats.summary.synthetic_only and ctx.stats.summary.count:
        out.append("Evidence is SYNTHETIC/DEMO, not NASA data.")
    return out


def _unc(ctx: Context) -> list[str]:
    return [c.challenge for c in ctx.challenges if not c.passed]


def _no_evidence(ctx: Context) -> bool:
    return ctx.stats.summary.count == 0


def scientist(ctx: Context) -> AgentOutput:
    r, s = ctx.risk, ctx.scenario
    ctx.broker.call("scientist", "read:evidence", lambda: None)
    ctx.broker.call("scientist", "read:risk", lambda: None)
    if _no_evidence(ctx):
        return AgentOutput(
            agent="combustion_scientist",
            finding=INSUFFICIENT_EVIDENCE_TEXT,
            evidence=[],
            confidence=0.0,
            verdict="INSUFFICIENT EVIDENCE",
            uncertainties=["No usable evidence retrieved."],
            limitations=_lims(ctx),
        )
    conf = max(
        0.0, min(1.0, (ctx.stats.quality - ctx.pen * 0.5 - (6 if r.nonlinear_airflow else 0) - 8) / 100)
    )
    finding = (
        f"Conditions rate {r.level} for flame growth with oxygen at {s.oxygen_percent:g} % and airflow at "
        f"{s.airflow_cm_s:g} cm/s for {s.material} ({s.fuel_geometry.replace('_', ' ')}, {s.gravity})."
    )
    if r.nonlinear_airflow:
        finding += " Airflow is in a nonlinear regime."
    return AgentOutput(
        agent="combustion_scientist",
        finding=finding,
        evidence=refs_for(ctx, ("flame_spread", "extinction", "oxygen")),
        confidence=round(conf, 2),
        verdict=r.level,
        uncertainties=_unc(ctx),
        limitations=_lims(ctx),
        payload={"risk_level": r.level, "nonlinear_airflow": r.nonlinear_airflow},
    )


def data_scientist(ctx: Context) -> AgentOutput:
    ctx.broker.call("data", "read:evidence", lambda: None)
    ctx.broker.call("data", "read:risk", lambda: None)
    st = ctx.stats
    if _no_evidence(ctx):
        return AgentOutput(
            agent="nasa_data_scientist",
            finding=INSUFFICIENT_EVIDENCE_TEXT,
            evidence=[],
            confidence=0.0,
            verdict="INSUFFICIENT EVIDENCE",
            uncertainties=["No usable evidence retrieved."],
            limitations=_lims(ctx),
        )
    q = max(0.0, min(100.0, st.quality - ctx.pen * 0.5))
    verdict = "VERIFIED" if q >= 80 else "PARTIAL" if q >= 65 else "LIMITED"
    finding = (
        f"Evidence quality {round(q)} % from {st.summary.count} chunks in {st.summary.documents} documents "
        f"({st.official_count} official, {st.synthetic_count} synthetic); coverage {round(st.summary.coverage * 100)} %."
    )
    return AgentOutput(
        agent="nasa_data_scientist",
        finding=finding,
        evidence=refs_for(ctx, n=4),
        confidence=round(q / 100, 2),
        verdict=verdict,
        uncertainties=_unc(ctx),
        limitations=_lims(ctx, "Coverage is measured by tag, not by reading comprehension."),
        payload={
            "coverage": st.summary.coverage,
            "official": st.official_count,
            "synthetic": st.synthetic_count,
        },
    )


def fire_risk(ctx: Context) -> AgentOutput:
    ctx.broker.call("fire", "read:evidence", lambda: None)
    ctx.broker.call("fire", "write:risk", lambda: None)
    r = ctx.risk
    top = [d.name.lower() for d in r.drivers[:3]]
    return AgentOutput(
        agent="fire_risk",
        finding=f"Fire risk {r.level} (score {r.score}/100). Top drivers: {', '.join(top)}.",
        evidence=refs_for(ctx, ("flame_spread", "ignition")),
        confidence=round(r.score / 100, 2),
        verdict=r.level,
        uncertainties=_unc(ctx),
        limitations=_lims(ctx),
        payload={
            "risk_level": r.level,
            "risk_score": r.score,
            "drivers": top,
            "spread_potential": r.spread_potential,
        },
    )


def mission_safety(ctx: Context) -> AgentOutput:
    ctx.broker.call("safety", "read:evidence", lambda: None)
    ctx.broker.call("safety", "write:risk", lambda: None)
    r = ctx.risk
    rec = "Isolate and protect crew" if LEVELS.index(r.level) >= 2 else "Monitor"
    return AgentOutput(
        agent="mission_safety",
        finding=f"Crew risk {r.crew_level}. Habitat module {'at risk' if LEVELS.index(r.level) >= 2 else 'stable'}.",
        evidence=refs_for(ctx, ("fire_safety", "suppression")),
        confidence=round(min(1.0, r.score * 0.88 / 100), 2),
        verdict=f"{r.crew_level} crew risk",
        uncertainties=_unc(ctx),
        limitations=_lims(ctx),
        recommendation=rec,
        payload={"crew_risk": r.crew_level},
    )


def red_team_agent(ctx: Context) -> AgentOutput:
    ctx.broker.call("red", "read:evidence", lambda: None)
    ctx.broker.call("red", "challenge:risk", lambda: None)
    unres = [c for c in ctx.challenges if not c.passed]
    passed = not any(c.severity == "HIGH" for c in unres) and len(unres) <= 1
    return AgentOutput(
        agent="red_team",
        finding=f"{len(ctx.challenges)} challenges raised, {len(unres)} unresolved.",
        evidence=refs_for(ctx, n=2),
        confidence=round(max(0.05, 1 - 0.18 * len(unres)), 2),
        verdict="CHALLENGE PASSED" if passed else "CHALLENGE RAISED",
        uncertainties=[c.challenge for c in unres],
        limitations=_lims(ctx),
        payload={"challenges": [c.model_dump() for c in ctx.challenges]},
    )


def guardian(ctx: Context) -> AgentOutput:
    ctx.broker.call("guardian", "read:evidence", lambda: None)
    ctx.broker.call("guardian", "validate:risk", lambda: None)
    t = ctx.trust
    return AgentOutput(
        agent="scientific_guardian",
        finding=t.verdict,
        evidence=refs_for(ctx, n=2),
        confidence=round(t.score / 100, 2),
        verdict=t.guardian_status,
        uncertainties=[g.label for g in t.gates if g.status == "fail"],
        limitations=[t.note],
        payload={
            "trust_score": t.score,
            "band": t.band,
            "gates": [{"gate": g.label, "status": g.status} for g in t.gates],
        },
    )


def commander(ctx: Context) -> AgentOutput:
    ctx.broker.call("commander", "read:evidence", lambda: None)
    ctx.broker.call("commander", "request:command", lambda: None)
    t, d, r = ctx.trust, ctx.decision, ctx.risk
    recommends = t.guardian_status == "TRUSTED" and not t.insufficient_evidence
    conf = max(
        0.0,
        min(1.0, 0.5 * (ctx.stats.quality - ctx.pen * 0.5) / 100 + 0.5 * ctx.trust.components[3].score / 100),
    )
    return AgentOutput(
        agent="mission_commander",
        finding=(
            "Recommends the listed actions for human approval."
            if recommends
            else (
                INSUFFICIENT_EVIDENCE_TEXT
                if t.insufficient_evidence
                else "Holding for human review before any action."
            )
        ),
        evidence=refs_for(ctx, n=2),
        confidence=round(conf, 2),
        verdict="RECOMMENDS" if recommends else "HOLD FOR REVIEW",
        uncertainties=_unc(ctx),
        limitations=[LIMIT, "All actions are simulated. A human must approve."],
        recommendation="; ".join(a.title for a in d.actions),
        payload={
            "risk": r.level,
            "human_approval_required": True,
            "simulated_only": True,
            "recommended_actions": [a.title for a in d.actions],
        },
    )


ROLE_FUNCS = {
    "scientist": scientist,
    "data": data_scientist,
    "fire": fire_risk,
    "safety": mission_safety,
    "red": red_team_agent,
    "guardian": guardian,
    "commander": commander,
}
