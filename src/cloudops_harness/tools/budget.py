"""Run-scoped tool call budget.

Enforcement is scoped to one graph invocation (``run_id``) via a ContextVar;
telemetry stays global and is never used for enforcement.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class ToolCallBudget:
    run_id: str
    max_calls: int
    calls: int = 0
    per_tool: dict[str, int] = field(default_factory=dict)
    exhausted: bool = False

    def record(self, tool_name: str) -> bool:
        """Record one call. Returns False when the run budget is exhausted."""
        if self.calls >= self.max_calls:
            self.exhausted = True
            return False
        self.calls += 1
        self.per_tool[tool_name] = self.per_tool.get(tool_name, 0) + 1
        return True

    def usage(self) -> dict[str, int]:
        return {"run_id": self.run_id, "calls": self.calls, "max_calls": self.max_calls, **self.per_tool}


current_tool_budget: ContextVar[ToolCallBudget | None] = ContextVar(
    "cloudops_harness_tool_budget", default=None
)


def start_tool_budget(run_id: str, max_calls: int) -> ToolCallBudget:
    budget = ToolCallBudget(run_id=run_id, max_calls=max_calls)
    current_tool_budget.set(budget)
    return budget


def get_tool_budget() -> ToolCallBudget | None:
    return current_tool_budget.get()
