"""Integration contracts for the five canonical board rows added by PR #149.

Exercise the real parser, validator and read-only JSON CLI. All five cards are
now archive bullets (DMR-085..089 closed 2026-10-24), so the markers below are
phrases that the archived bullet text really carries, and the issue-link
parsing contract is pinned on a fixture board rather than on the live file.

Run: python3 -m unittest discover -s scripts/tests -p 'test_test_discipline_board.py' -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from dataclasses import replace
from pathlib import Path

from scripts import board_state


REPO_ROOT = Path(__file__).resolve().parents[2]
REPO = "LLM-Mailroom-Services/Digital-Mailroom"
CARD_MARKERS = {
    "DMR-085": "§ Test discipline",
    "DMR-086": "`_engine_lock`",
    "DMR-087": "expected length 2 != predicted length 1",
    "DMR-088": "keeps the worst rc",
    "DMR-089": "`VERIFY: RED`",
}


class TestTestDisciplineBoard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = board_state.parse_board(REPO_ROOT / "governance" / "TASKS.md")

    def card(self, card_id):
        card = self.state.find(card_id)
        self.assertIsNotNone(card, f"missing audit card {card_id}")
        return card

    def test_new_cards_exist_exactly_once_across_open_and_archive(self):
        # Moving a card to the archive is allowed; dropping or duplicating it is not.
        counts = Counter(card.id for card in [*self.state.open_cards, *self.state.archived_cards])
        self.assertEqual({card_id: counts[card_id] for card_id in CARD_MARKERS}, dict.fromkeys(CARD_MARKERS, 1))

    def test_task_and_evidence_columns_survive_parsing(self):
        for card_id, marker in CARD_MARKERS.items():
            with self.subTest(card_id=card_id):
                card = self.card(card_id)
                self.assertIn(marker, card.task)
                self.assertTrue(card.evidence.strip(), f"{card_id} lost its evidence column")
                self.assertIn(card.lane, board_state.LANES)

    def test_parent_issue_link_is_parsed_as_issue_148(self):
        # DMR-085's archive bullet no longer links issue #148, so pin the parser
        # contract on a fixture open row that does.
        board = Path(self.enterContext(tempfile.TemporaryDirectory())) / "TASKS.md"
        board.write_text(
            "## Open cards\n\n"
            "| ID | Status | Task | Owner | Issue | Evidence |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            f"| DMR-085 | `done` | Test discipline | claude-code | "
            f"[#148](https://github.com/{REPO}/issues/148) | landed |\n",
            encoding="utf-8",
        )
        card = board_state.parse_board(board).find("DMR-085")
        self.assertEqual(card.issue_number, 148)
        self.assertEqual(card.issue_url, f"https://github.com/{REPO}/issues/148")
        self.assertIs(card.issue_wellformed, True)

    def test_archived_audit_cards_carry_no_issue_link(self):
        # None of the five archive bullets links an issue; a card without a link
        # must not invent a number or a URL.
        for card_id in CARD_MARKERS:
            with self.subTest(card_id=card_id):
                card = self.card(card_id)
                self.assertEqual(card.section, "archive")
                self.assertIsNone(card.issue_number)
                self.assertIsNone(card.issue_url)

    def test_follow_up_cards_have_coherent_optional_issue_metadata(self):
        for card_id in ("DMR-086", "DMR-087", "DMR-088", "DMR-089"):
            with self.subTest(card_id=card_id):
                card = self.card(card_id)
                if card.issue_number is None:
                    # No link must remain board-only rather than becoming a bad link.
                    self.assertIsNone(card.issue_url)
                else:
                    # Permit a follow-up to acquire a real issue later.
                    self.assertIs(card.issue_wellformed, True)
                    self.assertEqual(card.issue_url, f"https://github.com/{REPO}/issues/{card.issue_number}")

    def test_new_cards_pass_board_structural_validation(self):
        findings = board_state.board_findings(self.state, refs={}, stale_days=7, origin_repo=REPO)
        relevant = [
            (finding.severity, finding.code, finding.card)
            for finding in findings
            if finding.card in CARD_MARKERS and finding.severity in ("error", "warning")
        ]
        self.assertEqual(relevant, [])

    def test_invalid_lane_in_a_new_card_is_rejected(self):
        card = replace(self.card("DMR-085"), section="open", lane="in-progress")
        state = replace(self.state, open_cards=[card], archived_cards=[])
        findings = board_state.board_findings(state, refs={}, stale_days=7, origin_repo=REPO)
        self.assertEqual(
            [(finding.severity, finding.code, finding.card) for finding in findings],
            [("error", "invalid-lane", "DMR-085")],
        )

    def test_card_cli_emits_complete_json_for_each_new_record(self):
        for card_id, marker in CARD_MARKERS.items():
            with self.subTest(card_id=card_id):
                result = subprocess.run(
                    [sys.executable, "scripts/board_state.py", "card", card_id, "--json", "--log-limit", "1"],
                    cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                card = self.card(card_id)
                self.assertEqual(data["id"], card_id)
                self.assertIn(marker, data["task"])
                # Compare the parsed data across the CLI serialization boundary,
                # including Unicode, inline code and the separate evidence column.
                for field in ("section", "lane", "task", "evidence", "owner", "issue_number", "issue_url", "issue_wellformed"):
                    self.assertEqual(data[field], getattr(card, field), field)


if __name__ == "__main__":
    unittest.main()
