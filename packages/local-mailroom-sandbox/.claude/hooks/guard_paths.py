#!/usr/bin/env python3
"""PreToolUse guard: refuse Edit/Write/NotebookEdit on files Claude must not hand-edit.

Reads the hook JSON on stdin. Exit 2 (with a reason on stderr) blocks the call and
shows the reason to Claude; any other exit lets it through. Fails open on malformed
input so a hook bug can never wedge a session.
"""

from __future__ import annotations

import json
import os
import re
import sys

# (regex searched against the repo-relative POSIX path, explanation shown to Claude)
RULES = [
    (
        r"(^|/)\.env(\.(?!example$)[^/]+)?$",
        "Secrets file. Only .env.example files are tracked; ask the user to edit .env themselves.",
    ),
    (
        r"^vendor/(?!README\.md$)",
        "Tracked vendor snapshot, byte-checked by tests/test_vendor_drift.py. Fix the owning repo "
        "(llm-mailroom / llm-dojo-scoring) first, then refresh with `python scripts/sync_vendor.py` "
        "or `sandbox fetch-deps`.",
    ),
    (
        r"^requirements/[^/]+\.txt$",
        "Generated from pyproject.toml. Edit pyproject.toml, then run "
        "`python scripts/sync_requirements.py`.",
    ),
    (
        r"(^|/)uv\.lock$",
        "uv.lock is generated. Edit pyproject.toml and run `uv lock` instead.",
    ),
    (
        r"^data/(runtime|cache)/(?!README)",
        "Gitignored runtime state (prepared fixtures, Hub cache). Regenerate with `sandbox datasets ...`.",
    ),
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        tool_input = payload.get("tool_input") or {}
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    except Exception:
        return 0
    path = path.replace("\\", "/")
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    root = root.replace("\\", "/").rstrip("/") + "/"
    rel = path[len(root):] if path.startswith(root) else path
    for pattern, reason in RULES:
        if re.search(pattern, rel):
            print(f"Blocked edit to {path}: {reason}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
