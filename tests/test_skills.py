"""Project Cursor skills are present and discoverable."""

from __future__ import annotations

import re
from pathlib import Path

from mailroom_sandbox.paths import repo_root

REQUIRED = (
    "sandbox-tool-router",
    "langfuse",
    "braintrust",
    "apache-phoenix",
    "ollama",
    "modal",
    "huggingface",
)

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def test_cursor_skills_exist_with_frontmatter():
    root = repo_root() / ".cursor" / "skills"
    assert root.is_dir()
    for name in REQUIRED:
        path = root / name / "SKILL.md"
        assert path.is_file(), f"missing skill {path}"
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER.match(text)
        assert match, f"{path} missing YAML frontmatter"
        meta = match.group(1)
        assert f"name: {name}" in meta
        assert "description:" in meta
        assert len(meta.strip()) > 40
