"""Evidence statistics, red-team challenges, consensus and the AI Trust Score.

The Trust Score is a PROTOTYPE metric defined by this project. It is not NASA-approved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.risk import assumptions as A
from app.risk.model import clamp
from app.schemas import (
    INSUFFICIENT_EVIDENCE_TEXT,
    Challenge,
    Consensus,
    EvidenceSummary,
    Gate,
    RiskOut,
    ScenarioIn,
    TrustComponent,
    TrustOut,
)

GRAVITY_MATCH = {
    "microgravity": {"microgravity"},
    "lunar": {"reduced"},
    "mars": {"reduced"},
    "earth": {"normal"},
}
ASPECTS = ("oxygen", "airflow", "pressure", "temperature", "geometry")


@dataclass
class EvidenceStats:
    summary: EvidenceSummary
    quality: float  # 0..100 before envelope penalty
    relevance: float  # 0..100 mean of top three used chunks
    material_covered: bool
    gravity_covered: bool
    official_count: int
    synthetic_count: int


def evidence_stats(s: ScenarioIn, used: list[Any], excluded: int, mode: str) -> EvidenceStats:
    """`used` are retriever Candidates with status 'used'."""
    n = len(used)
    aspects = set(ASPECTS) | ({"heating"} if s.external_heating_kw_m2 > 0 else set())
    covered = {a for c in used for a in c.chunk.variables if a in aspects}
    material_covered = any(s.material in c.chunk.materials for c in used)
    gravity_covered = any(c.chunk.gravity in GRAVITY_MATCH[s.gravity] for c in used)
    total_aspects = len(aspects) + 2  # + material + gravity
    coverage = (len(covered) + material_covered + gravity_covered) / total_aspects if n else 0.0
    docs = {c.doc.doc_key for c in used}
    exps = {c.experiment for c in used if c.experiment and c.experiment != "DEMO"}
    diversity = 0.6 * min(1.0, len(docs) / 4) + 0.4 * min(1.0, len(exps) / 3)
    auth = sum(A.SYNTHETIC_AUTHORITY if c.chunk.synthetic else 1.0 for c in used) / n if n else 0.0
    w = A.EVIDENCE_QUALITY_WEIGHTS
    quality = 100 * (w["coverage"] * coverage + w["diversity"] * diversity + w["authority"] * auth)
    top = sorted((c.relevance for c in used), reverse=True)[:3]
    rel = 100 * sum(top) / len(top) if top else 0.0
    official = sum(1 for c in used if not c.chunk.synthetic)
    synth = n - official
    official_docs = len({c.doc.doc_key for c in used if not c.chunk.synthetic})
    mode_label = (
        "official" if n and synth == 0 else "demo" if n and official == 0 else "mixed" if n else "demo"
    )
    return EvidenceStats(
        summary=EvidenceSummary(
            count=n,
            documents=len(docs),
            official_documents=official_docs,
            synthetic_only=bool(n) and official == 0,
            mode=mode_label,
            coverage=round(coverage, 3),
            material_covered=material_covered,
            excluded=excluded,
        ),
        quality=quality,
        relevance=rel,
        material_covered=material_covered,
        gravity_covered=gravity_covered,
        official_count=official,
        synthetic_count=synth,
    )


def red_team(
    s: ScenarioIn,
    risk: RiskOut,
    pen: float,
    st: EvidenceStats,
    quarantined_docs: int,
    injected_excluded: int,
    mode: str,
) -> list[Challenge]:
    ch: list[Challenge] = []

    def add(text: str, sev: str, passed: bool, cat: str) -> None:
        ch.append(Challenge(challenge=text, severity=sev, passed=passed, category=cat))

    add(
        f"Verify the evidence applies to {s.material} under {s.gravity} conditions.",
        "LOW",
        st.material_covered and st.gravity_covered,
        "applicability",
    )
    if st.quality - pen * 0.5 < 70:
        add(
            "Evidence coverage is thin for these conditions. A strong claim is not supported.",
            "MEDIUM",
            False,
            "coverage",
        )
    if risk.nonlinear_airflow:
        add(
            "Airflow effects are nonlinear in this range. Cutting flow abruptly could raise flame growth before it falls.",
            "MEDIUM",
            True,
            "nonlinearity",
        )
    if pen > 0:
        add(
            "Conditions sit beyond the tested envelope ("
            + ", ".join(risk.out_of_range)
            + "). This is extrapolation.",
            "HIGH",
            False,
            "extrapolation",
        )
    if not st.material_covered:
        add(
            f"No retrieved evidence mentions {s.material}. Material coverage is unverified.",
            "MEDIUM",
            False,
            "material",
        )
    if st.summary.synthetic_only and st.summary.count:
        add(
            "All supporting evidence is SYNTHETIC/DEMO. It is not NASA data.",
            "LOW" if mode == "demo" else "HIGH",  # demo: labelled, not penalised; strict: unresolved
            mode == "demo",
            "provenance",
        )
    if quarantined_docs:
        add(
            f"{quarantined_docs} source document(s) failed the SHA-256 integrity check and are quarantined.",
            "HIGH",
            False,
            "integrity",
        )
    if injected_excluded:
        add(
            "A retrieved chunk contained instruction-like text. It was excluded from evidence.",
            "MEDIUM",
            True,
            "injection",
        )
    sf = s.sensor_flags
    if sf is not None:
        reported = [v for v in (sf.smoke_detected, sf.optical_flame_detected) if v is not None]
        if reported:
            fire_seen = any(reported)
            if risk.level in ("HIGH", "CRITICAL") and not fire_seen:
                add(
                    "The model rates this HIGH or CRITICAL, but no independent sensor corroborates a fire.",
                    "MEDIUM",
                    False,
                    "sensor",
                )
            elif risk.level == "LOW" and fire_seen:
                add(
                    "A sensor reports fire but the model rates LOW. Treat the sensor report seriously.",
                    "HIGH",
                    False,
                    "sensor",
                )
            else:
                add("Independent sensor reading is consistent with the model.", "LOW", True, "sensor")
        else:
            add(
                "Sensors are not reporting. Missing data is uncertainty, not proof of safety.",
                "LOW",
                False,
                "sensor",
            )
    return ch


SEV_PENALTY = {"HIGH": 35, "MEDIUM": 18, "LOW": 6}


def adversarial_score(ch: list[Challenge]) -> tuple[float, bool, int]:
    unres = [c for c in ch if not c.passed]
    passed = not any(c.severity == "HIGH" for c in unres) and len(unres) <= 1
    adv = clamp(
        100 - sum(SEV_PENALTY[c.severity] for c in unres) - sum(1 for c in ch if c.passed) * 2, 5, 100
    )
    return adv, passed, len(unres)


def consensus(risk: RiskOut, open_challenges: int, invalid_agents: int) -> Consensus:
    lv = level_index_from_name(risk.level)
    cl = level_index_from_name(risk.crew_level)
    fl = level_index_from_name(risk.flame_growth)
    spread = abs(lv - cl) + abs(lv - fl)
    pct = clamp(100 - 12 * spread - 6 * open_challenges - 15 * invalid_agents, 30, 98)
    return Consensus(
        level="HIGH" if pct >= 85 else "MEDIUM" if pct >= 65 else "LOW",
        agreement=round(pct / 100, 3),
        open_challenges=open_challenges,
    )


def level_index_from_name(name: str) -> int:
    return A.LEVELS.index(name)


def band_for(score: int) -> str:
    return next(b for t, b in A.TRUST_BANDS if score >= t)


def compute_trust(
    *,
    risk: RiskOut,
    pen: float,
    st: EvidenceStats,
    challenges: list[Challenge],
    cons: Consensus,
    quarantined_docs: int,
    mode: str,
) -> TrustOut:
    adv, adv_passed, unres = adversarial_score(challenges)
    evidence = clamp(st.quality - pen * 0.5, 0, 100)
    exp_match = clamp(100 - pen * 2, 15, 100)
    integ = clamp(100 - 60 * quarantined_docs, 0, 100)
    unc = clamp(100 - (100 - evidence) * 0.8 - (10 if risk.nonlinear_airflow else 0) - pen * 0.5, 10, 100)
    scores = {
        "evidence_quality": evidence,
        "source_relevance": st.relevance,
        "experimental_match": exp_match,
        "agent_consensus": cons.agreement * 100,
        "adversarial": adv,
        "data_integrity": integ,
        "uncertainty": unc,
    }
    comps = [
        TrustComponent(
            key=k, label=A.TRUST_LABELS[k], weight=A.TRUST_WEIGHTS[k] / 100, score=round(scores[k], 1)
        )
        for k in A.TRUST_WEIGHTS
    ]
    total = round(sum(A.TRUST_WEIGHTS[k] * scores[k] / 100 for k in A.TRUST_WEIGHTS))
    band = band_for(total)

    n = st.summary.count
    if st.official_count > 0:
        g1 = "pass"
    elif n > 0 and mode == "demo":
        g1 = "demo"
    else:
        g1 = "fail"
    gates = [
        Gate(
            key="nasa_evidence",
            label="NASA evidence found",
            status=g1,
            value=f"{n} chunks, {st.official_count} official"
            + (" (SYNTHETIC/DEMO only)" if g1 == "demo" else ""),
        ),
        Gate(
            key="relevance",
            label="Evidence relevant",
            status="pass" if evidence >= 70 else "fail",
            value=f"{round(evidence)}%",
        ),
        Gate(
            key="envelope",
            label="Conditions match experiments",
            status="pass" if pen == 0 else "fail",
            value="in range" if pen == 0 else "outside: " + ", ".join(risk.out_of_range),
        ),
        Gate(
            key="agreement",
            label="Independent agent agreement",
            status="pass" if cons.agreement >= 0.75 else "fail",
            value=f"{round(cons.agreement * 100)}%",
        ),
        Gate(
            key="adversarial",
            label="Adversarial challenge passed",
            status="pass" if adv_passed else "fail",
            value=f"{unres} open",
        ),
        Gate(
            key="integrity",
            label="Data integrity verified",
            status="pass" if quarantined_docs == 0 else "fail",
            value="verified" if quarantined_docs == 0 else f"{quarantined_docs} quarantined",
        ),
        Gate(
            key="trust",
            label="Trust score at least 85",
            status="pass" if total >= 85 else "fail",
            value=f"{total}/100",
        ),
    ]
    all_pass = all(g.status in ("pass", "demo") for g in gates)
    insufficient = n == 0 or evidence < 50 or (mode == "strict" and st.official_count == 0)
    if band == "REJECT":
        guardian = "REJECTED"
    elif band == "TRUSTED" and all_pass and not insufficient:
        guardian = "TRUSTED"
    else:
        guardian = "REQUIRES REVIEW"
    if insufficient:
        verdict = INSUFFICIENT_EVIDENCE_TEXT
    elif guardian == "TRUSTED":
        verdict = "TRUSTED — the recommendation may go to a human for approval."
    elif guardian == "REJECTED":
        verdict = "REJECTED — do not rely on this result."
    else:
        verdict = "REQUIRES REVIEW — a human must examine the open items before acting."
    note = "Trust Score is a prototype metric defined by FIREGUARD-X. It is not NASA-approved."
    if g1 == "demo":
        note += " The supporting evidence is SYNTHETIC/DEMO."
    return TrustOut(
        score=total,
        band=band,
        guardian_status=guardian,
        components=comps,
        gates=gates,
        all_gates_pass=all_pass,
        insufficient_evidence=insufficient,
        verdict=verdict,
        note=note,
    )
