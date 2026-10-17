"""Generate ``config/prompts/merger_agreement_specialist_maud_v2.txt`` (SAND-042 RCA).

``maud_v2`` = ``maud_v1`` with three fixes:

1. The answer catalog is rendered from the dojo's ``maud_schema`` (the same
   ``MAUD_ANSWER_CLASSES`` the scorer folds against), so prompt and scorer
   cannot drift.
2. The subclass brief no longer asks for free text ("exchange ratio",
   "election mechanics") inside ``maud_clauses`` — every entry must be
   ``'<Question>: <allowed answer>'``.
3. A chunk duty: merger agreements run as ~8 sequential chunks, and v1's
   "answer every question the text addresses" pushed preamble chunks into
   guesses the merge then kept.

    python scripts/gen_maud_v2_prompt.py          # write
    python scripts/gen_maud_v2_prompt.py --check  # fail if stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "vendor" / "llm-dojo-scoring" / "src"))

from llm_dojo_scoring.maud_schema import render_maud_question_block  # noqa: E402

V1 = REPO / "config" / "prompts" / "merger_agreement_specialist_maud_v1.txt"
V2 = REPO / "config" / "prompts" / "merger_agreement_specialist_maud_v2.txt"

_BRIEF_FIXES = {
    "exchange ratio / stock consideration language in maud_clauses":
        "exchange ratio / stock consideration language belongs in subject_matter or keywords, never in maud_clauses",
    "per-share cash and stock mix in maud_clauses":
        "per-share cash and stock mix belongs in subject_matter or keywords, never in maud_clauses",
    "election mechanics;":
        "election mechanics (subject_matter / keywords only);",
    "- Answer every question on the list that the visible text addresses; a question the text addresses must not be omitted.\n":
        "",
    "- Omit a question only when the visible (possibly truncated) text does not address it. Never write \"not specified\".\n":
        "- Omit a question when its operative clause is not visible in THIS text (you may be shown one chunk of the agreement). Never guess; never write \"not specified\".\n",
    "MAUD answering rules (v1):":
        "MAUD answering rules (v2):",
    "maud_clauses (string[]): answered LegalBench MAUD questions as '<Question>: <Answer>'.":
        "maud_clauses (string[]): answered LegalBench MAUD questions as '<Question>: <Answer>' — one entry per question, nothing else.",
}


def build() -> str:
    text = V1.read_text(encoding="utf-8")
    for old, new in _BRIEF_FIXES.items():
        if old not in text:
            raise SystemExit(f"maud_v1 anchor missing: {old[:60]!r}")
        text = text.replace(old, new)
    head, sep, rules = text.partition("MAUD question names")
    if not sep:
        raise SystemExit("maud_v1 has no 'MAUD question names' section")
    rules = rules[rules.index("MAUD answering rules (v2):"):]
    block = render_maud_question_block(shape="lines", chunked=True)
    return head.rstrip() + "\n\n" + block.rstrip() + "\n\n" + rules.rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    out = build()
    if args.check:
        if not V2.exists() or V2.read_text(encoding="utf-8") != out:
            print(f"{V2.name} is stale — run scripts/gen_maud_v2_prompt.py", file=sys.stderr)
            return 1
        return 0
    V2.write_text(out, encoding="utf-8")
    print(f"wrote {V2.relative_to(REPO)} ({len(out)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
