"""Run-scoped model-call budget (ContextVar), mirroring the tool budget."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class ModelCallBudget:
    run_id: str
    max_calls: int
    calls: int = 0
    exhausted: bool = False

    def record(self) -> bool:
        if self.calls >= self.max_calls:
            self.exhausted = True
            return False
        self.calls += 1
        return True


current_model_budget: ContextVar[ModelCallBudget | None] = ContextVar(
    "cloudops_harness_model_budget", default=None
)


def start_model_budget(run_id: str, max_calls: int) -> ModelCallBudget:
    budget = ModelCallBudget(run_id=run_id, max_calls=max_calls)
    current_model_budget.set(budget)
    return budget


def get_model_budget() -> ModelCallBudget | None:
    return current_model_budget.get()
