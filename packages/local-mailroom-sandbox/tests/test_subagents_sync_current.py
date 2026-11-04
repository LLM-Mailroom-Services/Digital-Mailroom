"""The committed agent files are exactly what `sandbox subagents sync` writes.

Otherwise the next operator sync rewrites tracked files nobody edited.
"""
from __future__ import annotations

import pytest

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.subagents import load_roster
from mailroom_sandbox.subagents.sync import render_cursor_agent, render_opencode_agent

ROOT = repo_root()
ENTRIES = [e for e in load_roster(ROOT, None) if e.opencode_path(ROOT).is_file()]


@pytest.mark.parametrize("entry", [e for e in ENTRIES if "opencode" in e.harnesses], ids=lambda e: e.id)
def test_canonical_opencode_prompt_is_sync_stable(entry):
    assert entry.opencode_path(ROOT).read_text(encoding="utf-8") == render_opencode_agent(entry, ROOT)


@pytest.mark.parametrize("entry", [e for e in ENTRIES if "cursor" in e.harnesses], ids=lambda e: e.id)
def test_cursor_stub_matches_its_canonical_prompt(entry):
    assert entry.cursor_path(ROOT).read_text(encoding="utf-8") == render_cursor_agent(entry, ROOT)


def test_table_rows_do_not_split_on_a_bare_pipe_in_code():
    # In a GFM table a `|` inside backticks still ends the cell; write it as \|.
    for entry in ENTRIES:
        for line in entry.opencode_path(ROOT).read_text(encoding="utf-8").splitlines():
            if line.startswith("|") and "`" in line:
                code = line.split("`")[1::2]
                assert not any("|" in span.replace("\\|", "") for span in code), (entry.id, line)
