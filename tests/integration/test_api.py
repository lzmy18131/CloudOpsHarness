"""API integration tests: SSE events, resume, history, traces."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from cloudops_harness.api.app import create_app
from cloudops_harness.config.settings import Settings
from tests.integration.test_main_agent import make_scenario

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_client(tmp_path) -> TestClient:
    settings = Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        fixtures_dir=PROJECT_ROOT / "fixtures",
        skills_dir=PROJECT_ROOT / "skills",
        checkpoint_backend="memory",
        sandbox_backend="local",
        tracing_enabled=True,
    )
    app = create_app(settings)
    client = TestClient(app)
    client.__enter__()
    scenario = make_scenario()
    app.state.runtime.scenario_index = {scenario["incident_id"]: scenario}
    return client


def parse_sse(lines: list[str]) -> list[dict]:
    events = []
    for line in lines:
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_sse_full_flow_interrupt_resume_history_traces(tmp_path) -> None:
    client = make_client(tmp_path)
    try:
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={
                "message": "payment-service 昨晚发布新版本后 P99 延迟暴涨，帮我排查",
                "user_id": "demo-user",
            },
        ) as response:
            assert response.status_code == 200
            events = parse_sse(
                [line.decode() if isinstance(line, bytes) else line for line in response.iter_lines()]
            )
        kinds = [event["type"] for event in events]
        assert "run_start" in kinds
        # Unified event envelope: every frame is attributable and ordered.
        sequences = []
        for event in events:
            assert event["event_type"] == event["type"]
            assert "run_id" in event and "thread_id" in event
            assert "timestamp" in event and "sequence" in event
            assert event["source"] in {
                "main",
                "observability",
                "log-analysis",
                "change-analysis",
                "remediation",
            }
            sequences.append(event["sequence"])
        assert sequences == sorted(sequences)
        assert len(set(sequences)) == len(sequences)  # no duplicates
        assert "plan" in kinds
        assert "agent_start" in kinds
        assert "tool_start" in kinds
        assert "token" in kinds
        assert "interrupt" in kinds
        done_event = events[-1]
        assert done_event["type"] == "done" and done_event["interrupted"] is True
        thread_id = done_event["thread_id"]

        approval = next(e for e in events if e["type"] == "interrupt" and "action_requests" in e)
        assert approval["interrupt_type"] == "approval"
        assert approval["action_requests"][0]["tool_name"] == "rollback_release"

        resume = client.post(
            f"/api/chat/{thread_id}/resume",
            json={"decisions": [{"type": "approve", "tool_name": "rollback_release"}]},
        )
        assert resume.status_code == 200
        assert resume.json()["status"] == "done"
        assert "Incident Report" in resume.json()["final_report"]

        record = client.get(f"/api/history/{thread_id}").json()
        assert record["status"] == "done"
        assert record["interrupts"][0]["type"] == "approval"
        assert record["resumes"][0]["payload"]["decisions"][0]["type"] == "approve"

        history = client.get("/api/history", params={"user_id": "demo-user"}).json()
        assert history[0]["thread_id"] == thread_id

        traces = client.get("/api/traces", params={"thread_id": thread_id}).json()
        tool_names = [t["tool_name"] for t in traces if t.get("tool_name")]
        assert "rollback_release" in tool_names
        kinds = {t.get("kind") for t in traces}
        assert {
            "tool_start",
            "tool_end",
            "agent_start",
            "agent_end",
            "hitl_decision",
            "action_executed",
            "verification",
            "incident_report",
        } <= kinds
        rollback_start = next(
            t for t in traces if t.get("tool_name") == "rollback_release" and t.get("kind") == "tool_start"
        )
        assert rollback_start.get("risk_level") == 3

        assert client.delete(f"/api/history/{thread_id}").json()["deleted"] is True
    finally:
        client.__exit__(None, None, None)


def test_missing_info_supplement_via_api(tmp_path) -> None:
    client = make_client(tmp_path)
    try:
        first = client.post("/api/chat", json={"message": "帮我查一下故障", "user_id": "demo-user"})
        body = first.json()
        assert body["status"] == "interrupted"
        assert body["interrupt"]["type"] == "missing_info"
        thread_id = body["thread_id"]

        second = client.post(
            f"/api/chat/{thread_id}/resume",
            json={"supplement": "payment-service 昨晚发布新版本后延迟暴涨"},
        )
        assert second.status_code == 200
        assert second.json()["interrupt"]["type"] == "approval"
        state_payload = client.get(f"/api/threads/{thread_id}/state", params={"user_id": "demo-user"}).json()
        assert state_payload["plan"] and len(state_payload["plan"]) > 0
    finally:
        client.__exit__(None, None, None)


def test_root_and_health_endpoints(tmp_path) -> None:
    client = make_client(tmp_path)
    try:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/").status_code == 200
        assert client.get("/api/scenarios").status_code == 200
        assert client.get("/api/policies").json()["auto_approve_max_risk"] == 1
    finally:
        client.__exit__(None, None, None)
