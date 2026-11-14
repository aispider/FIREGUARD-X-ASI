"""SHA-256 helpers and canonical JSON, shared by provenance, audit and agent identity."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, non-ASCII preserved."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def hash_json(obj: Any) -> str:
    return sha256_hex(canonical_json(obj))
