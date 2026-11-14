"""Optional drop-in for real NASA numeric data.

Put CSV exports (for example from NASA's Physical Sciences Informatics system, PSI) in data/raw/psi/. Required
columns: variable, value. Optional: unit, oxygen_percent, airflow_cm_s, pressure_kpa, material, source_reference.
Rows become Observation records tied to a provenance-sealed Document. Nothing is invented: if no files are
present, no observations exist and the envelope is labelled 'prototype_assumption'.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.evidence.catalog import experiment_by_key
from app.evidence.ingest import ensure_experiment, store_document
from app.models import Document, Observation

COND_COLS = ("oxygen_percent", "airflow_cm_s", "pressure_kpa", "material")


def load_psi_csvs(session: Session, say=print) -> int:
    root: Path = get_settings().data_dir / "raw" / "psi"
    if not root.exists():
        return 0
    spec = experiment_by_key("BASS-II")
    assert spec is not None
    exp = ensure_experiment(session, spec)
    total = 0
    for path in sorted(root.glob("*.csv")):
        raw = path.read_bytes()
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="replace"))))
        good = [r for r in rows if r.get("variable") and _num(r.get("value")) is not None]
        if not good:
            say(f"{path.name}: no usable rows")
            continue
        summary = f"User-supplied data file {path.name} with {len(good)} observations ({', '.join(sorted({r['variable'] for r in good})[:8])})."
        doc, _, _ = store_document(
            session,
            doc_key=f"PSI-{path.stem}"[:64],
            experiment=exp,
            title=f"PSI data file {path.name}",
            source="NASA PSI (user-supplied)",
            text=summary + " " * 0,
            meta_fields={"document_type": "dataset"},
            byte_sha=None,
            byte_length=len(raw),
        )
        session.execute(delete(Observation).where(Observation.document_id == doc.id))
        for r in good:
            session.add(
                Observation(
                    experiment_id=exp.id,
                    document_id=doc.id,
                    variable=r["variable"][:48],
                    value=_num(r["value"]) or 0.0,
                    unit=(r.get("unit") or "")[:32],
                    condition={
                        k: _num(r.get(k)) if k != "material" else r.get(k) for k in COND_COLS if r.get(k)
                    },
                    source_reference=(r.get("source_reference") or path.name)[:512],
                    synthetic=False,
                )
            )
        session.commit()
        total += len(good)
        say(f"{path.name}: {len(good)} observations")
    return total


def observed_ranges(session: Session) -> dict[str, tuple[float, float]]:
    """Min/max of conditions seen in real observations, used to set the data envelope."""
    out: dict[str, tuple[float, float]] = {}
    for (cond,) in session.execute(select(Observation.condition).where(Observation.synthetic.is_(False))):
        for k, v in (cond or {}).items():
            if isinstance(v, (int, float)):
                lo, hi = out.get(k, (v, v))
                out[k] = (min(lo, v), max(hi, v))
    return out


def has_real_observations(session: Session) -> bool:
    return session.scalar(select(Observation.id).where(Observation.synthetic.is_(False)).limit(1)) is not None


def _num(v: str | None) -> float | None:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


__all__ = ["load_psi_csvs", "observed_ranges", "has_real_observations", "Document"]
