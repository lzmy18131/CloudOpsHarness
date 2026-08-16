"""Exact HITL decision binding.

Every high-risk action gets a unique ``action_id``. A Decision must reference
that id (or, for legacy callers, a unique tool_name). An action without an
explicit decision is REJECTED by default - never approved by fallback.
"""

from __future__ import annotations

from typing import Any

from cloudops_harness.agents.models import Decision


def assign_action_ids(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give each proposed action a deterministic unique id."""
    for index, action in enumerate(actions, start=1):
        if not action.get("action_id"):
            action["action_id"] = f"act-{index}-{action.get('tool_name', 'unknown')}"
    return actions


def resolve_decisions(proposed: list[dict[str, Any]], decisions: list[Decision]) -> dict[str, Decision]:
    """Map every proposed action to exactly one decision.

    Explicit ``action_id`` binding wins. A legacy decision that only carries
    ``tool_name`` is accepted only when it matches exactly one proposed action.
    Anything else -> default reject.
    """
    resolved: dict[str, Decision] = {}
    used_decision_ids: set[int] = set()
    proposed_by_tool: dict[str, list[dict[str, Any]]] = {}
    for action in proposed:
        proposed_by_tool.setdefault(action.get("tool_name", ""), []).append(action)

    for action in proposed:
        action_id = action.get("action_id", "")
        decision = next(
            (
                (index, d)
                for index, d in enumerate(decisions)
                if index not in used_decision_ids and d.action_id == action_id
            ),
            None,
        )
        if decision is None:
            # legacy tool_name binding is only valid when unambiguous
            candidates = [
                (index, d)
                for index, d in enumerate(decisions)
                if index not in used_decision_ids
                and d.action_id is None
                and d.tool_name == action.get("tool_name")
            ]
            if len(candidates) == 1:
                decision = candidates[0]
        if decision is not None:
            used_decision_ids.add(decision[0])
            resolved[action_id or action.get("tool_name", "")] = decision[1]
            continue
        resolved[action_id or action.get("tool_name", "")] = Decision(
            type="reject", comment="no explicit approval for this action"
        )
    return resolved
