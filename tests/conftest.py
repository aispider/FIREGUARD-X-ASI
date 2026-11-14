"""Test fixtures: an isolated SQLite database, a temp data dir, no Redis, no network."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="fgx-test-"))
os.environ.update(
    APP_ENV="test", DATABASE_URL=f"sqlite:///{_TMP}/t.db", REDIS_URL="", DATA_DIR=str(_TMP / "data"),
    EVIDENCE_MODE="demo", EMBEDDING_PROVIDER="hash", LLM_ENABLED="false", AUTO_INGEST="false", SEED_PASSWORD="fireguard-demo",
)

import pytest  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import Base, init_engine, session_factory  # noqa: E402


@pytest.fixture()
def db():
    get_settings.cache_clear()
    engine = init_engine()  # file SQLite from DATABASE_URL, so the app lifespan re-opens the same database
    import app.models  # noqa: F401
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    (get_settings().data_dir / "manifests").mkdir(parents=True, exist_ok=True)
    mf = get_settings().data_dir / "manifests" / "manifest.json"
    if mf.exists():
        mf.unlink()
    from app.services.seed import seed_all
    with session_factory()() as s:
        seed_all(s)
        yield s


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient

    from app.api import deps
    from app.main import create_app

    deps.get_limiter.cache_clear()
    deps.get_redis.cache_clear()
    with TestClient(create_app()) as c:
        yield c


def login(client, user: str = "commander") -> dict[str, str]:
    r = client.post("/api/auth/login", json={"username": user, "password": "fireguard-demo"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture()
def auth(client):
    return lambda user="commander": login(client, user)


@pytest.fixture()
def session(db):
    return db


def _hdr(client, user):
    return login(client, user)


@pytest.fixture()
def admin(client):
    return _hdr(client, "admin")


@pytest.fixture()
def commander(client):
    return _hdr(client, "commander")


@pytest.fixture()
def analyst(client):
    return _hdr(client, "analyst")


@pytest.fixture()
def viewer(client):
    return _hdr(client, "viewer")
