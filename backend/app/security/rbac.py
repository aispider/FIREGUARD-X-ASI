"""Role-based access control. Roles map to permission strings; endpoints declare what they need."""

from __future__ import annotations

ALL_PERMISSIONS = [
    "evidence:read",
    "evidence:search",
    "simulation:run",
    "analysis:run",
    "risk:read",
    "risk:assess",
    "agents:council",
    "security:read",
    "security:validate",
    "security:red_team",
    "security:demo",
    "audit:read",
    "approval:decide",
    "ingest:run",
    "admin:users",
]

_VIEWER = [
    "evidence:read",
    "evidence:search",
    "simulation:run",
    "analysis:run",
    "risk:read",
    "security:read",
    "audit:read",
]
_ANALYST = [*_VIEWER, "risk:assess", "agents:council", "security:validate", "security:red_team"]
_COMMANDER = [*_ANALYST, "approval:decide"]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "viewer": _VIEWER,
    "analyst": _ANALYST,
    "commander": _COMMANDER,
    "admin": list(ALL_PERMISSIONS),
}


def permissions_for(role: str) -> list[str]:
    return list(ROLE_PERMISSIONS.get(role, []))
