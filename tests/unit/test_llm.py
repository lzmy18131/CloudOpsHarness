"""Unit tests for the LLM adapter layer (offline only)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from cloudops_harness.config.settings import Settings
from cloudops_harness.llm.fake import FakeLLM, ScriptedTurn
from cloudops_harness.llm.models import LLMMessage
from cloudops_harness.llm.openai_adapter import OpenAICompatibleAdapter
from cloudops_harness.llm.structured import StructuredOutputError, generate_structured, parse_json_object


class TinyModel(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)


@pytest.mark.asyncio
async def test_fake_llm_scripted_turns() -> None:
    llm = FakeLLM(
        script=[
            ScriptedTurn(
                match="check payment",
                tool_call_name="get_service_health",
                tool_call_args={"service": "payment-service"},
            ),
            ScriptedTurn(match="healthy", content="payment-service is healthy"),
        ]
    )
    messages = [LLMMessage(role="user", content="please check payment-service")]
    tools = [{"function": {"name": "get_service_health"}}]
    first = await llm.generate(messages, tools=tools)
    assert first.tool_calls[0].name == "get_service_health"
    messages.append(LLMMessage(role="assistant", content="", tool_calls=first.tool_calls))
    messages.append(LLMMessage(role="tool", content="status=healthy", tool_call_id=first.tool_calls[0].id))
    second = await llm.generate(messages)
    assert second.content == "payment-service is healthy"


@pytest.mark.asyncio
async def test_fake_llm_scenario_driven_tool_selection() -> None:
    scenario = {
        "incident_id": "INC-ABC-1",
        "service": "payment-service",
        "anomaly_start": "2026-01-15T00:00:00Z",
        "anomaly_end": "2026-01-15T01:00:00Z",
        "expected_tools": ["query_metrics", "get_service_health"],
        "metric_specs": [{"metric": "latency_p99_ms"}],
        "log_specs": [{"pattern": "timeout"}],
        "title": "latency",
        "root_cause": "bad deploy",
        "fault_type": "bad-deployment",
        "severity": "P1",
    }
    llm = FakeLLM(scenario=scenario)
    tools = [
        {"function": {"name": "query_metrics"}},
        {"function": {"name": "get_service_health"}},
        {"function": {"name": "get_current_release"}},
    ]
    first = await llm.generate([LLMMessage(role="system", content="AGENT_ROLE: observability")], tools=tools)
    second = await llm.generate([LLMMessage(role="system", content="AGENT_ROLE: observability")], tools=tools)
    third = await llm.generate([LLMMessage(role="system", content="AGENT_ROLE: observability")], tools=tools)
    assert first.tool_calls[0].name == "query_metrics"
    assert first.tool_calls[0].arguments["service"] == "payment-service"
    assert second.tool_calls[0].name == "get_service_health"
    assert third.tool_calls == []


@pytest.mark.asyncio
async def test_fake_llm_records_all_calls() -> None:
    llm = FakeLLM(default_content="ok")
    await llm.generate([LLMMessage(role="user", content="hi")])
    assert len(llm.calls) == 1
    assert llm.calls[0]["tool_names"] == []


def test_openai_adapter_builds_params_without_network(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    settings = Settings(_env_file=None)
    adapter = OpenAICompatibleAdapter(settings)
    params = adapter.build_params(
        [LLMMessage(role="user", content="hello")],
        tools=[{"type": "function", "function": {"name": "t", "description": "", "parameters": {}}}],
        response_format={"type": "json_object"},
    )
    assert params["model"] == "test-model"
    assert params["tool_choice"] == "auto"
    assert params["response_format"] == {"type": "json_object"}


def test_openai_adapter_requires_key() -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleAdapter(Settings(_env_file=None, llm_api_key=None))


def test_parse_json_object_handles_fences_and_wrapping() -> None:
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('prefix {"a": {"b": 2}} suffix') == {"a": {"b": 2}}
    with pytest.raises(StructuredOutputError):
        parse_json_object("no json at all")


@pytest.mark.asyncio
async def test_generate_structured_retries_once_on_malformed_output() -> None:
    llm = FakeLLM(
        script=[
            ScriptedTurn(content="this is {not json", match="query"),
            ScriptedTurn(
                json_payload={"answer": "recovered", "confidence": 0.9}, match="previous output was not valid"
            ),
        ]
    )
    result = await generate_structured(
        llm,
        [LLMMessage(role="user", content="query")],
        schema_name="TinyModel",
        output_model=TinyModel,
    )
    assert result.answer == "recovered"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_generate_structured_rejects_missing_field() -> None:
    llm = FakeLLM(script=[ScriptedTurn(json_payload={"confidence": 0.9}, match="query")])
    with pytest.raises(StructuredOutputError):
        await generate_structured(
            llm, [LLMMessage(role="user", content="query")], schema_name="TinyModel", output_model=TinyModel
        )


@pytest.mark.asyncio
async def test_generate_structured_rejects_wrong_type_and_invalid_confidence() -> None:
    wrong_type = FakeLLM(
        script=[ScriptedTurn(json_payload={"answer": 123, "confidence": 0.5}, match="query")]
    )
    with pytest.raises(StructuredOutputError):
        await generate_structured(
            wrong_type,
            [LLMMessage(role="user", content="query")],
            schema_name="TinyModel",
            output_model=TinyModel,
        )

    bad_confidence = FakeLLM(
        script=[ScriptedTurn(json_payload={"answer": "x", "confidence": 1.5}, match="query")]
    )
    with pytest.raises(StructuredOutputError):
        await generate_structured(
            bad_confidence,
            [LLMMessage(role="user", content="query")],
            schema_name="TinyModel",
            output_model=TinyModel,
        )


@pytest.mark.asyncio
async def test_generate_structured_repairs_truncated_then_recovers() -> None:
    llm = FakeLLM(
        script=[
            ScriptedTurn(content='{"answer": "broken"', match="query"),
            ScriptedTurn(json_payload={"answer": "repaired", "confidence": 0.7}, match="previous output"),
        ]
    )
    result = await generate_structured(
        llm, [LLMMessage(role="user", content="query")], schema_name="TinyModel", output_model=TinyModel
    )
    assert result.answer == "repaired"


@pytest.mark.asyncio
async def test_generate_structured_accepts_extra_text_around_json() -> None:
    llm = FakeLLM(
        script=[ScriptedTurn(content='prefix {"answer": "ok", "confidence": 0.5} suffix', match="query")]
    )
    result = await generate_structured(
        llm, [LLMMessage(role="user", content="query")], schema_name="TinyModel", output_model=TinyModel
    )
    assert result.answer == "ok"


@pytest.mark.asyncio
async def test_model_budget_is_concurrent_run_scoped() -> None:
    import asyncio

    from cloudops_harness.llm.base import LimitedModelAdapter
    from cloudops_harness.llm.budget import get_model_budget, start_model_budget

    async def run(name: str, calls: int) -> int:
        start_model_budget(f"run-{name}", max_calls=120)
        adapter = LimitedModelAdapter(FakeLLM(default_content="ok"), max_calls=120)
        for _ in range(calls):
            await adapter.generate([LLMMessage(role="user", content="hi")])
        return get_model_budget().calls

    results = await asyncio.gather(run("a", 30), run("b", 25))
    assert results == [30, 25]
    assert 30 + 25 > 40  # a shared resetable counter would have interfered


@pytest.mark.asyncio
async def test_model_budget_overflow_raises_gracefully() -> None:
    from cloudops_harness.llm.base import LimitedModelAdapter, ModelCallLimitError
    from cloudops_harness.llm.budget import start_model_budget

    start_model_budget("overflow-model-run", max_calls=2)
    adapter = LimitedModelAdapter(FakeLLM(default_content="ok"), max_calls=2)
    await adapter.generate([LLMMessage(role="user", content="1")])
    await adapter.generate([LLMMessage(role="user", content="2")])
    with pytest.raises(ModelCallLimitError):
        await adapter.generate([LLMMessage(role="user", content="3")])
