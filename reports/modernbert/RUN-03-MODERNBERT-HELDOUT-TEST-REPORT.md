# Held-out test report — ModernBERT run-3 (GPU eval harness)

Full-context evaluation export:
[`eval_run3_20260921.json`](./eval_run3_20260921.json) (copy of
`mailroom-ml/reports/eval_run3_20260921.json`). Checkpoint
`/checkpoints/runs/20260921-132753`, artifact sha
`56a4e8919cc3ae11d6bcfc13ec012677409afff99daf167cdd4fb70a6e1754f9`.

**Live run-3 SSH training (2026-09-27):** metrics below describe the **Sep 21
completed** checkpoint only. Replace this file after the live session finishes and
a new eval JSON is exported.

| | |
| --- | --- |
| n_docs | 323 |
| seed | 42 |
| sample | 0 (full test split) |
| model_kind | pytorch |
| windows evaluated | 504 (8,192-token context, 512 overlap) |

## Headline metrics

| metric | run-3 GPU harness | run-2 trainer test | Δ (run-3 − run-2) |
| --- | --- | --- | --- |
| doc_type accuracy | **0.8947** | 0.9319 | −0.0372 |
| subclass accuracy (conditional) | **0.526** | 0.5449 | −0.0189 |
| window ECE (calibrated) | **0.0203** | (not in run-2 export) | — |
| window band ECE | 0.0528 | — | — |

The harness reports **lower** doc_type accuracy than the trainer’s integrated test
(0.9288 on the same split). Treat the harness as the stricter, full-window
regression record; trainer test is still useful for epoch selection during training.

## Program gates (recorded, report-only)

| gate | threshold | actual | met |
| --- | --- | --- | --- |
| P0 doc_type | 0.95 | 0.8947 | no |
| P0 subclass | 0.75 | 0.526 | no |

## Per doc_type accuracy (from `per_stratum_confusion`)

| doc_type | correct | total | accuracy |
| --- | --- | --- | --- |
| insurance_claim | 114 | 114 | **1.000** |
| correspondence | 81 | 85 | **0.953** |
| merger_agreement | 17 | 17 | **1.000** |
| contract | 50 | 60 | **0.833** |
| corporate_record | 27 | 47 | **0.574** |

**Reading:** Errors concentrate in **corporate_record** (12 confused with
correspondence, 8 routed to `llm_overflow` for long/window policy) and **contract**
(7 with corporate_record, plus singleton confusions). Insurance and merger doc_types
are effectively solved at doc_type level on this split; the hard mass is structural
similarity between corporate records and correspondence/contract families.

## Window cohorts (#104)

| cohort | n_docs | doc_type accuracy | mean window agreement |
| --- | --- | --- | --- |
| single-window | 274 | **0.9124** | 1.0 |
| multi-window | 49 | **0.7959** | 0.7725 |

Multi-window documents drive most residual doc_type error: plurality merge and
cross-window disagreement punish long filings. Intake policy should assume LLM
fallback for low agreement or overflow paths regardless of point accuracy on
single-window mail.

## Selective risk (#104)

| field | value |
| --- | --- |
| recommended threshold | **0.93** |
| coverage at pick | **73.2%** of 504 windows (369 accepted at threshold 0.93, accuracy 0.9946) — corrected 2026-09-28; the JSON's top-level `coverage` 0.4325 is the 0.99 row (218 windows) |
| error budget | 2% |
| budget_met | **true** (Wilson lower bound on accuracy) |

Deployment interpretation: at threshold 0.93 the classifier can abstain on most of
the tail and still meet a 2% selective error budget on accepted windows — at 73.2%
coverage, **about a quarter of windows still flow to the LLM** unless thresholds are relaxed
(with measured risk tradeoff from the sweep in the JSON).

## Per-head calibrated ECE (fast-path exclusion)

| head | ECE | excluded (> 0.05) |
| --- | --- | --- |
| doc_type | 0.0228 | no |
| contract | 0.0443 | no |
| correspondence | 0.0713 | **yes** |
| insurance_claim | 0.0670 | **yes** |
| merger_agreement | 0.0655 | **yes** |
| corporate_record | 0.1346 | **yes** |

Even when doc_type is correct, **subclass fast-path** should not fire for excluded
heads; the LLM specialist remains source of truth for subclass on those doc_types.

## Comparison to LLM sorter (sandbox)

Offline fixture pair only (`data/fixtures/serving/sorter_vs_modernbert.json`):

```bash
sandbox eval sorter_vs_modernbert --mock
sandbox metrics compare --sorter-vs-modernbert
```

Live comparison requires a completed checkpoint and `sandbox modernbert eval` —
**wait until the SSH training session completes** before logging a new serving record.

## Next steps after live training

1. Point `MODERNBERT_MODEL_PATH` at the new checkpoint directory (`labels.json` present).
2. `uv run python training/eval_modernbert.py --checkpoint … --json --selective-risk`
   on the GPU host (same harness as this report).
3. `uv run python training/compare_runs.py --a reports/modernbert/eval_run3_20260921.json --b <new>.json`
   for paired bootstrap CIs on doc_type accuracy and window ECE.
