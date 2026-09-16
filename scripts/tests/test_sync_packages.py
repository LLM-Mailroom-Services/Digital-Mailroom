#!/usr/bin/env python3
"""Hermetic test suite for scripts/sync_packages.py (DMR-064).

Runs the script via subprocess against throwaway LOCAL git fixtures (bare
upstream + clone + `git subtree add` + synthetic divergent commits on both
sides to force conflicts). No network. stdlib unittest only.

Run:  python3 -m unittest discover scripts/tests -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sync_packages.py"
PKG = "llm-dojo-scoring"  # a real member of the script's PACKAGES map


def git(cwd, *args, check=False):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=check, text=True, capture_output=True
    )


def sha_of(cwd, rev="HEAD"):
    return git(cwd, "rev-parse", rev).stdout.strip()


class SyncScriptTest(unittest.TestCase):
    """Base fixture: bare upstream + seed clone + monorepo clone with subtree add."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dmr064-test-"))
        self.upstreams = self.tmp / "upstreams"
        self.upstreams.mkdir()
        self.origin = self.upstreams / f"{PKG}.git"
        git(self.tmp, "init", "--bare", "-b", "main", str(self.origin), check=True)
        self.src = self.tmp / "src"
        self.mono = self.tmp / "mono"
        git(self.tmp, "clone", str(self.origin), str(self.src), check=True)
        (self.src / "a.txt").write_text("base\n")
        git(self.src, "add", "-A", check=True)
        git(self.src, "commit", "-m", "base", check=True)
        git(self.src, "push", "origin", "main", check=True)
        git(self.tmp, "clone", str(self.origin), str(self.mono), check=True)
        git(
            self.mono, "subtree", "add", f"--prefix=packages/{PKG}",
            str(self.origin), "main", check=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_script(self, *argv, env_extra=None, root=None, manifest=None):
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        manifest = manifest or (self.tmp / "manifest.json")
        root = root or self.mono
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(root),
             "--manifest", str(manifest), *argv],
            cwd=str(root), env=env, text=True, capture_output=True,
        )

    def json_record(self, res):
        line = res.stdout.splitlines()[0]
        return json.loads(line)

    def read_manifest(self, path=None):
        p = path or (self.tmp / "manifest.json")
        if not p.is_file():
            return {"packages": {}}
        return json.loads(p.read_text())

    def diverge(self):
        """Monorepo-ahead commit + upstream commit on the same file (conflict pair)."""
        (self.mono / f"packages/{PKG}/a.txt").write_text("base\nmono change\n")
        git(self.mono, "add", "-A", check=True)
        git(self.mono, "commit", "-m", "mono ahead", check=True)
        (self.src / "a.txt").write_text("base\nupstream change\n")
        git(self.src, "add", "-A", check=True)
        git(self.src, "commit", "-m", "upstream change", check=True)
        git(self.src, "push", "origin", "main", check=True)
        return sha_of(self.src)

    @property
    def origin_env(self):
        return {"SYNC_PACKAGES_ORIGIN": str(self.upstreams)}


# --------------------------------------------------------------------------- #
# conflict detection + safe abort (test a), --keep-conflicts (a2), fast path (b)
# --------------------------------------------------------------------------- #


class TestConflictHandling(SyncScriptTest):
    def test_a_conflicting_pull_aborts_cleanly_exit_3(self):
        tip = self.diverge()
        mono_head_before = sha_of(self.mono)
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 3, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 3)
        self.assertEqual(rec["error_class"], "conflict")
        self.assertFalse(rec["ok"])
        self.assertEqual(rec["package"], PKG)
        kinds = {(c["path"], c["kind"]) for c in rec["conflicted_paths"]}
        self.assertIn((f"packages/{PKG}/a.txt", "both-modified"), kinds)
        self.assertTrue(rec["aborted"])
        self.assertFalse(rec["cursor_updated"])
        # stderr carries the structured summary
        self.assertIn("CONFLICT importing", res.stderr)
        self.assertIn("both-modified", res.stderr)
        self.assertIn("git merge --abort", res.stderr)
        # worktree restored: no MERGE_HEAD, no dirt, HEAD unchanged
        self.assertNotEqual(git(self.mono, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode, 0)
        self.assertEqual(git(self.mono, "status", "--porcelain").stdout.strip(), "")
        self.assertEqual(sha_of(self.mono), mono_head_before)
        # cursor NOT advanced
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))

    def test_a2_keep_conflicts_leaves_tree_dirty_exit_2(self):
        self.diverge()
        res = self.run_script(
            "pull", "--package", PKG, "--keep-conflicts", "--json", env_extra=self.origin_env
        )
        self.assertEqual(res.returncode, 2, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 2)
        self.assertEqual(rec["error_class"], "conflict")
        self.assertIn("abort", res.stderr)
        # merge left in place
        self.assertEqual(git(self.mono, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode, 0)
        status = git(self.mono, "status", "--porcelain").stdout
        self.assertIn("UU", status)

    def test_b_already_contained_fast_path(self):
        head = sha_of(self.src)
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["exit_code"], 0)
        self.assertTrue(rec["cursor_updated"])
        combined = res.stdout + res.stderr
        self.assertIn("already contained", combined)
        self.assertEqual(self.read_manifest()["packages"][PKG]["synced_sha"], head)
        # no merge state created
        self.assertNotEqual(git(self.mono, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode, 0)
        self.assertEqual(git(self.mono, "status", "--porcelain").stdout.strip(), "")


# --------------------------------------------------------------------------- #
# network failure class (c), patch_push cleanup (d), manifest atomicity (e)
# --------------------------------------------------------------------------- #


class TestFailureClasses(SyncScriptTest):
    def test_c_network_failure_is_exit_1_class_network(self):
        bad = {"SYNC_PACKAGES_ORIGIN": str(self.tmp / "no-such-origin")}
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=bad)
        self.assertEqual(res.returncode, 1, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 1)
        self.assertEqual(rec["error_class"], "network")
        self.assertFalse(rec["ok"])
        self.assertEqual(git(self.mono, "status", "--porcelain").stdout.strip(), "")

    def test_d_patch_push_failure_cleans_tmp_and_worktree(self):
        self.diverge()
        # pre-receive hook declines the push AFTER fetch/worktree work succeeds
        hooks = self.origin / "hooks"
        hooks.mkdir(exist_ok=True)
        hook = hooks / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        os.chmod(hook, 0o755)
        res = self.run_script("push", "--patch", "--package", PKG, "--json",
                              env_extra=self.origin_env)
        self.assertEqual(res.returncode, 4, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["error_class"], "git")
        self.assertIn("push", res.stderr)
        # no leaked sync-patch-* temp dirs anywhere in the fixture
        leftovers = list(self.tmp.rglob("sync-patch-*"))
        self.assertEqual(leftovers, [])
        # worktree registry back to exactly one worktree, prune finds nothing
        wl = git(self.mono, "worktree", "list").stdout.splitlines()
        self.assertEqual(len(wl), 1, wl)
        self.assertEqual(git(self.mono, "worktree", "prune", "-n").stdout.strip(), "")
        # cursor NOT advanced on failure
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))

    def test_e_manifest_corrupt_exits_4_with_repair_hint(self):
        mf = self.tmp / "manifest.json"
        mf.write_text("{ definitely not json")
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 4, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 4)
        self.assertEqual(rec["error_class"], "git")
        self.assertIn("corrupt", res.stderr)
        self.assertIn("git checkout", rec["remediation"] or "")
        # corrupt file untouched on disk
        self.assertEqual(mf.read_text(), "{ definitely not json")

    def test_e2_manifest_atomic_write_leaves_no_partial(self):
        mf = self.tmp / "manifest.json"
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        self.assertFalse(list(mf.parent.glob(mf.name + ".tmp")))
        data = json.loads(mf.read_text())
        self.assertEqual(data["packages"][PKG]["synced_sha"], sha_of(self.src))

    def test_f_entry_guard_recovery_for_leftover_merge(self):
        # build a genuine leftover merge state: main vs feature, same file
        (self.mono / "conflict.txt").write_text("one\n")
        git(self.mono, "add", "-A", check=True)
        git(self.mono, "commit", "-m", "conflict base", check=True)
        git(self.mono, "checkout", "-b", "feature", check=True)
        (self.mono / "conflict.txt").write_text("feature\n")
        git(self.mono, "commit", "-am", "feature", check=True)
        git(self.mono, "checkout", "main", check=True)
        (self.mono / "conflict.txt").write_text("main change\n")
        git(self.mono, "commit", "-am", "main change", check=True)
        merged = git(self.mono, "merge", "feature")
        self.assertNotEqual(merged.returncode, 0)
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 2, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 2)
        self.assertEqual(rec["error_class"], "dirty")
        self.assertIn("leftover merge state", res.stderr)
        self.assertIn("git merge --abort", res.stderr)
        # diagnosis only — NO auto-abort at entry
        self.assertEqual(git(self.mono, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode, 0)


# --------------------------------------------------------------------------- #
# PR branch flow (g) with a fake `gh` recorded on PATH, and gh-missing (h)
# --------------------------------------------------------------------------- #


class TestPrFlow(SyncScriptTest):
    def make_fake_gh(self, log_path):
        bin_dir = self.tmp / "ghbin"
        bin_dir.mkdir()
        sh = bin_dir / "gh"
        sh.write_text(
            "#!/bin/sh\n"
            f'printf \'%s\\n\' "$@" >> "{log_path}"\n'
            'echo "https://github.com/example/mono/pull/42"\n'
            "exit 0\n"
        )
        os.chmod(sh, 0o755)
        return bin_dir

    def test_g_open_pr_imports_via_branch_and_opens_pr(self):
        tip = self.diverge()
        log = self.tmp / "gh.log"
        bin_dir = self.make_fake_gh(log)
        env = {
            **self.origin_env,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_LOG": str(log),
        }
        mono_head_before = sha_of(self.mono)
        res = self.run_script("pull", "--open-pr", "--resolve", "ours",
                              "--package", PKG, "--json", env_extra=env)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["exit_code"], 0)
        branch = f"sync/{PKG}/import-{tip[:12]}"
        self.assertEqual(rec["branch"], branch)
        self.assertEqual(rec["pr_url"], "https://github.com/example/mono/pull/42")
        self.assertEqual(rec["resolution"], "ours")
        self.assertFalse(rec["cursor_updated"])
        # worktree back on main, unchanged; local branch removed; remote branch pushed
        self.assertEqual(sha_of(self.mono), mono_head_before)
        self.assertEqual(git(self.mono, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "main")
        self.assertEqual(git(self.mono, "branch", "--list", "sync/*").stdout.strip(), "")
        self.assertIn(branch, git(self.origin, "branch", "--list", "sync/*").stdout)
        # the branch's merge commit carries the DMR-064 message
        branch_log = git(self.origin, "log", "-1", "--format=%s", branch).stdout.strip()
        self.assertIn(f"sync: import {PKG} upstream {tip[:12]}", branch_log)
        self.assertIn("DMR-064 branch flow", branch_log)
        # the merge resolved content: upstream-divergent file present at our version
        merged = git(
            self.origin, "show", f"{branch}:packages/{PKG}/a.txt"
        ).stdout.strip()
        self.assertIn("mono change", merged)
        # fake gh got the exact invocation contract
        argv = log.read_text().splitlines()
        self.assertEqual(argv[0], "pr")
        self.assertEqual(argv[1], "create")
        self.assertEqual(argv[argv.index("--base") + 1], "main")
        self.assertEqual(argv[argv.index("--head") + 1], branch)
        self.assertEqual(
            argv[argv.index("--title") + 1], f"sync({PKG}): import upstream {tip[:12]}"
        )
        body = "\n".join(argv[argv.index("--body") + 1:])
        self.assertIn(f"packages/{PKG}/a.txt", body)
        self.assertIn("both-modified", body)
        self.assertIn("ours", body)
        self.assertIn("HUB-021", body)
        # cursor untouched
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))

    def test_h_gh_missing_reports_manual_command_exit_4(self):
        self.diverge()
        path = os.pathsep.join(
            d for d in os.environ.get("PATH", "").split(os.pathsep)
            if d and not os.path.exists(os.path.join(d, "gh"))
        )
        env = {**self.origin_env, "PATH": path}
        mono_head_before = sha_of(self.mono)
        res = self.run_script("pull", "--open-pr", "--package", PKG, "--json", env_extra=env)
        self.assertEqual(res.returncode, 4, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["error_class"], "git")
        self.assertIn("gh", rec["remediation"] or "")
        self.assertIn("gh pr create", res.stderr)
        # branch still pushed upstream for a manual PR; local worktree restored
        branches = git(self.origin, "branch", "--list", "sync/*").stdout
        self.assertIn(f"sync/{PKG}/import-", branches)
        self.assertEqual(sha_of(self.mono), mono_head_before)
        self.assertEqual(git(self.mono, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "main")
        self.assertEqual(git(self.mono, "status", "--porcelain").stdout.strip(), "")


# --------------------------------------------------------------------------- #
# backward-compat smoke (status --json keeps its array contract)
# --------------------------------------------------------------------------- #


class TestBackwardCompat(SyncScriptTest):
    def test_status_json_array_contract(self):
        res = self.run_script("status", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        rows = json.loads(res.stdout)
        self.assertIsInstance(rows, list)
        self.assertEqual(rows[0]["package"], PKG)


if __name__ == "__main__":
    unittest.main()