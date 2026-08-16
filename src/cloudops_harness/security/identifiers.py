"""Central identifier and path-containment validation.

External ``user_id`` / ``thread_id`` values must never be concatenated into
filesystem paths without passing through these helpers. This provides logical
isolation between supplied identifiers; it is NOT a production authN/authZ
boundary (see README limitations).
"""

from __future__ import annotations

import re
from pathlib import Path

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class InvalidIdentifierError(ValueError):
    """Raised when an external identifier is unsafe for use in a path."""


def validate_identifier(value: str, *, field: str = "identifier") -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.match(value):
        raise InvalidIdentifierError(f"invalid {field}: expected ^[A-Za-z0-9_-]{{1,64}}$ (got {value!r})")
    return value


def ensure_path_contained(base: Path, path: Path) -> Path:
    """Resolve ``path`` and require it to stay inside ``base``."""
    base_resolved = base.resolve()
    target_resolved = path.resolve()
    if base_resolved != target_resolved and base_resolved not in target_resolved.parents:
        raise InvalidIdentifierError(f"path escapes base directory: {path}")
    return target_resolved
