"""Run once at container start: migrate, seed, load optional PSI CSVs. Safe to repeat."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from app.config import get_settings
from app.db import init_engine, session_factory

log = logging.getLogger("fireguard.bootstrap")


def migrate() -> None:
    root = Path(__file__).resolve().parent.parent
    subprocess.run([sys.executable, "-m", "alembic", "-c", str(root / "alembic.ini"), "upgrade", "head"], check=True, cwd=root)  # noqa: S603


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    s = get_settings()
    s.assert_production_safe()
    for sub in ("raw", "processed", "manifests"):
        (s.data_dir / sub).mkdir(parents=True, exist_ok=True)
    migrate()
    init_engine()
    from app.evidence.observations import load_psi_csvs
    from app.services.seed import seed

    with session_factory()() as session:
        seed(session)
        load_psi_csvs(session, say=log.info)
    log.info("bootstrap complete")


if __name__ == "__main__":
    main()
