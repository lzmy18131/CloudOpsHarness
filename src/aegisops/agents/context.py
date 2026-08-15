"""Context Engineering: isolation assembly + compression for the main agent.

The invariant under test: main-agent LLM calls contain structured evidence
summaries only; raw telemetry transcripts stay in ``state.transcripts``.
"""

from __future__ import annotations

from typing import Any

from aegisops.llm.base import ModelAdapter
from aegisops.llm.models import LLMMessage

MAIN_SYSTEM_PROMPT = """You are the Incident Commander of AegisOps, a Harness-Engineered AIOps platform.
Your job: triage the incident, follow the plan, delegate to specialized subagents,
synthesize structured evidence into a root-cause hypothesis, request human approval
for risky production changes, execute approved actions, verify recovery and write
the incident report.

Safety rules (non-negotiable):
- You never execute restart_service / rollback_release / scale_service /
  apply_config_change without an explicit recorded HITL approval.
- You only reason over structured subagent reports; never request raw logs.
- CMDB facts (owners, versions, dependencies) come from tools, not from memory.
"""


def evidence_block(state: dict[str, Any], limit_per_source: int = 1200) -> str:
    """Render structured evidence for the main context (bounded)."""
    reports = state.get("subagent_reports", {}) or {}
    blocks: list[str] = []
    for source, report in reports.items():
        text = (
            f"[{source}] summary={report.get('summary', '')} "
            f"signals={report.get('signals', [])} hypotheses={report.get('hypotheses', [])} "
            f"confidence={report.get('confidence', 0)}"
        )
        if len(text) > limit_per_source:
            text = text[:limit_per_source] + "..."
        blocks.append(text)
    rca = state.get("rca") or {}
    if rca:
        blocks.append(f"[rca] {rca.get('root_cause', '')} (confidence={rca.get('confidence', 0)})")
    plan = state.get("plan") or []
    if plan:
        blocks.append("plan: " + " | ".join(f"{s['id']}:{s['status']}" for s in plan))
    return "\n".join(blocks) if blocks else "(no evidence yet)"


def assemble_main_messages(
    state: dict[str, Any],
    *,
    preferences: dict[str, Any] | None = None,
    skills_frontmatter: list[dict[str, Any]] | None = None,
    scenario: dict[str, Any] | None = None,
) -> list[LLMMessage]:
    """Build the main-agent context. This is the ONLY function allowed to feed
    the main LLM; it intentionally does not read ``state.transcripts``."""
    preferences = preferences or {}
    skills_frontmatter = skills_frontmatter or []
    scenario = scenario or state.get("scenario") or {}
    system_extra = [
        f"user_id: {state.get('user_id', 'anonymous')}",
        f"service: {state.get('service', 'unknown')}",
        f"environment: {state.get('environment', 'prod')}",
        f"window: {state.get('time_range_start', '?')} .. {state.get('time_range_end', '?')}",
        f"user preferences: {preferences}",
        "available skills (progressive disclosure): "
        + (", ".join(f"{s['name']}: {s['description']}" for s in skills_frontmatter) or "none"),
    ]
    if scenario:
        system_extra.append(f"INCIDENT_ID: {scenario.get('incident_id', '')}")
    messages = [
        LLMMessage(role="system", content=MAIN_SYSTEM_PROMPT + "\n" + "\n".join(system_extra)),
        LLMMessage(role="user", content=f"Evidence so far:\n{evidence_block(state)}"),
    ]
    # Append only the compressed tail of the main conversation.
    for item in state.get("messages", [])[-6:]:
        if item.get("role") in {"user", "assistant"}:
            messages.append(LLMMessage(role=item["role"], content=str(item.get("content", ""))[:4000]))
    return messages


class ContextCompressor:
    """Token-threshold compression for the main conversation.

    Strategy: move the oldest conversation turns into a single summary message
    while always keeping the most recent ``keep_last`` turns. Plan, evidence,
    decisions and unresolved hypotheses are state fields and therefore survive
    compression untouched.
    """

    def __init__(
        self,
        adapter: ModelAdapter | None = None,
        threshold_tokens: int = 24000,
        keep_last: int = 4,
    ) -> None:
        self.adapter = adapter
        self.threshold_tokens = threshold_tokens
        self.keep_last = keep_last

    def estimate(self, messages: list[LLMMessage]) -> int:
        return sum(ModelAdapter.estimate_tokens(m.content) for m in messages)

    def compress(self, messages: list[LLMMessage]) -> tuple[list[LLMMessage], list[LLMMessage]]:
        """Return (compressed_messages, offloaded_messages)."""
        if self.estimate(messages) <= self.threshold_tokens or len(messages) <= self.keep_last + 1:
            return messages, []
        offloaded: list[LLMMessage] = []
        working = list(messages)
        system = [m for m in working if m.role == "system"]
        tail = working[-self.keep_last :]
        middle = [m for m in working if m not in system and m not in tail]
        while self.estimate(system + middle + tail) > self.threshold_tokens and middle:
            offloaded.append(middle.pop(0))
        summary_text = self._summarize(offloaded)
        summary = LLMMessage(
            role="user",
            content=f"[compressed history] {len(offloaded)} earlier turns offloaded. Summary: {summary_text}",
        )
        return system + [summary] + tail, offloaded

    def _summarize(self, messages: list[LLMMessage]) -> str:
        if not messages:
            return ""
        roles = {}
        for message in messages:
            roles[message.role] = roles.get(message.role, 0) + 1
        first_user = next((m.content for m in messages if m.role == "user"), "")
        return f"roles={roles}; first_user_turn={first_user[:200]!r}"
