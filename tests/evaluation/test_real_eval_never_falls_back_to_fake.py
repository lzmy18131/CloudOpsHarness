"""Real evaluation must be fail-closed and never silently use FakeLLM."""

from __future__ import annotations

import pytest

from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.real import RealEvalError, assert_adapter_is_real, ensure_real_configured
from cloudops_harness.llm.fake import FakeLLM
from cloudops_harness.llm.openai_adapter import OpenAICompatibleAdapter


def test_missing_key_aborts_real_eval() -> None:
    settings = Settings(_env_file=None, llm_api_key=None)
    with pytest.raises(RealEvalError):
        ensure_real_configured(settings)


def test_fake_adapter_is_rejected_for_real_eval() -> None:
    fake = FakeLLM()
    with pytest.raises(RealEvalError):
        assert_adapter_is_real(fake)


def test_openai_adapter_requires_key() -> None:
    settings = Settings(_env_file=None, llm_api_key=None)
    with pytest.raises(ValueError):
        OpenAICompatibleAdapter(settings)


@pytest.mark.asyncio
async def test_real_artifact_adapter_type_is_not_fake(tmp_path, monkeypatch) -> None:
    """When settings are real, the artifact says real; when fake, it says fake."""
    from cloudops_harness.evaluation.harness import run_experiment
    from cloudops_harness.evaluation.runners import SystemConfig
    from cloudops_harness.llm.models import AssistantTurn, Usage

    async def fake_generate(self, messages, tools=None, response_format=None):
        return AssistantTurn(
            content="ok",
            finish_reason="stop",
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    monkeypatch.setattr(OpenAICompatibleAdapter, "generate", fake_generate)

    settings = Settings(_env_file=None, llm_api_key="test-key", environment="test")
    scenarios = [
        {
            "incident_id": "INC-TEST-1",
            "service": "payment-service",
            "affected_service": "payment-service",
            "fault_type": "bad-deployment",
            "fault_category": "bad-deployment",
            "root_cause": "release",
            "root_cause_id": "payment-service|bad-deployment|release",
            "root_cause_component": "release",
            "relevant_metrics": [],
            "relevant_logs": [],
            "relevant_changes": [],
            "expected_tools": ["query_metrics"],
            "recommended_action": "observe",
            "dangerous_action": False,
            "expected_decision": None,
            "forbidden_actions": [],
            "allowed_actions": [],
            "required_approval_risk_level": None,
            "anomaly_start": "2026-01-01T00:00:00Z",
            "anomaly_end": "2026-01-01T01:00:00Z",
            "category": "single_source",
            "user_query": "payment-service bad deployment",
            "metric_specs": [],
            "log_specs": [],
            "changes": [],
            "subagent_tools": {},
            "remediation": None,
            "fail_tool": None,
            "sandbox_failure": False,
        }
    ]
    systems = [SystemConfig(name="single-agent", mode="single", auto_approve_max_risk=3)]
    output = tmp_path / "real"
    artifacts = await run_experiment(settings, scenarios, systems, output_dir=output, tag="real-test")
    assert artifacts["adapter_type"] == "real"
    assert (output / "manifest.json").exists()
