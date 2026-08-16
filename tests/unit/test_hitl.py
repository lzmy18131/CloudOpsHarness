"""Exact HITL decision binding tests (regression for fallback-approval bug)."""

from __future__ import annotations

from cloudops_harness.agents.hitl import assign_action_ids, resolve_decisions
from cloudops_harness.agents.models import Decision


def test_assign_action_ids_is_stable_and_unique() -> None:
    actions = assign_action_ids([{"tool_name": "rollback_release"}, {"tool_name": "restart_service"}])
    ids = [a["action_id"] for a in actions]
    assert ids[0].startswith("act-1-") and ids[1].startswith("act-2-")
    assert len(set(ids)) == 2


def test_decision_must_bind_exact_action_no_fallback_approval() -> None:
    proposed = assign_action_ids(
        [
            {"tool_name": "rollback_release", "risk_level": 3},
            {"tool_name": "restart_service", "risk_level": 2},
        ]
    )
    decisions = [Decision(type="approve", action_id=proposed[0]["action_id"])]
    resolved = resolve_decisions(proposed, decisions)
    assert resolved[proposed[0]["action_id"]].type == "approve"
    assert resolved[proposed[1]["action_id"]].type == "reject"
    assert "no explicit approval" in resolved[proposed[1]["action_id"]].comment


def test_nonexistent_action_id_cannot_approve_anything() -> None:
    proposed = assign_action_ids([{"tool_name": "rollback_release"}, {"tool_name": "restart_service"}])
    decisions = [Decision(type="approve", action_id="act-nonexistent")]
    resolved = resolve_decisions(proposed, decisions)
    assert all(d.type == "reject" for d in resolved.values())


def test_legacy_tool_name_binding_works_only_when_unambiguous() -> None:
    proposed = assign_action_ids([{"tool_name": "rollback_release"}])
    decisions = [Decision(type="approve", tool_name="rollback_release")]
    resolved = resolve_decisions(proposed, decisions)
    assert resolved[proposed[0]["action_id"]].type == "approve"

    ambiguous = assign_action_ids([{"tool_name": "restart_service"}, {"tool_name": "restart_service"}])
    decisions_ambiguous = [Decision(type="approve", tool_name="restart_service")]
    resolved_ambiguous = resolve_decisions(ambiguous, decisions_ambiguous)
    assert all(d.type == "reject" for d in resolved_ambiguous.values())
