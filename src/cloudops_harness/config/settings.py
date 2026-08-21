"""Application settings.

Single source of runtime configuration. Values come from environment variables
(``CLOUDOPS_*`` prefix) or a ``.env`` file. The three LLM variables intentionally
support both plain ``LLM_*`` and prefixed ``CLOUDOPS_LLM_*`` names so the project
works with the documented OpenAI-style convention.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime settings for CloudOps Harness."""

    model_config = SettingsConfigDict(
        env_prefix="CLOUDOPS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # ---- application -------------------------------------------------
    app_name: str = "CloudOps Harness"
    app_version: str = "0.2.2"
    environment: Literal["dev", "test", "prod"] = "dev"
    host: str = "127.0.0.1"
    port: int = 8090
    log_level: str = "INFO"

    # ---- LLM adapter -------------------------------------------------
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "CLOUDOPS_LLM_API_KEY"),
    )
    llm_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "CLOUDOPS_LLM_BASE_URL"),
    )
    llm_model: str = Field(
        default="deepseek-chat",
        validation_alias=AliasChoices("LLM_MODEL", "CLOUDOPS_LLM_MODEL"),
    )
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 120.0
    llm_max_retries: int = 2
    llm_max_tokens: int | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MAX_TOKENS", "CLOUDOPS_LLM_MAX_TOKENS"),
    )

    # ---- storage -----------------------------------------------------
    checkpoint_backend: Literal["sqlite", "memory"] = "sqlite"
    storage_backend: Literal["file", "mongo"] = "file"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_database: str = "cloudops_harness"

    # ---- paths ---------------------------------------------------------
    data_dir: Path = PROJECT_ROOT / "data"
    fixtures_dir: Path = PROJECT_ROOT / "fixtures"
    skills_dir: Path = PROJECT_ROOT / "skills"

    @property
    def checkpoint_path(self) -> Path:
        """SQLite checkpoint database location."""
        return self.data_dir / "checkpoints" / "checkpoint.db"

    @property
    def history_dir(self) -> Path:
        return self.data_dir / "history"

    @property
    def memory_dir(self) -> Path:
        return self.data_dir / "memory"

    @property
    def traces_dir(self) -> Path:
        return self.data_dir / "traces"

    @property
    def sandbox_workspace_dir(self) -> Path:
        return self.data_dir / "sandbox-workspaces"

    @property
    def user_skills_dir(self) -> Path:
        return self.data_dir / "user-skills"

    @property
    def eval_results_dir(self) -> Path:
        return PROJECT_ROOT / "eval_results"

    # ---- sandbox ---------------------------------------------------------
    sandbox_backend: Literal["auto", "docker", "local"] = "auto"
    sandbox_image: str = "python:3.11-slim"
    sandbox_exec_timeout_seconds: float = 30.0
    sandbox_prewarm: bool = False
    sandbox_health_interval_seconds: float = 15.0
    sandbox_auto_recovery: bool = True
    context_isolation: bool = True

    # ---- harness limits -----------------------------------------------------
    model_call_limit: int = 60
    tool_call_limit: int = 120
    max_plan_steps: int = 20
    max_delegation_depth: int = 2
    context_compression_threshold_tokens: int = 24000
    context_compression_ratio: float = 0.8
    auto_approve_max_risk: int = 1
    tool_timeout_seconds: float = 20.0

    # ---- MCP -------------------------------------------------------------------
    mcp_transport: Literal["inprocess", "stdio"] = "inprocess"

    # ---- API ---------------------------------------------------------
    allowed_origins: str = "*"

    pii_redaction: bool = True

    # ---- observability ---------------------------------------------------
    tracing_enabled: bool = True

    def ensure_dirs(self) -> None:
        """Create all runtime directories lazily."""
        for path in (
            self.data_dir,
            self.checkpoint_path.parent,
            self.history_dir,
            self.memory_dir,
            self.traces_dir,
            self.sandbox_workspace_dir,
            self.user_skills_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def llm_configured(self) -> bool:
        """True when a real LLM key is present (offline/FakeLLM mode otherwise)."""
        return bool(self.llm_api_key and self.llm_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor for production use.

    Tests should construct ``Settings(...)`` directly with temporary paths;
    this cache keeps the FastAPI dependency graph cheap.
    """
    settings = Settings()
    settings.ensure_dirs()
    return settings
