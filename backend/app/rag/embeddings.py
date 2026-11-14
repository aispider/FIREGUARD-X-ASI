"""Embeddings.

`hash`   : deterministic lexical embedding (signed feature hashing of unigrams and bigrams, after mapping
           combustion vocabulary onto canonical terms). No network, no key. It matches vocabulary, not meaning,
           and the UI says so.
`openai` : OpenAI embeddings reduced to 384 dimensions with the API's `dimensions` parameter.

Switching provider requires re-embedding stored chunks: `python -m app.evidence.cli reembed`.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Protocol

import httpx

from app.config import EMBED_DIM, get_settings

_PHRASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p, re.I), r)
    for p, r in [
        (r"\bflow\s+velocit(?:y|ies)\b", " airflow "),
        (r"\bforced[\s-]+flow\b", " airflow "),
        (r"\bflow\s+speeds?\b", " airflow "),
        (r"\bair\s+flow\b", " airflow "),
        (r"\bwind\s+tunnel\b", " airflow "),
        (r"\bventilation\b", " airflow "),
        (r"\boxygen\s+(?:concentration|percentage|level|content)s?\b", " oxygen "),
        (r"\bO\s?2\b|O₂", " oxygen "),
        (r"\boxidi[sz]er\b", " oxygen "),
        (r"\bmicro[\s-]?gravity\b|\bzero[\s-]gravity\b|\bweightless(?:ness)?\b", " microgravity "),
        (r"\breduced[\s-]gravity\b|\blow[\s-]gravity\b", " microgravity "),
        (r"\bflame[\s-]spread(?:ing)?\b", " flamespread "),
        (r"\bflame\s+growth\b", " flamespread "),
        (
            r"\bextinguish(?:ment|ed|ing)?\b|\bextinction\b|\bblow[\s-]?off\b|\bquench(?:ing)?\b",
            " extinction ",
        ),
        (r"\bpoly\s?methyl\s?methacrylate\b|\bPMMA\b|\bacrylic\b", " pmma "),
        (r"\bfire\s+safety\b|\bspacecraft\s+fire\b", " firesafety "),
    ]
]
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "were",
        "which",
        "with",
        "we",
        "can",
        "used",
        "using",
        "use",
        "also",
        "these",
        "those",
        "than",
        "into",
        "such",
        "not",
        "been",
        "being",
        "more",
        "most",
        "may",
        "other",
        "our",
    ]
)


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _stem(t: str) -> str:
    """Tiny plural folding so 'sensors' and 'sensor' share a feature."""
    if len(t) > 5 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("s") and not t.endswith(("ss", "us", "is")):
        return t[:-1]
    return t


def _tokens(text: str) -> list[str]:
    for pat, rep in _PHRASES:
        text = pat.sub(rep, text)
    return [_stem(t) for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


def _bucket(token: str) -> tuple[int, float]:
    h = hashlib.blake2b(token.encode(), digest_size=8).digest()
    n = int.from_bytes(h, "big")
    return n % EMBED_DIM, 1.0 if (n >> 40) & 1 else -1.0


class HashEmbedder:
    name = "hash-v1"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    @staticmethod
    def _one(text: str) -> list[float]:
        toks = _tokens(text)
        feats = Counter(toks)
        feats.update(f"{a}_{b}" for a, b in zip(toks, toks[1:], strict=False))
        vec = [0.0] * EMBED_DIM
        for tok, tf in feats.items():
            idx, sign = _bucket(tok)
            vec[idx] += sign * (1.0 + math.log(tf))
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class OpenAIEmbedder:
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self._key, self._model = api_key, model

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 64):
            batch = texts[i : i + 64]
            r = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._key}"},
                json={"model": self._model, "input": batch, "dimensions": EMBED_DIM},
                timeout=60,
            )
            r.raise_for_status()
            rows = sorted(r.json()["data"], key=lambda d: d["index"])
            out.extend([[float(x) for x in d["embedding"]] for d in rows])
        return out


def get_embedder() -> Embedder:
    s = get_settings()
    if s.embedding_provider == "openai":
        if not s.openai_api_key:
            raise RuntimeError("EMBEDDING_PROVIDER=openai requires OPENAI_API_KEY")
        return OpenAIEmbedder(s.openai_api_key, s.openai_embedding_model)
    return HashEmbedder()


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))
