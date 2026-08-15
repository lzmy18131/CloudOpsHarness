"""Custom SSE event emission for LangGraph nodes.

Nodes call :func:`emit` with structured events; when the graph runs under
``astream(..., stream_mode="custom")`` the events reach the SSE endpoint.
Outside a streaming context the call is a no-op.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("aegisops.events")

try:
    from langgraph.config import get_stream_writer

    _HAS_STREAM_WRITER = True
except ImportError:  # pragma: no cover - future langgraph versions
    _HAS_STREAM_WRITER = False


def emit(event_type: str, **payload: Any) -> None:
    """Emit one custom event; safe no-op when not streaming."""
    event = {"type": event_type, **payload}
    if not _HAS_STREAM_WRITER:
        return
    try:
        writer = get_stream_writer()
        writer(event)
    except Exception:  # noqa: BLE001 - streaming is best-effort observability
        logger.debug("custom event dropped (no stream context): %s", event_type)
