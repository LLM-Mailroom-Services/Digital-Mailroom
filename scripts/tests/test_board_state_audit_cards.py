#!/usr/bin/env python3
"""Behavior contracts for the DMR-085 audit and its DMR-086..089 follow-ups.

PR #149 changes documentation and board data only. Exercise its actual new
rows through the board parser, validator and CLI; package defects described
by those rows belong to their respective fix PRs.

Hermetic stdlib unittest: only Git metadata/history are faked. Temporary
boards contain the repository's actual rows and are removed after each test.

Run: python3 -m unittest discover -s scripts/tests -p 'test_board_state_audit_cards.py' -v
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    import board_state
finally:
    sys.path.pop(0)

CARD_IDS = ("DMR-085", "DMR-086", "DMR-087", "DMR-088", "DMR-089")
ISSUE_URL = "https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/148"


class TestAuditCards(unittest.TestCase):
    def setUp(self):
        # Select by the ID column: child descriptions also mention DMR-085.
        # Missing or duplicate rows must fail rather than disappear from tests.
        rows = []
        for line in (REPO_ROOT / "governance" / "TASKS.md").read_text(
            encoding="utf-8",
        ).splitlines():
            cells = line.split("|", 2)
            if line.startswith("|") and cells[1].strip() in CARD_IDS:
                rows.append((cells[1].strip(), line))
        self.assertCountEqual([card_id for card_id, _ in rows], CARD_IDS)
        self.rows = dict(rows)

        directory = tempfile.TemporaryDirectory(prefix="audit-board-")
        self.addCleanup(directory.cleanup)
        self.board_path = Path(directory.name) / "TASKS.md"
        self.write_board()

        patches = contextlib.ExitStack()
        self.addCleanup(patches.close)
        patches.enter_context(mock.patch.object(board_state, "BOARD_PATH", self.board_path))
        patches.enter_context(mock.patch.object(
            board_state, "git_head", return_value=("fixture-head", False),
        ))
        patches.enter_context(mock.patch.object(
            board_state, "commits_for_cards", return_value={},
        ))
        # No test may accidentally execute Git, gh, or a remote write.
        patches.enter_context(mock.patch.object(
            board_state, "run", side_effect=AssertionError("unexpected external command"),
        ))

    def write_board(self, extra_rows=()):
        self.board_path.write_text(
            "# Audit board\n\n## Open cards\n\n"
            "| Card | Status | Task | Owner | Issue | Evidence |\n"
            "|---|---|---|---|---|---|\n"
            + "\n".join([*self.rows.values(), *extra_rows])
            + "\n\n## Archive\n",
            encoding="utf-8",
        )

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = board_state.main(list(args))
        return rc, stdout.getvalue(), stderr.getvalue()

    def check(self, expected_rc, *options):
        rc, stdout, stderr = self.cli(
            "check", "--json", "--repo", "LLM-Mailroom-Services/Digital-Mailroom", *options,
        )
        self.assertEqual(stderr, "")
        self.assertEqual(rc, expected_rc, stdout)
        result = json.loads(stdout)
        self.assertEqual(result["passed"], expected_rc == 0)
        # INFOs about the documented UTC date convention are legitimate.
        actionable = [
            (finding["severity"], finding["code"], finding["card"])
            for finding in result["findings"]
            if finding["severity"] in ("error", "warning")
        ]
        return result, actionable

    def test_parser_reads_each_row_once_despite_parent_references(self):
        state = board_state.parse_board()
        self.assertCountEqual([card.id for card in state.open_cards], CARD_IDS)
        self.assertEqual(state.archived_cards, [])
        for card_id in CARD_IDS:
            with self.subTest(card=card_id):
                card = state.find(card_id)
                self.assertEqual(card.id, card_id)
                self.assertEqual(card.section, "open")
                self.assertEqual(card.lane, "in_progress")
                self.assertEqual(card.owner, "claude-code 2026-10-21")
                self.assertFalse(card.pending_archive)

    def test_parent_has_issue_link_and_children_are_board_only(self):
        state = board_state.parse_board()
        parent = state.find("DMR-085")
        self.assertEqual(
            (parent.issue_number, parent.issue_url, parent.issue_wellformed),
            (148, ISSUE_URL, True),
        )
        for card_id in CARD_IDS[1:]:
            with self.subTest(card=card_id):
                card = state.find(card_id)
                self.assertEqual(card.issue_raw, "—")
                self.assertEqual(
                    (card.issue_number, card.issue_url, card.issue_wellformed),
                    (None, None, None),
                )

    def test_complex_task_text_and_branch_evidence_keep_their_columns(self):
        expected = {
            "DMR-085": ("new § Test discipline law", "claude/agents-md-test-discipline"),
            "DMR-086": ("table … already exists", "claude/dmr-086-storage-race"),
            "DMR-087": ("accuracy(['a','b'],['a']) == 1.0", "claude/dmr-087-dojo-length-guard"),
            "DMR-088": ("rc = rc or _refresh…()", "claude/dmr-088-fetch-deps-rc"),
            "DMR-089": ("VERIFY: RED", "claude/dmr-089-enron-verify-exit"),
        }
        state = board_state.parse_board()
        for card_id, (task, branch) in expected.items():
            with self.subTest(card=card_id):
                card = state.find(card_id)
                self.assertIn(task, card.task)
                self.assertIn(f"branch `{branch}`", card.evidence)
                self.assertNotIn(branch, card.task)

    def test_status_json_counts_synced_and_board_only_cards_separately(self):
        rc, stdout, stderr = self.cli("status", "--json")
        self.assertEqual((rc, stderr), (0, ""))
        result = json.loads(stdout)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["counts"], {
            "open": 5,
            "open_by_lane": {
                "unassigned": 0, "assigned": 0, "in_progress": 5,
                "needs_attention": 0, "done": 0,
            },
            "archived": 0, "synced": 1, "board_only": 4,
        })
        self.assertCountEqual([card["id"] for card in result["open_cards"]], CARD_IDS)

    def test_card_cli_accepts_lowercase_and_preserves_unicode_in_json(self):
        for card_id in CARD_IDS:
            with self.subTest(card=card_id):
                rc, stdout, stderr = self.cli("card", card_id.lower(), "--json")
                self.assertEqual((rc, stderr), (0, ""))
                card = json.loads(stdout)
                self.assertEqual(card["id"], card_id)
                self.assertEqual(card["lane"], "in_progress")
                self.assertEqual(card["issue_number"], 148 if card_id == "DMR-085" else None)
                self.assertEqual(card["commits"], [])
                if card_id == "DMR-085":
                    self.assertIn("Enron publish RED→exit 0", card["evidence"])

    def test_missing_card_cli_fails_without_printing_a_card(self):
        rc, stdout, stderr = self.cli("card", "dmr-999", "--json")
        self.assertEqual((rc, stdout), (1, ""))
        self.assertIn("no card DMR-999 on the board", stderr)

    def test_new_rows_pass_strict_governance_check(self):
        result, actionable = self.check(0, "--strict")
        self.assertEqual((result["errors"], result["warnings"]), (0, 0))
        self.assertEqual(actionable, [])

    def test_duplicate_followup_row_is_a_structural_error(self):
        self.write_board(extra_rows=[self.rows["DMR-087"]])
        result, actionable = self.check(1)
        self.assertEqual((result["errors"], result["warnings"]), (1, 0))
        self.assertEqual(actionable, [("error", "duplicate-card-id", "DMR-087")])

    def test_parent_issue_number_must_match_its_link(self):
        self.rows["DMR-085"] = self.rows["DMR-085"].replace("/issues/148", "/issues/149")
        self.write_board()
        result, actionable = self.check(1)
        self.assertEqual((result["errors"], result["warnings"]), (1, 0))
        self.assertEqual(actionable, [("error", "issue-link-malformed", "DMR-085")])

    def test_invalid_lane_is_a_structural_error(self):
        self.rows["DMR-089"] = self.rows["DMR-089"].replace("`in_progress`", "`in_progres`", 1)
        self.write_board()
        result, actionable = self.check(1)
        self.assertEqual((result["errors"], result["warnings"]), (1, 0))
        self.assertEqual(actionable, [("error", "invalid-lane", "DMR-089")])

    def test_unclaimed_followup_is_warned_and_fails_strict_mode(self):
        self.rows["DMR-088"] = self.rows["DMR-088"].replace(
            "| claude-code 2026-10-21 |", "| unclaimed |", 1,
        )
        self.write_board()
        for options, expected_rc in (((), 0), (("--strict",), 1)):
            with self.subTest(options=options):
                result, actionable = self.check(expected_rc, *options)
                self.assertEqual((result["errors"], result["warnings"]), (0, 1))
                self.assertEqual(actionable, [("warning", "in-progress-unclaimed", "DMR-088")])


if __name__ == "__main__":
    unittest.main()
