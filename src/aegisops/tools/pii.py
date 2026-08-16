"""PII redaction applied at the tool boundary (before any agent context)."""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -])?(?:\(\d{2,4}\)|\d{2,4})[ -]\d{2,4}[ -]\d{3,8}(?!\d)")
API_KEY_RE = re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._-]{12,})\b")

REDACTED = "[REDACTED]"


def redact_pii(text: str) -> str:
    """Replace common PII shapes in tool output. Best-effort, not a legal
    guarantee: the real boundary against secrets is the sandbox + policy."""
    text = EMAIL_RE.sub(REDACTED, text)
    text = API_KEY_RE.sub(REDACTED, text)
    text = PHONE_RE.sub(REDACTED, text)
    return text
