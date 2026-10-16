#!/usr/bin/env python3
"""Contracts for the three sync cursors re-baselined in DMR-082 (PR #136).

Read the committed manifest, isolating Git and network operations. Future
cursor advances are allowed; the pre-push baselines must not return.

Run: python3 -m unittest discover -s scripts/tests -p 'test_packages_sync_manifest.py' -v
"""

import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "scripts" / "packages_sync.json"
PRE_PUSH_CURSORS = {
    "llm-dojo-scoring": (
        "a2862cec3c7688a62e4d7fa4ba329a53d26c9c23", "2026-10-16T22:58:38Z",
    ),
    "llm-mailroom": (
        "a5bf7c8a74f2cc183624f7f12cb3decfa1df34fd", "2026-10-16T21:27:50Z",
    ),
    "local-mailroom-sandbox": (
        "850e75b252ef554b24a7316123be6cdb3fff0e49", "2026-10-16T21:27:50Z",
    ),
}
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class ManifestTestCase(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "sync_packages_manifest_test", REPO_ROOT / "scripts" / "sync_packages.py",
        )
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        # Missing tracked state must fail rather than load_manifest's empty fallback.
        self.assertTrue(MANIFEST.is_file())
        self.original_bytes = MANIFEST.read_bytes()
        self.manifest = self.mod.load_manifest("status")
        self.entries = self.manifest["packages"]

    def tearDown(self):
        self.assertEqual(MANIFEST.read_bytes(), self.original_bytes)


class TestRebaselinedManifest(ManifestTestCase):
    def test_manifest_has_no_duplicate_keys(self):
        # json.loads normally silently shadows a duplicated package/cursor key.
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                self.assertNotIn(key, result, f"duplicate manifest key: {key}")
                result[key] = value
            return result

        parsed = json.loads(self.original_bytes, object_pairs_hook=unique_object)
        self.assertEqual(parsed, self.manifest)

    def test_rebaselined_entries_have_complete_revision_and_upstream_metadata(self):
        self.assertEqual(self.manifest["version"], 1)
        for package in PRE_PUSH_CURSORS:
            with self.subTest(package=package):
                entry = self.entries[package]
                self.assertRegex(entry["synced_sha"], r"\A[0-9a-f]{40}\Z")
                self.assertNotEqual(entry["synced_sha"], "0" * 40)
                self.assertEqual(entry["branch"], "main")
                self.assertEqual(entry["url"], f"https://github.com/Exios66/{package}.git")

    def test_sync_timestamps_are_canonical_utc_dates(self):
        for package in PRE_PUSH_CURSORS:
            with self.subTest(package=package):
                stamp = self.entries[package]["synced_at"]
                parsed = datetime.strptime(stamp, TIMESTAMP_FORMAT)
                self.assertEqual(parsed.strftime(TIMESTAMP_FORMAT), stamp)

    def test_cursors_do_not_regress_to_pre_push_baselines(self):
        # Guard the actual data change without pinning every future sync SHA.
        for package, (old_sha, old_stamp) in PRE_PUSH_CURSORS.items():
            with self.subTest(package=package):
                entry = self.entries[package]
                self.assertNotEqual(entry["synced_sha"], old_sha)
                self.assertGreater(
                    datetime.strptime(entry["synced_at"], TIMESTAMP_FORMAT),
                    datetime.strptime(old_stamp, TIMESTAMP_FORMAT),
                )


class TestRebaselinedStatus(ManifestTestCase):
    def setUp(self):
        super().setUp()
        self.patches = contextlib.ExitStack()
        self.addCleanup(self.patches.close)

        def patch(name, **kwargs):
            return self.patches.enter_context(mock.patch.object(self.mod, name, **kwargs))

        # Only external plumbing is replaced; load_manifest and cmd_status are real.
        patch("ORIGIN", new="https://github.com/Exios66")
        self.fetch = patch("fetch_upstream", side_effect=AssertionError("unexpected fetch"))
        self.git = patch("git", side_effect=AssertionError("unexpected Git command"))
        self.rev_exists = patch("rev_exists", return_value=False)
        self.gaps = patch("unimported_upstream_paths", return_value={})
        self.ahead = patch("local_ahead_paths", return_value=[])
        self.save = patch("save_manifest", side_effect=AssertionError("unexpected cursor write"))

    def tearDown(self):
        self.save.assert_not_called()
        super().tearDown()

    def status_row(self, package, *, no_fetch=False):
        args = argparse.Namespace(command="status", package=package, json=True, no_fetch=no_fetch)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.mod.cmd_status(args), 0)
        rows = json.loads(output.getvalue())
        self.assertEqual(len(rows), 1)
        row = rows[0]
        entry = self.entries[package]
        self.assertEqual(row["package"], package)
        self.assertEqual(row["prefix"], f"packages/{package}")
        self.assertEqual(row["synced_sha"], entry["synced_sha"])
        self.assertEqual(row["synced_at"], entry["synced_at"])
        self.assertEqual(row["branch"], entry["branch"])
        self.assertEqual(row["upstream"], entry["url"])
        return row

    def test_offline_status_preserves_cursors_without_claiming_verified_sync(self):
        for package in PRE_PUSH_CURSORS:
            with self.subTest(package=package):
                row = self.status_row(package, no_fetch=True)
                self.assertEqual(row["upstream_head"], "unreachable")
                self.assertIsNone(row["new_upstream_commits"])
                self.assertFalse(row["up_to_date"])
                self.assertIsNone(row["local_ahead_files"])
                self.rev_exists.assert_called_with(self.entries[package]["synced_sha"])
        self.fetch.assert_not_called()
        self.git.assert_not_called()
        self.gaps.assert_not_called()
        self.ahead.assert_not_called()

    def test_status_uses_rebaselined_cursor_to_measure_upstream_drift(self):
        # Zero is the boundary for "up to date"; a later commit must show drift.
        for package in PRE_PUSH_CURSORS:
            cursor = self.entries[package]["synced_sha"]
            for count in (0, 1):
                with self.subTest(package=package, new_commits=count):
                    head = cursor if count == 0 else "f" * 40
                    self.fetch.side_effect = None
                    self.fetch.return_value = head
                    self.git.side_effect = None
                    self.git.return_value = subprocess.CompletedProcess(
                        args=[], returncode=0, stdout=f"{count}\n", stderr="",
                    )
                    self.rev_exists.return_value = True
                    row = self.status_row(package)
                    self.git.assert_called_with(["rev-list", "--count", f"{cursor}..{head}"])
                    self.fetch.assert_called_with(package)
                    self.gaps.assert_called_with(cursor, package)
                    self.ahead.assert_called_with(head, package)
                    self.assertEqual(row["upstream_head"], head)
                    self.assertEqual(row["new_upstream_commits"], count)
                    self.assertEqual(row["up_to_date"], count == 0)
                    self.assertEqual(row["local_ahead_files"], 0)

    def test_missing_cursor_object_does_not_report_zero_drift(self):
        # A fresh/shallow checkout may lack the standalone commit recorded here.
        self.fetch.side_effect = None
        self.fetch.return_value = "f" * 40
        self.rev_exists.side_effect = lambda revision: revision == "f" * 40
        self.git.side_effect = None
        self.git.return_value = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: Invalid revision range",
        )
        for package in PRE_PUSH_CURSORS:
            with self.subTest(package=package):
                row = self.status_row(package)
                cursor = self.entries[package]["synced_sha"]
                self.git.assert_called_with(["rev-list", "--count", f"{cursor}..{'f' * 40}"])
                self.assertIsNone(row["new_upstream_commits"])
                self.assertFalse(row["up_to_date"])
                self.assertEqual(row["upstream_head"], "f" * 40)
        self.gaps.assert_not_called()

    def test_unreachable_upstream_preserves_saved_cursors(self):
        self.fetch.side_effect = None
        self.fetch.return_value = None
        for package in PRE_PUSH_CURSORS:
            with self.subTest(package=package):
                row = self.status_row(package)
                self.fetch.assert_called_with(package)
                self.assertEqual(row["upstream_head"], "unreachable")
                self.assertIsNone(row["new_upstream_commits"])
                self.assertFalse(row["up_to_date"])
                self.assertIsNone(row["local_ahead_files"])
        self.git.assert_not_called()
        self.ahead.assert_not_called()


if __name__ == "__main__":
    unittest.main()
