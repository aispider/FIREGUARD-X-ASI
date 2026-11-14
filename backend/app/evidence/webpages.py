"""Plain-text extraction for public NASA web pages and PDFs."""

from __future__ import annotations

import io
import re

from bs4 import BeautifulSoup


def html_to_text(raw: bytes) -> tuple[str, str]:
    soup = BeautifulSoup(raw, "html.parser")
    for t in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "svg"]):
        t.decompose()
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()
    return title, text


def pdf_to_text(raw: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:  # noqa: BLE001 - a bad page should not abort the document
            pages.append("")
    return "\f".join(pages)
