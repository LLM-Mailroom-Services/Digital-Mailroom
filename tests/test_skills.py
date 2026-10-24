"""Project Cursor skills are present and discoverable."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Family names match local-mailroom-sandbox PR #4; extras are this visualizer.
REQUIRED = (
    "mailroom-tool-router",
    "langfuse",
    "braintrust",
    "apache-phoenix",
    "ollama",
    "modal",
    "huggingface",
    "pixel-console",
    "observatory",
    "live-floor",
    "pipeline-schema-sync",
    "gh-pages",
    "tui",
    "operator-desk",
    "optional-ui",
)

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def test_cursor_skills_exist_with_frontmatter():
    root = ROOT / ".cursor" / "skills"
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


def test_skills_readme_indexes_every_skill():
    readme = (ROOT / ".cursor" / "skills" / "README.md").read_text(encoding="utf-8")
    for name in REQUIRED:
        assert name in readme, f"README missing {name}"
    assert "mailroom-tool-router" in readme
    assert "local-mailroom-sandbox" in readme


def test_router_encodes_langfuse_default_and_no_node():
    router = (ROOT / ".cursor" / "skills" / "mailroom-tool-router" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "MAILROOM_SOURCE=langfuse" in router
    assert "no npm" in router.lower() or "npm" in router
    langfuse = (ROOT / ".cursor" / "skills" / "langfuse" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "LANGFUSE_HOST" in langfuse
    assert "MAILROOM CLOSED" in langfuse
    brain = (ROOT / ".cursor" / "skills" / "braintrust" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "not a display source" in brain.lower() or "Not a display source" in brain
    ollama = (ROOT / ".cursor" / "skills" / "ollama" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "not served here" in ollama.lower() or "not part of The-Mailroom" in ollama
    tui = (ROOT / ".cursor" / "skills" / "tui" / "SKILL.md").read_text(encoding="utf-8")
    assert "--resolve" in tui
    assert "--doc-type" in tui
    assert "/api/review/source" in tui
    assert "MAILROOM_API_URL" in tui
    assert "/api/review/resolve" in router
