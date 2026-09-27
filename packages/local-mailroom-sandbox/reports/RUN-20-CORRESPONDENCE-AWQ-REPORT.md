# Run report — `run-20-correspondence-awq`

First specialist extraction run with the SAND-019 scoring fixes in place, so
this is the first report whose headline accuracy reflects the *model*, not a
ground-truth/scorer artifact.

| | |
|---|---|
| run_id | `run-20-correspondence-awq` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local, pinned) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1x L4 |
| context / quant | `max_model_len=32768`, AWQ, gpu_util=0.90, max_num_seqs=256 |
| profile / provider | `modal-vllm` / `vllm` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `46a4d3c2`, seed 42 |
| draw | 20 correspondence docs (seeded class bucket) |
| timestamp | `2026-09-25T13:27:47.586681+00:00` |
| git | `7410a0b` (dirty=True) |
| spec_hash | `e809da8c473ed9d66053105699546dbdf7c7ecbd6d653c25f998ba45b7199923` |

## Headline results

| metric | value |
|---|---|
| docs ok / total | **20 / 20** (`error_count=0`) |
| **overall_extraction_score** | **0.08934** |
| exact_match | 0.08934 |
| offline_fallback rows | 0 |

## Serving / cost metrics

| metric | value |
|---|---|
| wall (busy interval) | 253.692 s |
| concurrency | 5 |
| cold boot (measured) | 260.348 s |
| gpu_seconds | 514.04 s (wall + cold boot) |
| estimated GPU cost | **$0.114231** |
| cost per document | $0.00571155 |
| latency e2e / p50 / max | 61.400907 / 23.29779 / 187.642898 s |
| prompt / completion / total tokens | 39058 / 3424 / 42482 |
| cost cap | $0.35 (config) -> under cap |

**Concurrency proof (not serial):**
- sum(per-doc latency) = 1228.0 s
- wall = 253.692 s -> speedup 4.84x at concurrency 5
- serial would show wall ~= sum(latency); observed wall is the batched value.

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | latency s | prompt tok | compl tok | error |
|---|---|---|---|---|---|---|---|---|
| 1 | `DOC-2b5939247214be02` | demand | 0.0218 | 0.0 | 184.5 | 1890 | 173 | None |
| 2 | `DOC-b8d0988b09eefe09` | notice | 0.0478 | 0.0 | 173.7 | 1804 | 180 | None |
| 3 | `DOC-7d05b5b564199628` | notice | 0.0909 | 0.0952 | 180.3 | 1704 | 122 | None |
| 4 | `DOC-edc1649f20e66169` | letter | 0.059 | 0.0 | 177.2 | 1964 | 140 | None |
| 5 | `DOC-2116c1f1706dced1` | email | 0.0917 | 0.0 | 187.6 | 1714 | 127 | None |
| 6 | `DOC-a4a29801ed53a8b1` | press_release | 0.1144 | 0.0833 | 17.4 | 1856 | 142 | None |
| 7 | `DOC-0fb811b124432763` | email | 0.1191 | 0.0769 | 19.8 | 2416 | 234 | None |
| 8 | `DOC-81dde8f2cd0e6c5b` | email | 0.1192 | 0.0769 | 24.6 | 2148 | 327 | None |
| 9 | `DOC-38a7cb4be93dbecd` | notice | 0.2121 | 0.1538 | 25.9 | 2090 | 228 | None |
| 10 | `DOC-f1db54435294f184` | email | 0.0 | 0.0 | 23.2 | 1660 | 10 | None |
| 11 | `DOC-27306248d00b66c2` | press_release | 0.1295 | 0.0869 | 22.8 | 1702 | 124 | None |
| 12 | `DOC-3ab61766974251fd` | demand | 0.0364 | 0.0 | 21.3 | 2137 | 176 | None |
| 13 | `DOC-5c54a5baef4b9f06` | email | 0.0348 | 0.0 | 16.7 | 1714 | 130 | None |
| 14 | `DOC-9ba1246dd99b264d` | notice | 0.0364 | 0.0 | 16.0 | 2184 | 198 | None |
| 15 | `DOC-56a2f3a613f97dee` | meeting_request | 0.1917 | 0.0769 | 20.4 | 1847 | 208 | None |
| 16 | `DOC-59f834ec3e6a34c0` | press_release | 0.1582 | 0.0741 | 22.6 | 2575 | 208 | None |
| 17 | `DOC-0e928cc6feb45aa1` | email | 0.1169 | 0.08 | 23.4 | 1827 | 211 | None |
| 18 | `DOC-3936c819036c3b03` | letter | 0.0973 | 0.0 | 24.3 | 1786 | 172 | None |
| 19 | `DOC-816e7205bde414f2` | email | 0.0218 | 0.0 | 24.0 | 2163 | 181 | None |
| 20 | `DOC-25e99e5e72fe5b90` | email | 0.0878 | 0.0 | 22.3 | 1877 | 133 | None |

- scored rows: 20/20; min=0.0 max=0.2121 mean=0.0893

## Context: the two SAND-019 fixes this run validates

1. **Hub GT column alias.** The Hub `ground_truth` config stores field labels
   in `gt_fields` (JSON string); `corpus.normalize_rows` read only
   `expected_fields`, so every corpus row carried `{}` GT. Fixed to fall back
   to `gt_fields`; `sandbox datasets pull` now yields 3,302/3,302 populated
   rows (this draw: 20/20).
2. **Nested suite aggregate.** Suites return a flat dict with the real score at
   `result['extraction'].overall_score`; `eval.scoring.score_extraction_row`
   now reads it. Before this fix the same predictions produced
   `overall_extraction_score = null` and run-level 0.0.

## Caveats

- ~~`scipy` absent -> greedy entity matching~~ **Resolved (SAND-019):**
  `scipy>=1.11` is now a base dependency (alongside numpy/pandas), so
  entity-list matching is **optimal** (`scipy.optimize.linear_sum_assignment`)
  and the `bipartite_matching_failed` greedy fallback no longer fires. Re-scoring
  this same draw with scipy present reproduces 0.0893 to 4 dp (the draw has
  mostly single-item entity lists), so the fix removes the caveat without
  inflating the score.
- Metric is the dojo suite mean over per-field scores; correspondence GT has
  ~18 keys/doc, many empty for non-insurance rows (empty GT = not a
  requirement). 0.089 is a genuine small-model extraction score, not a ceiling.
- Re-run at concurrency 8 (same draw) logged in
  [`RUN-20-CORRESPONDENCE-AWQ-C8-REPORT.md`](RUN-20-CORRESPONDENCE-AWQ-C8-REPORT.md).

