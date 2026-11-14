"""Application settings, read from environment variables (see .env.example)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-only-change-me-dev-only-change-me"  # noqa: S105
DEFAULT_SEED_PASSWORD = "fireguard-demo"  # noqa: S105

EMBED_DIM = 384


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://fireguard:fireguard@localhost:5432/fireguard"
    redis_url: str | None = "redis://localhost:6379/0"

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_expire_minutes: int = 480
    seed_password: str = DEFAULT_SEED_PASSWORD
    enable_security_demo: bool = True

    evidence_mode: Literal["demo", "strict"] = "demo"
    auto_ingest: bool = True
    ntrs_base_url: str = "https://ntrs.nasa.gov"
    ingest_timeout_s: float = 45.0
    ingest_max_bytes: int = 15_000_000

    embedding_provider: Literal["hash", "openai"] = "hash"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    llm_enabled: bool = False

    data_dir: Path = Field(default=Path("/data"))
    cors_origins: str = "http://localhost:8080,http://localhost:5173"

    max_body_bytes: int = 65_536
    rate_limit_per_min: int = 240
    analysis_rate_per_min: int = 600
    login_rate_per_min: int = 12

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def _blank_key(cls, v: str | None) -> str | None:
        return v or None

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def demo_mode(self) -> bool:
        return self.app_env != "production"

    def assert_production_safe(self) -> None:
        if self.app_env != "production":
            return
        problems = []
        if self.jwt_secret == DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be a unique string of at least 32 characters")
        if self.seed_password == DEFAULT_SEED_PASSWORD:
            problems.append("SEED_PASSWORD must not be the default demo password")
        if problems:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
