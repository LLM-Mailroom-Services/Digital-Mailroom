# Modal (sandbox-vllm) — completed job reports

Committed companion to the sandbox-local `reports/experiment_log.jsonl`
(gitignored). Each row below is the FINAL record for a completed Modal
job; every numeric field is read straight from the experiment log, not
hand-transcribed. Engine: `Qwen/Qwen3-8B` bf16 or `Qwen/Qwen3-8B-AWQ` on
1x L4 ($0.80/hr) — except the two `*-correspondence-specialist-awq` rows,
which ran on 2x L4 data-parallel (cost = measured warm interval x 2 x L4
rate). Cost = measured warm interval x L4 rate.

| run_id | task | model | n | headline | errors | wall s | conc | cold boot s | gpu s | cost $ | $/doc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| run-20-insurance-claims-specialist-awq | insurance_claims_specialist | Qwen/Qwen3-8B-AWQ | 20 | overall=0.671435 (exact=0.671435) | 0 | 422.152 | 8 | 0.361 | 422.513 | 0.093892 | 0.0046946 |
| run-20-correspondence-specialist-awq | correspondence_specialist | Qwen/Qwen3-8B-AWQ | 20 | overall=0.22799 (exact=0.22799) | 0 | 75.084 | 8 | 0.553 | 151.274 | 0.033616 | 0.0016808 |
| run-50-correspondence-specialist-awq | correspondence_specialist | Qwen/Qwen3-8B-AWQ | 50 | overall=0.254748 (exact=0.254748) | 0 | 280.099 | 8 | 0.503 | 561.204 | 0.124712 | 0.00249424 |
| run-20-contracts-specialist | contracts_specialist | Qwen/Qwen3-8B | 20 | overall=0.0 (exact=0.0) | 14 | None | None | 178.255 | None | None | None |
| run-20-contracts-awq | contracts_specialist | Qwen/Qwen3-8B-AWQ | 20 | overall=0.0 (exact=0.0) | 2 | 1030.43 | 4 | 251.419 | 1281.849 | 0.284855 | 0.01424275 |
| run-20-correspondence-awq | correspondence_specialist | Qwen/Qwen3-8B-AWQ | 20 | overall=0.08934 (exact=0.08934) | 0 | 253.692 | 5 | 260.348 | 514.04 | 0.114231 | 0.00571155 |
| run-50-modal-hf | sorter | Qwen/Qwen3-8B | 50 | exact_match=0.98 | None | None | None | None | None | None | None |
| run-50-five-types | sorter_5type | Qwen/Qwen3-8B | 50 | exact_match=0.0 | None | None | None | None | None | None | None |
| pilot-sorter-modal-hf | sorter | Qwen/Qwen3-8B | 7 | exact_match=1.0 | None | None | None | None | None | None | None |

## Per-run detail

### run-50-correspondence-specialist-awq

- timestamp: `2026-09-27T07:29:28.078828+00:00`
- task/model: `correspondence_specialist` / `Qwen/Qwen3-8B-AWQ` (profile `modal-vllm`, provider `vllm`, prompt `correspondence_specialist_production`)
- topology: 2×L4 data-parallel (MIN=MAX=2 pinned, same warm app as the 20-doc run)
- n=50 | scores={"exact_match": 0.254748, "n": 50, "offline_fallback": 0, "error_count": 0, "overall_extraction_score": 0.254748, "schema_valid_rate": 0.94}
- latency: e2e=28.555953s p50=27.26012s max=142.829407s
- tokens: prompt=111514 completion=9183 total=120697
- wall=280.099s concurrency=8 cold_boot=0.503s gpu=561.204s (2 replicas)
- cost=$0.124712 ($0.00249424/doc)
- git: `59b9d35` dirty=True
- full report: [`reports/SAND-32/correspondence/RUN-50-CORRESPONDENCE-SPECIALIST-AWQ-REPORT.md`](../SAND-32/correspondence/RUN-50-CORRESPONDENCE-SPECIALIST-AWQ-REPORT.md)

### run-20-correspondence-specialist-awq

- timestamp: `2026-09-27T07:21:48.455725+00:00` (canonical repeat; first attempt `2026-09-27T07:17:42.700175+00:00` scored 0.244565 @ 80.43s)
- task/model: `correspondence_specialist` / `Qwen/Qwen3-8B-AWQ` (profile `modal-vllm`, provider `vllm`, prompt `correspondence_specialist_production`)
- topology: 2×L4 data-parallel (MIN=MAX=2 pinned, one warm app shared with the 50-doc run)
- n=20 | scores={"exact_match": 0.22799, "n": 20, "offline_fallback": 0, "error_count": 0, "overall_extraction_score": 0.22799, "schema_valid_rate": 0.9}
- latency: e2e=25.168468s p50=26.595458s max=35.414844s
- tokens: prompt=49878 completion=3813 total=53691
- wall=75.084s concurrency=8 cold_boot=0.553s gpu=151.274s (2 replicas)
- cost=$0.033616 ($0.0016808/doc)
- git: `59b9d35` dirty=False
- full report: [`reports/SAND-32/correspondence/RUN-20-CORRESPONDENCE-SPECIALIST-AWQ-REPORT.md`](../SAND-32/correspondence/RUN-20-CORRESPONDENCE-SPECIALIST-AWQ-REPORT.md)

### run-20-insurance-claims-specialist-awq

- timestamp: `2026-09-27T06:45:06.707339+00:00`
- task/model: `insurance_claims_specialist` / `Qwen/Qwen3-8B-AWQ` (profile `modal-vllm`, provider `vllm`)
- n=20 | scores={"exact_match": 0.671435, "n": 20, "offline_fallback": 0, "error_count": 0, "overall_extraction_score": 0.671435, "schema_valid_rate": 0.25}
- latency: e2e=128.025659s p50=145.269082s max=184.188645s
- tokens: prompt=68687 completion=9731 total=78418
- wall=422.152s concurrency=8 cold_boot=0.361s gpu=422.513s
- cost=$0.093892 ($0.0046946/doc)
- git: `500eeee` dirty=True
- full report: [`reports/SAND-32/insurance/RUN-20-INSURANCE-CLAIMS-SPECIALIST-AWQ-REPORT.md`](../SAND-32/insurance/RUN-20-INSURANCE-CLAIMS-SPECIALIST-AWQ-REPORT.md)

### run-20-contracts-specialist

- timestamp: `2026-09-25T03:52:18.916867+00:00`
- task/model: `contracts_specialist` / `Qwen/Qwen3-8B` (profile `modal-vllm`, provider `vllm`)
- n=20 | scores={"exact_match": 0.0, "n": 20, "offline_fallback": 0, "error_count": 14, "overall_extraction_score": 0.0}
- latency: e2e=Nones p50=Nones max=Nones
- tokens: prompt=None completion=None total=None
- wall=Nones concurrency=None cold_boot=178.255s gpu=Nones
- cost=$None ($None/doc)
- git: `ea74ec8` dirty=True

### run-20-contracts-awq

- timestamp: `2026-09-25T12:28:34.924336+00:00`
- task/model: `contracts_specialist` / `Qwen/Qwen3-8B-AWQ` (profile `modal-vllm`, provider `vllm`)
- n=20 | scores={"exact_match": 0.0, "n": 20, "offline_fallback": 0, "error_count": 2, "overall_extraction_score": 0.0}
- latency: e2e=196.853416s p50=213.592771s max=282.68513s
- tokens: prompt=193819 completion=25519 total=219338
- wall=1030.43s concurrency=4 cold_boot=251.419s gpu=1281.849s
- cost=$0.284855 ($0.01424275/doc)
- git: `7410a0b` dirty=True

### run-20-correspondence-awq

- timestamp: `2026-09-25T13:27:47.586681+00:00`
- task/model: `correspondence_specialist` / `Qwen/Qwen3-8B-AWQ` (profile `modal-vllm`, provider `vllm`)
- n=20 | scores={"exact_match": 0.08934, "n": 20, "offline_fallback": 0, "error_count": 0, "overall_extraction_score": 0.08934}
- latency: e2e=61.400907s p50=23.29779s max=187.642898s
- tokens: prompt=39058 completion=3424 total=42482
- wall=253.692s concurrency=5 cold_boot=260.348s gpu=514.04s
- cost=$0.114231 ($0.00571155/doc)
- git: `7410a0b` dirty=True

### run-50-modal-hf

- timestamp: `2026-09-16T08:35:58.662689+00:00`
- task/model: `sorter` / `Qwen/Qwen3-8B` (profile `modal-vllm`, provider `vllm`)
- n=50 | scores={"exact_match": 0.98, "accuracy": 0.98, "exact_match_ci": {"lo": 0.94, "hi": 1.0, "half": 0.03, "n": 50, "seed": 42, "n_boot": 2000, "method": "percentile-bootstrap"}, "n": 50, "task": {"task": "docclass", "kind": "docclass", "doc_type_accuracy": 0.98, "accuracy": 0.98, "doc_type_accuracy_ci": {"lo": 0.94, "hi": 1.0, "half": 0.03, "n": 50, "seed": 42, "n_boot": 2000, "method": "percentile-bootstrap"}, "per_class": {"contract": {"n": 50, "correct": 49, "accuracy": 0.98, "precision": 1.0, "recall": 0.98, "f1": 0.9899, "f2": 0.9839}}, "precision_macro": 1.0, "recall_macro": 0.98, "f1_macro": 0.9899, "f2_macro": 0.9839, "precision": 1.0, "recall": 0.98, "f2": 0.9839, "n": 50}, "f1_macro": 0.9899, "precision_macro": 1.0, "recall_macro": 0.98, "f2_macro": 0.9839}
- latency: e2e=970.89436218s p50=Nones max=Nones
- tokens: prompt=None completion=None total=None
- wall=Nones concurrency=None cold_boot=Nones gpu=Nones
- cost=$None ($None/doc)
- git: `None` dirty=None

### run-50-five-types

- timestamp: `2026-09-17T03:13:29.257534+00:00`
- task/model: `sorter` / `Qwen/Qwen3-8B` (profile `modal-vllm`, provider `vllm`)
- n=50 | scores={"exact_match": 0.0, "accuracy": 0.0, "exact_match_ci": {"lo": 0.0, "hi": 0.0, "half": 0.0, "n": 50, "seed": 42, "n_boot": 2000, "method": "percentile-bootstrap"}, "n": 50, "task": {"task": "docclass", "kind": "docclass", "doc_type_accuracy": 0.0, "accuracy": 0.0, "doc_type_accuracy_ci": {"lo": 0.0, "hi": 0.0, "half": 0.0, "n": 50, "seed": 42, "n_boot": 2000, "method": "percentile-bootstrap"}, "per_class": {"contract": {"n": 10, "correct": 0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "f2": 0.0}, "corporate_record": {"n": 10, "correct": 0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "f2": 0.0}, "correspondence": {"n": 10, "correct": 0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "f2": 0.0}, "insurance_claim": {"n": 10, "correct": 0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "f2": 0.0}, "merger_agreement": {"n": 10, "correct": 0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "f2": 0.0}}, "precision_macro": 0.0, "recall_macro": 0.0, "f1_macro": 0.0, "f2_macro": 0.0, "precision": 0.0, "recall": 0.0, "f2": 0.0, "n": 50}, "task_source": "sorter-suite", "f1_macro": 0.0, "precision_macro": 0.0, "recall_macro": 0.0, "f2_macro": 0.0}
- latency: e2e=0.42049192s p50=Nones max=Nones
- tokens: prompt=None completion=None total=None
- wall=Nones concurrency=None cold_boot=Nones gpu=Nones
- cost=$None ($None/doc)
- git: `None` dirty=None

### pilot-sorter-modal-hf

- timestamp: `2026-09-16T06:19:02.215844+00:00`
- task/model: `sorter` / `Qwen/Qwen3-8B` (profile `modal-vllm`, provider `vllm`)
- n=7 | scores={"exact_match": 1.0, "accuracy": 1.0, "exact_match_ci": {"lo": 1.0, "hi": 1.0, "half": 0.0, "n": 7, "seed": 42, "n_boot": 2000, "method": "percentile-bootstrap"}, "n": 7, "task": {"task": "docclass", "kind": "docclass", "doc_type_accuracy": 1.0, "accuracy": 1.0, "doc_type_accuracy_ci": {"lo": 1.0, "hi": 1.0, "half": 0.0, "n": 7, "seed": 42, "n_boot": 2000, "method": "percentile-bootstrap"}, "per_class": {"contract": {"n": 1, "correct": 1, "accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "f2": 1.0}, "corporate_record": {"n": 1, "correct": 1, "accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "f2": 1.0}, "correspondence": {"n": 1, "correct": 1, "accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "f2": 1.0}, "insurance_claim": {"n": 3, "correct": 3, "accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "f2": 1.0}, "merger_agreement": {"n": 1, "correct": 1, "accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "f2": 1.0}}, "precision_macro": 1.0, "recall_macro": 1.0, "f1_macro": 1.0, "f2_macro": 1.0, "precision": 1.0, "recall": 1.0, "f2": 1.0, "n": 7}, "f1_macro": 1.0, "precision_macro": 1.0, "recall_macro": 1.0, "f2_macro": 1.0}
- latency: e2e=82.98670842857142s p50=Nones max=Nones
- tokens: prompt=None completion=None total=None
- wall=Nones concurrency=None cold_boot=Nones gpu=Nones
- cost=$None ($None/doc)
- git: `None` dirty=None

## SAND-019 defects fixed (why pre-fix rows read 0.0)

Two independent harness defects made every specialist extraction score `0.0`
regardless of model quality. Both are fixed in this commit:

1. **Ground truth never loaded from the Hub.** The pinned HF `ground_truth`
   config stores field labels in a column named **`gt_fields`** (a JSON string).
   `corpus.normalize_rows` read only `expected_fields`, which does not exist on
   the Hub config, so all 3,302 corpus rows were normalized with
   `expected_fields = {}`. With no ground truth the suite returns
   `overall_score = null` and the run-level `exact_match` collapses to 0.0.
   Fix: `normalize_rows` now falls back to `gt_fields`
   (`src/mailroom_sandbox/corpus.py`). `sandbox datasets pull` re-materializes
   all 3,302 rows with populated GT (verified: 3,302/3,302 non-empty;
   correspondence = 18 GT fields/doc). Pinned by
   `tests/test_corpus.py::test_normalize_rows_maps_hub_gt_fields`.

2. **Suite aggregate not read.** Mailroom suites return a *flat dict* whose real
   aggregate is nested at `result["extraction"].overall_score` (an
   `ExtractionScoreResult`). `eval.scoring.score_extraction_row` only looked at
   top-level `overall_score` / `extraction_overall_score`, so even with GT
   present the headline score stayed null while `extraction_f1` was computed.
   Fix: resolve the nested aggregate (`src/mailroom_sandbox/eval/scoring.py`).
   Pinned by
   `tests/test_eval.py::test_score_extraction_row_reads_nested_suite_overall`.

**Consequence for the table above:** `run-20-contracts-specialist` (bf16) and
`run-20-contracts-awq` both predate these fixes, so their `overall=0.0` is an
artifact of missing GT + unread aggregate, not a measured extraction failure.
Their error counts (14 and 2) and serving metrics are still valid.
`run-20-correspondence-awq` is the first run with both fixes and yields a real
score (`overall_extraction_score = 0.08934`, 20/20 ok, 0 errors).

### Concurrency is honored (not serial)

The 20-correspondence AWQ record proves the isolated specialist path batches:
`sum(per-doc latency) = 1228.0 s` vs `wall_seconds = 253.7 s` -> **4.84x**
speedup at `concurrency = 5`. A serial path would show wall ~= sum(latency).
Code: `eval.runners._run_rows_bounded` drives a `ThreadPoolExecutor` with
`workers = min(concurrency, len(rows))`; the serial shortcut fires only when
`workers <= 1`. `gpu_seconds = wall + cold_boot` (253.7 + 260.3 = 514.0).

### Caveat: scipy greedy fallback

The vendored dojo scorer soft-imports `scipy.optimize.linear_sum_assignment`
for optimal entity-list matching; `scipy` is not installed in the sandbox venv,
so entity-list scoring logs `bipartite_matching_failed` and falls back to
greedy. This is loud but silent in the score. A `scoring` extra (or declaring
`scipy`) would make entity F1 optimal instead of greedy.
