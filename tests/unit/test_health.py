"""Health endpoint tests (Phase 1 acceptance)."""

from __future__ import annotations


def test_health_returns_ok(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app"] == "AegisOps"
    assert payload["llm_mode"] == "offline-fake"
    assert payload["storage_backend"] == "file"


def test_openapi_schema_exposed(client) -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
