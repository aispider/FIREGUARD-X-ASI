"""Seed roles, demo users, scenario presets and (offline) synthetic evidence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.evidence.catalog import EXPERIMENTS
from app.evidence.ingest import ensure_experiment
from app.evidence.synthetic import seed_synthetic
from app.models import Role, Scenario, User
from app.security.auth import hash_password
from app.security.rbac import ROLE_PERMISSIONS

DEMO_USERS = [("admin", "admin"), ("commander", "commander"), ("analyst", "analyst"), ("viewer", "viewer")]

PRESETS = [
    ("day183", "Mission Day 183", dict(oxygen_percent=20.4, pressure_kpa=101, airflow_cm_s=3.2, temperature_k=420, external_heating_kw_m2=10, material="PMMA", fuel_geometry="thin_sheet", gravity="microgravity")),
    ("nominal", "Nominal cabin", dict(oxygen_percent=20.9, pressure_kpa=101, airflow_cm_s=1, temperature_k=295, external_heating_kw_m2=0, material="Nomex fabric", fuel_geometry="thick_slab", gravity="microgravity")),
    ("o2leak", "O2-enriched leak", dict(oxygen_percent=24.5, pressure_kpa=101, airflow_cm_s=5, temperature_k=450, external_heating_kw_m2=5, material="Cotton-fiberglass fabric", fuel_geometry="thin_sheet", gravity="microgravity")),
    ("blowoff", "High-flow blow-off", dict(oxygen_percent=21, pressure_kpa=101, airflow_cm_s=38, temperature_k=420, external_heating_kw_m2=0, material="PMMA", fuel_geometry="thick_slab", gravity="microgravity")),
    ("beyond", "Beyond tested range", dict(oxygen_percent=24.8, pressure_kpa=140, airflow_cm_s=5, temperature_k=590, external_heating_kw_m2=25, material="Silicone", fuel_geometry="cylinder", gravity="microgravity")),
]


def seed(session: Session, with_demo_evidence: bool = True) -> None:
    s = get_settings()
    for name, perms in ROLE_PERMISSIONS.items():
        r = session.get(Role, name)
        if r is None:
            session.add(Role(name=name, permissions=list(perms)))
        else:
            r.permissions = list(perms)
    session.flush()
    for username, role in DEMO_USERS:
        if session.scalar(select(User).where(User.username == username)) is None:
            session.add(User(username=username, role=role, password_hash=hash_password(s.seed_password)))
    for _key, name, params in PRESETS:
        if session.scalar(select(Scenario).where(Scenario.name == name, Scenario.preset.is_(True))) is None:
            session.add(Scenario(name=name, params={**params, "name": name}, preset=True, synthetic=True))
    for spec in EXPERIMENTS:
        ensure_experiment(session, spec)
    session.commit()
    if with_demo_evidence:
        seed_synthetic(session)


def seed_all(session: Session) -> None:
    seed(session)
