"""Relative markdown links keep pointing at the post-reorganization tree."""

from __future__ import annotations

import re
from pathlib import Path

from mailroom_sandbox.job.runbooks import catalog_path, generated_dir
from mailroom_sandbox.paths import repo_root

_LINK = re.compile(r"(?<!!)\[(?:[^\]]*)\]\(([^)]+)\)")
_IMAGE = re.compile(r"!\[(?:[^\]]*)\]\(([^)]+)\)")
_FENCE = re.compile(r"```.*?```", re.DOTALL)

_SKIP_PREFIXES = (
    "vendor/",
    "CHANGELOG.md",
    "docs/releases/",
    "governance/TASKS.md",
    "governance/archive/",
)

_SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:")


def _iter_markdown() -> list[Path]:
    """Yield tracked markdown files, skipping vendor and release trees."""
    root = repo_root()
    files: list[Path] = []
    for path in root.rglob("*.md"):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(_SKIP_PREFIXES) or "/." in f"/{rel}":
            continue
        if any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in path.parts):
            continue
        files.append(path)
    return files


def _targets(text: str) -> list[str]:
    """Collect relative markdown link and image targets, ignoring fences."""
    stripped = _FENCE.sub("", text)
    found: list[str] = []
    for pattern in (_LINK, _IMAGE):
        for match in pattern.finditer(stripped):
            target = match.group(1).strip()
            if not target or target.startswith(_SKIP_SCHEMES) or target.startswith("#"):
                continue
            found.append(target.split("#", 1)[0].strip())
    return found


def test_relative_markdown_links_resolve():
    """Every relative markdown href in the repo tree must exist on disk."""
    root = repo_root()
    missing: list[str] = []
    for path in _iter_markdown():
        for target in _targets(path.read_text(encoding="utf-8")):
            if "://" in target:
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                rel = path.relative_to(root).as_posix()
                missing.append(f"{rel} -> {target}")
    assert missing == [], "broken relative markdown links:\n" + "\n".join(missing)


_STALE_DOC_PATHS = (
    "docs/LAYOUT.md",
    "docs/QUICKSTART.md",
    "docs/docker-offline.md",
    "docs/providers.md",
    "docs/remote-serving.md",
    "docs/sister-repos.md",
    "docs/mailroom-themed-logging.md",
    "docs/mailroom-watch-web.md",
    "docs/benchmark-l4.md",
    "docs/modal-doc-jobs.md",
    "docs/modal-serving-ops.md",
    "docs/extraction-quality-diagnosis.md",
    "docs/runbooks/l4-qwen3-8b.md",
    "docs/runbooks/baseline.md",
    "docs/runbooks/improved.md",
    "docs/PROMPT-ENHANCEMENT-PLAN.md",
)


def test_moved_doc_paths_are_not_cited():
    """Operator docs cite the current nested paths, not the pre-move names."""
    root = repo_root()
    stale: list[str] = []
    skip = (
        "vendor/",
        "docs/releases/",
    )
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".yml", ".yaml", ".example", ".html", ".ipynb"}:
            continue
        rel = path.relative_to(root).as_posix()
        if (
            rel.startswith(skip)
            or rel == "tests/test_doc_paths.py"
            or any(part in {".git", ".venv", "__pycache__"} for part in path.parts)
        ):
            continue
        text = path.read_text(encoding="utf-8")
        for old in _STALE_DOC_PATHS:
            if old not in text:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if old not in line:
                    continue
                if "github.com/" in line:
                    continue
                stale.append(f"{rel}:{i}: {old}")
    assert stale == [], "stale pre-move doc paths:\n" + "\n".join(stale)


def test_generated_runbook_catalog_links_resolve():
    """Generated runbook catalog hrefs resolve from each family file depth."""
    catalog = catalog_path().resolve()
    link_re = re.compile(r"\[`config/runbooks/catalog.yaml`\]\(([^)]+)\)")
    broken: list[str] = []
    for path in generated_dir().rglob("*.md"):
        for match in link_re.finditer(path.read_text(encoding="utf-8")):
            target = (path.parent / match.group(1)).resolve()
            if target != catalog:
                rel = path.relative_to(repo_root()).as_posix()
                broken.append(f"{rel} -> {match.group(1)}")
    assert broken == [], "generated catalog links do not resolve:\n" + "\n".join(broken)
