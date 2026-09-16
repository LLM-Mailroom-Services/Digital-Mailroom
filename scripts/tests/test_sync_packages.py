#!/usr/bin/env python3
"""Hermetic test suite for scripts/sync_packages.py (DMR-064).

Runs the script via subprocess against throwaway LOCAL git fixtures (bare
upstream + clone + `git subtree add` + synthetic divergent commits on both
sides to force conflicts). No network. stdlib unittest only.

Run:  python3 -m unittest discover scripts/tests -v
"""

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sync_packages.py"
PKG = "llm-dojo-scoring"  # a real member of the script's PACKAGES map

# Hermetic git env: no prompt, no host/global/system config leaking into the
# fixtures (and no anonymous-committer failures now that global config is gone).
GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "DMR-064 Test",
    "GIT_AUTHOR_EMAIL": "dmr064@test.invalid",
    "GIT_COMMITTER_NAME": "DMR-064 Test",
    "GIT_COMMITTER_EMAIL": "dmr064@test.invalid",
}


def git(cwd, *args, check=False):
    env = dict(os.environ)
    env.update(GIT_ENV)
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=check, text=True,
        capture_output=True, env=env, timeout=60,
    )


def sha_of(cwd, rev="HEAD"):
    return git(cwd, "rev-parse", rev).stdout.strip()


class SyncScriptTest(unittest.TestCase):
    """Base fixture: bare upstream + seed clone + monorepo clone with subtree add.

    The base upstream tree carries a.txt (both-modified leg), b.txt (modify/
    delete leg), r.txt (rename-vs-delete leg) and t.txt (delete-vs-rename leg);
    `diverge()` uses only a.txt, `diverge_penta()` uses all four.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dmr064-test-"))
        self.upstreams = self.tmp / "upstreams"
        self.upstreams.mkdir()
        self.origin = self.upstreams / f"{PKG}.git"
        git(self.tmp, "init", "--bare", "-b", "main", str(self.origin), check=True)
        self.src = self.tmp / "src"
        self.mono = self.tmp / "mono"
        git(self.tmp, "clone", str(self.origin), str(self.src), check=True)
        (self.src / "a.txt").write_text("base a\n")
        (self.src / "b.txt").write_text("base b\n")
        (self.src / "r.txt").write_text("base r\n")
        (self.src / "t.txt").write_text("base t\n")
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
        env.update(GIT_ENV)
        if env_extra:
            env.update(env_extra)
        manifest = manifest or (self.tmp / "manifest.json")
        root = root or self.mono
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(root),
             "--manifest", str(manifest), *argv],
            cwd=str(root), env=env, text=True, capture_output=True, timeout=60,
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
        (self.mono / f"packages/{PKG}/a.txt").write_text("base a\nmono change\n")
        git(self.mono, "add", "-A", check=True)
        git(self.mono, "commit", "-m", "mono ahead", check=True)
        (self.src / "a.txt").write_text("base a\nupstream change\n")
        git(self.src, "add", "-A", check=True)
        git(self.src, "commit", "-m", "upstream change", check=True)
        git(self.src, "push", "origin", "main", check=True)
        return sha_of(self.src)

    def diverge_penta(self):
        """Five-kind divergence pair (pins classification + resolution ladder):
          a.txt    both-modified   (both sides edit)
          b.txt    modify-delete   (ours modifies, upstream deletes)
          both.txt add/add         (both sides add, different content)
          r.txt    rename/delete   (ours renames -> r2.txt, upstream deletes)
          t.txt    delete/rename   (ours deletes, upstream renames -> t3.txt)
        """
        p = f"packages/{PKG}"
        (self.mono / f"{p}/a.txt").write_text("base a\nmono a\n")
        (self.mono / f"{p}/b.txt").write_text("base b\nmono b\n")
        (self.mono / f"{p}/both.txt").write_text("mono both\n")
        git(self.mono, "mv", f"{p}/r.txt", f"{p}/r2.txt", check=True)
        git(self.mono, "rm", "-q", f"{p}/t.txt", check=True)
        git(self.mono, "add", "-A", check=True)
        git(self.mono, "commit", "-m", "mono penta", check=True)
        (self.src / "a.txt").write_text("base a\nup a\n")
        git(self.src, "rm", "-q", "b.txt", "r.txt")
        (self.src / "both.txt").write_text("up both\n")
        git(self.src, "mv", "t.txt", "t3.txt")
        git(self.src, "add", "-A", check=True)
        git(self.src, "commit", "-m", "up penta", check=True)
        git(self.src, "push", "origin", "main", check=True)
        return sha_of(self.src)

    @property
    def origin_env(self):
        return {"SYNC_PACKAGES_ORIGIN": str(self.upstreams)}

    def make_fake_gh(self, log_path, *, exit_code=0, stderr_url=False):
        """Fake `gh` on a PATH dir: logs each argv line to log_path, then emits
        a PR URL (stdout, or stderr when stderr_url) and exits `exit_code`."""
        bin_dir = self.tmp / "ghbin"
        bin_dir.mkdir(exist_ok=True)
        sh = bin_dir / "gh"
        body = (
            "#!/bin/sh\n"
            f'printf \'%s\\n\' "$@" >> "{log_path}"\n'
        )
        if exit_code == 0:
            url_line = (
                'echo "https://github.com/example/mono/pull/42" >&2\n'
                if stderr_url
                else 'echo "https://github.com/example/mono/pull/42"\n'
            )
            body += url_line + "exit 0\n"
        else:
            body += 'echo "auth required" >&2\n' + f"exit {exit_code}\n"
        sh.write_text(body)
        os.chmod(sh, 0o755)
        return bin_dir


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
        self.assertFalse(rec["aborted"])
        self.assertIn("abort", res.stderr)
        # merge left in place
        self.assertEqual(git(self.mono, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode, 0)
        status = git(self.mono, "status", "--porcelain").stdout
        self.assertIn("UU", status)
        # cursor NOT advanced
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))

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
# PR branch flow: gh failure fail-closed (g2), stderr URL parse (g2b),
# resolution ladder (i), classification kinds (l)
# --------------------------------------------------------------------------- #


class TestPrFlow(SyncScriptTest):
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

    def test_g2a_gh_create_failure_is_fail_closed(self):
        tip = self.diverge()
        mono_head_before = sha_of(self.mono)
        log = self.tmp / "gh.log"
        bin_dir = self.make_fake_gh(log, exit_code=1)
        env = {
            **self.origin_env,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_LOG": str(log),
        }
        res = self.run_script("pull", "--open-pr", "--package", PKG, "--json", env_extra=env)
        self.assertEqual(res.returncode, 4, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["error_class"], "git")
        self.assertEqual(rec["exit_code"], 4)
        self.assertIn("gh pr create", rec["remediation"] or "")
        self.assertIn("auth required", res.stderr)
        self.assertIn("gh pr create failed", res.stderr)
        # gh WAS invoked with the right contract before failing (fail-closed)
        argv = log.read_text().splitlines()
        self.assertEqual(argv[argv.index("--base") + 1], "main")
        self.assertEqual(argv[argv.index("--head") + 1], f"sync/{PKG}/import-{tip[:12]}")
        # teardown: back on main, local branch removed, pushed remote branch stays
        self.assertEqual(sha_of(self.mono), mono_head_before)
        self.assertEqual(git(self.mono, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "main")
        self.assertEqual(git(self.mono, "branch", "--list", "sync/*").stdout.strip(), "")
        self.assertEqual(git(self.mono, "status", "--porcelain").stdout.strip(), "")
        self.assertIn(f"sync/{PKG}/import-{tip[:12]}",
                      git(self.origin, "branch", "--list", "sync/*").stdout)
        # cursor untouched
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))

    def test_g2b_pr_url_parsed_from_stderr_only(self):
        self.diverge()
        log = self.tmp / "gh.log"
        bin_dir = self.make_fake_gh(log, stderr_url=True)
        env = {
            **self.origin_env,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_LOG": str(log),
        }
        res = self.run_script("pull", "--open-pr", "--package", PKG, "--json", env_extra=env)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["pr_url"], "https://github.com/example/mono/pull/42")

    def test_h_gh_missing_reports_manual_command_exit_4(self):
        tip = self.diverge()
        path = os.pathsep.join(
            d for d in os.environ.get("PATH", "").split(os.pathsep)
            if d and not os.path.exists(os.path.join(d, "gh"))
        )
        # never starve the harness of git itself when a dir holds both binaries
        if not shutil.which("git", path=path):
            git_dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep)
                        if d and os.path.exists(os.path.join(d, "git"))]
            path = os.pathsep.join([path] + git_dirs) if path else os.pathsep.join(git_dirs)
        env = {**self.origin_env, "PATH": path}
        mono_head_before = sha_of(self.mono)
        res = self.run_script("pull", "--open-pr", "--package", PKG, "--json", env_extra=env)
        self.assertEqual(res.returncode, 4, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["error_class"], "git")
        self.assertIn("gh", rec["remediation"] or "")
        self.assertIn("gh pr create", res.stderr)
        self.assertEqual(rec["branch"], f"sync/{PKG}/import-{tip[:12]}")
        # branch still pushed upstream for a manual PR; local worktree restored
        branches = git(self.origin, "branch", "--list", "sync/*").stdout
        self.assertIn(f"sync/{PKG}/import-", branches)
        self.assertEqual(sha_of(self.mono), mono_head_before)
        self.assertEqual(git(self.mono, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "main")
        self.assertEqual(git(self.mono, "status", "--porcelain").stdout.strip(), "")


class TestResolutionLadder(SyncScriptTest):
    """Pins the manual-resolution ladder (`resolve_remaining_ours_theirs` and
    the strategy-merge conflict branch in pr_branch_flow): `-X ours|theirs`
    auto-resolves both-modified + add/add but leaves modify/delete and
    rename/delete conflicts unmerged — those must be taken by the ladder."""

    def test_i_theirs_resolution_ladder_runs(self):
        tip = self.diverge_penta()
        log = self.tmp / "gh.log"
        bin_dir = self.make_fake_gh(log)
        env = {
            **self.origin_env,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_LOG": str(log),
        }
        mono_head_before = sha_of(self.mono)
        res = self.run_script("pull", "--open-pr", "--resolve", "theirs",
                              "--package", PKG, "--json", env_extra=env)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertTrue(rec["ok"])
        branch = f"sync/{PKG}/import-{tip[:12]}"
        self.assertEqual(rec["branch"], branch)
        self.assertEqual(rec["resolution"], "theirs")
        # THE LADDER RAN (pins both its branches): git rm kept the deletions,
        # checkpoint --theirs restored their renamed file
        self.assertIn(f"resolved packages/{PKG}/b.txt: kept deletion under theirs", res.stderr)
        self.assertIn(f"resolved packages/{PKG}/r2.txt: kept deletion under theirs", res.stderr)
        self.assertIn(f"resolved packages/{PKG}/t3.txt: took theirs version", res.stderr)
        # merged branch content on the pushed upstream ref
        def tree_has(path):
            return git(self.origin, "cat-file", "-e", f"{branch}:{path}").returncode == 0

        self.assertFalse(tree_has(f"packages/{PKG}/b.txt"))    # upstream deletion kept (git rm)
        self.assertFalse(tree_has(f"packages/{PKG}/r2.txt"))   # rename target deleted (theirs)
        self.assertTrue(tree_has(f"packages/{PKG}/a.txt"))
        self.assertEqual(
            git(self.origin, "show", f"{branch}:packages/{PKG}/a.txt").stdout, "base a\nup a\n"
        )
        self.assertEqual(
            git(self.origin, "show", f"{branch}:packages/{PKG}/both.txt").stdout, "up both\n"
        )
        self.assertEqual(
            git(self.origin, "show", f"{branch}:packages/{PKG}/t3.txt").stdout, "base t\n"
        )
        # the merge commit lands the DMR-064 subject; no unmerged paths remain
        subject = git(self.origin, "log", "-1", "--format=%s", branch).stdout.strip()
        self.assertIn("DMR-064 branch flow", subject)
        # PR body names the conflicted paths + kinds
        argv = log.read_text().splitlines()
        body = "\n".join(argv[argv.index("--body") + 1:])
        self.assertIn(f"packages/{PKG}/b.txt", body)
        self.assertIn(f"packages/{PKG}/both.txt", body)
        self.assertIn("modify-delete", body)
        self.assertIn("add/add", body)
        # worktree restored to main; local branch gone; cursor untouched
        self.assertEqual(sha_of(self.mono), mono_head_before)
        self.assertEqual(git(self.mono, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "main")
        self.assertEqual(git(self.mono, "status", "--porcelain").stdout.strip(), "")
        self.assertEqual(git(self.mono, "branch", "--list", "sync/*").stdout.strip(), "")
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))

    def test_l_classification_pins_all_kinds(self):
        self.diverge_penta()
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 3, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["error_class"], "conflict")
        kinds = {(c["path"], c["kind"]) for c in rec["conflicted_paths"]}
        self.assertIn((f"packages/{PKG}/a.txt", "both-modified"), kinds)
        self.assertIn((f"packages/{PKG}/b.txt", "modify-delete"), kinds)
        self.assertIn((f"packages/{PKG}/both.txt", "add/add"), kinds)
        # rename/delete surfaces at the rename target, classified modify-delete
        self.assertIn((f"packages/{PKG}/r2.txt", "modify-delete"), kinds)
        self.assertIn((f"packages/{PKG}/t3.txt", "modify-delete"), kinds)
        # aborted cleanly, cursor untouched
        self.assertTrue(rec["aborted"])
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))


# --------------------------------------------------------------------------- #
# multi-package severity law (j), dirty-entry semantics (k/k2)
# --------------------------------------------------------------------------- #


class TestSeverityAndDirty(SyncScriptTest):
    def test_j_multi_package_severity_law(self):
        # second package (llm-mailroom-graph) stays in sync -> fast path
        origin2 = self.upstreams / "llm-mailroom-graph.git"
        src2 = self.tmp / "src2"
        git(self.tmp, "init", "--bare", "-b", "main", str(origin2), check=True)
        git(self.tmp, "clone", str(origin2), str(src2), check=True)
        (src2 / "f.txt").write_text("f\n")
        git(src2, "add", "-A", check=True)
        git(src2, "commit", "-m", "base2", check=True)
        git(src2, "push", "origin", "main", check=True)
        git(self.mono, "subtree", "add", "--prefix=packages/llm-mailroom-graph",
            str(origin2), "main", check=True)
        self.diverge()  # llm-dojo-scoring now conflicts
        res = self.run_script("pull", "--all", "--json", env_extra=self.origin_env)
        # max severity across packages: conflict(3) beats network(1)
        self.assertEqual(res.returncode, 3, res.stderr + res.stdout)
        recs = {}
        for line in res.stdout.splitlines():
            rec = json.loads(line)
            recs[rec["package"]] = rec
        self.assertEqual(set(recs), {
            "Enron-Evaluation-Environment", "The-Mailroom", "agent-mailroom",
            "claims-data-eda", "llm-dojo-scoring", "llm-entity-extraction",
            "llm-mailroom", "llm-mailroom-graph", "local-mailroom-sandbox",
            "mailroom-corpus-eda",
        })
        self.assertEqual(recs[PKG]["error_class"], "conflict")
        self.assertEqual(recs[PKG]["exit_code"], 3)
        self.assertFalse(recs[PKG]["cursor_updated"])
        self.assertEqual(recs["llm-mailroom-graph"]["error_class"], "ok")
        self.assertTrue(recs["llm-mailroom-graph"]["cursor_updated"])
        self.assertEqual(recs["agent-mailroom"]["error_class"], "network")
        # cursor advanced ONLY for the fast-path package
        self.assertEqual(set(self.read_manifest().get("packages", {})), {"llm-mailroom-graph"})

    def test_k_allow_dirty_conflict_leaves_merge_in_place(self):
        self.diverge()
        scratch = self.mono / "user-scratch.txt"
        scratch.write_text("user work\n")
        res = self.run_script("pull", "--allow-dirty", "--package", PKG, "--json",
                              env_extra=self.origin_env)
        self.assertEqual(res.returncode, 2, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 2)
        self.assertEqual(rec["error_class"], "conflict")  # conflict kind, dirty exit code
        self.assertFalse(rec["aborted"])
        # the auto-abort was blocked: MERGE_HEAD + UU remain, dirt untouched
        self.assertEqual(git(self.mono, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode, 0)
        self.assertIn("UU", git(self.mono, "status", "--porcelain").stdout)
        self.assertEqual(scratch.read_text(), "user work\n")
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))

    def test_k2_plain_dirty_entry_refusal(self):
        scratch = self.mono / "user-scratch.txt"
        scratch.write_text("user work\n")
        head_before = sha_of(self.mono)
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 2, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 2)
        self.assertEqual(rec["error_class"], "dirty")
        self.assertIn("worktree is dirty", res.stderr)
        self.assertIn("--allow-dirty", rec["remediation"] or "")
        # no auto-cleanup: dirt survives, nothing committed, no merge state
        self.assertEqual(scratch.read_text(), "user work\n")
        self.assertEqual(sha_of(self.mono), head_before)
        self.assertEqual(git(self.mono, "status", "--porcelain").stdout.strip(),
                         "?? user-scratch.txt")
        self.assertNotEqual(
            git(self.mono, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode, 0
        )


# --------------------------------------------------------------------------- #
# cheap pins: non-dict manifest (m), unknown package (n), status row contract (o)
# --------------------------------------------------------------------------- #


class TestEntryGuardPins(SyncScriptTest):
    def test_m_non_dict_manifest_exits_4(self):
        mf = self.tmp / "manifest.json"
        mf.write_text("[1, 2, 3]\n")
        res = self.run_script("pull", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 4, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 4)
        self.assertEqual(rec["error_class"], "git")
        self.assertIn("not a JSON object", res.stderr)
        # non-dict manifest never overwritten
        self.assertEqual(mf.read_text(), "[1, 2, 3]\n")

    def test_n_unknown_package_exits_4(self):
        res = self.run_script("pull", "--package", "no-such-package", "--json",
                              env_extra=self.origin_env)
        self.assertEqual(res.returncode, 4, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 4)
        self.assertEqual(rec["error_class"], "git")
        self.assertIn("unknown package", res.stderr)
        self.assertIn("llm-dojo-scoring", res.stderr)  # lists valid packages

    def test_o_status_json_row_contract(self):
        res = self.run_script("status", "--package", PKG, "--json", env_extra=self.origin_env)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        rows = json.loads(res.stdout)
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0].keys()), {
            "package", "prefix", "upstream", "branch", "upstream_head",
            "synced_sha", "synced_at", "new_upstream_commits", "up_to_date",
            "cursor_gap", "cursor_gap_sample", "local_ahead_files",
        })
        self.assertEqual(rows[0]["package"], PKG)
        self.assertEqual(rows[0]["upstream_head"], sha_of(self.src))
        self.assertEqual(rows[0]["prefix"], f"packages/{PKG}")


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


# --------------------------------------------------------------------------- #
# DMR-070: post-import verification seams
# --------------------------------------------------------------------------- #


def _load_sync_module():
    """Import scripts/sync_packages.py as a module for unit-level seams."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("sync_packages_dmr070", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestResolutionClassifier(unittest.TestCase):
    """DMR-070(a): classify_resolution — the verdict table."""

    def test_l_classify_resolution_table(self):
        mod = _load_sync_module()
        f = mod.classify_resolution
        self.assertEqual(f(None, "a", "b"), "absent")       # deletion kept
        self.assertEqual(f("a", "a", "b"), "ours")          # faithful ours
        self.assertEqual(f("b", "a", "b"), "theirs")        # faithful theirs
        self.assertEqual(f("a", "a", "a"), "both")          # identical sides
        self.assertEqual(f("c", "a", "b"), "divergent")     # the v0.6 mangle
        self.assertEqual(f("c", None, "b"), "divergent")    # ours deleted, new content
        self.assertEqual(f(None, None, None), "absent")

    def test_l2_resolution_divergences_maps_theirs_prefix(self):
        """The theirs side is addressed WITHOUT the packages/<pkg>/ prefix
        (upstream repo-root layout) while ours/resolved carry the prefix."""
        mod = _load_sync_module()
        repo = Path(tempfile.mkdtemp(prefix="dmr070-div-"))
        self.addCleanup(shutil.rmtree, repo, ignore_errors=True)
        env = dict(os.environ)
        env.update(GIT_ENV)

        def g(*args):
            return subprocess.run(["git", *args], cwd=str(repo), env=env,
                                  text=True, capture_output=True, check=True)

        # monorepo-style layout: the package lives under packages/<pkg>/
        g("init", "-q", "-b", "main", ".")
        (repo / "packages" / "pkg").mkdir(parents=True)
        (repo / "packages" / "pkg" / "doc.txt").write_text("ours side\n")
        g("add", "-A")
        g("commit", "-m", "ours")
        pre_head = g("rev-parse", "HEAD").stdout.strip()
        g("checkout", "-q", "-b", "upstream")
        g("mv", "packages/pkg/doc.txt", "doc.txt")  # upstream repo-root layout
        (repo / "doc.txt").write_text("upstream side\n")
        g("add", "-A")
        g("commit", "-m", "upstream")
        theirs = g("rev-parse", "HEAD").stdout.strip()
        g("checkout", "-q", "main")
        # the "resolved" blob matches NEITHER side (hand-mangled, v0.6 class)
        (repo / "packages" / "pkg" / "doc.txt").write_text("mangled fusion\n")
        g("add", "-A")
        g("commit", "-m", "resolved merge")
        saved_root = mod.REPO_ROOT
        mod.REPO_ROOT = repo  # point the module's git cwd at the fixture
        try:
            divs = mod.resolution_divergences("pkg", pre_head, theirs,
                                              ["packages/pkg/doc.txt"])
        finally:
            mod.REPO_ROOT = saved_root
        self.assertEqual(len(divs), 1)
        d = divs[0]
        self.assertEqual(d["path"], "packages/pkg/doc.txt")
        self.assertEqual(d["verdict"], "divergent")
        self.assertTrue(d["ours"] and d["theirs"] and d["resolved"])
        self.assertNotEqual(d["resolved"], d["ours"])
        self.assertNotEqual(d["resolved"], d["theirs"])


class TestPatchPushDeletionGuard(SyncScriptTest):
    """DMR-070(b): a package whose monorepo tree deletes tracked upstream
    paths is REFUSED on --patch (exit 5, error_class verify) and directed to
    the full subtree-push leg — the content-push path can never carry
    deletions (the v0.6.0 lesson; previously it failed containment with the
    misleading "pull first" remediation)."""

    def test_m_patch_push_refused_on_deletion(self):
        (self.mono / f"packages/{PKG}/a.txt").unlink()
        git(self.mono, "add", "-A", check=True)
        git(self.mono, "commit", "-m", "mono deletes a.txt", check=True)
        upstream_before = git(self.origin, "rev-parse", "main").stdout.strip()
        res = self.run_script("push", "--patch", "--package", PKG, "--json",
                              env_extra=self.origin_env)
        self.assertEqual(res.returncode, 5, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["exit_code"], 5)
        self.assertEqual(rec["error_class"], "verify")
        self.assertFalse(rec["ok"])
        self.assertEqual(rec["deleted_paths"], [f"packages/{PKG}/a.txt"])
        self.assertIn("subtree-push leg", rec["remediation"])
        self.assertIn("DMR-070", res.stderr)
        self.assertIn(f"packages/{PKG}/a.txt", res.stderr)
        # nothing pushed, cursor untouched
        self.assertEqual(git(self.origin, "rev-parse", "main").stdout.strip(),
                         upstream_before)
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))


class TestVerifySuiteGate(SyncScriptTest):
    """DMR-070 --verify-suite: SYNC_VERIFY_CMD stubs the package suite.
    Red refuses push / cursor-advance (exit 5); green lets the flow run."""

    def _mono_ahead(self):
        (self.mono / f"packages/{PKG}/a.txt").write_text("base a\nmono change\n")
        git(self.mono, "add", "-A", check=True)
        git(self.mono, "commit", "-m", "mono ahead", check=True)

    @staticmethod
    def _stub(path, body):
        path.write_text(body)
        os.chmod(path, 0o755)
        return path

    def test_n_patch_push_red_suite_refuses(self):
        self._mono_ahead()
        stub = self._stub(self.tmp / "fail-suite",
                          "#!/bin/sh\necho '3 failed'\nexit 1\n")
        upstream_before = git(self.origin, "rev-parse", "main").stdout.strip()
        res = self.run_script("push", "--patch", "--verify-suite",
                              "--package", PKG, "--json",
                              env_extra={**self.origin_env,
                                         "SYNC_VERIFY_CMD": str(stub)})
        self.assertEqual(res.returncode, 5, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["error_class"], "verify")
        self.assertIn("verify-suite failed", rec["remediation"])
        self.assertIn("3 failed", rec.get("verify_detail_tail", ""))
        # nothing pushed, cursor untouched
        self.assertEqual(git(self.origin, "rev-parse", "main").stdout.strip(),
                         upstream_before)
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))

    def test_n2_patch_push_green_suite_pushes_and_advances_cursor(self):
        self._mono_ahead()
        stub = self._stub(self.tmp / "ok-suite", "#!/bin/sh\nexit 0\n")
        upstream_before = git(self.origin, "rev-parse", "main").stdout.strip()
        res = self.run_script("push", "--patch", "--verify-suite",
                              "--package", PKG, "--json",
                              env_extra={**self.origin_env,
                                         "SYNC_VERIFY_CMD": str(stub)})
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertTrue(rec["ok"])
        self.assertTrue(rec["cursor_updated"])
        self.assertIn(PKG, self.read_manifest().get("packages", {}))
        self.assertNotEqual(git(self.origin, "rev-parse", "main").stdout.strip(),
                            upstream_before)

    def test_n3_pull_red_suite_refuses_cursor_advance(self):
        # non-conflicting upstream commit (new file) → clean subtree pull
        (self.src / "upnew.txt").write_text("up new\n")
        git(self.src, "add", "-A", check=True)
        git(self.src, "commit", "-m", "up new", check=True)
        git(self.src, "push", "origin", "main", check=True)
        stub = self._stub(self.tmp / "fail-suite", "#!/bin/sh\nexit 1\n")
        res = self.run_script("pull", "--package", PKG, "--verify-suite",
                              "--json",
                              env_extra={**self.origin_env,
                                         "SYNC_VERIFY_CMD": str(stub)})
        self.assertEqual(res.returncode, 5, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertEqual(rec["error_class"], "verify")
        self.assertIn("verify-suite failed", rec["remediation"])
        # the merge landed in the worktree but the cursor did NOT advance
        self.assertNotIn(PKG, self.read_manifest().get("packages", {}))
        self.assertIn("upnew.txt",
                      git(self.mono, "ls-files", "--", f"packages/{PKG}").stdout)

    def test_n4_open_pr_record_carries_resolution_divergences(self):
        # clean -X strategy path: no ladder resolution → empty divergence list,
        # but the record field is always present (structural seam).
        self.diverge()
        log = self.tmp / "gh.log"
        bin_dir = self.make_fake_gh(log)
        env = {
            **self.origin_env,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_LOG": str(log),
        }
        res = self.run_script("pull", "--open-pr", "--package", PKG, "--json",
                              env_extra=env)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        rec = self.json_record(res)
        self.assertTrue(rec["ok"])
        self.assertIn("resolution_divergences", rec)
        self.assertEqual(rec["resolution_divergences"], [])


class TestSilentNoOpGuard(unittest.TestCase):
    """DMR-073: a push rc==0 is NOT evidence of a landing.

    The DMR-071 hole: the patch-push success line printed the PRE-push tip and
    nothing verified the remote actually moved, so the dojo (9-file) and
    entity (4-file) deltas silently never left the monorepo while the session
    and the cursors recorded success. These pins drive every branch of the
    post-push guard at the unit level (module imported with stubbed plumbing;
    the end-to-end happy path is covered by test_n2 above).
    """

    TIP = "1" * 40            # remote tip before the push
    PUSHED = "2" * 40         # the worktree commit patch_push creates
    FOREIGN = "3" * 40        # a concurrent push's commit

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import sync_packages as sp
        cls.sp = sp

    def setUp(self):
        self.sp = type(self).sp
        # JSON_MODE off so info() goes to stdout and never breaks record parsing
        self._json_mode = self.sp.JSON_MODE
        self.sp.JSON_MODE = False
        self.notes = []
        self.warnings = []

    def tearDown(self):
        self.sp.JSON_MODE = self._json_mode

    @contextlib.contextmanager
    def _patched(self, *, upstream_heads, ahead_paths=(),
                 staged_diff=" packages/x/a.txt | 1 +\n"):
        """Stub the plumbing patch_push needs; git() dispatches on argv."""
        sp = self.sp
        heads = iter(upstream_heads)

        def fake_upstream_head(url, branch):
            try:
                return next(heads)
            except StopIteration:  # probe repeated (cursor write re-probes)
                return upstream_heads[-1]

        def fake_git(args, *, capture=True, binary=False):
            class P:
                def __init__(self, returncode=0, stdout="", stderr=""):
                    self.returncode, self.stdout, self.stderr = returncode, stdout, stderr
            if args[:2] == ["-C", mock.ANY] or args[0] == "-C":
                if "push" in args:
                    return P()
                if "diff" in args:  # staged delta vs the worktree tip
                    return P(stdout=staged_diff)
                if "rev-parse" in args and "--short" not in args:
                    return P(stdout=self.PUSHED)
                return P()
            if args[:2] == ["ls-tree", "-r"]:
                entry = f"100644 blob {'a' * 40}\tpackages/{PKG}/a.txt"
                out = (entry + "\0").encode() if binary else entry + "\0"
                return P(stdout=out)
            if args[:2] == ["cat-file", "blob"]:
                return P(stdout=b"new content\n")
            if args[:2] == ["rev-parse", "--short"]:
                return P(stdout="abc1234")
            return P()

        with mock.patch.object(sp, "monorepo_deleted_paths", return_value=[]), \
             mock.patch.object(sp, "unimported_upstream_paths", return_value={}), \
             mock.patch.object(sp, "local_ahead_paths", return_value=list(ahead_paths)), \
             mock.patch.object(sp, "upstream_head", side_effect=fake_upstream_head), \
             mock.patch.object(sp, "git", side_effect=fake_git), \
             mock.patch.object(sp, "info", side_effect=self.notes.append), \
             mock.patch.object(sp, "warn", side_effect=self.warnings.append):
            yield

    def test_a_push_that_did_not_move_the_tip_is_verify_refusal(self):
        # THE DMR-071 regression: push rc==0, remote tip unchanged → refuse.
        with self._patched(upstream_heads=[self.TIP]):
            code, rec = self.sp.patch_push(PKG, "https://fake/up.git", self.TIP, dry_run=False)
        self.assertEqual(code, self.sp.E_VERIFY)
        self.assertEqual(rec["error_class"], "verify")
        self.assertFalse(rec["ok"])
        self.assertIn("SILENT NO-OP", rec["remediation"])
        self.assertEqual(rec["pushed_commit"], self.PUSHED[:12])
        self.assertEqual(rec["landed_tip"], self.TIP[:12])
        self.assertTrue(any("SILENT NO-OP GUARD" in n for n in self.warnings))

    def test_b_push_that_lands_reports_post_tip_and_commit(self):
        with self._patched(upstream_heads=[self.PUSHED]):
            code, rec = self.sp.patch_push(PKG, "https://fake/up.git", self.TIP, dry_run=False)
        self.assertEqual(code, self.sp.E_OK)
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["landed_tip"], self.PUSHED[:12])
        self.assertEqual(rec["pushed_commit"], self.PUSHED[:12])
        self.assertTrue(any(self.PUSHED[:12] in n and "propagated" in n for n in self.notes))

    def test_c_unreachable_remote_after_push_is_network(self):
        with self._patched(upstream_heads=[None]):
            code, rec = self.sp.patch_push(PKG, "https://fake/up.git", self.TIP, dry_run=False)
        self.assertEqual(code, self.sp.E_NETWORK)
        self.assertEqual(rec["error_class"], "network")
        self.assertIn("cursor NOT advanced", rec["remediation"])

    def test_d_foreign_post_tip_is_verify_refusal(self):
        with self._patched(upstream_heads=[self.FOREIGN]):
            code, rec = self.sp.patch_push(PKG, "https://fake/up.git", self.TIP, dry_run=False)
        self.assertEqual(code, self.sp.E_VERIFY)
        self.assertEqual(rec["landed_tip"], self.FOREIGN[:12])
        self.assertIn("concurrent push", rec["remediation"])

    def test_e_empty_delta_with_ahead_paths_is_extraction_mismatch(self):
        # staged diff empty BUT the tree-level comparison says the monorepo is
        # ahead → the blob extraction under-copied; refuse the no-delta claim.
        with self._patched(upstream_heads=[self.TIP], ahead_paths=["a.txt", "b/c.txt"],
                           staged_diff=""):
            code, rec = self.sp.patch_push(PKG, "https://fake/up.git", self.TIP, dry_run=False)
        self.assertEqual(code, self.sp.E_VERIFY)
        self.assertIn("extraction mismatch", rec["remediation"])
        self.assertEqual(rec["monorepo_ahead_paths"],
                         [f"packages/{PKG}/a.txt", f"packages/{PKG}/b/c.txt"])

    def test_f_true_empty_delta_still_succeeds_without_cursor(self):
        with self._patched(upstream_heads=[self.TIP], staged_diff=""):
            code, rec = self.sp.patch_push(PKG, "https://fake/up.git", self.TIP, dry_run=False)
        self.assertEqual(code, self.sp.E_OK)
        self.assertTrue(rec["ok"])
        self.assertFalse(rec["cursor_updated"])
        self.assertTrue(any("no content delta" in n for n in self.notes))

    # --- subtree (non-patch) leg ------------------------------------------ #

    def _cmd_args(self):
        return argparse.Namespace(command="push", patch=False, dry_run=False,
                                  verify_suite=False, package=None,
                                  allow_dirty=False)

    @contextlib.contextmanager
    def _push_cmd_env(self, upstream_heads):
        sp = self.sp
        saved = {n: getattr(sp, n) for n in
                 ("assert_clean_tree", "load_manifest", "selected_packages",
                  "url_for", "git_foreground", "upstream_head", "save_manifest",
                  "emit", "info", "warn")}
        sp.assert_clean_tree = lambda *a, **k: None
        sp.info = lambda msg: self.notes.append(msg)
        sp.warn = lambda msg: self.warnings.append(msg)
        sp.load_manifest = lambda *a, **k: {"version": 1, "packages": {}}
        sp.selected_packages = lambda *a, **k: [PKG]
        sp.url_for = lambda pkg: "https://fake/up.git"
        sp.git_foreground = lambda args: subprocess.CompletedProcess(args, 0)
        heads = iter(upstream_heads)
        sp.upstream_head = lambda url, branch: (
            next(heads) if not hasattr(sp, "_heads_exhausted") else upstream_heads[-1])
        written = {}
        sp.save_manifest = lambda m: written.setdefault("saved", True)
        records = []
        sp.emit = lambda rec: records.append(rec)
        try:
            yield records, written
        finally:
            for n, v in saved.items():
                setattr(sp, n, v)

    def test_g_subtree_push_already_contained_is_honest_noop(self):
        # git verified containment (rc 0, remote unchanged) → E_OK with an
        # explicit already-contained note, cursor re-baselined at the true tip.
        with self._push_cmd_env([self.TIP, self.TIP]) as (records, written):
            code = self.sp.cmd_push(self._cmd_args())
        self.assertEqual(code, self.sp.E_OK)
        self.assertTrue(written.get("saved"))
        self.assertTrue(records[0]["ok"])
        self.assertEqual(records[0]["landed_tip"], self.TIP[:12])
        self.assertTrue(any("already contains" in n for n in self.notes))

    def test_h_subtree_push_landing_names_the_post_tip(self):
        with self._push_cmd_env([self.TIP, self.PUSHED]) as (records, written):
            code = self.sp.cmd_push(self._cmd_args())
        self.assertEqual(code, self.sp.E_OK)
        self.assertEqual(records[0]["landed_tip"], self.PUSHED[:12])
        self.assertTrue(any(self.PUSHED[:12] in n and "landed" in n for n in self.notes))

    def test_i_subtree_push_unreachable_probe_is_network(self):
        with self._push_cmd_env([self.TIP, None]) as (records, written):
            code = self.sp.cmd_push(self._cmd_args())
        self.assertEqual(code, self.sp.E_NETWORK)
        self.assertFalse(written.get("saved"))
        self.assertFalse(records[0]["ok"])


if __name__ == "__main__":
    unittest.main()