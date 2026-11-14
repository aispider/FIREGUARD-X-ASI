"""Database engine, session factory and shared column types."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy import JSON, TypeDecorator, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import EMBED_DIM, get_settings

# JSON on SQLite (tests), JSONB on PostgreSQL.
JSONType = JSON().with_variant(JSONB(), "postgresql")


class EmbeddingType(TypeDecorator):
    """pgvector `vector(384)` on PostgreSQL, a JSON list elsewhere (unit tests)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(EMBED_DIM))
        return dialect.type_descriptor(JSON())

    def process_result_value(self, value: Any, dialect: Any) -> list[float] | None:
        if value is None:
            return None
        return [float(x) for x in value]


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
        )
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=10, future=True)


def init_engine(url: str | None = None) -> Engine:
    global _engine, _SessionLocal
    _engine = make_engine(url or get_settings().database_url)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        init_engine()
    assert _engine is not None
    return _engine


def session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        init_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_session() -> Iterator[Session]:
    session = session_factory()()
    try:
        yield session
    finally:
        session.close()
