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

    def test_normalized_paths_and_duplicates_select_each_gate_once(self):
        paths = [r" .\packages\llm-mailroom\src\app.py ",
                 "././packages/llm-mailroom/src/other.py", "", "  "]
        self.assertEqual(ci.map_paths_to_gates(paths),
                         ["vendor", "llm-mailroom", "local-mailroom-sandbox"])

    def test_blank_paths_fall_back_to_governance(self):
        self.assertEqual(ci.map_paths_to_gates(["", "  ", "././"]), self.GOV)


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

    def test_final_summary_overrides_progress_and_earlier_summary(self):
        c = ci.parse_pytest_summary("...sF [100%]\n100 passed in 2.0s\n2 failed in 0.1s\n")
        self.assertEqual(c, {"passed": 0, "failed": 2, "skipped": 0, "errors": 0,
                             "xfailed": 0, "xpassed": 0, "found": True})

    def test_no_tests_summary_overrides_progress(self):
        c = ci.parse_pytest_summary("...F [100%]\n=== no tests ran in 0.01s ===\n")
        self.assertTrue(c["found"])
        self.assertEqual((c["passed"], c["failed"]), (0, 0))

    def test_progress_without_percentage_ignores_non_progress_logs(self):
        c = ci.parse_pytest_summary("...sFExX\nFAILED tests/test_x.py::test_case\n")
        self.assertEqual(c, {"passed": 3, "failed": 1, "skipped": 1, "errors": 1,
                             "xfailed": 1, "xpassed": 1, "found": True})


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

    def test_payload_truncates_long_description_without_changing_state(self):
        payload = ci.build_status_payload({"state": "failure", "description": "x" * 141})
        self.assertEqual(payload, {"state": "failure", "context": "ci", "description": "x" * 140})

    def test_all_skipped_run_does_not_count_skips_as_passes(self):
        summary = ci.summarize([{"status": "skip"}, {"status": "skip"}], mode="all",
                               sha="a" * 40, branch="main", started="t")
        self.assertEqual(summary["totals"], {"gates": 2, "pass": 0, "fail": 0, "skip": 2})
        self.assertEqual(summary["state"], "success")
        self.assertEqual(summary["description"], "2 gates: 0 pass, 2 skip")


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
    def test_refuses_unresolvable_head_before_posting(self):
        poster = FakePoster()
        summary = self.summary()
        with mock.patch.object(ci, "head_sha", return_value=""):
            with self.assertRaisesRegex(ci.Refused, "cannot resolve HEAD"):
                ci.report_status(summary, self.work, poster=poster, token="tok")
        self.assertEqual(poster.calls, [])

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

    def test_blank_tokens_fall_through_and_values_are_trimmed(self):
        gh = mock.Mock(return_value="  cli-token\n")
        self.assertEqual(ci.find_token({"GITHUB_TOKEN": " \n", "MAILROOM_GH_TOKEN": " m "}, gh), "m")
        gh.assert_not_called()
        self.assertEqual(ci.find_token({"GITHUB_TOKEN": "", "MAILROOM_GH_TOKEN": "  "}, gh), "cli-token")

    def test_expected_cli_errors_return_no_token(self):
        for exc in (OSError("cannot start gh"), subprocess.TimeoutExpired("gh", 20),
                    subprocess.CalledProcessError(1, "gh")):
            with self.subTest(error=type(exc).__name__):
                self.assertIsNone(ci.find_token({}, mock.Mock(side_effect=exc)))

    def test_unexpected_cli_error_propagates(self):
        with self.assertRaisesRegex(ValueError, "invalid response"):
            ci.find_token({}, mock.Mock(side_effect=ValueError("invalid response")))

    def test_failed_gh_command_cannot_supply_a_token(self):
        result = subprocess.CompletedProcess(["gh", "auth", "token"], 1, "not-a-token", "error")
        with mock.patch.object(ci.shutil, "which", return_value="/fake/gh"), \
                mock.patch.object(ci.subprocess, "run", return_value=result) as run:
            self.assertIsNone(ci.find_token({}))
        run.assert_called_once_with(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)

    def test_repo_override_is_trimmed_and_blank_uses_default(self):
        self.assertEqual(ci.target_repo({"MAILROOM_GITHUB_REPO": " fork/repo\n"}), "fork/repo")
        for env in ({}, {"MAILROOM_GITHUB_REPO": " \n"}):
            with self.subTest(env=env):
                self.assertEqual(ci.target_repo(env), ci.DEFAULT_REPO)


class TestRunGate(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="ci-gate-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.logs = self.root / ".ci"

    def gate(self, program, **kwargs):
        return ci.Gate("unit", "test", [sys.executable, "-c", program], **kwargs)

    def test_precheck_skip_never_starts_process_or_creates_logs(self):
        gate = self.gate("raise SystemExit(1)", precheck=lambda: "missing prerequisite")
        with mock.patch.object(ci.subprocess, "run") as run:
            rec = ci.run_gate(gate, self.root, self.logs)
        run.assert_not_called()
        self.assertEqual((rec["status"], rec["rc"], rec["reason"]),
                         ("skip", None, "missing prerequisite"))
        self.assertEqual(rec["log"], "")
        self.assertFalse(self.logs.exists())

    def test_precheck_exception_propagates_without_execution(self):
        gate = self.gate("pass", precheck=mock.Mock(side_effect=RuntimeError("broken precheck")))
        with mock.patch.object(ci.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "broken precheck"):
                ci.run_gate(gate, self.root, self.logs)
        run.assert_not_called()

    def test_working_directory_environment_and_output_capture(self):
        cwd = self.root / "directory with spaces"
        cwd.mkdir()
        program = ("import json, os, sys; "
                   "print(json.dumps([os.getcwd(), os.environ['CI_TEST_VALUE'], "
                   "os.environ['CI_TEST_INHERITED']])); print('diagnostic', file=sys.stderr)")
        gate = self.gate(program, cwd=cwd, env={"CI_TEST_VALUE": "override"}, precheck=lambda: None)
        with mock.patch.dict(os.environ, {"CI_TEST_VALUE": "original", "CI_TEST_INHERITED": "inherited"}):
            rec = ci.run_gate(gate, self.root, self.logs)
            self.assertEqual(os.environ["CI_TEST_VALUE"], "original")
        lines = (self.logs / "unit.log").read_text().splitlines()
        self.assertEqual(json.loads(lines[0]), [str(cwd), "override", "inherited"])
        self.assertEqual(lines[1:], ["diagnostic"])
        self.assertEqual((rec["status"], rec["rc"], rec["log"]), ("pass", 0, ".ci/unit.log"))

    def test_missing_executable_is_a_failed_gate_with_diagnostic_log(self):
        gate = ci.Gate("missing", "test", [str(self.root / "nonexistent-command")])
        rec = ci.run_gate(gate, self.root, self.logs)
        self.assertEqual((rec["status"], rec["rc"], rec["reason"]), ("fail", 127, "exit 127"))
        log = (self.logs / "missing.log").read_text()
        self.assertIn("could not execute", log)
        self.assertIn("nonexistent-command", log)
        self.assertEqual(rec["tail"], log.rstrip("\n"))

    def test_failed_gate_keeps_full_log_but_limits_tail_to_25_lines(self):
        program = "import sys; print('\\n'.join(str(i) for i in range(40))); sys.exit(7)"
        rec = ci.run_gate(self.gate(program), self.root, self.logs)
        self.assertEqual((rec["status"], rec["rc"], rec["reason"]), ("fail", 7, "exit 7"))
        self.assertEqual((self.logs / "unit.log").read_text().splitlines(), list(map(str, range(40))))
        self.assertEqual(rec["tail"].splitlines(), list(map(str, range(15, 40))))

    def test_exit_code_controls_status_independently_of_pytest_counts(self):
        cases = [(0, "2 failed in 0.1s", "pass", True),
                 (5, "no tests ran in 0.1s", "fail", True),
                 (1, "ImportError: collection failed", "fail", False)]
        for rc, output, status, found in cases:
            with self.subTest(rc=rc, output=output):
                gate = self.gate(f"import sys; print({output!r}); sys.exit({rc})", parse="pytest")
                rec = ci.run_gate(gate, self.root, self.logs)
                self.assertEqual((rec["rc"], rec["status"], rec["counts"]["found"]), (rc, status, found))

    def test_labels_gate_passes_discovered_token_to_gh(self):
        gate = ci.Gate("labels-audit", "governance", ["fake-command"])
        proc = subprocess.CompletedProcess(gate.argv, 0, "", "")
        with mock.patch.object(ci, "find_token", return_value="synthetic-token"), \
                mock.patch.dict(os.environ, {"GH_TOKEN": "ambient"}), \
                mock.patch.object(ci.subprocess, "run", return_value=proc) as run:
            ci.run_gate(gate, self.root, self.logs)
            self.assertEqual(run.call_args.kwargs["env"]["GH_TOKEN"], "synthetic-token")
            self.assertEqual(os.environ["GH_TOKEN"], "ambient")

    def test_log_write_failure_propagates(self):
        with mock.patch.object(Path, "write_text", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                ci.run_gate(self.gate("pass"), self.root, self.logs)


class TestPostStatus(unittest.TestCase):
    URL = "https://api.github.com/repos/example/repo/statuses/" + "a" * 40
    PAYLOAD = {"state": "failure", "context": "ci", "description": "1 gate failed"}

    def test_post_request_and_success_response(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 201
        response.read.return_value = b'{"created": true}'
        with mock.patch.object(ci.urllib.request, "urlopen", return_value=response) as open_url:
            self.assertEqual(ci.post_status(self.URL, "synthetic-token", self.PAYLOAD),
                             (201, '{"created": true}'))
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, self.URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data), self.PAYLOAD)
        self.assertEqual(dict((k.lower(), v) for k, v in request.header_items()),
                         {"authorization": "Bearer synthetic-token", "accept": "application/vnd.github+json",
                          "content-type": "application/json", "user-agent": "mailroom-local-ci"})
        self.assertEqual(open_url.call_args.kwargs, {"timeout": 30})

    def test_http_error_returns_code_and_body(self):
        error = ci.urllib.error.HTTPError(self.URL, 403, "Forbidden", {}, io.BytesIO(b"denied\xff"))
        self.addCleanup(error.close)
        with mock.patch.object(ci.urllib.request, "urlopen", side_effect=error):
            self.assertEqual(ci.post_status(self.URL, "tok", self.PAYLOAD), (403, "denied\ufffd"))

    def test_network_error_returns_zero_and_reason(self):
        with mock.patch.object(ci.urllib.request, "urlopen", side_effect=ci.urllib.error.URLError("offline")):
            self.assertEqual(ci.post_status(self.URL, "tok", self.PAYLOAD), (0, "offline"))

    def test_unexpected_request_error_propagates(self):
        with mock.patch.object(ci.urllib.request, "urlopen", side_effect=ValueError("bad request")):
            with self.assertRaisesRegex(ValueError, "bad request"):
                ci.post_status(self.URL, "tok", self.PAYLOAD)


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

    def test_missing_base_runs_all_but_still_refuses_partial_success(self):
        poster = FakePoster()
        with mock.patch.object(ci, "find_token", return_value="synthetic-token"):
            rc, out, err = self.run_ci(["run", "--base", "missing-base", "--report-status", "--json"],
                                       fail=False, poster=poster)
        summary = json.loads(out)
        self.assertEqual(rc, 2)
        self.assertEqual(summary["mode"], "changed")
        self.assertEqual(summary["totals"], {"gates": 4, "pass": 3, "fail": 0, "skip": 1})
        self.assertIn("cannot compute merge-base with missing-base; running ALL gates", err)
        self.assertIn("partial run", summary["report"]["refused"])
        self.assertEqual(poster.calls, [])

    def test_only_unions_names_and_groups_in_canonical_order_without_duplicates(self):
        rc, out, _ = self.run_ci(["run", "--all", "--only", "g-last", "grp", "g-ok", "--json"], fail=False)
        summary = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual(summary["mode"], "only")
        self.assertEqual([g["name"] for g in summary["gates"]], ["g-ok", "g-skip", "g-last"])

    def test_unknown_selector_preserves_previous_report_and_runs_nothing(self):
        self.run_ci(["run", "--all"], fail=False)
        report = self.work / ".ci" / "last-run.json"
        previous = report.read_bytes()
        with mock.patch.object(ci, "run_gate") as run:
            rc, _, err = self.run_ci(["run", "--only", "g-ok", "unknown-gate"], fail=False)
        self.assertEqual(rc, 2)
        self.assertIn("unknown gate/group", err)
        run.assert_not_called()
        self.assertEqual(report.read_bytes(), previous)

    def test_http_failure_exits_one_and_persists_reporting_error(self):
        poster = FakePoster(503, "service unavailable")
        with mock.patch.object(ci, "find_token", return_value="synthetic-token"):
            rc, out, err = self.run_ci(["run", "--all", "--report-status", "--json"],
                                       fail=False, poster=poster)
        summary = json.loads(out)
        self.assertEqual(rc, 1)
        self.assertEqual(summary["state"], "success")  # gates passed; delivery failed
        self.assertIn("HTTP 503: service unavailable", summary["report"]["error"])
        self.assertIn("--report-status FAILED", err)
        self.assertEqual(len(poster.calls), 1)
        self.assertEqual(json.loads((self.work / ".ci" / "last-run.json").read_text()), summary)

    def test_refused_status_preserves_failed_gate_exit_code(self):
        (self.work / "dirty.txt").write_text("dirty\n")
        poster = FakePoster()
        rc, out, err = self.run_ci(["run", "--all", "--report-status", "--json"], fail=True, poster=poster)
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(out)["state"], "failure")
        self.assertIn("dirty", json.loads(out)["report"]["refused"])
        self.assertIn("REFUSED", err)
        self.assertEqual(poster.calls, [])

    def test_second_run_overwrites_both_reports(self):
        self.run_ci(["run", "--all"], fail=True)
        rc, out, _ = self.run_ci(["run", "--only", "g-ok", "--json"], fail=False)
        summary = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads((self.work / ".ci" / "last-run.json").read_text()), summary)
        markdown = (self.work / ".ci" / "last-run.md").read_text()
        self.assertIn("| `g-ok` | pass |", markdown)
        self.assertNotIn("`g-last`", markdown)
        self.assertIn("partial run: cannot mark the required `ci` check green", markdown)

    def test_status_table_reads_saved_report_without_running_gates(self):
        self.run_ci(["run", "--all"], fail=True)
        with mock.patch.object(ci, "run_gate") as run:
            rc, out, err = self.run_ci(["status"], fail=False)
        self.assertEqual(rc, 0)
        self.assertIn("g-last", out)
        self.assertIn("ci: failure", out)
        self.assertEqual(err, "")
        run.assert_not_called()


class TestChangedRun(GitFixture):
    def run_changed(self, argv, gates):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = ci.main(argv, gates=gates, root=self.work, poster=FakePoster())
        return rc, json.loads(out.getvalue()), err.getvalue()

    def test_default_and_explicit_changed_select_only_affected_gates(self):
        (self.work / "board-site").mkdir()
        (self.work / "board-site" / "new.js").write_text("// changed\n")
        gates = [ci.Gate("board-check", "governance", [sys.executable, "-c", "raise SystemExit(1)"]),
                 ci.Gate("board-site", "board-site", [sys.executable, "-c", "print('selected')"])]
        for options in ([], ["--changed", "--base", "origin/main"]):
            with self.subTest(options=options):
                rc, summary, _ = self.run_changed(["run", *options, "--json"], gates)
                self.assertEqual(rc, 0)
                self.assertEqual(summary["mode"], "changed")
                self.assertEqual([g["name"] for g in summary["gates"]], ["board-site"])
                self.assertFalse((self.work / ".ci" / "board-check.log").exists())

    def test_failure_does_not_prevent_later_gate_execution(self):
        gates = [ci.Gate("first", "test", [sys.executable, "-c", "raise SystemExit(1)"]),
                 ci.Gate("second", "test", [sys.executable, "-c", "print('still ran')"])]
        rc, summary, err = self.run_changed(["run", "--all", "--json"], gates)
        self.assertEqual(rc, 1)
        self.assertEqual([g["status"] for g in summary["gates"]], ["fail", "pass"])
        self.assertEqual((self.work / ".ci" / "second.log").read_text(), "still ran\n")
        self.assertIn("second: PASS", err)

    def test_missing_pytest_summary_is_visible_in_reports(self):
        gates = [ci.Gate("broken-pytest", "pytest", [sys.executable, "-c", "raise SystemExit(2)"], parse="pytest")]
        rc, summary, _ = self.run_changed(["run", "--all", "--json"], gates)
        self.assertEqual(rc, 1)
        self.assertFalse(summary["gates"][0]["counts"]["found"])
        for report in (ci.render_table(summary), (self.work / ".ci" / "last-run.md").read_text()):
            self.assertIn("no pytest summary line (exit 2)", report)


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
                          "-p", "no:cacheprovider"])
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

    def test_board_site_precheck_requires_node(self):
        gate = {g.name: g for g in ci.build_gates()}["board-site"]
        with mock.patch.object(ci.shutil, "which", return_value=None):
            self.assertEqual(gate.precheck(), "node not installed")
        with mock.patch.object(ci.shutil, "which", return_value="/fake/node"):
            self.assertIsNone(gate.precheck())

    def test_labels_precheck_accepts_discovered_credentials(self):
        gate = {g.name: g for g in ci.build_gates()}["labels-audit"]
        with mock.patch.object(ci, "find_token", return_value="synthetic-token"):
            self.assertIsNone(gate.precheck())


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


class TestPrePushExecution(GitFixture):
    def setUp(self):
        super().setUp()
        scripts = self.work / "scripts"
        scripts.mkdir()
        # The hook runs a harmless recorder instead of the real CI gates.
        (scripts / "ci.py").write_text(
            "import json, os, sys\n"
            "print(json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[1:]}))\n"
            "sys.exit(int(os.environ.get('CI_TEST_EXIT_CODE', '0')))\n")
        self.nested = self.work / "nested directory"
        self.nested.mkdir()

    def run_hook(self, *, skip="", exit_code=0, cwd=None):
        return subprocess.run(["sh", str(TestPrePushHook.HOOK), "origin", "unused-url"],
                              cwd=str(cwd or self.nested), input="synthetic ref update\n",
                              env=dict(os.environ, SKIP_CI=skip, CI_TEST_EXIT_CODE=str(exit_code)),
                              capture_output=True, text=True, timeout=10)

    def test_success_runs_changed_gates_from_repository_root(self):
        for skip in ("", "0", "true"):
            with self.subTest(skip=skip):
                proc = self.run_hook(skip=skip)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout), {"cwd": str(self.work), "argv": ["run", "--changed"]})
                self.assertIn("running python3 scripts/ci.py run --changed", proc.stderr)
                self.assertNotIn("BYPASSED", proc.stderr)

    def test_failed_ci_aborts_push(self):
        proc = self.run_hook(exit_code=23)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stdout)["argv"], ["run", "--changed"])
        self.assertIn("local CI failed; push aborted", proc.stderr)

    def test_root_discovery_failure_does_not_run_ci(self):
        proc = self.run_hook(cwd=self.tmp)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout, "")
        self.assertIn("not a git repository", proc.stderr)


if __name__ == "__main__":
    unittest.main()
