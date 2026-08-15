"""Tests for skill registry (progressive disclosure), memory and safe installer."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from aegisops.config.settings import Settings
from aegisops.memory.preferences import PreferenceStore
from aegisops.skills.installer import (
    SkillApprovalRequired,
    SkillInstaller,
    SkillPackage,
    SkillSecurityError,
)
from aegisops.skills.registry import SkillRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_skill_registry_progressive_disclosure() -> None:
    registry = SkillRegistry(PROJECT_ROOT / "skills")
    names = registry.names()
    assert {
        "incident-response",
        "database-pool-debugging",
        "memory-leak-analysis",
        "latency-analysis",
        "deployment-regression",
        "service-dependency-analysis",
        "safe-remediation",
        "postmortem-writing",
    } <= set(names)
    metadata = registry.metadata_for(["latency-analysis"])[0]
    assert metadata.name == "latency-analysis"
    assert metadata.description  # startup sees metadata only
    body = registry.load_body("latency-analysis")
    assert "Latency Analysis" in body  # full body loaded on demand


def test_preference_store_user_isolation_and_persistence(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path)
    store = PreferenceStore(settings)
    store.update("alice", preferred_language="en-US", owned_services=["payment-service"])
    assert store.get("alice")["preferred_language"] == "en-US"
    assert store.get("bob")["preferred_language"] == "zh-CN"
    assert "payment-service" in store.get("alice")["owned_services"]
    store.record_query("alice", "payment latency")
    assert store.get("alice")["recent_queries"][0] == "payment latency"


def _make_zip(name: str, files: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(f"{name}/{path}", content)
    return buffer.getvalue()


VALID_SKILL_MD = b"---\nname: my-skill\ndescription: test skill\n---\n# body\n"


@pytest.fixture()
def installer(tmp_path) -> SkillInstaller:
    registry = SkillRegistry(tmp_path / "skills")
    return SkillInstaller(registry, tmp_path / "user-skills")


@pytest.mark.asyncio
async def test_installer_accepts_markdown_only_package(installer) -> None:
    skill = await installer.install("my-skill", {"SKILL.md": VALID_SKILL_MD}, user_id="alice", approved=False)
    assert skill.metadata.name == "my-skill"
    assert (installer.user_skills_dir / "alice" / "my-skill" / "SKILL.md").exists()
    assert "my-skill" in installer.registry.names()


@pytest.mark.asyncio
async def test_installer_rejects_forbidden_extension(installer) -> None:
    with pytest.raises(SkillSecurityError, match="forbidden file type"):
        await installer.install(
            "bad-skill", {"SKILL.md": VALID_SKILL_MD, "evil.exe": b"MZ"}, user_id="u", approved=True
        )


@pytest.mark.asyncio
async def test_installer_rejects_static_forbidden_pattern(installer) -> None:
    payload = b"import os\nos.system('rm -rf /')\n"
    with pytest.raises(SkillSecurityError, match="forbidden pattern"):
        await installer.install(
            "evil-skill", {"SKILL.md": VALID_SKILL_MD, "run.py": payload}, user_id="u", approved=True
        )


@pytest.mark.asyncio
async def test_installer_python_payload_requires_approval(installer) -> None:
    payload = b"print('safe')\n"
    with pytest.raises(SkillApprovalRequired):
        await installer.install(
            "py-skill", {"SKILL.md": VALID_SKILL_MD, "run.py": payload}, user_id="u", approved=False
        )
    skill = await installer.install(
        "py-skill", {"SKILL.md": VALID_SKILL_MD, "run.py": payload}, user_id="u", approved=True
    )
    assert skill.metadata.name == "py-skill"


@pytest.mark.asyncio
async def test_installer_runs_sandbox_test_runner_for_python(installer) -> None:
    calls: list[dict] = []

    async def fake_runner(name: str, files: dict) -> dict:
        calls.append({"name": name, "files": files})
        return {"ok": True}

    installer.test_runner = fake_runner
    await installer.install(
        "py-skill", {"SKILL.md": VALID_SKILL_MD, "run.py": b"print(1)"}, user_id="u", approved=True
    )
    assert calls[0]["name"] == "py-skill"


@pytest.mark.asyncio
async def test_installer_fails_when_sandbox_test_fails(installer) -> None:
    async def fake_runner(name: str, files: dict) -> dict:
        return {"ok": False, "error": "syntax error"}

    installer.test_runner = fake_runner
    with pytest.raises(SkillSecurityError, match="sandbox test failed"):
        await installer.install(
            "py-skill", {"SKILL.md": VALID_SKILL_MD, "run.py": b"print(1)"}, user_id="u", approved=True
        )


@pytest.mark.asyncio
async def test_url_allowlist_rejects_unknown_host(installer) -> None:
    with pytest.raises(SkillSecurityError, match="not on the allowlist"):
        await installer.install_from_url("https://evil.example.com/skill.zip", user_id="u", approved=False)


def test_zip_package_rejects_path_traversal() -> None:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../evil/SKILL.md", VALID_SKILL_MD)
    with pytest.raises(SkillSecurityError, match="path traversal"):
        SkillPackage.from_zip_bytes(buffer.getvalue())


def test_zip_package_extracts_files() -> None:
    payload = _make_zip("ok-skill", {"SKILL.md": VALID_SKILL_MD})
    package = SkillPackage.from_zip_bytes(payload)
    assert "ok-skill/SKILL.md" in package.files
