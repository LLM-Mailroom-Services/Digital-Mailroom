#!/usr/bin/env python3
"""pull-issues reverse-lane precedence (mailroom-issues #70 B5).

Cements the closed-state-wins rule in ``board_state._reverse_lane_from_issue``:
a directly-closed issue (closed on GitHub, not via the site's archived:true +
lane:done path) may still carry a stale ``stage/*`` label (e.g.
``stage/in-progress``); pull-issues must import ``done``, not the stale work
lane. Open issues keep the stage/*-label-wins rule unchanged.

Hermetic: stdlib unittest only, no network, read-only. Import of
``scripts/board_state.py`` is safe (argparse lives behind __main__).

Run:  python3 -m unittest discover scripts/tests -v
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from board_state import _reverse_lane_from_issue  # noqa: E402


def issue(state="open", labels=()):
    return {"state": state, "labels": [{"name": n} for n in labels]}


class TestReverseLaneFromIssue(unittest.TestCase):
    def test_closed_state_wins_over_stale_stage_label(self):
        # B5 regression: closed on GitHub while still carrying a work-lane
        # label — must import as done, not as the stale lane.
        for stale in ("stage/in-progress", "stage/needs-attention", "stage/assigned", "stage/unassigned"):
            with self.subTest(stale=stale):
                self.assertEqual(
                    _reverse_lane_from_issue(issue("closed", [stale])),
                    "done",
                    f"closed issue with {stale} must reverse-sync as done",
                )

    def test_closed_without_labels_still_done(self):
        self.assertEqual(_reverse_lane_from_issue(issue("closed")), "done")

    def test_open_stage_label_still_wins(self):
        for label, lane in (
            ("stage/unassigned", "unassigned"),
            ("stage/assigned", "assigned"),
            ("stage/in-progress", "in_progress"),
            ("stage/needs-attention", "needs_attention"),
            ("stage/done", "done"),
        ):
            with self.subTest(label=label):
                self.assertEqual(
                    _reverse_lane_from_issue(issue("open", [label])),
                    lane,
                    f"open issue with {label} must reverse-sync as {lane}",
                )

    def test_open_without_stage_label_falls_to_assigned(self):
        self.assertEqual(_reverse_lane_from_issue(issue("open")), "assigned")
        self.assertEqual(
            _reverse_lane_from_issue(issue("open", ["priority/high", "kanban"])),
            "assigned",
        )

    def test_missing_state_field_treated_as_open(self):
        self.assertEqual(_reverse_lane_from_issue({"labels": [{"name": "stage/done"}]}), "done")


if __name__ == "__main__":
    unittest.main()