"""Rule-based tagging of evidence text: experimental variables, fuel materials, gravity regime, topic.

These tags are extracted from the text itself. They never add information that is not in the chunk.
"""

from __future__ import annotations

import re

_V = re.IGNORECASE
VARIABLE_PATTERNS: dict[str, re.Pattern[str]] = {
    "oxygen": re.compile(r"\boxygen\b|\bO2\b|O₂|oxidi[sz]er", _V),
    "airflow": re.compile(
        r"\bairflow\b|\bair\s+flow\b|flow\s+velocit|forced[\s-]flow|flow\s+speed|ventilation|wind\s+tunnel"
        r"|flow\s+duct|concurrent\s+flow|opposed\s+flow|low[\s-]speed\s+flow|\bflow\b.{0,30}\b(?:cm/s|m/s)\b",
        _V,
    ),
    "pressure": re.compile(r"\bpressure\b|\bkpa\b|\bpsi\b|\batmospheres?\b", _V),
    "temperature": re.compile(r"\btemperature\b|\bkelvin\b|preheat", _V),
    "geometry": re.compile(
        r"\bgeometry\b|\bthickness\b|\bthin\b|\bthick\b|\bcylind|\bslab\b|sample\s+(?:size|shape|width)", _V
    ),
    "heating": re.compile(r"external\s+heating|internal\s+heating|heat\s+flux|radiant|preheat", _V),
    "extinction": re.compile(r"extinction|extinguish|quench|blow[\s-]?off", _V),
    "flame spread": re.compile(r"flame[\s-]spread|spread\s+rate|flame\s+growth", _V),
    "ignition": re.compile(r"\bignit", _V),
    "soot": re.compile(r"\bsoot\b", _V),
    "stability": re.compile(r"flame\s+stabilit|stable\s+flame", _V),
    "suppression": re.compile(r"suppress|fire\s+detection", _V),
    "large-scale": re.compile(r"large[\s-]scale|\bsaffire\b|\bcygnus\b", _V),
    "flammability": re.compile(r"flammab", _V),
}

MATERIAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "PMMA": re.compile(r"\bPMMA\b|poly\s?methyl\s?methacrylate|\bacrylic\b|plexiglas", _V),
    "Cotton-fiberglass fabric": re.compile(
        r"\bSIBAL\b|cotton[\s-]*(?:and\s+)?fib(?:er|re)glass|\bcotton\b", _V
    ),
    "Polyethylene": re.compile(r"polyethylene|\bHDPE\b|\bLDPE\b", _V),
    "Silicone": re.compile(r"\bsilicone\b", _V),
    "Nomex fabric": re.compile(r"\bnomex\b", _V),
}

_MICROG = re.compile(r"micro[\s-]?gravity|zero[\s-]gravity|weightless", _V)
_REDUCED = re.compile(
    r"reduced[\s-]gravity|low[\s-]gravity|partial[\s-]gravity|\blunar\b|\bmartian\b|\bmars\b", _V
)
_NORMAL = re.compile(r"normal[\s-]gravity|\bearth\b|\b1[\s-]?g\b", _V)

_TOPIC_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("extinction", VARIABLE_PATTERNS["extinction"]),
    ("flame_spread", VARIABLE_PATTERNS["flame spread"]),
    ("ignition", VARIABLE_PATTERNS["ignition"]),
    ("fire_safety", re.compile(r"fire[\s-]safety|fire\s+prevention|fire\s+detection|suppress", _V)),
    ("flammability", VARIABLE_PATTERNS["flammability"]),
]


def tag_variables(text: str) -> list[str]:
    return [name for name, pat in VARIABLE_PATTERNS.items() if pat.search(text)]


def tag_materials(text: str) -> list[str]:
    return [name for name, pat in MATERIAL_PATTERNS.items() if pat.search(text)]


def tag_gravity(text: str) -> str:
    if _MICROG.search(text):
        return "microgravity"
    if _REDUCED.search(text):
        return "reduced"
    if _NORMAL.search(text):
        return "normal"
    return "unspecified"


def tag_topic(text: str) -> str:
    best, best_n = "combustion", 0
    for topic, pat in _TOPIC_RULES:
        n = len(pat.findall(text))
        if n > best_n:
            best, best_n = topic, n
    return best
