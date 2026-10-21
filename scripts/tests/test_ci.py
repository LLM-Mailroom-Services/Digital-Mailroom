#!/usr/bin/env python3
"""Hermetic tests for scripts/ci.py (DMR-090).

Pins the local CI runner: path->gate mapping, pytest summary parsing, every
``--report-status`` refusal (against REAL temp git repos with a bare origin,
and a fake HTTP poster that can express HTTP errors), the status payload, and
an end-to-end ``run`` with fake gate commands that exit 0 / 1.

Run:  python3 -m unittest discover scripts/tests -v
"""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci.py"


def _load():
    spec = importlib.util.spec_from_file_location("ci_test_mod", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ci_test_mod"] = mod  # dataclasses needs the module registered
    spec.loader.exec_module(mod)
    return mod


ci = _load()


class TestPathMapping(unittest.TestCase):
    ALL_SUITES = [
        "llm-dojo-scoring", "llm-mailroom", "The-Mailroom", "local-mailroom-sandbox",
        "mailroom-corpus-eda", "claims-data-eda", "Enron-Evaluation-Environment",
    ]
    GOV = ["board-check", "audit-references", "taxonomy-parity", "release-chain", "labels-audit"]

    def test_empty_diff_is_governance_only(self):
        self.assertEqual(ci.map_paths_to_gates([]), self.GOV)

    def test_unknown_path_is_governance_only(self):
        self.assertEqual(ci.map_paths_to_gates(["README.md", "docs/wiki/Home.md"]), self.GOV)

    def test_non_vendored_package_maps_to_its_suite_only(self):
        self.assertEqual(ci.map_paths_to_gates(["packages/The-Mailroom/mailroom_ui/app.py"]), ["The-Mailroom"])

    def test_dojo_scoring_adds_vendor_and_sandbox(self):
        got = ci.map_paths_to_gates(["packages/llm-dojo-scoring/llm_dojo_scoring/corpus.py"])
        self.assertEqual(got, ["vendor", "llm-dojo-scoring", "local-mailroom-sandbox"])

    def test_llm_mailroom_adds_vendor_and_sandbox(self):
        got = ci.map_paths_to_gates(["packages/llm-mailroom/src/pipeline/hf_corpora.py"])
        self.assertEqual(got, ["vendor", "llm-mailroom", "local-mailroom-sandbox"])

    def test_vendor_tree_edit_runs_vendor_and_sandbox(self):
        got = ci.map_paths_to_gates(["packages/local-mailroom-sandbox/vendor/llm-mailroom/x.py"])
        self.assertEqual(got, ["vendor", "local-mailroom-sandbox"])

    def test_scripts_governance_github_map_to_governance_plus_scripts(self):
        expected = self.GOV[:0] + ["board-check", "audit-references", "taxonomy-parity",
                                   "release-chain", "labels-audit", "scripts"]
        for path in ("scripts/ci.py", "governance/TASKS.md", ".github/workflows/board-governance.yml"):
            self.assertEqual(ci.map_paths_to_gates([path]), expected, path)

    def test_board_site(self):
        self.assertEqual(ci.map_paths_to_gates(["board-site/api/board.js"]), ["board-site"])

    def test_uv_lock_runs_lock_and_every_suite(self):
        self.assertEqual(ci.map_paths_to_gates(["uv.lock"]), ["lock"] + self.ALL_SUITES)

    def test_nested_pyproject_runs_lock_and_every_suite(self):
        self.assertEqual(ci.map_paths_to_gates(["packages/claims-data-eda/pyproject.toml"]),
                         ["lock"] + self.ALL_SUITES)

    def test_unknown_package_dir_is_governance_only(self):
        self.assertEqual(ci.map_paths_to_gates(["packages/not-a-package/x.py"]), self.GOV)

    def test_union_of_multiple_paths_in_canonical_order(self):
        got = ci.map_paths_to_gates(["board-site/index.html", "packages/claims-data-eda/a.py", "scripts/x.py"])
        self.assertEqual(got, self.GOV + ["scripts", "board-site", "claims-data-eda"])


class TestPytestSummary(unittest.TestCase):
    def test_pass_skip_fail_with_duration(self):
        c = ci.parse_pytest_summary("....\n1864 passed, 37 skipped, 2 failed in 80.1s\n")
        self.assertEqual((c["passed"], c["skipped"], c["failed"], c["errors"]), (1864, 37, 2, 0))
        self.assertTrue(c["found"])

    def test_decorated_summary_with_wallclock(self):
        c = ci.parse_pytest_summary("======= 995 passed, 36 skipped in 290.12s (0:04:50) =======\n")
        self.assertEqual((c["passed"], c["skipped"], c["failed"]), (995, 36, 0))

    def test_no_duration(self):
        c = ci.parse_pytest_summary("186 passed, 17 skipped\n")
        self.assertEqual((c["passed"], c["skipped"], c["failed"]), (186, 17, 0))
        self.assertTrue(c["found"])

    def test_no_tests_ran(self):
        c = ci.parse_pytest_summary("no tests ran in 0.01s\n")
        self.assertEqual((c["passed"], c["failed"], c["skipped"], c["errors"]), (0, 0, 0, 0))
        self.assertTrue(c["found"])

    def test_errors_and_xfail_variants(self):
        c = ci.parse_pytest_summary("3 passed, 1 xfailed, 2 xpassed, 1 error, 4 warnings in 1.5s")
        self.assertEqual((c["passed"], c["xfailed"], c["xpassed"], c["errors"]), (3, 1, 2, 1))
        c = ci.parse_pytest_summary("2 errors in 0.30s")
        self.assertEqual((c["errors"], c["passed"]), (2, 0))

    def test_uses_last_summary_not_a_log_line_above_it(self):
        out = "FAILED test_x.py::t - 5 passed things\n12 passed, 1 failed in 3.0s\n"
        c = ci.parse_pytest_summary(out)
        self.assertEqual((c["passed"], c["failed"]), (12, 1))

    def test_progress_characters_when_summary_suppressed(self):
        out = ("................................s....s..                                 [ 40%]\n"
               "..F.....sE.......x.X                                                     [100%]\n"
               "warning: The `UV_NATIVE_TLS` environment variable is deprecated\n")
        c = ci.parse_pytest_summary(out)
        # hand count: line 1 = 32+4+2 = 38 dots, 2 s; line 2 = 2+5+7+1 = 15 dots, 1 s
        self.assertTrue(c["found"])
        self.assertEqual((c["failed"], c["errors"], c["xfailed"], c["xpassed"]), (1, 1, 1, 1))
        self.assertEqual(c["skipped"], 2 + 1)
        self.assertEqual(c["passed"], 53)

    def test_garbage_is_not_found(self):
        c = ci.parse_pytest_summary("Traceback (most recent call last):\nImportError: boom\n")
        self.assertFalse(c["found"])
        self.assertEqual(c["passed"], 0)


class TestDescribeAndPayload(unittest.TestCase):
    def test_description_matches_spec_example(self):
        self.assertEqual(ci.describe(12, 11, 0, 1), "12 gates: 11 pass, 1 skip")

    def test_description_with_fail_and_partial(self):
        self.assertEqual(ci.describe(4, 2, 1, 1, partial=True), "partial run, 4 gates: 2 pass, 1 fail, 1 skip")

    def test_payload_content(self):
        rec = [{"status": "pass"}, {"status": "pass"}, {"status": "skip"}]
        s = ci.summarize(rec, mode="all", sha="a" * 40, branch="b", started="t")
        self.assertEqual(ci.build_status_payload(s),
                         {"state": "success", "context": "ci", "description": "3 gates: 2 pass, 1 skip"})

    def test_payload_failure_state(self):
        rec = [{"status": "pass"}, {"status": "fail"}]
        s = ci.summarize(rec, mode="all", sha="a" * 40, branch="b", started="t")
        p = ci.build_status_payload(s)
        self.assertEqual((p["state"], p["description"]), ("failure", "2 gates: 1 pass, 1 fail"))


def _git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=str(cwd), env=env, capture_output=True, text=True, check=True)


class FakePoster:
    """Records calls; can answer with any HTTP status (e.g. 422 / 401)."""

    def __init__(self, code=201, body="{}"):
        self.calls, self.code, self.body = [], code, body

    def __call__(self, url, token, payload):
        self.calls.append((url, token, payload))
        return self.code, self.body


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ci-test-"))
        self.origin = self.tmp / "origin.git"
        self.work = self.tmp / "work"
        _git(self.tmp, "init", "--bare", "-b", "main", str(self.origin))
        _git(self.tmp, "clone", str(self.origin), str(self.work))
        (self.work / "a.txt").write_text("a\n")
        (self.work / ".gitignore").write_text(".ci/\n")
        _git(self.work, "add", "a.txt", ".gitignore")
        _git(self.work, "commit", "-m", "init")
        _git(self.work, "push", "-u", "origin", "HEAD:main")
        self._env = dict(os.environ)
        os.environ.pop("MAILROOM_GITHUB_REPO", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def summary(self, mode="all", fail=False):
        recs = [{"status": "pass"}, {"status": "fail" if fail else "pass"}]
        return ci.summarize(recs, mode=mode, sha=ci.head_sha(self.work), branch="main", started="t")


class TestReportStatus(GitFixture):
    def test_clean_pushed_full_run_posts_success_to_head(self):
        poster = FakePoster()
        out = ci.report_status(self.summary(), self.work, poster=poster, token="tok")
        sha = ci.head_sha(self.work)
        self.assertEqual(len(poster.calls), 1)
        url, token, payload = poster.calls[0]
        self.assertEqual(url, f"https://api.github.com/repos/LLM-Mailroom-Services/Digital-Mailroom/statuses/{sha}")
        self.assertEqual(token, "tok")
        self.assertEqual(payload, {"state": "success", "context": "ci", "description": "2 gates: 2 pass"})
        self.assertEqual(out["http"], 201)

    def test_repo_override_env(self):
        os.environ["MAILROOM_GITHUB_REPO"] = "me/fork"
        self.assertEqual(ci.target_repo(), "me/fork")
        poster = FakePoster()
        ci.report_status(self.summary(), self.work, poster=poster, token="tok", repo=ci.target_repo())
        self.assertTrue(poster.calls[0][0].startswith("https://api.github.com/repos/me/fork/statuses/"))

    def test_refuses_dirty_tree(self):
        (self.work / "a.txt").write_text("changed\n")
        poster = FakePoster()
        with self.assertRaisesRegex(ci.Refused, "dirty"):
            ci.report_status(self.summary(), self.work, poster=poster, token="tok")
        self.assertEqual(poster.calls, [])

    def test_refuses_untracked_file_as_dirty(self):
        (self.work / "new.txt").write_text("x\n")
        with self.assertRaisesRegex(ci.Refused, "dirty"):
            ci.report_status(self.summary(), self.work, poster=FakePoster(), token="tok")

    def test_refuses_head_not_on_remote(self):
        (self.work / "b.txt").write_text("b\n")
        _git(self.work, "add", "b.txt")
        _git(self.work, "commit", "-m", "local only")
        poster = FakePoster()
        with self.assertRaisesRegex(ci.Refused, "not on any remote"):
            ci.report_status(self.summary(), self.work, poster=poster, token="tok")
        self.assertEqual(poster.calls, [])

    def test_partial_run_cannot_post_success(self):
        for mode in ("only", "changed"):
            poster = FakePoster()
            with self.assertRaisesRegex(ci.Refused, "partial run"):
                ci.report_status(self.summary(mode=mode), self.work, poster=poster, token="tok")
            self.assertEqual(poster.calls, [], mode)

    def test_partial_run_may_post_failure(self):
        poster = FakePoster()
        ci.report_status(self.summary(mode="only", fail=True), self.work, poster=poster, token="tok")
        self.assertEqual(poster.calls[0][2]["state"], "failure")
        self.assertEqual(poster.calls[0][2]["description"], "partial run, 2 gates: 1 pass, 1 fail")

    def test_refuses_when_head_moved_since_run(self):
        stale = self.summary()
        (self.work / "c.txt").write_text("c\n")
        _git(self.work, "add", "c.txt")
        _git(self.work, "commit", "-m", "second")
        _git(self.work, "push", "origin", "HEAD:main")
        with self.assertRaisesRegex(ci.Refused, "HEAD moved"):
            ci.report_status(stale, self.work, poster=FakePoster(), token="tok")

    def test_refuses_without_token(self):
        for k in ("GITHUB_TOKEN", "MAILROOM_GH_TOKEN"):
            os.environ.pop(k, None)
        with mock.patch.object(ci.shutil, "which", return_value=None):  # no gh either
            with self.assertRaisesRegex(ci.Refused, "no GitHub token"):
                ci.report_status(self.summary(), self.work, poster=FakePoster())

    def test_http_error_is_surfaced_not_swallowed(self):
        with self.assertRaisesRegex(RuntimeError, "HTTP 422"):
            ci.report_status(self.summary(), self.work, poster=FakePoster(422, "bad"), token="tok")


class TestTokenOrder(unittest.TestCase):
    def test_github_token_wins_then_mailroom_then_gh(self):
        gh = lambda: "from-gh\n"
        self.assertEqual(ci.find_token({"GITHUB_TOKEN": "g", "MAILROOM_GH_TOKEN": "m"}, gh), "g")
        self.assertEqual(ci.find_token({"MAILROOM_GH_TOKEN": "m"}, gh), "m")
        self.assertEqual(ci.find_token({}, gh), "from-gh")
        self.assertIsNone(ci.find_token({}, lambda: ""))


def _fake_gates(tmp: Path, *, fail: bool):
    py = sys.executable
    return [
        ci.Gate("g-ok", "grp", [py, "-c", "print('fine')"]),
        ci.Gate("g-pytest", "pytest",
                [py, "-c", "print('....');print('7 passed, 3 skipped in 0.5s')"], parse="pytest"),
        ci.Gate("g-skip", "grp", [py, "-c", "raise SystemExit(1)"], precheck=lambda: "no credentials here"),
        ci.Gate("g-last", "grp", [py, "-c", f"raise SystemExit({1 if fail else 0})"]),
    ]


class TestRunEndToEnd(GitFixture):
    def run_ci(self, argv, *, fail, poster=None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = ci.main(argv, gates=_fake_gates(self.tmp, fail=fail), root=self.work,
                         poster=poster or FakePoster())
        return rc, out.getvalue(), err.getvalue()

    def test_passing_run_json(self):
        rc, out, _ = self.run_ci(["run", "--all", "--json"], fail=False)
        d = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual(d["state"], "success")
        self.assertEqual(d["mode"], "all")
        self.assertEqual(d["totals"], {"gates": 4, "pass": 3, "fail": 0, "skip": 1})
        self.assertEqual(d["description"], "4 gates: 3 pass, 1 skip")
        by = {g["name"]: g for g in d["gates"]}
        self.assertEqual(by["g-skip"]["status"], "skip")
        self.assertEqual(by["g-skip"]["reason"], "no credentials here")
        self.assertEqual(by["g-pytest"]["counts"]["passed"], 7)
        self.assertEqual(by["g-pytest"]["counts"]["skipped"], 3)

    def test_failing_gate_gives_nonzero_and_failure_state(self):
        rc, out, _ = self.run_ci(["run", "--all", "--json"], fail=True)
        d = json.loads(out)
        self.assertEqual(rc, 1)
        self.assertEqual(d["state"], "failure")
        self.assertEqual(d["totals"]["fail"], 1)
        self.assertEqual({g["name"]: g["status"] for g in d["gates"]}["g-last"], "fail")

    def test_summary_files_written(self):
        self.run_ci(["run", "--all"], fail=True)
        saved = json.loads((self.work / ".ci" / "last-run.json").read_text())
        self.assertEqual(saved["state"], "failure")
        md = (self.work / ".ci" / "last-run.md").read_text()
        self.assertIn("| `g-last` | fail |", md)
        self.assertIn("| `g-pytest` | pass | ", md)
        self.assertIn("7 passed, 3 skipped", md)

    def test_status_subcommand_reads_last_run(self):
        self.run_ci(["run", "--all"], fail=False)
        rc, out, _ = self.run_ci(["status", "--json"], fail=False)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["totals"]["gates"], 4)

    def test_status_without_previous_run(self):
        rc, _, err = self.run_ci(["status"], fail=False)
        self.assertEqual(rc, 1)
        self.assertIn("no previous run", err)

    def test_only_selects_group_and_marks_partial(self):
        rc, out, _ = self.run_ci(["run", "--only", "pytest", "--json"], fail=True)
        d = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual([g["name"] for g in d["gates"]], ["g-pytest"])
        self.assertEqual(d["mode"], "only")

    def test_unknown_only_is_usage_error(self):
        rc, _, err = self.run_ci(["run", "--only", "nope"], fail=False)
        self.assertEqual(rc, 2)
        self.assertIn("unknown gate/group", err)

    def test_report_status_full_pass_posts_success(self):
        os.environ["GITHUB_TOKEN"] = "tok"
        poster = FakePoster()
        rc, out, _ = self.run_ci(["run", "--all", "--report-status", "--json"], fail=False, poster=poster)
        self.assertEqual(rc, 0)
        self.assertEqual(poster.calls[0][2],
                         {"state": "success", "context": "ci", "description": "4 gates: 3 pass, 1 skip"})
        self.assertEqual(json.loads(out)["report"]["posted"], "success")

    def test_report_status_partial_pass_refused_exit_2_and_nothing_posted(self):
        os.environ["GITHUB_TOKEN"] = "tok"
        poster = FakePoster()
        rc, out, err = self.run_ci(["run", "--only", "g-ok", "--report-status", "--json"], fail=False,
                                   poster=poster)
        self.assertEqual(rc, 2)
        self.assertEqual(poster.calls, [])
        self.assertIn("REFUSED", err)
        self.assertIn("partial", json.loads(out)["report"]["refused"])

    def test_report_status_failing_run_posts_failure_and_exits_1(self):
        os.environ["GITHUB_TOKEN"] = "tok"
        poster = FakePoster()
        rc, _, _ = self.run_ci(["run", "--all", "--report-status"], fail=True, poster=poster)
        self.assertEqual(rc, 1)
        self.assertEqual(poster.calls[0][2]["state"], "failure")
        self.assertEqual(poster.calls[0][2]["description"], "4 gates: 2 pass, 1 fail, 1 skip")

    def test_report_status_dirty_tree_refused(self):
        # gate side effect would dirty the tree; here the pre-existing untracked file does
        os.environ["GITHUB_TOKEN"] = "tok"
        (self.work / "stray.txt").write_text("x\n")
        poster = FakePoster()
        rc, _, err = self.run_ci(["run", "--all", "--report-status"], fail=False, poster=poster)
        self.assertEqual(rc, 2)
        self.assertEqual(poster.calls, [])
        self.assertIn("dirty", err)


class TestChangedPaths(GitFixture):
    def test_committed_uncommitted_and_untracked_are_all_seen(self):
        _git(self.work, "checkout", "-b", "feat")
        (self.work / "scripts").mkdir()
        (self.work / "scripts" / "x.py").write_text("x\n")
        _git(self.work, "add", "scripts/x.py")
        _git(self.work, "commit", "-m", "x")
        (self.work / "a.txt").write_text("edited\n")
        (self.work / "board-site").mkdir()
        (self.work / "board-site" / "n.js").write_text("n\n")
        got = ci.changed_paths(self.work, "origin/main")
        self.assertEqual(got, ["a.txt", "board-site/n.js", "scripts/x.py"])

    def test_no_changes_is_empty_list(self):
        self.assertEqual(ci.changed_paths(self.work, "origin/main"), [])

    def test_missing_base_returns_none(self):
        self.assertIsNone(ci.changed_paths(self.work, "origin/does-not-exist"))


class TestRealGateTable(unittest.TestCase):
    def test_gate_commands_match_spec(self):
        gates = {g.name: g for g in ci.build_gates()}
        self.assertEqual(len(gates), 16)
        self.assertEqual(gates["board-check"].argv[1:], ["scripts/board_state.py", "check", "--log-limit", "500"])
        self.assertEqual(gates["lock"].argv, ["uv", "lock", "--check"])
        self.assertEqual(gates["scripts"].argv[1:], ["-m", "unittest", "discover", "scripts/tests"])
        self.assertEqual(gates["llm-mailroom"].argv,
                         ["uv", "run", "--frozen", "pytest", "packages/llm-mailroom/src/tests",
                          "-q", "-p", "no:cacheprovider"])
        self.assertEqual(gates["board-site"].argv, ["node", "tests/api.test.js"])
        self.assertEqual(gates["board-site"].cwd.name, "board-site")

    def test_labels_audit_skips_without_credentials(self):
        saved = dict(os.environ)
        try:
            for k in ("GITHUB_TOKEN", "MAILROOM_GH_TOKEN"):
                os.environ.pop(k, None)
            with mock.patch.object(ci.shutil, "which", return_value=None):  # gh unavailable
                gate = {g.name: g for g in ci.build_gates()}["labels-audit"]
                self.assertIn("no GitHub credentials", gate.precheck())
                out = Path(tempfile.mkdtemp(prefix="ci-skip-"))
                rec = ci.run_gate(gate, REPO_ROOT, out)
                shutil.rmtree(out, ignore_errors=True)
            self.assertEqual((rec["status"], rec["rc"]), ("skip", None))
        finally:
            os.environ.clear()
            os.environ.update(saved)


class TestPrePushHook(unittest.TestCase):
    HOOK = REPO_ROOT / "scripts" / "githooks" / "pre-push"

    def test_executable_and_posix_sh(self):
        self.assertTrue(os.access(self.HOOK, os.X_OK))
        self.assertEqual(self.HOOK.read_text().splitlines()[0], "#!/bin/sh")

    def test_skip_ci_bypasses_loudly(self):
        proc = subprocess.run(["sh", str(self.HOOK)], capture_output=True, text=True,
                              env=dict(os.environ, SKIP_CI="1"))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("BYPASSED", proc.stderr)


if __name__ == "__main__":
    unittest.main()
