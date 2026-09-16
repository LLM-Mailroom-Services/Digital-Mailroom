#!/usr/bin/env python3
"""Hermetic tests for scripts/sync_vendor.py (DMR-057 / DMR-070).

Pins the workspace->vendor mirror: content copies AND deletions carry (a
copy-only refresh is how the docclass-era compliance files survived their
upstream removal — the v0.6.0 lesson), the exclusion set matches the sandbox
drift guard (tests/test_vendor_drift.py), and --check is a no-op drift gate.

Run:  python3 -m unittest discover scripts/tests -v
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sync_vendor.py"


def _load():
    spec = importlib.util.spec_from_file_location("sync_vendor_test_mod", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestMirrorPlan(unittest.TestCase):
    def setUp(self):
        self.mod = _load()
        self.ws = Path(tempfile.mkdtemp(prefix="syncv-ws-"))
        self.vd = Path(tempfile.mkdtemp(prefix="syncv-vd-"))

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)
        shutil.rmtree(self.vd, ignore_errors=True)

    def test_plan_copy_overwrite_delete(self):
        (self.vd / "keep.py").write_text("keep\n")
        (self.vd / "stale.py").write_text("stale\n")  # deleted workspace-side
        (self.vd / "ch.py").write_text("old\n")       # drifted
        (self.ws / "keep.py").write_text("keep\n")
        (self.ws / "ch.py").write_text("new\n")
        (self.ws / "add.py").write_text("add\n")      # new workspace-side
        copy, overwrite, delete = self.mod.plan_refresh(self.ws, self.vd)
        self.assertEqual(copy, ["add.py"])
        self.assertEqual(overwrite, ["ch.py"])
        self.assertEqual(delete, ["stale.py"])

    def test_exclusions_match_drift_guard(self):
        # Excluded paths are invisible to BOTH sides: never copied, never
        # deleted (top-level tests/, egg-info, legalbench/reports,
        # __pycache__, *.pyc).
        (self.ws / "real.py").write_text("x\n")
        (self.ws / "tests").mkdir()
        (self.ws / "tests" / "t.py").write_text("x\n")
        (self.ws / "pkg.egg-info").mkdir()
        (self.ws / "pkg.egg-info" / "r").write_text("x\n")
        reports = self.ws / "legalbench" / "reports"
        reports.mkdir(parents=True)
        (reports / "exp.md").write_text("x\n")
        (self.ws / "__pycache__").mkdir()
        (self.ws / "__pycache__" / "c.pyc").write_text("x\n")
        (self.ws / "gen.pyc").write_text("x\n")
        (self.vd / "real.py").write_text("x\n")
        copy, overwrite, delete = self.mod.plan_refresh(self.ws, self.vd)
        self.assertEqual((copy, overwrite, delete), ([], [], []))

    def test_apply_carries_deletions_and_prunes_dirs(self):
        (self.ws / "a" / "b").mkdir(parents=True)
        (self.ws / "a" / "b" / "f.py").write_text("1\n")
        self.mod.apply_refresh(self.ws, self.vd)
        self.assertTrue((self.vd / "a" / "b" / "f.py").is_file())
        # delete workspace-side; re-apply: the vendor file AND its now-empty
        # directories must be gone (the compliance-residue class)
        shutil.rmtree(self.ws / "a")
        self.mod.apply_refresh(self.ws, self.vd)
        self.assertFalse((self.vd / "a" / "b" / "f.py").exists())
        self.assertFalse((self.vd / "a").exists())

    def test_apply_converges_to_zero_drift(self):
        for i in range(5):
            (self.ws / f"m{i}.py").write_text(f"{i}\n")
        (self.vd / "gone.py").write_text("old\n")
        self.mod.apply_refresh(self.ws, self.vd)
        self.assertEqual(self.mod.plan_refresh(self.ws, self.vd), ([], [], []))
        self.assertFalse((self.vd / "gone.py").exists())

    def test_snapshot_configs_cover_both_vendored_trees(self):
        # The shipped SNAPSHOTS map exactly the two drift-guard comparisons.
        labels = [s[0] for s in self.mod.SNAPSHOTS]
        self.assertEqual(labels, ["llm-mailroom", "llm-dojo-scoring"])
        for _label, ws_rel, vd_rel in self.mod.SNAPSHOTS:
            self.assertTrue((REPO_ROOT / ws_rel).is_dir(), ws_rel)
            self.assertTrue((REPO_ROOT / vd_rel).is_dir(), vd_rel)
        # and the workspace sides hash-match the vendor sides right now
        # (refreshes are committed with the workspace change — hub#62).
        for _label, ws_rel, vd_rel in self.mod.SNAPSHOTS:
            copy, overwrite, delete = self.mod.plan_refresh(
                REPO_ROOT / ws_rel, REPO_ROOT / vd_rel)
            self.assertEqual(
                (copy, overwrite, delete), ([], [], []),
                f"{ws_rel} drifted from {vd_rel} — run: python scripts/sync_vendor.py",
            )


class TestCheckGate(unittest.TestCase):
    def test_check_mode_current_repo_is_green(self):
        # The real repo's vendor snapshots track the workspace packages;
        # --check must exit 0 and print no drift plan (it never writes).
        res = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertNotIn("vendor drift detected", res.stderr)


if __name__ == "__main__":
    unittest.main()
