# Threat model

Scope: this application. Security tests are local; nothing here targets an external system.

| # | Threat | Defence | Where | Test |
|---|---|---|---|---|
| 1 | Evidence tampering (altered NASA text) | SHA-256 per document, sealed manifest, quarantine, restore | `security/integrity.py` | `tests/security` |
| 2 | Prompt injection in retrieved text | Normalisation (NFKC, zero-width, homoglyphs), precision-tuned patterns, scan at ingest **and** retrieval, high severity excluded | `security/injection.py`, `rag/retriever.py` | `tests/unit/test_injection.py`, `tests/evaluation/test_injection_precision.py` (benign combustion text must not trigger) |
| 3 | Injection via search box | Instruction-like queries rejected (400) | `api/routes.py` | `tests/integration` |
| 4 | Hallucinated or fabricated citations | Output validation: cited IDs must be in the retrieved set | `security/validation.py` | attack suite |
| 5 | Agent privilege escalation / command execution | Least-privilege matrix; `execute:command` and `admin:users` denied to every agent; tool broker logs each call | `security/policy.py` | attack suite |
| 6 | Unauthorised use | JWT + RBAC (viewer/analyst/commander/admin), role re-read from DB per request | `security/auth.py`, `rbac.py` | integration |
| 7 | Brute force / abuse | Per-IP and per-user rate limits (Redis, memory fallback), login limit | `security/ratelimit.py`, `main.py` | `test_login_rate_limit` |
| 8 | Oversized or malformed input | 64 KB body cap, strict Pydantic schemas (`extra=forbid`, ranges) | `main.py`, `schemas.py` | integration |
| 9 | Audit tampering | Hash-chained audit log, verified on read | `security/audit.py` | unit |
| 10 | Silent extrapolation | Envelope check; out-of-range lowers trust and raises a HIGH challenge | `risk/envelope.py` | evaluation |
| 11 | Unsafe autonomy | Human approval, two-step confirm, command simulator only | `services/mission.py`, `simulation/command_sim.py` | integration |
| 12 | Malicious download | HTTPS and `*.nasa.gov` only, re-checked on redirects, size cap | `evidence/ntrs.py` | `tests/integration/test_ingest.py` |
| 13 | Weak deployment | Production mode refuses default JWT secret or seed password; non-root containers; CSP and security headers | `config.py`, Dockerfiles, `nginx.conf` | unit |

## Security Center demos

Tamper, inject and restore act on a **simulated overlay** or clearly labelled `DEMO-attack` rows. Original documents are never modified.
Disable with `ENABLE_SECURITY_DEMO=false`. `POST /api/security/red-team` runs ten local attack simulations and reports how many were blocked.

## Out of scope / residual risk

Regex-based injection detection can be evaded by novel phrasing; the real protection is architectural (retrieved text is data, scores are
computed in code, no agent has command rights, a human approves). Dependencies are pinned by range, not audited line by line.
