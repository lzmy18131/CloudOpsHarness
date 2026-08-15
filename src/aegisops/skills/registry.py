"""Skill registry with progressive disclosure.

Startup exposes only YAML frontmatter (name + description + metadata); the
full SKILL.md body is loaded on demand by agents or sandbox sync.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

FRONTMATTER_RE = r"\A---\s*\n(?P<frontmatter>.*?)\n---\s*\n(?P<body>.*)\Z"


class SkillMetadata(BaseModel):
    name: str
    description: str = ""
    path: str = ""
    when_to_use: str = ""
    tools: list[str] = Field(default_factory=list)
    safety: str = ""


class Skill(BaseModel):
    metadata: SkillMetadata
    body: str


class SkillRegistry:
    """Scans ``<root>/<skill-name>/SKILL.md`` directories."""

    def __init__(self, skills_dir: Path | str) -> None:
        self.root = Path(skills_dir)
        self._skills: dict[str, Skill] = {}
        self.scan()

    def scan(self) -> None:
        import re

        self._skills.clear()
        if not self.root.exists():
            return
        pattern = re.compile(FRONTMATTER_RE, re.DOTALL)
        for skill_file in sorted(self.root.glob("*/SKILL.md")):
            text = skill_file.read_text(encoding="utf-8")
            match = pattern.match(text)
            if not match:
                continue
            try:
                frontmatter = yaml.safe_load(match.group("frontmatter")) or {}
            except yaml.YAMLError:
                frontmatter = {}
            name = str(frontmatter.get("name", skill_file.parent.name))
            metadata = SkillMetadata(
                name=name,
                description=str(frontmatter.get("description", "")),
                path=str(skill_file),
                when_to_use=str(frontmatter.get("when_to_use", "")),
                tools=[str(t) for t in frontmatter.get("tools", [])],
                safety=str(frontmatter.get("safety", "")),
            )
            self._skills[name] = Skill(metadata=metadata, body=match.group("body").strip())

    def list_metadata(self) -> list[SkillMetadata]:
        return [skill.metadata for skill in self._skills.values()]

    def metadata_for(self, names: list[str]) -> list[SkillMetadata]:
        return [self._skills[name].metadata for name in names if name in self._skills]

    def load_body(self, name: str) -> str:
        """Progressive disclosure: full content only when needed."""
        return self._skills[name].body

    def register(self, skill: Skill) -> None:
        """Register a user-installed skill without rescanning the filesystem."""
        self._skills[skill.metadata.name] = skill

    def names(self) -> list[str]:
        return sorted(self._skills)
