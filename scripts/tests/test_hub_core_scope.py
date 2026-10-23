#!/usr/bin/env python3
"""DMR-093: real workspace/config contracts and offline CLI selection.

Only external Git/GitHub commands are faked. The CLIs, argument parsing,
manifest loading, report copying and generated landing page all run for real.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE = {
    "The-Mailroom": "the-mailroom",
    "llm-dojo-scoring": "llm-dojo-scoring",
    "llm-mailroom": "mailroom",
    "local-mailroom-sandbox": "mailroom-sandbox",
    "mailroom-corpus-eda": "mailroom-corpus-eda",
}
ARCHIVED = ("Enron-Evaluation-Environment", "claims-data-eda")


class TestCoreWorkspace(unittest.TestCase):
    def test_real_workspace_manifest_and_lock_agree_on_five_core_packages(self):
        workspace = tomllib.loads((ROOT / "pyproject.toml").read_text())
        lock = tomllib.loads((ROOT / "uv.lock").read_text())
        manifest = json.loads((ROOT / "scripts/packages_sync.json").read_text())
        self.assertCountEqual(workspace["tool"]["uv"]["workspace"]["members"],
                              [f"packages/{name}" for name in CORE])
        self.assertEqual(set(manifest["packages"]), set(CORE))
        self.assertCountEqual(lock["manifest"]["members"],
                              ["mailroom-hub", *CORE.values()])
        local_sources = {
            package["name"]: package["source"]
            for package in lock["package"]
            if "registry" not in package["source"] and "git" not in package["source"]
        }
        expected_sources = {"mailroom-hub": {"virtual": "."}}
        for directory, distribution in CORE.items():
            with self.subTest(package=directory):
                path = ROOT / "packages" / directory
                project = tomllib.loads((path / "pyproject.toml").read_text())
                self.assertEqual(project["project"]["name"], distribution)
                virtual = project.get("tool", {}).get("uv", {}).get("package", True) is False
                self.assertEqual(virtual, directory == "mailroom-corpus-eda")
                self.assertTrue((path / ("src/tests" if directory == "llm-mailroom" else "tests")).is_dir())
                expected_sources[distribution] = {"virtual" if virtual else "editable": f"packages/{directory}"}
                upstream = "Mailroom-Corpus-EDA" if directory == "mailroom-corpus-eda" else directory
                self.assertEqual(manifest["packages"][directory]["url"],
                                 f"https://github.com/Exios66/{upstream}.git")
        self.assertEqual(local_sources, expected_sources)
        self.assertEqual(workspace["tool"]["uv"]["sources"], {
            name: {"workspace": True} for name in CORE.values() if name != "mailroom-corpus-eda"
        })
        for name in ARCHIVED:
            self.assertFalse((ROOT / "packages" / name).exists())


class OfflineCLI(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dmr093-cli-")
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)
        self.bin = self.temp / "bin"
        self.bin.mkdir()
        self.log = self.temp / "commands.jsonl"
        # git simulates an absent object database for sync. For Pages it
        # records the actual built tree and accepts local Git plumbing.
        # gh only answers the repo lookup; every other API call fails.
        fake = f"#!{sys.executable}\n" + r'''import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
record = {"tool": name, "args": args}
if name == "git" and args[:1] == ["init"]:
    record["files"] = sorted(str(p.relative_to(Path.cwd())) for p in Path.cwd().rglob("*") if p.is_file())
    record["index"] = Path("index.html").read_text()
with open(os.environ["DMR093_COMMAND_LOG"], "a") as stream:
    stream.write(json.dumps(record) + "\n")
if name == "gh":
    if args == ["api", "repos/Exios66/mailroom-corpus-eda", "--jq", ".ssh_url"]:
        print("git@github.com:Exios66/Mailroom-Corpus-EDA.git")
        sys.exit(0)
    sys.exit(91)
if os.environ.get("DMR093_SYNC_FAKE"):
    sys.exit(1)
if args[:1] == ["push"]:
    sys.exit(92)
sys.exit(0)
'''
        for name in ("git", "gh"):
            command = self.bin / name
            command.write_text(fake)
            command.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin), DMR093_COMMAND_LOG=str(self.log),
                        PYTHONDONTWRITEBYTECODE="1")

    def cli(self, script, *arguments, sync=False):
        env = dict(self.env)
        if sync:
            env["DMR093_SYNC_FAKE"] = "1"
        return subprocess.run([sys.executable, str(script), *arguments], cwd=self.temp,
                              env=env, capture_output=True, text=True, timeout=30)

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []


class TestSyncSelection(OfflineCLI):
    def test_offline_all_uses_real_manifest_without_fetch_or_cursor_writes(self):
        manifest_path = ROOT / "scripts/packages_sync.json"
        before = manifest_path.read_bytes()
        entries = json.loads(before)["packages"]
        result = self.cli(ROOT / "scripts/sync_packages.py", "status", "--all", "--no-fetch", "--json", sync=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertCountEqual([row["package"] for row in rows], CORE)
        for row in rows:
            name = row["package"]
            self.assertEqual(row["prefix"], f"packages/{name}")
            self.assertEqual(row["synced_sha"], entries[name]["synced_sha"])
            self.assertEqual(row["synced_at"], entries[name]["synced_at"])
            self.assertEqual(row["upstream"], entries[name]["url"])
            self.assertEqual(row["upstream_head"], "unreachable")
            self.assertIsNone(row["new_upstream_commits"])
            self.assertFalse(row["up_to_date"])
        self.assertEqual(manifest_path.read_bytes(), before)
        self.assertTrue(self.commands())
        for command in self.commands():
            self.assertEqual(command["tool"], "git")
            self.assertEqual(command["args"][:3], ["rev-parse", "--verify", "--quiet"])

    def test_archived_and_unknown_packages_reject_before_external_calls_or_writes(self):
        manifest_path = ROOT / "scripts/packages_sync.json"
        before = manifest_path.read_bytes()
        for name in (*ARCHIVED, "not-a-package"):
            for operation in ("status", "snapshot"):
                with self.subTest(package=name, operation=operation):
                    self.log.unlink(missing_ok=True)
                    result = self.cli(ROOT / "scripts/sync_packages.py", operation,
                                      "--package", name, "--json", sync=True)
                    self.assertEqual(result.returncode, 4, result.stderr)
                    self.assertIn(f"unknown package {name!r}", result.stderr)
                    record = json.loads(result.stdout)
                    self.assertFalse(record["cursor_updated"])
                    self.assertEqual(record["error_class"], "git")
                    self.assertEqual(manifest_path.read_bytes(), before)
                    self.assertFalse(Path(str(manifest_path) + ".tmp").exists())
                    self.assertEqual(self.commands(), [])


class TestPagesSelection(OfflineCLI):
    def setUp(self):
        super().setUp()
        scripts = self.temp / "scripts"
        scripts.mkdir()
        self.script = scripts / "deploy_gh_pages.py"
        shutil.copy2(ROOT / "scripts/deploy_gh_pages.py", self.script)
        self.reports = self.temp / "packages/mailroom-corpus-eda/reports"

    def fixture(self):
        self.reports.mkdir(parents=True)
        (self.reports / "summary.md").write_text("Core report fixture\n")

    def test_all_builds_only_core_reports_without_deploying(self):
        self.fixture()
        result = self.cli(self.script, "--all", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        builds = [call for call in self.commands() if call["tool"] == "git" and call["args"][:1] == ["init"]]
        self.assertEqual(len(builds), 1)
        self.assertEqual(builds[0]["files"], [".nojekyll", "index.html", "summary.md"])
        self.assertIn('<a href="summary.md">summary.md</a>', builds[0]["index"])
        self.assertIn("Mailroom Corpus EDA", builds[0]["index"])
        self.assertIn("https://exios66.github.io/mailroom-corpus-eda/", result.stdout)
        for call in self.commands():
            self.assertNotIn("push", call["args"])
            if call["tool"] == "gh":
                self.assertEqual(call["args"], ["api", "repos/Exios66/mailroom-corpus-eda", "--jq", ".ssh_url"])
        for name in ARCHIVED:
            self.assertNotIn(name, result.stdout)
            self.assertFalse((self.temp / "packages" / name).exists())
        self.assertEqual((self.reports / "summary.md").read_text(), "Core report fixture\n")
        self.assertFalse((self.reports / "index.html").exists())

    def test_archived_and_unknown_targets_fail_before_build_or_external_calls(self):
        for name in (*ARCHIVED, "not-a-package"):
            with self.subTest(package=name):
                self.log.unlink(missing_ok=True)
                result = self.cli(self.script, "--all", "--package", name, "--dry-run")
                self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
                self.assertIn("invalid choice", result.stderr)
                self.assertEqual(self.commands(), [])
                self.assertFalse((self.temp / "packages").exists())

    def test_missing_core_reports_is_failure_instead_of_successful_skip(self):
        result = self.cli(self.script, "--package", "mailroom-corpus-eda", "--dry-run")
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn("ERROR", result.stdout)
        self.assertNotIn("Done. URLs:", result.stdout)
        self.assertEqual(self.commands(), [])
        self.assertFalse((self.temp / "packages").exists())

    def test_url_list_contains_only_core_and_never_builds(self):
        result = self.cli(self.script, "--list-urls")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "Mailroom Corpus EDA: https://exios66.github.io/mailroom-corpus-eda/")
        self.assertEqual(self.commands(), [])
        self.assertFalse((self.temp / "packages").exists())


if __name__ == "__main__":
    unittest.main()
