"""Explicit failure-injection tests (the suite must not only test happy paths)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegisops.api.app import create_app
from aegisops.config.settings import Settings
from aegisops.providers.mock import MockOpsProvider
from aegisops.storage.file_backend import FileThreadStorage
from aegisops.tools.registry import ToolRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_registry(provider: MockOpsProvider) -> ToolRegistry:
    settings = Settings(_env_file=None, environment="test", tool_timeout_seconds=5.0)
    return ToolRegistry(provider, settings)


@pytest.mark.asyncio
async def test_tool_timeout_degrades_to_error_result() -> None:
    provider = MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures")
    provider.fault_injection.timeout_tools.add("query_logs")
    registry = make_registry(provider)
    result = await registry.call(
        "query_logs",
        {"service": "payment-service", "start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
    )
    assert result.ok is False
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_invalid_tool_result_degrades_to_error_result() -> None:
    provider = MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures")
    provider.fault_injection.fail_next["query_metrics"] = 1
    registry = make_registry(provider)
    result = await registry.call(
        "query_metrics",
        {
            "service": "payment-service",
            "metric": "cpu_usage",
            "start": "2026-01-01T00:00:00Z",
            "end": "2026-01-01T01:00:00Z",
        },
    )
    assert result.ok is False
    assert "injected failure" in result.error


@pytest.mark.asyncio
async def test_mcp_unavailable_degrades_to_boundary_error() -> None:
    from aegisops.mcp.client import MCPToolAdapter
    from aegisops.mcp.server import AegisMcpServer, McpToolError

    provider = MockOpsProvider(fixtures_dir=PROJECT_ROOT / "fixtures")
    provider.fault_injection.unavailable = True
    adapter = MCPToolAdapter(server=AegisMcpServer(provider=provider))
    with pytest.raises(McpToolError):
        await adapter.get_service_health("payment-service")


def test_mongo_unavailable_falls_back_to_file_storage(tmp_path, monkeypatch) -> None:
    class BrokenMongo:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("pymongo unavailable (injected)")

    monkeypatch.setattr("aegisops.api.app.MongoThreadStorage", BrokenMongo)
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
        storage_backend="mongo",
        checkpoint_backend="memory",
        sandbox_backend="local",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert isinstance(app.state.storage, FileThreadStorage)


def test_llm_timeout_is_retried_then_recovers() -> None:
    import asyncio

    from pydantic import BaseModel

    from aegisops.llm.fake import FakeLLM
    from aegisops.llm.models import LLMMessage
    from aegisops.llm.structured import generate_structured

    class TimeoutOnceLLM(FakeLLM):
        def __init__(self):
            super().__init__(
                script=[
                    __import__("aegisops.llm.fake", fromlist=["ScriptedTurn"]).ScriptedTurn(
                        json_payload={"answer": "recovered", "confidence": 0.5}, match="previous output"
                    )
                ]
            )
            self.failed = False

        async def generate(self, messages, tools=None, response_format=None):
            if not self.failed:
                self.failed = True
                raise TimeoutError("llm timeout (injected)")
            return await super().generate(messages, tools, response_format)

    class Tiny(BaseModel):
        answer: str
        confidence: float

    result = asyncio.run(
        generate_structured(
            TimeoutOnceLLM(),
            [LLMMessage(role="user", content="query")],
            schema_name="Tiny",
            output_model=Tiny,
        )
    )
    assert result.answer == "recovered"
