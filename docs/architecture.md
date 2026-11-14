# Architecture

```
Browser (React/TS, voice layer) ──► nginx :8080 ──/api──► FastAPI :8000 ──► PostgreSQL + pgvector
                                                              │  └──────► Redis (rate limits, job queue)
                                                              └─ data/ (raw files, manifest.json)
                                   worker ── NTRS / science.nasa.gov ──► ingest ──► DB + data/
```

## One analysis, end to end (`backend/app/agents/orchestrator.py`)

1. **Integrity check** — every document's SHA-256 is compared with the stored hash and the sealed manifest. Mismatches are quarantined.
2. **Retrieve** (`rag/retriever.py`) — the scenario becomes a query; pgvector cosine search returns candidates, reranked by tag overlap
   (variables, material, gravity). Each candidate is re-scanned for instruction-like text. Quarantined or injected chunks are listed but never used.
3. **Risk model** (`risk/model.py`, assumptions in `risk/assumptions.py`) — a transparent weighted model; envelope check (`risk/envelope.py`).
4. **Seven agents** (`agents/roles.py`) — Combustion Scientist, NASA Data Scientist, Fire Risk, Mission Safety, Red Team, Scientific Guardian,
   Mission Commander. Each returns structured JSON with evidence IDs, confidence, uncertainties and limitations. Their outputs are validated
   (`security/validation.py`): unknown evidence IDs, instruction-like text or "I executed…" claims invalidate the output and lower consensus.
5. **Trust** (`security/trust.py`) — evidence quality, relevance, experimental match, consensus, adversarial score, integrity, uncertainty → 0–100.
6. **Decision** (`agents/decision.py`) — recommended actions, the approval chain, a debate transcript. Insufficient evidence returns exactly
   `INSUFFICIENT EVIDENCE — HUMAN REVIEW REQUIRED.`
7. **Approval** (`POST /api/approvals`) — human, two-step confirm, policy engine, then the **command simulator**. Nothing leaves the system.

Scores and levels come from code, not from agent prose, so a manipulated agent output cannot raise them. The optional LLM
(`LLM_ENABLED`) may only rephrase one finding sentence; its text is scanned and length-limited and it has no tools.

## Data model (`backend/app/models/tables.py`)

users/roles · experiments · documents (provenance, sha256, tamper overlay, quarantine flag) · evidence_chunks (384-d pgvector embedding, tags,
injection flags) · observations · scenarios · risk_assessments · agent_runs (identity, input/output hashes) · security_events ·
audit_logs (hash-chained) · approvals · ingestion_jobs. Migration: `backend/alembic/versions/0001_initial_schema.py`.

## Frontend

Vite + React 18 + TypeScript + Tailwind (preflight off) + Recharts. Nine screens in `src/screens`, a vertical sidebar and mission pipeline,
a login screen, debounced API calls, and a voice layer in `src/voice` (Web Speech API, `en-IN` voice preferred, command parser with unit tests).
Fonts are self-hosted. nginx sets a strict CSP and proxies `/api`.

## Embeddings

`EMBEDDING_PROVIDER=hash` (default): deterministic 384-d lexical hashing, no network or key. `openai`: OpenAI embeddings reduced to 384 dimensions.
Change provider, then `python -m app.evidence.cli reembed`.
