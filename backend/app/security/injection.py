"""Prompt-injection defense for retrieved text.

Rule: retrieved scientific content is DATA, never instructions. Every chunk is scanned at ingestion and again
at retrieval. Instruction-like spans are replaced with a marker, and high-severity chunks are excluded from
evidence altogether.

The patterns target instruction-like phrasing aimed at an AI system, not ordinary scientific English. The
evaluation tests run them against benign combustion sentences to keep false positives low.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

REMOVED = "[REMOVED:INSTRUCTION]"

# (compiled pattern, label, severity)
_RAW_PATTERNS: list[tuple[str, str, str]] = [
    (
        r"ignore\s+(?:all\s+|any\s+|the\s+|your\s+)*(?:previous|prior|above|earlier|preceding)\s+"
        r"(?:instructions?|prompts?|rules?|directions?)",
        "override previous instructions",
        "HIGH",
    ),
    (
        r"disregard\s+(?:all\s+|any\s+|the\s+|your\s+)*(?:previous|prior|above|earlier|system)?\s*"
        r"(?:instructions?|prompts?|rules?|guidelines?)",
        "disregard instructions",
        "HIGH",
    ),
    (
        r"(?:give|set|return|output|report|respond\s+with|answer)\s+(?:a\s+|an\s+|the\s+)?"
        r"(?:\w+\s+){0,2}(?:critical|low|high|medium)\s+(?:risk|score|rating|level)",
        "forces a risk result",
        "HIGH",
    ),
    (
        r"(?:reveal|print|show|display|leak|output)\s+(?:\w+\s+){0,3}"
        r"(?:system\s+prompt|hidden\s+prompt|api[\s_-]?key|secret|password|credentials?)",
        "secret exfiltration",
        "HIGH",
    ),
    (r"you\s+are\s+now\s+(?:a|an|the|in)\b", "role hijack", "HIGH"),
    (
        r"act\s+as\s+(?:a|an|the)?\s*(?:ai|assistant|system|developer|administrator|admin|jailbroken|dan)\b",
        "role hijack",
        "HIGH",
    ),
    (r"\bnew\s+(?:system\s+)?instructions?\s*:", "instruction injection", "HIGH"),
    (r"^\s*(?:system|assistant|developer)\s*:", "fake role marker", "HIGH"),
    (r"<\s*(?:system|assistant|instructions?)\s*>", "fake role marker", "HIGH"),
    (r"<\s*script\b|javascript\s*:|data\s*:\s*text/html", "active content", "HIGH"),
    (
        r"\b(?:execute|run|invoke|call)\s+(?:the\s+)?(?:command|tool|function|shell)\b",
        "tool invocation attempt",
        "MEDIUM",
    ),
    (r"do\s+not\s+(?:tell|inform|alert)\s+the\s+(?:user|operator|crew)", "concealment instruction", "HIGH"),
    (
        r"(?:override|bypass|disable)\s+(?:the\s+)?(?:safety|guardian|trust|human\s+approval)",
        "bypass attempt",
        "HIGH",
    ),
]

_PATTERNS = [(re.compile(p, re.IGNORECASE | re.MULTILINE), label, sev) for p, label, sev in _RAW_PATTERNS]

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
# Common look-alike letters used to dodge keyword filters.
_HOMOGLYPHS = str.maketrans(
    {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "і": "i", "ѕ": "s", "ԁ": "d", "ɡ": "g"}
)


def normalize(text: str) -> str:
    """NFKC, strip zero-width characters, fold common homoglyphs, collapse whitespace."""
    t = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH).translate(_HOMOGLYPHS)
    return re.sub(r"[ \t\r\f\v]+", " ", t)


@dataclass
class ScanResult:
    detected: bool = False
    flags: list[str] = field(default_factory=list)
    clean_text: str = ""
    severity: str | None = None

    @property
    def exclude(self) -> bool:
        """High-severity hits are excluded from evidence, not merely scrubbed."""
        return self.severity == "HIGH"


def scan(text: str) -> ScanResult:
    norm = normalize(text)
    flags: list[str] = []
    severity: str | None = None
    clean = norm
    for pattern, label, sev in _PATTERNS:
        if pattern.search(norm):
            if label not in flags:
                flags.append(label)
            if severity != "HIGH":
                severity = sev
            clean = pattern.sub(REMOVED, clean)
    return ScanResult(detected=bool(flags), flags=flags, clean_text=clean, severity=severity)
