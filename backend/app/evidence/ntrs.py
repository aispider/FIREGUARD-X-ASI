"""Minimal NASA NTRS client with an allowlist, size cap and manual redirect checks."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.config import get_settings

ALLOWED_SUFFIXES = (".nasa.gov",)
MAX_REDIRECTS = 4


class FetchError(RuntimeError):
    pass


def host_allowed(url: str) -> bool:
    p = urlparse(url)
    host = (p.hostname or "").lower()
    return p.scheme == "https" and any(host == s[1:] or host.endswith(s) for s in ALLOWED_SUFFIXES)


@dataclass
class Fetched:
    url: str
    content: bytes
    content_type: str


def safe_get(url: str, *, accept: str = "*/*", client: httpx.Client | None = None) -> Fetched:
    """GET with: https + *.nasa.gov only (re-checked on every redirect), streaming size cap, retries."""
    s = get_settings()
    own = client is None
    c = client or httpx.Client(
        timeout=s.ingest_timeout_s,
        follow_redirects=False,
        headers={"User-Agent": "FIREGUARD-X/1.0 (NASA Space Apps research prototype)"},
    )
    try:
        last: Exception | None = None
        for attempt in range(3):
            try:
                cur = url
                for _ in range(MAX_REDIRECTS + 1):
                    if not host_allowed(cur):
                        raise FetchError(f"blocked host: {cur}")
                    with c.stream("GET", cur, headers={"Accept": accept}) as r:
                        if r.status_code in (301, 302, 303, 307, 308):
                            cur = urljoin(cur, r.headers.get("location", ""))
                            continue
                        if r.status_code >= 500 or r.status_code == 429:
                            raise FetchError(f"HTTP {r.status_code}")
                        if r.status_code != 200:
                            raise FetchError(f"HTTP {r.status_code} for {cur}")
                        buf = bytearray()
                        for part in r.iter_bytes():
                            buf.extend(part)
                            if len(buf) > s.ingest_max_bytes:
                                raise FetchError("response larger than INGEST_MAX_BYTES")
                        return Fetched(cur, bytes(buf), r.headers.get("content-type", ""))
                raise FetchError("too many redirects")
            except (httpx.HTTPError, FetchError) as e:
                last = e
                if isinstance(e, FetchError) and (
                    "blocked" in str(e) or "larger" in str(e) or "HTTP 4" in str(e)
                ):
                    break
                time.sleep(1.5 * (attempt + 1))
        raise FetchError(str(last))
    finally:
        if own:
            c.close()


def get_record(ntrs_id: str) -> dict[str, Any]:
    base = get_settings().ntrs_base_url.rstrip("/")
    f = safe_get(f"{base}/api/citations/{ntrs_id}", accept="application/json")
    import json

    data = json.loads(f.content)
    if not isinstance(data, dict):
        raise FetchError("unexpected NTRS record shape")
    return data


def search(query: str, size: int = 8) -> list[dict[str, Any]]:
    import json
    from urllib.parse import quote

    base = get_settings().ntrs_base_url.rstrip("/")
    f = safe_get(f"{base}/api/citations/search?q={quote(query)}&page.size={size}", accept="application/json")
    data = json.loads(f.content)
    results = data.get("results", []) if isinstance(data, dict) else []
    return [r for r in results if isinstance(r, dict)]


def pdf_link(record: dict[str, Any]) -> str | None:
    base = get_settings().ntrs_base_url.rstrip("/")
    for d in record.get("downloads", []) or []:
        links = (d or {}).get("links", {}) or {}
        if links.get("pdf"):
            return urljoin(base + "/", links["pdf"])
    return None


def record_meta(record: dict[str, Any]) -> dict[str, Any]:
    pubs = record.get("publications") or []
    date = record.get("distributionDate") or (
        pubs[0].get("publicationDate") if pubs and isinstance(pubs[0], dict) else None
    )
    copyright_ = record.get("copyright") or {}
    return {
        "title": str(record.get("title") or "").strip(),
        "abstract": str(record.get("abstract") or "").strip(),
        "date": str(date)[:10] if date else None,
        "center": (
            (record.get("center") or {}).get("name") if isinstance(record.get("center"), dict) else None
        ),
        "document_type": record.get("stiType"),
        "distribution": record.get("distribution"),
        "license": (copyright_.get("determinationType") if isinstance(copyright_, dict) else None),
    }
