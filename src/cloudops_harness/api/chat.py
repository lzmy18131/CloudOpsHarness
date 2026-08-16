"""Chat / SSE / resume / history API routes."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field, field_validator

from cloudops_harness.agents.events import emit, make_event, reset_sequence
from cloudops_harness.middleware.models import RunContext
from cloudops_harness.runtime_context import (
    current_run_id,
    current_thread_id,
    current_user_id,
    token_sink,
)

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    thread_id: str | None = None
    user_id: str = "anonymous"

    @field_validator("user_id", "thread_id")
    @classmethod
    def _validate_identifiers(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from cloudops_harness.security.identifiers import validate_identifier

        return validate_identifier(value, field="identifier")


class ResumeRequest(BaseModel):
    supplement: str | None = None
    decisions: list[dict[str, Any]] | None = None
    user_id: str | None = None


def _runtime(request: Request):
    return request.app.state.runtime


def _storage(request: Request):
    return request.app.state.storage


def _graph(request: Request):
    return request.app.state.graph


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _source_name(node: str) -> str:
    for name in ("observability", "log-analysis", "change-analysis", "remediation"):
        if name in node:
            return name
    return "main"


def _new_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


async def _run_with_middleware(request: Request, ctx: RunContext, invoke):
    runtime = _runtime(request)
    return await runtime.middleware.run(ctx, invoke)


async def _record_outcome(request: Request, result: dict[str, Any], ctx: RunContext) -> dict[str, Any]:
    storage = _storage(request)
    pending = result.get("pending_interrupt")
    if pending:
        await storage.append_event(
            ctx.thread_id, ctx.user_id, {"kind": "interrupt", "type": pending.get("type"), "payload": pending}
        )
        return {
            "thread_id": ctx.thread_id,
            "status": "interrupted",
            "interrupt": pending,
        }
    await storage.append_event(
        ctx.thread_id,
        ctx.user_id,
        {"kind": "final", "content": result.get("final_report", ""), "status": result.get("status", "done")},
    )
    return {
        "thread_id": ctx.thread_id,
        "status": result.get("status", "done"),
        "final_report": result.get("final_report", ""),
        "report_data": result.get("report_data", {}),
        "verification": result.get("verification", {}),
    }


@router.post("/chat")
async def chat(request_body: ChatRequest, request: Request) -> dict[str, Any]:
    """Non-streaming chat (same graph, useful for scripts/tests)."""
    graph = _graph(request)
    storage = _storage(request)
    thread_id = request_body.thread_id or f"thread-{uuid.uuid4().hex[:12]}"
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    ctx = RunContext(
        user_id=request_body.user_id,
        thread_id=thread_id,
        run_id=run_id,
        input_message=request_body.message,
    )
    await storage.append_event(
        thread_id, request_body.user_id, {"kind": "message", "role": "user", "content": request_body.message}
    )
    current_user_id.set(request_body.user_id)
    current_thread_id.set(thread_id)
    current_run_id.set(run_id)
    _runtime(request).reset_model_budget()
    _runtime(request).start_tool_budget(run_id)

    async def invoke():
        return await graph.ainvoke(
            {
                "messages": [{"role": "user", "content": request_body.message}],
                "user_id": request_body.user_id,
                "thread_id": thread_id,
                "run_id": run_id,
            },
            config=_new_config(thread_id),
        )

    result = await _run_with_middleware(request, ctx, invoke)
    outcome = await _record_outcome(request, result, ctx)
    outcome["run_id"] = run_id
    return outcome


@router.post("/chat/stream")
async def chat_stream(request_body: ChatRequest, request: Request) -> StreamingResponse:
    """SSE stream: token / plan / agent_* / tool_* / interrupt / error / done."""
    runtime = _runtime(request)
    graph = _graph(request)
    storage = _storage(request)
    thread_id = request_body.thread_id or f"thread-{uuid.uuid4().hex[:12]}"
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    user_id = request_body.user_id

    async def generate():
        await storage.append_event(
            thread_id, user_id, {"kind": "message", "role": "user", "content": request_body.message}
        )
        ctx = RunContext(
            user_id=user_id, thread_id=thread_id, run_id=run_id, input_message=request_body.message
        )
        reset_sequence()
        yield _sse(make_event("run_start", run_id=run_id, thread_id=thread_id, source="main"))
        current_user_id.set(user_id)
        current_thread_id.set(thread_id)
        current_run_id.set(run_id)
        runtime.reset_model_budget()
        runtime.start_tool_budget(run_id)
        stack = runtime.middleware
        token_sink.set(lambda event: emit(event.pop("type"), **event))
        try:
            for middleware in stack.active():
                await middleware.before_run(ctx)
            async for chunk in graph.astream(
                {
                    "messages": [{"role": "user", "content": request_body.message}],
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "run_id": run_id,
                },
                config=_new_config(thread_id),
                stream_mode=["messages", "custom"],
            ):
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, payload = chunk
                    if mode == "messages" and isinstance(payload, tuple) and len(payload) == 2:
                        message_chunk, metadata = payload
                        content = getattr(message_chunk, "content", "") or ""
                        if isinstance(content, str) and content:
                            yield _sse(
                                make_event(
                                    "token",
                                    content=content,
                                    source=_source_name(metadata.get("langgraph_node", "main")),
                                )
                            )
                    elif mode == "custom" and isinstance(payload, dict):
                        yield _sse(payload)
                elif isinstance(chunk, dict) and "type" in chunk:
                    yield _sse(chunk)

            snapshot = await graph.aget_state(_new_config(thread_id))
            values = snapshot.values or {}
            pending = values.get("pending_interrupt")
            if pending:
                await storage.append_event(
                    thread_id, user_id, {"kind": "interrupt", "type": pending.get("type"), "payload": pending}
                )
                pending_payload = {key: value for key, value in pending.items() if key != "type"}
                yield _sse(
                    make_event(
                        "interrupt",
                        **pending_payload,
                        interrupt_type=pending.get("type"),
                        thread_id=thread_id,
                    )
                )
                yield _sse(make_event("done", thread_id=thread_id, status="interrupted", interrupted=True))
                return
            final_report = values.get("final_report", "")
            if final_report:
                yield _sse(make_event("report", content=final_report, source="main"))
            await storage.append_event(
                thread_id,
                user_id,
                {"kind": "final", "content": final_report, "status": values.get("status", "done")},
            )
            yield _sse(
                make_event(
                    "done",
                    thread_id=thread_id,
                    status=values.get("status", "done"),
                    interrupted=False,
                )
            )
        except Exception as exc:  # noqa: BLE001 - SSE boundary must always terminate the stream
            yield _sse(make_event("error", message=f"{type(exc).__name__}: {exc}", source="main"))
            yield _sse(make_event("done", thread_id=thread_id, status="error", interrupted=False))
        finally:
            for middleware in reversed(stack.active()):
                try:
                    await middleware.after_run(ctx)
                except Exception:  # noqa: BLE001 - after_run must not break the stream
                    pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/{thread_id}/resume")
async def resume_chat(thread_id: str, request_body: ResumeRequest, request: Request) -> dict[str, Any]:
    """Resume an interrupted thread with supplement and/or approval decisions."""
    runtime = _runtime(request)
    graph = _graph(request)
    storage = _storage(request)
    record = await storage.get_thread(thread_id)
    if record is None:
        raise HTTPException(status_code=404, detail="thread not found")
    owner = record.get("user_id", "anonymous")
    if request_body.user_id and request_body.user_id != owner:
        raise HTTPException(status_code=403, detail="thread does not belong to this user")
    user_id = owner
    payload: dict[str, Any] = {}
    if request_body.supplement:
        payload["supplement"] = request_body.supplement
    if request_body.decisions:
        payload["decisions"] = request_body.decisions
    if not payload:
        raise HTTPException(status_code=422, detail="supplement or decisions is required")

    ctx = RunContext(
        user_id=user_id,
        thread_id=thread_id,
        run_id=f"run-{uuid.uuid4().hex[:12]}",
        input_message=request_body.supplement or "resume",
    )
    await storage.append_event(thread_id, user_id, {"kind": "resume", "payload": payload})
    current_user_id.set(user_id)
    current_thread_id.set(thread_id)
    current_run_id.set(ctx.run_id)
    runtime.reset_model_budget()
    runtime.start_tool_budget(f"resume-{thread_id}")

    async def invoke():
        return await graph.ainvoke(Command(resume=payload), config=_new_config(thread_id))

    result = await _run_with_middleware(request, ctx, invoke)
    outcome = await _record_outcome(request, result, ctx)
    return outcome


@router.get("/history")
async def history(user_id: str, request: Request) -> list[dict[str, Any]]:
    return await _storage(request).list_threads(user_id)


@router.get("/history/{thread_id}")
async def history_detail(thread_id: str, request: Request, user_id: str | None = None) -> dict[str, Any]:
    record = await _storage(request).get_thread(thread_id)
    if record is None:
        raise HTTPException(status_code=404, detail="thread not found")
    if user_id and record.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="thread does not belong to this user")
    return record


@router.delete("/history/{thread_id}")
async def history_delete(thread_id: str, request: Request, user_id: str | None = None) -> dict[str, Any]:
    storage = _storage(request)
    record = await storage.get_thread(thread_id)
    if record is None:
        raise HTTPException(status_code=404, detail="thread not found")
    if user_id and record.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="thread does not belong to this user")
    deleted = await storage.delete_thread(thread_id)
    return {"thread_id": thread_id, "deleted": deleted}
