"""Unit tests for configuration and logging."""

from __future__ import annotations

import logging

from aegisops.config.logging_conf import JsonLineFormatter, setup_logging
from aegisops.config.settings import Settings


def test_settings_defaults_resolve_project_paths() -> None:
    settings = Settings(_env_file=None)
    assert settings.checkpoint_path.name == "checkpoint.db"
    assert settings.history_dir.name == "history"
    assert settings.auto_approve_max_risk == 1
    assert settings.llm_configured is False


def test_settings_llm_env_aliases(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    settings = Settings(_env_file=None)
    assert settings.llm_api_key == "sk-test"
    assert settings.llm_base_url == "https://example.com/v1"
    assert settings.llm_model == "test-model"
    assert settings.llm_configured is True


def test_settings_prefixed_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_LLM_API_KEY", "sk-prefixed")
    monkeypatch.setenv("AEGIS_PORT", "1234")
    settings = Settings(_env_file=None)
    assert settings.llm_api_key == "sk-prefixed"
    assert settings.port == 1234


def test_ensure_dirs_creates_runtime_tree(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data")
    settings.ensure_dirs()
    assert settings.checkpoint_path.parent.exists()
    assert settings.traces_dir.exists()
    assert settings.sandbox_workspace_dir.exists()


def test_json_line_formatter_emits_json() -> None:
    record = logging.LogRecord(
        name="aegisops.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.thread_id = "t-1"
    output = JsonLineFormatter().format(record)
    assert '"msg": "hello"' in output
    assert '"thread_id": "t-1"' in output


def test_setup_logging_is_idempotent() -> None:
    setup_logging("INFO")
    setup_logging("INFO")
    root_handlers = [h for h in logging.getLogger().handlers if isinstance(h.formatter, JsonLineFormatter)]
    assert len(root_handlers) == 1
