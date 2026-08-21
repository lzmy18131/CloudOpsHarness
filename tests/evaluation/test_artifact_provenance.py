"""Artifact provenance and schema tests."""

from __future__ import annotations

import json

import pytest

from cloudops_harness.config.settings import Settings
from cloudops_harness.evaluation.harness import run_experiment
from cloudops_harness.evaluation.runners import SystemConfig


def _scenario() -> dict:
    return {
        "incident_id": "INC-PROV-001",
        "service": "payment-service",
        "affected_service": "payment-service",
        "fault_type": "bad-deployment",
        "fault_category": "bad-deployment",
        "root_cause": "release regression",
        "root_cause_component": "release",
        "root_cause_id": "payment-service|bad-deployment|release",
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


@pytest.mark.asyncio
async def test_artifact_contains_model_and_commit(tmp_path) -> None:
    settings = Settings(_env_file=None, environment="test")
    output = tmp_path / "artifact"
    artifacts = await run_experiment(
        settings,
        [_scenario()],
        [SystemConfig(name="single-agent", mode="single", auto_approve_max_risk=3)],
        output_dir=output,
        tag="provenance-test",
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["config"]["model"] == settings.llm_model
    assert "git_commit" in manifest
    assert "git_dirty" in manifest
    assert "python_version" in manifest
    assert "dataset_sha256" in manifest["config"]
    assert (output / "runs.jsonl").exists()
    assert (output / "failures.json").exists()
    assert (output / "dataset_manifest.json").exists()
    assert artifacts["adapter_type"] == "fake"
