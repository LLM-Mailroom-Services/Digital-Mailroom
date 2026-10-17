#!/usr/bin/env python3
"""Re-score a finished run's items.jsonl with the current sandbox scorer (no LLM calls).

Usage:
    rescore.py <run_id> [--dry-run] [--force]

Keeps the prior score under ``score_original`` so the methodology change is auditable;
items.jsonl lives in gitignored data/runtime/runs/.

Rescoring needs only what the run already persists — ``items.jsonl`` (the raw ``pred``
payload) and ``dataset.jsonl`` (the ground truth, whose sha256 the spec lock pins). So a
finished run can be re-scored, or scored under a DIFFERENT metric, with no model call,
no Hub fetch and no network.

Safety: this REWRITES ``items.jsonl``. Never point it at a run that is still writing —
use ``--dry-run`` to compute and compare without touching the file. A live run (its
checkpoint says ``running``, or a runner process exists) is refused unless ``--force``.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import mailroom_sandbox  # noqa: E402,F401  (puts vendored trees on sys.path)
from mailroom_sandbox.eval.agents import _score_class  # noqa: E402
from mailroom_sandbox.eval.scoring import score_extraction_row  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
FLAGS = {a for a in sys.argv[1:] if a.startswith("--")}
DRY = "--dry-run" in FLAGS
FORCE = "--force" in FLAGS
if not args:
    raise SystemExit(__doc__)

rid = args[0]
run = ROOT / "data" / "runtime" / "runs" / rid
items_path = run / "items.jsonl"


def _is_live() -> str | None:
    """Why this run must not be rewritten, or None if it is safe."""
    try:
        state = json.loads((run / "checkpoint.json").read_text()).get("state")
    except (OSError, ValueError):
        state = None
    if state == "running":
        return "its checkpoint says 'running'"
    proc = subprocess.run(["pgrep", "-f", "sandbox run|sand42-cell"], capture_output=True, text=True)
    if proc.stdout.strip():
        return "a runner process is alive"
    return None


live = _is_live()
if live and not FORCE and not DRY:
    raise SystemExit(
        f"refusing to rewrite {items_path}: {live}.\n"
        f"Re-run with --dry-run to compute without writing, or --force if you are sure."
    )
if live:
    print(f"note: {live} — running in {'dry-run' if DRY else 'FORCED write'} mode", file=sys.stderr)

rows = {json.loads(l)["id"]: json.loads(l) for l in (run / "dataset.jsonl").open() if l.strip()}
items = [json.loads(l) for l in items_path.open() if l.strip()]

changed = same = 0
for it in items:
    if not it.get("ok") or not isinstance(it.get("pred"), dict):
        continue
    row = rows.get(it["item_id"])
    if not row:
        continue
    if "sorter" in rid:  # isolated sorter: doc-class match (parses legacy tuple strings)
        fresh = _score_class(row, it["pred"])
    else:
        pred = {k: v for k, v in it["pred"].items() if k != "reasoning"}
        fresh = score_extraction_row(row["expected_doc_class"], pred, row["expected_fields"],
                                     doc_text=row.get("doc_text"))
    old = it.get("score") or {}
    keys = [k for k in fresh
            if k in old and isinstance(fresh[k], (int, float)) and isinstance(old[k], (int, float))]
    if keys and all(abs(fresh[k] - old[k]) < 1e-12 for k in keys):
        same += 1
    else:
        changed += 1
    if not DRY:
        it.setdefault("score_original", it.get("score"))
        it["score"] = fresh

if not DRY:
    items_path.write_text(
        "".join(json.dumps(i, default=lambda o: getattr(o, "__dict__", str(o))) + "\n" for i in items)
    )

ok = [i for i in items if i.get("ok")]
acc = [i["score"].get("match", i["score"].get("overall_extraction_score")) for i in ok]
acc = [a for a in acc if isinstance(a, (int, float))]
verdict = "reproduced" if changed == 0 else f"{changed} changed"
print(f"{rid}: {'dry-run, ' if DRY else ''}rescored {len(ok)} ok items "
      f"({same} {verdict}); mean overall {sum(acc) / len(acc):.4f}" if acc else f"{rid}: no scores")
