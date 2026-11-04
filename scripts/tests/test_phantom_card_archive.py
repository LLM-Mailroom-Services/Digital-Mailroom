"""Regression coverage for the DMR-103 archive reconciliation in PR #229."""

import unittest
from collections import Counter
from dataclasses import replace
from pathlib import Path

from scripts import board_state


ROOT = Path(__file__).resolve().parents[2]
REPO = "LLM-Mailroom-Services/Digital-Mailroom"
# The first seven records reserve IDs used by historical deliveries. The last
# three were moved from the open table after their PRs merged.
DELIVERIES = {
    "DMR-120": ("2026-09-30", "9fa7725f", None),
    "DMR-176": ("2026-09-24", "a5df7e41", 87),
    "DMR-182": ("2026-09-24", "6c90382a", 88),
    "DMR-188": ("2026-09-24", "82cc7660", 90),
    "DMR-189": ("2026-09-24", "82cc7660", 90),
    "DMR-190": ("2026-09-24", "82cc7660", 90),
    "DMR-191": ("2026-09-24", "16f17797", 89),
    "DMR-116": ("2026-11-04", "84685833", 224),
    "DMR-117": ("2026-11-04", "1e857921", 225),
    "DMR-118": ("2026-11-04", "28c42f59", 227),
}
PHANTOM_IDS = ("DMR-120", "DMR-176", "DMR-182", "DMR-188", "DMR-191")


class TestPhantomCardArchive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = board_state.parse_board(ROOT / "governance" / "TASKS.md")

    def test_deliveries_exist_once_in_archive_and_not_open(self):
        counts = Counter(card.id for card in [*self.state.open_cards, *self.state.archived_cards])
        for card_id, (date, _, _) in DELIVERIES.items():
            with self.subTest(card=card_id):
                self.assertEqual(counts[card_id], 1)
                card = self.state.find(card_id)
                self.assertEqual((card.section, card.lane, card.archived_date), ("archive", "done", date))

    def test_archive_entries_preserve_delivery_evidence(self):
        for card_id, (_, commit, pr) in DELIVERIES.items():
            with self.subTest(card=card_id):
                card = self.state.find(card_id)
                self.assertIsNotNone(card)
                self.assertIn(commit, card.evidence)
                if pr is not None:
                    self.assertIn(f"https://github.com/{REPO}/pull/{pr}", card.evidence)
                # A PR link must not be interpreted as a linked issue.
                self.assertIsNone(card.issue_number)
                self.assertIsNone(card.issue_url)
        self.assertIn("out of sequence", self.state.find("DMR-120").evidence)
        self.assertIn("https://github.com/Exios66/local-mailroom-sandbox/pull/247",
                      self.state.find("DMR-116").evidence)

    def test_historical_references_are_not_phantoms(self):
        refs = {card_id: [(DELIVERIES[card_id][1], f"{card_id} delivered")]
                for card_id in PHANTOM_IDS}
        findings = board_state.board_findings(self.state, refs, stale_days=7, origin_repo=REPO)
        self.assertEqual([f.card for f in findings if f.code == "phantom-card-reference"], [])

    def test_removing_each_historical_record_reveals_its_phantom(self):
        # Prove that the positive test depends on the archive records rather
        # than on disabling the validator or omitting the commit references.
        for card_id in PHANTOM_IDS:
            with self.subTest(card=card_id):
                state = replace(self.state, archived_cards=[
                    card for card in self.state.archived_cards if card.id != card_id
                ])
                refs = {card_id: [(DELIVERIES[card_id][1], f"{card_id} delivered")]}
                findings = board_state.board_findings(state, refs, stale_days=7, origin_repo=REPO)
                self.assertEqual([(f.severity, f.card) for f in findings
                                  if f.code == "phantom-card-reference"], [("error", card_id)])

    def test_reconciliation_card_retains_handoff_and_remaining_work(self):
        card = self.state.find("DMR-103")
        self.assertIsNotNone(card)
        self.assertIn("2026-11-04 handoff (Exios66)", card.evidence)
        for follow_up in ("foreign-issue-URL sync guard", "Glossary reference-audit",
                          "local v0.0.1 release-chain"):
            with self.subTest(follow_up=follow_up):
                self.assertIn(follow_up, card.evidence)
        if card.section == "open":
            self.assertEqual(card.issue_number, 190)


if __name__ == "__main__":
    unittest.main()
