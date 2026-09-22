#!/usr/bin/env python3
"""ArchiveBrowser doc-type filter taxonomy parity (mailroom-issues #70 B4).

Cements the ArchiveBrowser type filter against the canonical doc-class set:
``merger_agreement`` is a live class (mailroom_ui/pipeline_schema.py) and must
be offered as a filter; ``compliance_filing`` is RETIRED and must not be.
Guards against a subtree/UI refresh re-adding the retired option or dropping
the live one.

The Mailroom UI is a Vite React app without a JS unit-suite in-repo, so this
pin reads the component source like the compliance-removal guard does.

Run:  python3 -m unittest discover scripts/tests -v
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_BROWSER = (
    REPO_ROOT
    / "packages"
    / "The-Mailroom"
    / "ui"
    / "src"
    / "components"
    / "ArchiveBrowser.tsx"
)

FIVE_LIVE_CLASSES = {
    "contract": "Contract",
    "merger_agreement": "Merger Agreement",
    "corporate_record": "Corporate Record",
    "correspondence": "Correspondence",
    "insurance_claim": "Insurance Claim",
}


class TestArchiveBrowserDocTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = ARCHIVE_BROWSER.read_text(encoding="utf-8")

    def test_source_exists(self):
        self.assertTrue(ARCHIVE_BROWSER.is_file(), f"missing {ARCHIVE_BROWSER}")

    def test_all_five_live_classes_offered_as_filters(self):
        for cls_name, label in FIVE_LIVE_CLASSES.items():
            with self.subTest(doc_type=cls_name):
                self.assertIn(
                    f'value="{cls_name}"', self.src,
                    f"{cls_name} filter option missing from ArchiveBrowser")
                self.assertIn(label, self.src, f"{label} label missing from ArchiveBrowser")

    def test_retired_class_not_offered(self):
        self.assertNotIn(
            "compliance_filing", self.src,
            "retired compliance_filing option must not appear in ArchiveBrowser")


if __name__ == "__main__":
    unittest.main()