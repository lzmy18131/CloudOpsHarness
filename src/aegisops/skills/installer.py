"""Safe dynamic skill installation.

Security gates (all mandatory, in order):
1. URL / source allowlist or local path validation
2. file-type allowlist
3. total size limit
4. static inspection (forbidden patterns, path traversal)
5. optional sandbox test execution for Python payloads
6. approval policy for any executable payload
"""

from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from aegisops.skills.registry import Skill, SkillMetadata, SkillRegistry

ALLOWED_EXTENSIONS = {".md", ".py", ".txt", ".yaml", ".yml", ".json"}
FORBIDDEN_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\s*\.\s*\w+\s*\([^)]*shell\s*=\s*True",
    r"\brm\s+-rf\s+/",
    r"curl\s+[^\n|]*\|\s*(ba)?sh",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"__import__\s*\(",
    r"base64\.b64decode\s*\(",
    r"/etc/(passwd|shadow)",
    r"C:\\Windows\\System32",
]
SAFE_SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class SkillSecurityError(RuntimeError):
    """A skill package failed a security gate."""


class SkillApprovalRequired(RuntimeError):
    """Executable skill payload needs explicit approval."""


@dataclass
class SkillPackage:
    files: dict[str, bytes] = field(default_factory=dict)

    @classmethod
    def from_zip_bytes(cls, payload: bytes, max_size_bytes: int = 512 * 1024) -> SkillPackage:
        if len(payload) > max_size_bytes:
            raise SkillSecurityError(f"package size {len(payload)} exceeds {max_size_bytes} bytes")
        package = cls()
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename.replace("\\", "/")
                    if name.startswith("/") or ".." in Path(name).parts:
                        raise SkillSecurityError(f"zip entry path traversal: {info.filename}")
                    package.files[name] = archive.read(info)
        except zipfile.BadZipFile as exc:
            raise SkillSecurityError(f"not a valid zip: {exc}") from exc
        return package


class SkillInstaller:
    """Validates, tests and persists user skills under a per-user namespace."""

    def __init__(
        self,
        registry: SkillRegistry,
        user_skills_dir: Path | str,
        *,
        allowed_hosts: tuple[str, ...] = ("github.com", "raw.githubusercontent.com"),
        max_size_bytes: int = 512 * 1024,
        test_runner: Callable[..., Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        self.registry = registry
        self.user_skills_dir = Path(user_skills_dir)
        self.user_skills_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_hosts = set(allowed_hosts)
        self.max_size_bytes = max_size_bytes
        self.test_runner = test_runner

    # ------------------------------------------------------------- validation
    def validate(self, name: str, files: dict[str, bytes]) -> list[str]:
        """Return security issues; empty list means the package is acceptable."""
        issues: list[str] = []
        if not SAFE_SKILL_NAME.match(name):
            issues.append(f"invalid skill name: {name!r}")
        if not files:
            issues.append("empty skill package")
            return issues
        total = sum(len(content) for content in files.values())
        if total > self.max_size_bytes:
            issues.append(f"package too large: {total} bytes")
        for path, content in files.items():
            suffix = Path(path).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                issues.append(f"forbidden file type: {path} ({suffix or 'no extension'})")
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, content.decode("utf-8", errors="ignore"), re.IGNORECASE):
                    issues.append(f"forbidden pattern {pattern!r} in {path}")
        skill_md = next((p for p in files if p.endswith("SKILL.md")), None)
        if skill_md is None:
            issues.append("missing SKILL.md")
        else:
            text = files[skill_md].decode("utf-8", errors="ignore")
            if not text.startswith("---"):
                issues.append("SKILL.md missing YAML frontmatter")
        return issues

    def _parse_skill(self, name: str, files: dict[str, bytes]) -> Skill:
        skill_md = next(p for p in files if p.endswith("SKILL.md"))
        body = files[skill_md].decode("utf-8")
        import yaml

        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", body, re.DOTALL)
        frontmatter = yaml.safe_load(match.group(1)) if match else {}
        return Skill(
            metadata=SkillMetadata(
                name=name,
                description=str((frontmatter or {}).get("description", "")),
                path=str(skill_md),
            ),
            body=match.group(2) if match else body,
        )

    # ---------------------------------------------------------------- install
    async def install(self, name: str, files: dict[str, bytes], *, user_id: str, approved: bool) -> Skill:
        issues = self.validate(name, files)
        if issues:
            raise SkillSecurityError("; ".join(issues))
        has_executable = any(path.endswith(".py") for path in files)
        if has_executable and not approved:
            raise SkillApprovalRequired(f"skill {name!r} contains Python files and needs approval")
        if has_executable and self.test_runner is not None:
            result = await self.test_runner(name, files)
            if not result.get("ok"):
                raise SkillSecurityError(f"sandbox test failed: {result.get('error', 'unknown')}")

        skill = self._parse_skill(name, files)
        user_dir = self.user_skills_dir / user_id / name
        user_dir.mkdir(parents=True, exist_ok=True)
        for path, content in files.items():
            target = user_dir / Path(path).name
            target.write_bytes(content)
        self.registry.register(skill)
        return skill

    async def install_from_url(self, url: str, *, user_id: str, approved: bool) -> Skill:
        host = (urlparse(url).hostname or "").lower()
        if host not in self.allowed_hosts:
            raise SkillSecurityError(f"URL host {host!r} is not on the allowlist")
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.content
        package = SkillPackage.from_zip_bytes(payload, self.max_size_bytes)
        name = Path(urlparse(url).path).stem
        return await self.install(name, package.files, user_id=user_id, approved=approved)
