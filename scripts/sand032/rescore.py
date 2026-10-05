#!/usr/bin/env python3
"""Re-score a finished run's items.jsonl with the current sandbox scorer (no LLM calls).

Usage: rescore.py <run_id>. Keeps the prior score under ``score_original`` so the
methodology change is auditable; items.jsonl lives in gitignored data/runtime/runs/.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import mailroom_sandbox  # noqa: E402,F401  (puts vendored trees on sys.path)
from mailroom_sandbox.eval.agents import _score_class  # noqa: E402
from mailroom_sandbox.eval.scoring import score_extraction_row  # noqa: E402

rid = sys.argv[1]
run = ROOT / "data/runtime/runs" / rid
rows = {json.loads(l)["id"]: json.loads(l) for l in (run / "dataset.jsonl").open()}
items = [json.loads(l) for l in (run / "items.jsonl").open()]
for it in items:
    if not it.get("ok") or not isinstance(it.get("pred"), dict):
        continue
    row = rows[it["item_id"]]
    it.setdefault("score_original", it.get("score"))
    if "sorter" in rid:  # isolated sorter: doc-class match (parses legacy tuple strings)
        it["score"] = _score_class(row, it["pred"])
        continue
    pred = {k: v for k, v in it["pred"].items() if k != "reasoning"}
    it["score"] = score_extraction_row(row["expected_doc_class"], pred, row["expected_fields"],
                                       doc_text=row.get("doc_text"))
(run / "items.jsonl").write_text("".join(json.dumps(i, default=lambda o: getattr(o, "__dict__", str(o))) + "\n" for i in items))
ok = [i for i in items if i.get("ok")]
acc = [i["score"].get("match", i["score"].get("overall_extraction_score")) for i in ok]
acc = [a for a in acc if isinstance(a, (int, float))]
print(f"{rid}: rescored {len(ok)} ok items; mean overall {sum(acc)/len(acc):.4f}" if acc else f"{rid}: no scores")
