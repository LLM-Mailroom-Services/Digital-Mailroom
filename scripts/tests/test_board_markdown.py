"""Keep the open-card table renderable as GitHub-flavored Markdown."""

import re
import unittest
from pathlib import Path


BOARD = Path(__file__).resolve().parents[2] / "governance" / "TASKS.md"


def cells(line):
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip()[1:-1])]


class TestOpenBoardMarkdown(unittest.TestCase):
    def test_open_cards_table_is_rectangular(self):
        section = BOARD.read_text(encoding="utf-8").split("## Open cards\n", 1)[1]
        table = [line for line in section.split("\n## ", 1)[0].splitlines() if line.startswith("|")]
        self.assertGreater(len(table), 2)
        header, delimiter, *rows = map(cells, table)
        self.assertEqual(header, ["Card", "Status", "Task", "Owner", "Issue", "Evidence"])
        self.assertEqual(len(delimiter), len(header), "delimiter must match the header width")
        self.assertTrue(all(re.fullmatch(r":?-{3,}:?", cell) for cell in delimiter))
        for row in rows:
            with self.subTest(card=row[0]):
                self.assertEqual(len(row), len(header), "card row must match the header width")


if __name__ == "__main__":
    unittest.main()
