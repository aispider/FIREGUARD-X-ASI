"""Recommended actions, the human-approval chain and the council debate transcript."""

from __future__ import annotations

from app.risk.assumptions import LEVELS
from app.schemas import (
    INSUFFICIENT_EVIDENCE_TEXT,
    ActionStep,
    ChainLink,
    Challenge,
    DebateMessage,
    DecisionOut,
    RiskOut,
    TrustOut,
)


def actions_for(risk: RiskOut) -> list[ActionStep]:
    L = LEVELS.index(risk.level)
    flow = "Step airflow down in stages" if risk.nonlinear_airflow else "Reduce airflow"
    if L == 3:
        return [
            ActionStep(
                title="Isolate affected module", detail="Close hatches and shut the module ventilation loop."
            ),
            ActionStep(
                title=flow,
                detail="Lower flow in steps and confirm the flame responds before cutting further.",
            ),
            ActionStep(
                title="Initiate appropriate suppression procedure",
                detail="Release the fixed suppression agent for the module.",
            ),
            ActionStep(
                title="Protect the crew", detail="Breathing equipment on, move to the unaffected module."
            ),
            ActionStep(
                title="Monitor secondary ignition", detail="Watch adjacent fabric and cabling for hot spots."
            ),
            ActionStep(
                title="Re-evaluate after 30 seconds", detail="Council re-runs with fresh sensor data."
            ),
        ]
    if L == 2:
        return [
            ActionStep(
                title="Isolate affected module", detail="Close hatches and shut the module ventilation loop."
            ),
            ActionStep(title=flow, detail="Lower flow and verify the flame response."),
            ActionStep(title="Prepare suppression", detail="Arm the agent and pre-position the crew."),
            ActionStep(title="Continue monitoring", detail="Track flame growth and module temperature."),
            ActionStep(
                title="Re-evaluate after 30 seconds", detail="Council re-runs with fresh sensor data."
            ),
        ]
    if L == 1:
        return [
            ActionStep(
                title="Increase sensor sampling", detail="Switch smoke and temperature sensors to 1 Hz."
            ),
            ActionStep(
                title="Hold ventilation steady", detail="Avoid airflow changes until the trend is clear."
            ),
            ActionStep(
                title="Re-evaluate after 60 seconds", detail="Council re-runs with fresh sensor data."
            ),
        ]
    return [
        ActionStep(
            title="Continue routine monitoring",
            detail="No action needed. Conditions are inside the safe envelope.",
        )
    ]


def decide(risk: RiskOut, trust: TrustOut) -> DecisionOut:
    acts = actions_for(risk)
    if trust.insufficient_evidence:
        return DecisionOut(
            level=risk.level,
            actions=[
                ActionStep(
                    title="Escalate to human review",
                    detail="Evidence is insufficient to support a recommendation.",
                )
            ],
            insufficient_evidence=True,
            summary=INSUFFICIENT_EVIDENCE_TEXT,
        )
    return DecisionOut(
        level=risk.level,
        actions=acts,
        insufficient_evidence=False,
        summary=f"{risk.level} risk. {len(acts)} simulated action(s) proposed for human approval.",
    )


def chain_for(trust: TrustOut, decision: DecisionOut, approval: str = "pending") -> list[ChainLink]:
    g_ok = trust.guardian_status != "REJECTED" and not trust.insufficient_evidence
    pol_ok = g_ok
    return [
        ChainLink(
            key="recommendation",
            label="AI recommendation",
            status="fail" if trust.insufficient_evidence else "pass",
            value="insufficient evidence"
            if trust.insufficient_evidence
            else f"{len(decision.actions)} action(s)",
        ),
        ChainLink(
            key="guardian",
            label="Scientific guardian",
            status="pass"
            if trust.guardian_status == "TRUSTED"
            else "fail"
            if trust.guardian_status == "REJECTED"
            else "wait",
            value=trust.guardian_status,
        ),
        ChainLink(
            key="policy",
            label="Policy engine",
            status="pass" if pol_ok else "fail",
            value="allowed" if pol_ok else "blocked",
        ),
        ChainLink(
            key="human",
            label="Human approval",
            status="pass" if approval == "approved" else "fail" if approval == "rejected" else "wait",
            value=approval,
        ),
        ChainLink(key="simulator", label="Command simulator", status="sim", value="simulation only"),
    ]


def debate(
    risk: RiskOut, trust: TrustOut, challenges: list[Challenge], cites: list[str], top_drivers: list[str]
) -> list[DebateMessage]:
    c = cites[:2]
    unres = [x for x in challenges if not x.passed]
    msgs = [
        DebateMessage(
            speaker="fire",
            label="Fire risk",
            citations=c,
            text=f"I rate this {risk.level}, score {risk.score} out of 100. The main drivers are {', '.join(top_drivers)}.",
        ),
    ]
    if unres:
        top = sorted(unres, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[x.severity])[0]
        msgs.append(
            DebateMessage(
                speaker="red", label="Red team", citations=c, text=f"I challenge that. {top.challenge}"
            )
        )
        msgs.append(
            DebateMessage(
                speaker="dat",
                label="NASA data scientist",
                citations=c,
                text=f"Evidence quality is {round(trust.components[0].score)} percent across the retrieved chunks. {'Some of it is synthetic demo text.' if 'SYNTHETIC' in trust.note else ''}".strip(),
            )
        )
    else:
        msgs.append(
            DebateMessage(
                speaker="red",
                label="Red team",
                citations=c,
                text="I tried to break this and could not find an unresolved weakness.",
            )
        )
        msgs.append(
            DebateMessage(
                speaker="dat",
                label="NASA data scientist",
                citations=c,
                text=f"Evidence quality is {round(trust.components[0].score)} percent and it matches the conditions.",
            )
        )
    msgs.append(
        DebateMessage(
            speaker="grd",
            label="Scientific guardian",
            citations=[],
            text=f"Trust score {trust.score}, band {trust.band}. {trust.verdict}",
        )
    )
    msgs.append(
        DebateMessage(
            speaker="cmdr",
            label="Mission commander",
            citations=[],
            text="I will not recommend action on this evidence. A human must review it."
            if trust.guardian_status != "TRUSTED"
            else "I recommend these steps for human approval. They run in simulation only.",
        )
    )
    msgs.append(
        DebateMessage(
            speaker="con",
            label="Consensus",
            citations=[],
            text=f"Open items: {len(unres)}. Human approval is required for every action.",
        )
    )
    return msgs
