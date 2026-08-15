"""Observability and metadata API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api")


@router.get("/traces")
async def traces(
    request: Request,
    thread_id: str | None = None,
    run_id: str | None = None,
    user_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    return request.app.state.trace_store.query(
        thread_id=thread_id, run_id=run_id, user_id=user_id, limit=limit
    )


@router.get("/threads/{thread_id}/state")
async def thread_state(thread_id: str, request: Request) -> dict[str, Any]:
    """Expose checkpointed graph state for debugging / observability."""
    snapshot = await request.app.state.graph.aget_state({"configurable": {"thread_id": thread_id}})
    values = snapshot.values or {}
    return {
        "thread_id": thread_id,
        "status": values.get("status"),
        "pending_interrupt": values.get("pending_interrupt"),
        "plan": values.get("plan"),
        "subagent_reports": values.get("subagent_reports"),
        "final_report": values.get("final_report"),
    }


@router.get("/scenarios")
async def scenarios(request: Request) -> list[dict[str, Any]]:
    """Scenario dataset metadata (used by the UI and demos)."""
    runtime = request.app.state.runtime
    return [
        {
            "incident_id": s.get("incident_id"),
            "service": s.get("service"),
            "fault_type": s.get("fault_type"),
            "title": s.get("title"),
            "severity": s.get("severity"),
            "dangerous_action": s.get("dangerous_action"),
            "recommended_action": s.get("recommended_action"),
        }
        for s in runtime.scenario_index.values()
    ]


@router.get("/catalog")
async def catalog(request: Request) -> list[dict[str, Any]]:
    runtime = request.app.state.runtime
    entries = await runtime.provider.get_service_catalog()
    return [entry.model_dump(mode="json") for entry in entries]


@router.get("/topology")
async def topology(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    topo = await runtime.provider.get_service_topology()
    return topo.model_dump(mode="json")


@router.get("/runtime")
async def runtime_info(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    return {
        "sandbox_backend": runtime.settings.sandbox_backend,
        "sandbox_breaker": runtime.sandbox_breaker.state.value,
        "sandbox_stats": runtime.sandbox_manager.stats(),
        "llm_mode": "real" if runtime.settings.llm_configured else "offline-fake",
        "subagents": list(runtime.subagent_configs),
        "skills": runtime.skills.names(),
    }


@router.get("/policies")
async def policies(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    return {
        "auto_approve_max_risk": runtime.settings.auto_approve_max_risk,
        "model_call_limit": runtime.settings.model_call_limit,
        "tool_call_limit": runtime.settings.tool_call_limit,
        "sandbox_backend": runtime.settings.sandbox_backend,
    }


@router.post("/scenarios/{incident_id}/activate")
async def activate_scenario(incident_id: str, request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    scenario = runtime.activate_scenario(incident_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    return {"activated": incident_id}
