"""Unified SSE event envelope + LangGraph custom-stream emitter.

Every AegisOps event carries the same envelope:

    event_type | type (alias) | run_id | thread_id | source |
    timestamp | sequence

The sequence is monotonic per streaming task, so UIs can drop duplicates and
detect out-of-order frames. ``emit()`` is used inside graph nodes/tool
observer; API endpoints use ``make_event()`` for terminal frames.
"""

from __future__ import annotations

import itertools
import logging
from datetime import UTC, datetime
from typing import Any

from aegisops.runtime_context import current_run_id, current_thread_id

logger = logging.getLogger("aegisops.events")

_sequence = itertools.count(1)

try:
    from langgraph.config import get_stream_writer

    _HAS_STREAM_WRITER = True
except ImportError:  # pragma: no cover - future langgraph versions
    _HAS_STREAM_WRITER = False


def next_sequence() -> int:
    return next(_sequence)


def reset_sequence() -> None:
    global _sequence
    _sequence = itertools.count(1)


def make_event(event_type: str, **payload: Any) -> dict[str, Any]:
    """Build one envelope; never mutates caller payloads."""
    source = payload.pop("source", "main")
    event: dict[str, Any] = {
        "event_type": event_type,
        "type": event_type,  # alias kept for UI compatibility
        "run_id": current_run_id.get() or "",
        "thread_id": current_thread_id.get() or "",
        "source": source,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "sequence": next_sequence(),
    }
    event.update(payload)
    return event


def emit(event_type: str, **payload: Any) -> None:
    """Emit one custom stream event; safe no-op outside a streaming context."""
    if not _HAS_STREAM_WRITER:
        return
    event = make_event(event_type, **payload)
    try:
        writer = get_stream_writer()
        writer(event)
    except Exception:  # noqa: BLE001 - streaming is best-effort observability
        logger.debug("custom event dropped (no stream context): %s", event_type)
