"""Suite-inventory contracts for the documentation corrected in DMR-085.

Treat documented commands as data, without executing shell text or running
package suites. Derive package coverage from the workspace, not a second
hand-maintained package list.

Run: python3 -m unittest discover -s scripts/tests -p 'test_testing_documentation.py' -v
"""

import re
import shlex
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def command_tokens(command):
    # The board command uses a subshell; pytest's -q only changes verbosity.
    lexer = shlex.shlex(command, posix=True, punctuation_chars="()")
    lexer.whitespace_split = True
    tokens = list(lexer)
    if tokens[:1] == ["("] and tokens[-1:] == [")"]:
        tokens = tokens[1:-1]
    return tuple(token for token in tokens if token != "-q")


class TestDocumentedSuiteInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        testing = (REPO_ROOT / "docs" / "TESTING.md").read_text(encoding="utf-8")
        section = agents.split("Per-package test suites", 1)[1]
        block = re.search(r"```bash\n(.*?)```", section, re.DOTALL)
        if block is None:
            raise AssertionError("AGENTS.md is missing its suite command block")
        cls.agents_commands = [
            command_tokens(line) for line in block.group(1).splitlines() if line.strip()
        ]
        table = testing.split("## Per-package commands (measured)", 1)[1].split("\n## ", 1)[0]
        cls.testing_commands = [
            command_tokens(command)
            for command in re.findall(r"^\| [^|]+ \| `([^`]+)` \|", table, re.MULTILINE)
        ]

        workspace = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        cls.package_suites = []
        for pattern in workspace["tool"]["uv"]["workspace"]["members"]:
            for member in sorted(REPO_ROOT.glob(pattern)):
                suites = [path for path in (member / "tests", member / "src" / "tests") if path.is_dir()]
                if len(suites) != 1:
                    raise AssertionError(f"expected one test suite for workspace member {member}: {suites}")
                cls.package_suites.append(suites[0].relative_to(REPO_ROOT).as_posix())
        if not cls.package_suites:
            raise AssertionError("workspace contains no package test suites")

        cls.expected_commands = [
            ("uv", "run", "pytest", suite) for suite in cls.package_suites
        ] + [
            ("python3", "-m", "unittest", "discover", "scripts/tests"),
            ("cd", "board-site", "&&", "node", "tests/api.test.js"),
        ]

    def test_agents_lists_each_workspace_and_hub_suite_once(self):
        # In particular, dropping corpus-eda, scripts/tests, or board-site
        # reproduces the omissions repaired in PR #149. Duplicates also fail.
        self.assertCountEqual(self.agents_commands, self.expected_commands)

    def test_testing_table_lists_each_workspace_and_hub_suite_once(self):
        self.assertCountEqual(self.testing_commands, self.expected_commands)

    def test_documented_suite_targets_contain_tests(self):
        for suite in [*self.package_suites, "scripts/tests"]:
            with self.subTest(suite=suite):
                self.assertTrue(
                    any((REPO_ROOT / suite).rglob("test_*.py")),
                    f"documented suite {suite} contains no Python tests",
                )
        board_test = REPO_ROOT / "board-site" / "tests" / "api.test.js"
        self.assertTrue(board_test.is_file(), f"missing documented board test: {board_test}")
        self.assertGreater(board_test.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
