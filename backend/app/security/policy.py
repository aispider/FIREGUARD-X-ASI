"""Least-privilege policy: what each agent may do, and when a command may even be *simulated*.

No agent can execute a command. `execute:command` and `admin:users` are denied to every agent, always.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.schemas import PolicyDecisionOut

ACTIONS = [
    "read:evidence",
    "read:risk",
    "write:risk",
    "challenge:risk",
    "validate:risk",
    "request:command",
    "execute:command",
    "admin:users",
]
DENIED_ALWAYS = ["execute:command", "admin:users"]

AGENT_PERMISSIONS: dict[str, list[str]] = {
    "scientist": ["read:evidence", "read:risk"],
    "data": ["read:evidence", "read:risk"],
    "fire": ["read:evidence", "write:risk"],
    "safety": ["read:evidence", "write:risk"],
    "red": ["read:evidence", "challenge:risk"],
    "guardian": ["read:evidence", "validate:risk"],
    "commander": ["read:evidence", "final:risk", "request:command"],
}


def check(agent: str, action: str) -> PolicyDecisionOut:
    if action in DENIED_ALWAYS:
        return PolicyDecisionOut(
            allowed=False, reason=f"'{action}' is denied to every agent. Agents advise; humans decide."
        )
    if agent not in AGENT_PERMISSIONS:
        return PolicyDecisionOut(allowed=False, reason=f"Unknown agent '{agent}'.")
    if action in AGENT_PERMISSIONS[agent]:
        return PolicyDecisionOut(allowed=True, reason=f"{agent} holds '{action}'.")
    return PolicyDecisionOut(allowed=False, reason=f"{agent} does not hold '{action}'.")


def matrix() -> dict[str, Any]:
    from app.agents.base import AGENT_SPECS

    return {
        "agents": [
            {
                "key": a.key,
                "name": a.name,
                "role": a.role,
                "grants": {
                    act: act in AGENT_PERMISSIONS[a.key] and act not in DENIED_ALWAYS for act in ACTIONS
                },
            }
            for a in AGENT_SPECS
        ],
        "actions": ACTIONS,
        "denied_always": DENIED_ALWAYS,
    }


class PermissionDenied(PermissionError):
    pass


@dataclass
class ToolBroker:
    """Every data access an agent makes goes through here, is permission-checked and logged."""

    log: list[dict[str, str]] = field(default_factory=list)

    def call(self, agent: str, action: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        d = check(agent, action)
        self.log.append({"agent": agent, "action": action, "allowed": str(d.allowed).lower()})
        if not d.allowed:
            raise PermissionDenied(d.reason)
        return fn(*args, **kwargs)


def command_policy(
    *,
    guardian_status: str,
    trust_band: str,
    insufficient: bool,
    decision: str,
    can_decide: bool,
    confirmed: bool,
) -> PolicyDecisionOut:
    """May a human approval proceed to the *command simulator*? (Never to a real command.)"""
    if not can_decide:
        return PolicyDecisionOut(allowed=False, reason="Your role cannot approve actions.")
    if decision == "reject":
        return PolicyDecisionOut(allowed=True, reason="Rejection recorded. No simulation runs.")
    if insufficient:
        return PolicyDecisionOut(
            allowed=False,
            reason="INSUFFICIENT EVIDENCE — HUMAN REVIEW REQUIRED. Approval is blocked until evidence improves.",
        )
    if guardian_status == "REJECTED" or trust_band == "REJECT":
        return PolicyDecisionOut(
            allowed=False, reason="The Scientific Guardian rejected this recommendation."
        )
    if not confirmed:
        return PolicyDecisionOut(
            allowed=False, reason="Second confirmation required: send confirm=true to run the simulator."
        )
    note = (
        ""
        if guardian_status == "TRUSTED"
        else " Guardian status is REQUIRES REVIEW; your approval is recorded as a human override."
    )
    return PolicyDecisionOut(
        allowed=True,
        reason="Approved by a human. The command simulator will run; nothing is sent to any spacecraft."
        + note,
    )
