# Pipeline floor run report — local-GPU full-pipeline runs (2026-11-02/03)

Two full LangGraph pipeline runs on the local sandbox lane, analyzed with the
floor-digest analytics (`build_floor_digest.py` → `floor_digest.json` →
`floor.template.html` node viewer). All numbers below are generated from run
artifacts (`items.jsonl`, `nodes.jsonl`, `spec.lock.json`, `dataset.jsonl`),
not hand-entered.

## Runs

| run | docs attempted | ok | shipped | held (human-review tray) | failed | prompt tok | completion tok |
|---|---|---|---|---|---|---|---|
| `pipeline-lmstudio-even100-shuf2` | 106 / 500 | 83 | 77 (73%) | 6 (6%) | 23 (22%) | 8.24M | 0.63M |
| `pipeline-lmstudio-mergers-only` | 10 / 10 | 10 | 10 (100%) | 0 | 0 | 10.72M | 0.50M |

- Corpus: HF `mailroom-dataset`, 100 docs × 5 classes drawn (20% of the
  3,211-doc pool), shuffled (seed 20261102) so intake order is class-blind.
- Engine: LM Studio `qwen3.5-9b` served OpenAI-compatible on localhost,
  concurrency 4, JSON mode off, thinking off. $0 local lane; the `cost_cap_usd`
  is GPU-seconds *pricing*, not spend — a known estimator pitfall on local lanes.

## Headline findings (viewer-reproducible, class-isolate → node-select)

1. **Merger failure mode (shuf2): 18/18 attempted merger docs failed pre-archive.**
   Isolate `merger_agreement` and select `classify`: its only live out-edges are
   `→retry_classify` and `→human_review`; `classify→extract` carries **zero**
   merger traffic. Long chunked contracts blow the 1h per-doc `_bounded`
   deadline plus the output-token clamp; the failures land as `aborted`, not
   pipeline verdicts.
2. **The same class succeeds 10/10 when run alone** (mergers-only, after the
   vendor `handoff_context` hotfix): every merger shipped through the full
   fan (extract → judge_verify → arbiter → compile_report → catalog → archive).
   So the failure was capacity/pacing at concurrency 4, not doc class.
3. **Node traffic overall (shuf2):** intake 106 → classify 106 → extract ~88
   (11 gate-parked at class), judge_verify 40, arbiter 24 (partly re-ingestion
   inflation across attempts — see caveats), boss_escalation 34, tray 30.
   Eight of fourteen graph nodes call the LLM; a merger doc costs 20+ calls vs
   ~4–5 for correspondence.

## Caveats (stated up front, as the viewer shows them)

- shuf2 stopped at 106/500 by a bogus local cost-cap, not data.
- Same 500 docs were reprocessed across three locked attempts without wiping
  `mailroom.db`, so arbiter/boss counts include same-doc re-ingestion conflict
  traffic, not only fresh-mail arbitration.
- attempt-1 (disk-I/O era) has no archived `dataset.jsonl`; its per-class counts
  are `n/?` in the viewer — honest gap, not a zero.

## Reproduce

```
python reports/dashboard/selftest_floor_digest.py           # 20/20 gate
MAILROOM_BASE_DIR=/path/to/sandbox-data python reports/dashboard/build_floor_digest.py
# open floor.template.html beside floor_digest.js (rebuild emits both)
```

Spec: `specs/floor-digest.md` (sandbox repo). Topology is parsed from
`vendor/llm-mailroom/src/graph/build_graph.py` — no hand-drawn graph.
