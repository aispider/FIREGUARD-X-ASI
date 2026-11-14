# AI Trust

The **Trust Score** (0–100) is a prototype metric defined by FIREGUARD-X. It is not NASA-approved.

| Component | Weight | How it is computed (`backend/app/security/trust.py`) |
|---|---|---|
| Evidence quality | 20 | 0.5 coverage + 0.3 diversity + 0.2 authority, minus an extrapolation penalty. Coverage = scenario aspects (oxygen, airflow, pressure, temperature, geometry, material, gravity) found in used chunks. Diversity = distinct documents and experiments. Authority = official 1.0, synthetic 0.35 |
| Source relevance | 20 | Mean relevance of the top three used chunks |
| Experimental match | 15 | 100 − 2 × envelope penalty |
| Agent consensus | 15 | Agreement of risk, crew risk and flame-growth levels, minus open challenges and invalid agents |
| Adversarial verification | 15 | Starts at 100; unresolved HIGH/MEDIUM/LOW challenges subtract 35/18/6 |
| Data integrity | 10 | 100 − 60 per quarantined document |
| Uncertainty | 5 | Falls with thin evidence, nonlinear airflow, extrapolation |

Bands: 0–49 **REJECT**, 50–69 **LOW CONFIDENCE**, 70–84 **REVIEW**, 85–100 **TRUSTED**.

## Seven gates

NASA evidence found · evidence relevant (≥ 70) · conditions match experiments · agent agreement (≥ 75 %) · adversarial challenge passed ·
data integrity verified · trust ≥ 85. The first gate shows **demo** (not pass) when the only evidence is synthetic; in `EVIDENCE_MODE=strict` it fails.
The Guardian reports TRUSTED only if the band is TRUSTED, all gates pass or are `demo`, and the evidence is sufficient.

## Insufficient evidence

If no usable evidence is retrieved, evidence quality is below 50, or (strict mode) no official evidence exists, the system returns exactly
`INSUFFICIENT EVIDENCE — HUMAN REVIEW REQUIRED.` and approval is blocked.

## Agent identity and audit

Each agent output carries `agent_id`, role, version, model, permissions, and SHA-256 hashes of its input and output (stored in `agent_runs`).
Every approval, login, tamper demo and ingestion is appended to the hash-chained audit log.

## What the system will not do

Claim superintelligence, invent NASA data, obey text found in documents, execute commands, or approve its own recommendations.
