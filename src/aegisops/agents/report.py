"""Deterministic Incident Report renderer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def render_incident_report(state: dict[str, Any]) -> str:
    """Render a complete postmortem-style markdown report from graph state."""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    service = state.get("service", "unknown")
    scenario = state.get("scenario") or {}
    rca = state.get("rca") or {}
    reports = state.get("subagent_reports", {}) or {}
    plan = state.get("plan") or []
    actions = state.get("executed_actions", [])
    rejected = state.get("rejected_actions", [])
    verification = state.get("verification") or {}
    remediation = state.get("remediation_plan") or {}

    lines: list[str] = []
    lines.append("# AegisOps Incident Report")
    lines.append("")
    lines.append(f"- **Incident ID**: {scenario.get('incident_id', state.get('scenario_id', 'N/A'))}")
    lines.append(f"- **Service**: {service}")
    lines.append(f"- **Environment**: {state.get('environment', 'prod')}")
    lines.append(f"- **Window**: {state.get('time_range_start', '?')} .. {state.get('time_range_end', '?')}")
    lines.append(f"- **Generated at**: {now}")
    lines.append("")
    lines.append("## 1. Root Cause")
    lines.append("")
    lines.append(f"- **Root cause**: {rca.get('root_cause', scenario.get('root_cause', 'unknown'))}")
    lines.append(f"- **Fault type**: {rca.get('fault_type', scenario.get('fault_type', 'unknown'))}")
    lines.append(f"- **Confidence**: {rca.get('confidence', 0)}")
    if rca.get("supporting_evidence"):
        lines.append(f"- **Supporting evidence**: {rca['supporting_evidence']}")
    if rca.get("contradicting_evidence"):
        lines.append(f"- **Contradicting evidence**: {rca['contradicting_evidence']}")
    if rca.get("unresolved"):
        lines.append(f"- **Unresolved**: {rca['unresolved']}")
    lines.append("")
    lines.append("## 2. Evidence Summary")
    lines.append("")
    for source, report in reports.items():
        lines.append(f"- **{source}** ({report.get('confidence', 0):.2f}): {report.get('summary', '')}")
        if source == "change-analysis" and report.get("temporal_correlation") is not None:
            lines.append(
                f"  - temporal_correlation={report['temporal_correlation']} "
                f"causal_confidence={report.get('causal_confidence', 0)}"
            )
        for signal in report.get("signals", [])[:6]:
            lines.append(f"  - signal: {signal}")
    lines.append("")
    lines.append("## 3. Plan")
    lines.append("")
    lines.append(" | ".join(f"{s['id']}:{s['status']}" for s in plan))
    lines.append("")
    lines.append("## 4. Remediation")
    lines.append("")
    if remediation.get("proposed_actions"):
        for action in remediation["proposed_actions"]:
            lines.append(
                f"- Proposed: `{action.get('tool_name')}` risk={action.get('risk_level')} "
                f"reason={action.get('reason', '')}"
            )
    else:
        lines.append("- No production actions proposed.")
    if remediation.get("safe_alternative"):
        lines.append(f"- Safe alternative: {remediation['safe_alternative']}")
    lines.append("")
    lines.append("## 5. Actions Taken")
    lines.append("")
    if actions:
        for action in actions:
            lines.append(
                f"- ✅ `{action.get('tool_name')}` args={action.get('arguments')} -> {action.get('result', {}).get('message', action.get('result'))}"
            )
    else:
        lines.append("- None (read-only investigation or all actions rejected).")
    if rejected:
        lines.append("")
        lines.append("## 6. Rejected Actions & Safe Alternatives")
        lines.append("")
        for action in rejected:
            lines.append(f"- ⛔ Rejected: `{action.get('tool_name')}` args={action.get('arguments')}")
        for alternative in remediation.get("safe_alternative", "").split("; "):
            if alternative:
                lines.append(f"  - Alternative: {alternative}")
    lines.append("")
    lines.append("## 7. Verification")
    lines.append("")
    lines.append(
        f"- resolved={verification.get('resolved', False)} status={verification.get('status', 'not verified')}"
    )
    lines.append(f"- {verification.get('summary', 'not verified')}")
    if verification.get("before_state"):
        lines.append(f"- before-state: {verification['before_state']}")
    lines.append("")
    lines.append("## 8. Follow-ups")
    lines.append("")
    lines.append("- Review runbook and schedule a blameless postmortem.")
    lines.append("- Add automated guard for the observed fault signature.")
    lines.append("")
    return "\n".join(lines)
