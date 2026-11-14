"""SYNTHETIC/DEMO evidence: offline passages written for this prototype.

These are NOT NASA data and do not report experimental results. They describe, in qualitative terms, the
relationships the prototype risk model encodes, so the demo works without internet. Every one is flagged
synthetic in the database, in the manifest, in the API and in the UI. In EVIDENCE_MODE=strict they can never
produce a TRUSTED result.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.evidence.catalog import DEMO_EXPERIMENT
from app.evidence.ingest import ensure_experiment, store_document

BANNER = "SYNTHETIC/DEMO passage written for the FIREGUARD-X prototype. Not NASA data. Qualitative statement of a modelling assumption. "

DEMO_DOCS: list[tuple[str, str, str]] = [
    (
        "DEMO-oxygen",
        "Demo: oxygen concentration and flame spread",
        "In the prototype model, higher oxygen concentration raises the flame spread rate and lowers the chance of extinction for solid fuels, "
        "with the effect growing faster than linearly as oxygen rises above normal cabin air. Microgravity flame behaviour is studied with oxygen "
        "concentration as a primary variable, so the model weights oxygen most heavily. Reducing oxygen concentration is the strongest single lever the model recognises for lowering flame spread.",
    ),
    (
        "DEMO-airflow",
        "Demo: airflow and the opposed-flow regime",
        "The prototype treats airflow nonlinearly. At very low ventilation flow, oxygen supply limits a flame, so it spreads slowly or extinguishes. "
        "At moderate flow in microgravity the supply of oxygen to the flame improves and spread can peak. At high flow, convective heat loss and blow-off tendencies reduce spread. "
        "This produces a flow velocity of greatest concern in the low tens of centimetres per second. The exact peak location here is a modelling assumption, not a measured value.",
    ),
    (
        "DEMO-pressure",
        "Demo: ambient pressure and oxygen partial pressure",
        "Ambient pressure and oxygen fraction jointly set the oxygen partial pressure that a flame experiences. In the prototype, lower total pressure reduces the fire risk contribution, "
        "while elevated pressure increases it. Exploration spacecraft may operate at reduced pressure and elevated oxygen fraction, so both variables are tracked together.",
    ),
    (
        "DEMO-temperature",
        "Demo: ambient temperature and external heating",
        "Higher ambient temperature and external radiant heating bring a solid fuel closer to ignition and speed up flame spread. In the prototype model they contribute less than oxygen and airflow, "
        "but external heating from a hot surface or failed electronics can move a marginal scenario into a higher risk band. This is a qualitative assumption for demonstration.",
    ),
    (
        "DEMO-geometry",
        "Demo: fuel geometry and thickness",
        "Thin sheet fuels such as fabrics and thin films heat up quickly and sustain flame spread more readily than thick slabs. Cylindrical samples fall in between. "
        "The prototype applies a larger multiplier to thin sheet geometry and a smaller one to thick slab geometry. Sample thickness and geometry are recorded in combustion experiments because they change flame spread.",
    ),
    (
        "DEMO-materials",
        "Demo: material classes used in the prototype",
        "The prototype includes PMMA, a cotton-fiberglass fabric, polyethylene, silicone and Nomex fabric as example fuels. Fabrics burn readily as thin sheets in the model, "
        "polyethylene and PMMA are treated as moderately to highly flammable solids, silicone as less flammable, and Nomex fabric as the most fire resistant. "
        "These relative rankings are assumptions used to drive the demonstration and are not test results.",
    ),
    (
        "DEMO-gravity",
        "Demo: gravity level and buoyancy",
        "Without buoyancy in microgravity, flames can behave differently from the same flame on Earth, and flame spread can persist at oxygen levels where it would stop under normal gravity. "
        "The prototype applies a gravity multiplier that is highest for microgravity, lower for Martian and lunar gravity, and lowest for Earth. The size of each multiplier is an assumption.",
    ),
    (
        "DEMO-detection",
        "Demo: sensor corroboration and false alarms",
        "A single smoke detector or flame sensor can be wrong and cause a false alarm or a missed alarm. The prototype raises confidence when independent sensors agree and lowers it when only one sensor reports or sensors disagree. "
        "Missing sensor data is treated as uncertainty, not as proof that no fire exists. Recommendations for a critical fire scenario always need human review in this prototype.",
    ),
    (
        "DEMO-suppression",
        "Demo: suppression and crew safety",
        "Fire response in a sealed spacecraft balances stopping the flame against exposing the crew to hazards, such as reduced visibility and toxic products. "
        "The prototype recommends reducing ventilation, isolating the affected module and preparing suppression, and it simulates the steps only. A human commander must approve any action.",
    ),
]


def seed_synthetic(session: Session) -> int:
    exp = ensure_experiment(session, DEMO_EXPERIMENT)
    n = 0
    for key, title, body in DEMO_DOCS:
        text = BANNER + body
        store_document(
            session,
            doc_key=key,
            experiment=exp,
            title=title,
            source="SYNTHETIC/DEMO",
            text=text,
            meta_fields={
                "document_type": "synthetic demonstration",
                "license": "Project-original, demo only",
            },
            synthetic=True,
        )
        n += 1
    return n
