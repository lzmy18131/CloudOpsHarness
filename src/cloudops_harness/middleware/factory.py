"""Build the full middleware stack in the order defined by the harness design."""

from __future__ import annotations

from cloudops_harness.middleware.base import MiddlewareStack
from cloudops_harness.middleware.context_injection import ContextInjectionMiddleware
from cloudops_harness.middleware.memory_update import MemoryUpdateMiddleware
from cloudops_harness.middleware.model_limit import ModelCallLimitMiddleware
from cloudops_harness.middleware.pii_redaction import PIIRedactionMiddleware
from cloudops_harness.middleware.sandbox_breaker import SandboxCircuitBreakerMiddleware
from cloudops_harness.middleware.sandbox_health import SandboxHealthMiddleware
from cloudops_harness.middleware.skills_sync import SkillsSyncMiddleware
from cloudops_harness.middleware.tool_limit import ToolCallLimitMiddleware
from cloudops_harness.middleware.tool_policy import ToolPolicyMiddleware
from cloudops_harness.middleware.tracing import TracingMiddleware
from cloudops_harness.middleware.user_skills_restore import UserSkillsRestoreMiddleware


def build_middleware_stack(runtime) -> MiddlewareStack:
    """1 health → 2 context → 3 skills sync → 4 restore → 5 memory → 6 breaker →
    7 model limit → 8 tool limit → + policy/tracing."""
    stack = MiddlewareStack(
        [
            SandboxHealthMiddleware(runtime.sandbox_health),
            ContextInjectionMiddleware(
                runtime.memory,
                runtime.skills,
                auto_approve_max_risk=runtime.settings.auto_approve_max_risk,
            ),
            SkillsSyncMiddleware(runtime.sandbox_manager, runtime.skills),
            UserSkillsRestoreMiddleware(runtime.sandbox_manager, runtime.settings.user_skills_dir),
            MemoryUpdateMiddleware(runtime.memory),
            SandboxCircuitBreakerMiddleware(runtime.sandbox_breaker),
            ModelCallLimitMiddleware(limit=runtime.settings.model_call_limit),
            ToolCallLimitMiddleware(runtime.registry),
            ToolPolicyMiddleware(runtime.registry.policy),
            PIIRedactionMiddleware(enabled=runtime.settings.pii_redaction),
            TracingMiddleware(),
        ]
    )
    return stack
