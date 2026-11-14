"""Validate agent output before anything downstream uses it."""

from __future__ import annotations

import re

from app.schemas import AgentOutput
from app.security import injection

_EXEC_CLAIM = re.compile(
    r"\b(?:i|we)\s+(?:have\s+)?(?:executed|launched|sent|commanded|fired|released)\b|command\s+(?:was\s+)?executed",
    re.I,
)


def validate_output(out: AgentOutput, allowed_ids: set[str]) -> list[str]:
    """Returns a list of problems; empty means the output is valid."""
    errs: list[str] = []
    for ref in out.evidence:
        if ref.source_id not in allowed_ids:
            errs.append(f"cites unknown evidence id {ref.source_id}")
    blob = " ".join([out.finding, out.recommendation or "", *out.uncertainties, *out.limitations])
    sc = injection.scan(blob)
    if sc.detected and sc.exclude:
        errs.append("output contains instruction-like text: " + ", ".join(sc.flags))
    if _EXEC_CLAIM.search(blob):
        errs.append("output claims an action was executed")
    if not out.limitations:
        errs.append("missing limitations")
    return errs
