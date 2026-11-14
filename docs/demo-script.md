# Demo script (about 5 minutes)

Setup: `docker compose up --build`, open http://localhost:8080, wait for `docker compose logs worker` to show the ingestion finishing (or demo on synthetic evidence — the UI says so).

1. **Frame it (30 s).** "Fire in a spacecraft is different: no buoyancy, closed air. FIREGUARD-X advises; humans decide; everything is simulated."
2. **Mission command.** Sign in as `commander`. Scenario *Mission Day 183*. Point at risk level, trust band, the layer labels (NASA evidence / prototype assumption / SYNTHETIC-DEMO).
3. **Control the physics.** Raise oxygen with the slider: risk climbs faster than linearly; move airflow through ~13 cm/s: nonlinear. Load *Beyond tested range*: trust drops and the HIGH challenge appears.
4. **Evidence explorer.** Search "oxygen concentration flame spread". Open a result: URL, SHA-256, version, licence. Click *Download official NASA documents* if not yet ingested.
5. **AI council and debate.** Show seven agents, their cited evidence IDs, identity hashes; the red team's challenge in the debate.
6. **Security center.** Click *Tamper with …* → document quarantined, integrity gate fails. *Inject poisoned chunk* → excluded, event raised. *Run red-team suite* → 10/10 blocked. *Restore* / *Clear it*.
7. **Approval.** Back on Mission command, click *Approve (simulate)*, then *Confirm approval (simulate)* → simulated steps with falling risk. A viewer cannot approve.
8. **Audit center.** Hash chain OK; every action present.
9. **Voice (optional, Chromium).** "Go to trust", "status", "load scenario 3" — alerts are spoken in Indian English.
10. **Close (20 s).** "Prototype, not NASA-approved. The trust score tells you when not to trust the AI, and that is the point."

Fallback if offline: the demo evidence works without internet; say so explicitly.
