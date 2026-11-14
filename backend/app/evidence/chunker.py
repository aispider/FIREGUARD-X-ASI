"""Split a document into citable chunks, keeping page numbers when the source has them."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RawChunk:
    text: str
    page: int | None


_WS = re.compile(r"[ \t]+")


def _alpha_ratio(s: str) -> float:
    letters = sum(c.isalpha() for c in s)
    return letters / max(1, len(s))


def chunk_text(text: str, max_chars: int = 1000, overlap: int = 150, min_chars: int = 220) -> list[RawChunk]:
    chunks: list[RawChunk] = []
    pages = text.split("\f") if "\f" in text else [text]
    has_pages = len(pages) > 1
    for page_no, page in enumerate(pages, start=1):
        paras = [_WS.sub(" ", p).strip() for p in re.split(r"\n\s*\n", page)]
        paras = [p.replace("\n", " ") for p in paras if p]
        buf = ""
        for para in paras:
            # Split long paragraphs on sentence boundaries.
            parts = re.split(r"(?<=[.!?])\s+", para) if len(para) > max_chars else [para]
            for part in parts:
                if buf and len(buf) + len(part) + 1 > max_chars:
                    chunks.append(RawChunk(buf.strip(), page_no if has_pages else None))
                    tail = buf[-overlap:] if overlap else ""
                    buf = (tail.split(" ", 1)[-1] + " " + part) if tail else part
                else:
                    buf = f"{buf} {part}".strip()
        if buf.strip():
            chunks.append(RawChunk(buf.strip(), page_no if has_pages else None))
    # Merge fragments that are too short into the previous chunk; drop number-heavy table debris.
    merged: list[RawChunk] = []
    for c in chunks:
        if _alpha_ratio(c.text) < 0.55:
            continue
        if merged and len(c.text) < min_chars and merged[-1].page == c.page:
            merged[-1] = RawChunk(f"{merged[-1].text} {c.text}", c.page)
        else:
            merged.append(c)
    return [c for c in merged if len(c.text) >= min_chars // 2]
