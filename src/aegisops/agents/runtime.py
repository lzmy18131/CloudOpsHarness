"""AegisRuntime: composition root wiring provider/MCP/tools/subagents/memory."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aegisops.agents.context import ContextCompressor
from aegisops.agents.events import emit
from aegisops.agents.subagents import (
    SubAgentRunner,
    load_subagent_configs,
    validate_subagent_config,
)
from aegisops.config.settings import Settings
from aegisops.llm.base import LimitedModelAdapter, ModelAdapter
from aegisops.llm.fake import FakeLLM
from aegisops.llm.openai_adapter import OpenAICompatibleAdapter
from aegisops.mcp.client import MCPToolAdapter
from aegisops.mcp.server import AegisMcpServer
from aegisops.memory.preferences import PreferenceStore
from aegisops.providers.mock import MockOpsProvider
from aegisops.providers.protocol import OpsProvider
from aegisops.runtime_context import current_run_id, current_thread_id, current_user_id, token_sink
from aegisops.sandbox.breaker import SandboxCircuitBreaker
from aegisops.sandbox.docker_backend import DockerSandboxBackend
from aegisops.sandbox.health import SandboxHealthMiddleware
from aegisops.sandbox.local_backend import LocalSandboxBackend
from aegisops.sandbox.manager import SandboxManager
from aegisops.skills.registry import SkillRegistry
from aegisops.tools.registry import ToolObserver, ToolRegistry, ToolResult
from aegisops.tools.sandbox_tools import (
    SandboxExecuteArgs,
    SandboxReadFileArgs,
    SandboxToolBridge,
    SandboxWriteFileArgs,
)

logger = logging.getLogger("aegisops.runtime")

FAULT_KEYWORDS: dict[str, list[str]] = {
    "bad-deployment": ["部署", "发布", "deploy", "release", "rollback", "新版本", "上线"],
    "database-connection-pool-exhaustion": ["连接池", "db pool", "connection pool", "数据库连接", "timeout"],
    "memory-leak": ["内存", "memory leak", "oom", "gc"],
    "redis-cache-timeout": ["redis", "缓存", "cache timeout"],
    "upstream-dependency-timeout": ["上游", "upstream", "dependency timeout", "依赖超时"],
    "disk-usage-saturation": ["磁盘", "disk", "容量"],
    "traffic-spike": ["流量", "spike", "traffic", "洪峰", "突增"],
    "configuration-error": ["配置", "config error", "configuration"],
    "cpu-saturation": ["cpu", "饱和", "打满"],
    "cascading-service-failure": ["级联", "cascading", "雪崩", "连锁"],
}


class TracingToolObserver(ToolObserver):
    """Emits tool_start/tool_end SSE events and persists JSONL traces."""

    def __init__(self, trace_store=None) -> None:
        self.trace_store = trace_store

    async def on_tool_start(
        self, agent: str, tool_name: str, args: dict[str, Any], risk_level: int = 0
    ) -> None:
        emit("tool_start", source=agent, tool_name=tool_name, risk_level=risk_level)
        emit("tool_args", source=agent, tool_name=tool_name, args=args)
        if self.trace_store is not None:
            self.trace_store.append(
                {
                    "kind": "tool_start",
                    "agent_name": agent,
                    "tool_name": tool_name,
                    "thread_id": current_thread_id.get(),
                    "run_id": current_run_id.get(),
                    "user_id": current_user_id.get(),
                    "arguments": args,
                    "risk_level": risk_level,
                }
            )

    async def on_tool_end(self, agent: str, result: ToolResult) -> None:
        emit(
            "tool_result",
            source=agent,
            tool_name=result.tool_name,
            ok=result.ok,
            error=result.error,
            latency_ms=result.latency_ms,
        )
        emit("tool_end", source=agent, tool_name=result.tool_name, ok=result.ok)
        if self.trace_store is not None:
            self.trace_store.append(
                {
                    "kind": "tool_end",
                    "agent_name": agent,
                    "tool_name": result.tool_name,
                    "thread_id": current_thread_id.get(),
                    "run_id": current_run_id.get(),
                    "user_id": current_user_id.get(),
                    "status": "ok" if result.ok else "error",
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                }
            )


class AegisRuntime:
    """Holds every long-lived object; FastAPI app state owns one instance."""

    def __init__(self, settings: Settings, provider: OpsProvider | None = None) -> None:
        self.settings = settings
        settings.ensure_dirs()
        self.base_provider = provider or MockOpsProvider(fixtures_dir=settings.fixtures_dir)
        self.mcp_server = AegisMcpServer(provider=self.base_provider)
        self.provider: OpsProvider = MCPToolAdapter(server=self.mcp_server)
        self.registry = ToolRegistry(self.provider, settings, observer=TracingToolObserver())
        self.memory = PreferenceStore(settings)
        self.skills = SkillRegistry(settings.skills_dir)
        self.compressor = ContextCompressor(threshold_tokens=settings.context_compression_threshold_tokens)
        self.scenario_index = self._load_scenario_index()

        # Sandbox five-component chain: health middleware -> manager -> proxy ->
        # backend protocol -> Docker/Local backend.
        self.sandbox_breaker = SandboxCircuitBreaker()
        self._docker_available: bool | None = None
        self.sandbox_manager = SandboxManager(
            self._make_sandbox_backend,
            seed_files=self._seed_files(),
            prewarm=settings.sandbox_prewarm,
            fallback_factory=self._make_local_sandbox_backend if settings.sandbox_backend == "auto" else None,
        )
        self.sandbox_health = SandboxHealthMiddleware(self.sandbox_manager)
        bridge = SandboxToolBridge(
            self.sandbox_manager,
            self.sandbox_breaker,
            auto_recovery=settings.sandbox_auto_recovery,
        )
        self.registry.register_dynamic(
            "sandbox_execute",
            "Execute a command inside the user's isolated sandbox (python/grep/analysis).",
            SandboxExecuteArgs,
            bridge.execute,
            read_only=True,
        )
        self.registry.register_dynamic(
            "sandbox_read_file",
            "Read a workspace-relative file from the sandbox.",
            SandboxReadFileArgs,
            bridge.read_file,
        )
        self.registry.register_dynamic(
            "sandbox_write_file",
            "Write a workspace-relative file into the sandbox.",
            SandboxWriteFileArgs,
            bridge.write_file,
        )

        configs = load_subagent_configs()
        errors: list[str] = []
        for config in configs:
            errors.extend(validate_subagent_config(config, self.registry))
        if errors:
            raise RuntimeError("invalid subagent configs: " + "; ".join(errors))
        self.subagent_configs = {config.name: config for config in configs}
        skills_frontmatter = {name: [] for name in self.skills.names()}
        for meta in self.skills.list_metadata():
            skills_frontmatter.setdefault(meta.name, []).append(meta.model_dump())
        self.subagent_runner = SubAgentRunner(
            self.registry,
            self.adapter_for,
            skills_frontmatter=skills_frontmatter,
        )
        self._real_adapter: OpenAICompatibleAdapter | None = None
        self.created_adapters: list[ModelAdapter] = []
        self.model_call_counter: dict[str, int] = {"calls": 0}

    # ------------------------------------------------------------- scenarios
    def _load_scenario_index(self) -> dict[str, dict[str, Any]]:
        path = self.settings.fixtures_dir / "incidents" / "scenarios.json"
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            records = data if isinstance(data, list) else data.get("scenarios", [])
            return {item["incident_id"]: item for item in records}
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("scenario index unavailable: %s", exc)
            return {}

    def activate_scenario(self, incident_id: str) -> dict[str, Any] | None:
        scenario = self.scenario_index.get(incident_id)
        if scenario is None:
            return None
        self.base_provider.activate_scenario(scenario)
        return scenario

    def match_scenario(self, user_query: str, service: str | None = None) -> dict[str, Any] | None:
        """Best-effort offline demo matching (real LLM mode does not need it)."""
        query = user_query.lower()
        # Explicit activation wins: evaluation/demo runners activate one
        # scenario before the run; never silently rematch it to a sibling.
        for active_id in self.base_provider.active_scenarios:
            active = self.scenario_index.get(active_id)
            if active and (service is None or active.get("service") == service):
                return active
        direct = next((s for s in self.scenario_index.values() if s["incident_id"].lower() in query), None)
        if direct:
            return direct
        candidates: list[dict[str, Any]] = []
        for scenario in self.scenario_index.values():
            if service and scenario.get("service") != service:
                continue
            keywords = FAULT_KEYWORDS.get(scenario.get("fault_type", ""), [])
            if any(keyword in query for keyword in keywords):
                candidates.append(scenario)
        if not candidates:
            return None
        # Prefer scenarios that demonstrate the HITL gate in demos.
        candidates.sort(
            key=lambda s: (bool(s.get("dangerous_action")), s.get("incident_id", "")), reverse=True
        )
        return candidates[0]

    # ------------------------------------------------------------------- llm
    def adapter_for(self, scenario: dict[str, Any] | None = None) -> ModelAdapter:
        if self.settings.llm_configured:
            if self._real_adapter is None:
                self._real_adapter = OpenAICompatibleAdapter(self.settings)
                self.created_adapters.append(self._real_adapter)
            self._real_adapter.token_callback = token_sink.get()
            base: ModelAdapter = self._real_adapter
        else:
            base = FakeLLM(scenario=scenario, scenario_index=self.scenario_index)
            base.token_callback = token_sink.get()
            self.created_adapters.append(base)
        return LimitedModelAdapter(
            base, max_calls=self.settings.model_call_limit, counter=self.model_call_counter
        )

    def reset_model_budget(self) -> None:
        """Start a fresh per-run model-call budget (called before each invoke)."""
        self.model_call_counter["calls"] = 0

    # ---------------------------------------------------------------- sandbox
    def _seed_files(self) -> dict[str, bytes]:
        seeds: dict[str, bytes] = {
            "AGENTS.md": b"# AegisOps sandbox workspace\nSandboxed analysis area. Host files are not mounted.\n"
        }
        for metadata in self.skills.list_metadata():
            path = Path(metadata.path)
            if path.exists():
                seeds[f"skills/{metadata.name}/SKILL.md"] = path.read_bytes()
        return seeds

    async def _make_local_sandbox_backend(self, user_id: str):
        workspace = self.settings.sandbox_workspace_dir / user_id
        return LocalSandboxBackend(workspace, user_id=user_id)

    async def _make_sandbox_backend(self, user_id: str):
        from aegisops.sandbox.protocol import SandboxBackend

        backend: SandboxBackend
        mode = self.settings.sandbox_backend
        if mode == "local":
            backend = await self._make_local_sandbox_backend(user_id)
        else:
            if self._docker_available is None:
                self._docker_available = await DockerSandboxBackend.is_available()
            if mode == "docker" and not self._docker_available:
                raise RuntimeError("AEGIS_SANDBOX_BACKEND=docker but Docker is unavailable")
            if self._docker_available:
                backend = DockerSandboxBackend(image=self.settings.sandbox_image, user_id=user_id)
            else:
                logger.warning(
                    "Docker unavailable; using LocalSandboxBackend (dev fallback, NOT a security boundary)"
                )
                backend = await self._make_local_sandbox_backend(user_id)
        return backend

    async def destroy_sandboxes(self) -> None:
        await self.sandbox_manager.destroy_all()

    def record_trace(self, kind: str, **fields: Any) -> None:
        """Persist one agent/HITL/report timeline record (no-op without a store)."""
        store = getattr(self.registry.observer, "trace_store", None)
        if store is None:
            return
        store.append(
            {
                "kind": kind,
                "run_id": current_run_id.get(),
                "thread_id": current_thread_id.get(),
                "user_id": current_user_id.get(),
                **fields,
            }
        )

    def snapshot_llm_usage(self) -> dict[str, int]:
        adapters = getattr(self, "created_adapters", [])
        return {
            "model_calls": sum(getattr(a, "call_count", 0) for a in adapters),
            "tokens": sum(getattr(a, "usage_total", 0) for a in adapters),
        }

    @property
    def middleware(self):
        if not hasattr(self, "_middleware"):
            from aegisops.middleware.factory import build_middleware_stack

            self._middleware = build_middleware_stack(self)
        return self._middleware

    # ----------------------------------------------------------------- graph
    def build_graph(self, checkpointer: Any = None) -> Any:
        from aegisops.agents.graph import build_incident_graph

        return build_incident_graph(self, checkpointer=checkpointer)
