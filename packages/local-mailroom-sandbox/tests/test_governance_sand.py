"""SAND board governance — prefix isolation from the family DMR board."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "governance"
TASKS = GOV / "TASKS.md"
README = GOV / "README.md"
PREFIX = GOV / "PREFIX.md"
ARCHIVE_050 = GOV / "archive" / "SANDBOX-050.md"

# Primary: SAND-001 ; sub-card: SAND-010-3
SAND_ID_RE = re.compile(r"^SAND-(\d{3})(?:-(\d+))?$")
# Anything that looks like a board card id in a markdown table first column.
CARD_CELL_RE = re.compile(r"\|\s*(SAND-\d+(?:-\d+)?|DMR-\d+|SANDBOX-\d+(?:-\d+)?)\s*\|")


def _ids_in(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [m.group(1) for m in CARD_CELL_RE.finditer(text)]


def test_tasks_board_uses_sand_prefix_only():
    ids = _ids_in(TASKS)
    assert ids, "TASKS.md must list SAND cards"
    for card_id in ids:
        assert SAND_ID_RE.match(card_id), f"invalid or non-SAND card id: {card_id}"
        assert not card_id.startswith("DMR-"), "DMR cards must not appear on the SAND board"
        assert not card_id.startswith("SANDBOX-"), (
            "legacy SANDBOX-* ids belong in archive/, not TASKS.md"
        )


def test_next_id_line_present_and_ahead_of_listed_cards():
    text = TASKS.read_text(encoding="utf-8")
    m = re.search(r"\*\*Next ID:\s*`?(SAND-\d{3})`?\*\*", text)
    assert m, "TASKS.md must declare **Next ID: `SAND-NNN`**"
    next_id = m.group(1)
    next_n = int(SAND_ID_RE.match(next_id).group(1))
    primary_ns = {
        int(SAND_ID_RE.match(cid).group(1))
        for cid in _ids_in(TASKS)
        if SAND_ID_RE.match(cid)
    }
    assert next_n > max(primary_ns), (
        f"Next ID {next_id} must be greater than max listed primary ({max(primary_ns)})"
    )


