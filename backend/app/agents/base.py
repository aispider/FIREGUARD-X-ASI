"""Agent identity, shared context and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas import AgentIdentity, AgentOutput, Challenge, EvidenceRef, RiskOut, ScenarioIn
from app.security.hashing import hash_json
from app.security.policy import AGENT_PERMISSIONS, ToolBroker
from app.security.trust import EvidenceStats

AGENT_VERSION = "1.0.0"


@dataclass(frozen=True)
class AgentSpec:
    key: str
    code: str
    name: str
    role: str


AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec("scientist", "SCI", "Combustion scientist", "COMBUSTION_SCIENTIST"),
    AgentSpec("data", "DAT", "NASA data scientist", "NASA_DATA"),
    AgentSpec("fire", "FIR", "Fire risk", "FIRE_RISK"),
    AgentSpec("safety", "SAF", "Mission safety", "MISSION_SAFETY"),
    AgentSpec("red", "RED", "Adversarial red team", "RED_TEAM"),
    AgentSpec("guardian", "GRD", "Scientific guardian", "GUARDIAN"),
    AgentSpec("commander", "CMD", "Mission commander", "COMMANDER"),
)
SPEC_BY_KEY = {a.key: a for a in AGENT_SPECS}


@dataclass
class Context:
    scenario: ScenarioIn
    risk: RiskOut
    pen: float
    used: list[Any]  # retriever Candidates, status 'used'
    stats: EvidenceStats
    challenges: list[Challenge] = field(default_factory=list)
    trust: Any = None  # TrustOut, set before guardian runs
    decision: Any = None  # DecisionOut, set before commander runs
    broker: ToolBroker = field(default_factory=ToolBroker)
    mode: str = "demo"
    narrate: Any = None  # optional callable(agent_key, facts) -> str | None


def refs_for(ctx: Context, topics: tuple[str, ...] = (), n: int = 3) -> list[EvidenceRef]:
    """Cite the most relevant used chunks, preferring the given topics or variables."""
    pool = ctx.used
    if topics:
        pref = [c for c in pool if c.chunk.topic in topics or set(topics) & set(c.chunk.variables)]
        pool = pref or pool
    out = []
    for c in pool[:n]:
        claim = c.text.strip().split(". ")[0][:160]
        out.append(
            EvidenceRef(source_id=c.chunk.chunk_key, claim=claim, confidence=round(min(1.0, c.relevance), 2))
        )
    return out


def identity(spec: AgentSpec, ctx: Context, out: AgentOutput, model: str) -> AgentIdentity:
    inp = {
        "scenario": ctx.scenario.model_dump(mode="json"),
        "evidence": [[c.chunk.chunk_key, c.chunk.content_hash] for c in ctx.used],
    }
    return AgentIdentity(
        agent_id=f"fireguard.{spec.key}",
        role=spec.role,
        version=AGENT_VERSION,
        model=model,
        permissions=[p for p in AGENT_PERMISSIONS[spec.key]],
        input_hash=hash_json(inp),
        output_hash=hash_json(out.model_dump(mode="json")),
    )
