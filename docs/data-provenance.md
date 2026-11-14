# Data provenance

## Three layers, never mixed

1. **NASA evidence** — text from documents ingested from NASA sources, with full provenance.
2. **Prototype assumptions** — model weights, multipliers, thresholds, the tested envelope. Listed in `backend/app/risk/assumptions.py` and shown in the app.
3. **SYNTHETIC/DEMO values** — nine short offline passages (`backend/app/evidence/synthetic.py`) and the demo scenarios. They describe modelling assumptions
   qualitatively, do not report experimental results, carry a banner in their text, `synthetic=true` in the database and manifest, and a label in the UI.

## What is recorded per document

`doc_key` (e.g. `NTRS-<id>`), title, source, source URL, NTRS ID, document type, publication date, centre, licence/copyright determination,
distribution, version, retrieval time, SHA-256 of the extracted text, SHA-256 of the downloaded bytes, byte length, processing status.
Metadata is read from the NTRS record, never hand-typed. The same fields are mirrored into `data/manifests/manifest.json`.

## Pipeline (`backend/app/evidence/ingest.py`)

metadata → distribution check (PUBLIC only) → download PDF (or fall back to the abstract) → text extraction → quality gates (minimum length, relevance
terms, alphabetic ratio) → SHA-256 → upsert with version bump if content changed → chunk → injection scan → tag (variables, materials, gravity, topic)
→ embed → write raw file under `data/raw/ntrs/` → seal manifest → audit entry. Failures are recorded with an error and excluded.

## Sources

`backend/app/evidence/catalog.py`: BASS-II, SoFIE, ACME, Saffire and general spacecraft fire safety. It lists a few NTRS IDs that NASA web searches returned
for these investigations, plus NTRS search queries. **No finding is asserted in the catalog**; each candidate is kept only if its own text is about combustion or
fire safety. Public pages: the NASA BASS-II station page and the PSI spotlight blog on science.data.nasa.gov.

## Numeric data

Drop PSI CSV exports in `data/raw/psi/` (see README). They become `observations`, are linked to a sealed document, and set the envelope
(`envelope_source: nasa_observations`). Without them the envelope is `prototype_assumption`.

## Licensing

NASA-authored works are generally public, but each NTRS record carries its own copyright determination, stored in `documents.license`. Check it
before redistributing downloaded files. This repository does not ship NASA documents.
