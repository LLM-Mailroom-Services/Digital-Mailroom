# Run report — `sand032-l2-marlin`

SAND-032 Modal × vLLM specialist extract: **20 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-l2-marlin` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=6 |
| engine flags | prefix_caching=on, enforce_eager=on, kv_cache_dtype=`auto`, thinking=off, cudagraph sizes=—, max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 20 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `0ec3314ab111` |
| git | `67e7be3 (dirty)` |
| spec_hash | `0549944efb2ab93a4932a3189433640490cde04a7cfdb8c630dcc6f99c17309a` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **20 / 20** (errors 0) |
| **overall_extraction_score** | **0.2674** (sd 0.2215, min 0.0000, max 0.7843) |
| schema_valid_rate | 0.900 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 26.439 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 119.7 s |
| preflight probe (engine answering) | 116.974 s |
| latency p50 / p95 / max | 8.06 / 12.74 / 14.27 s |
| prompt / completion tokens | 37212 / 3131 |
| throughput | 1525.9 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.005875 |
| **$ per doc (busy)** | **0.000294** |
| fleet window deploy→stop (upper est.) | 171 s → 0.0381 USD |
| cost cap | $0.15 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546047.99`: requests Δ 20 (cumulative 20), measured TTFT mean 2.654 s (vLLM histogram, cumulative), prefix-cache hit 58.8%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 173.9 s over wall 26.4 s = **6.58×** effective parallelism at c8 (82% of the ideal 8×).
- **Tail:** slowest doc `DOC-a318b50872273528` (email) 14.3 s = 54% of wall — p95/p50 = 1.58×.
- **Prompt length vs latency:** Pearson r = 0.65 across 20 docs (prefill-bound).
- **Decode budget:** mean completion 157 tok/doc, mean prompt 1861 tok/doc.
- **Subclass spread:** best `notice` 0.551 (n=2), worst `letter` 0.089 (n=1).
- **Field-level extraction:** 13/20 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 120 s (driver stamps); preflight probe measured 117.0 s once the engine answered.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-l2-marlin-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-l2-marlin-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 11 | 0.2229 |
| memo | 5 | 0.3077 |
| notice | 2 | 0.5513 |
| press_release | 1 | 0.1667 |
| letter | 1 | 0.0889 |
| **total** | **20** | **0.2674** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✗ | 7.0 | 1698 | 109 |  |
| 2 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 7.0 | 1685 | 115 |  |
| 3 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 7.4 | 1707 | 120 |  |
| 4 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 8.0 | 1779 | 134 |  |
| 5 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 10.3 | 2025 | 199 |  |
| 6 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 12.7 | 2075 | 269 |  |
| 7 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 12.7 | 1996 | 160 |  |
| 8 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 6.2 | 1739 | 154 |  |
| 9 | `DOC-c4debd478f2c06e0` | email | 0.3156 | 0.0000 | ✓ | 6.5 | 1936 | 143 |  |
| 10 | `DOC-a318b50872273528` | email | 0.1167 | 0.0000 | ✓ | 14.3 | 2028 | 178 |  |
| 11 | `DOC-16dfd03aed14e557` | email | 0.0000 | 0.0000 | ✓ | 5.8 | 1674 | 76 |  |
| 12 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 9.3 | 1954 | 159 |  |
| 13 | `DOC-38265bcc6ecfecc3` | email | 0.1111 | 0.0000 | ✓ | 10.6 | 1729 | 143 |  |
| 14 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 7.6 | 1976 | 183 |  |
| 15 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 7.2 | 1724 | 134 |  |
| 16 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1112 | ✓ | 8.9 | 1913 | 220 |  |
| 17 | `DOC-21460a9f6d7e6348` | memo | 0.7843 | 0.2354 | ✗ | 8.1 | 1806 | 151 |  |
| 18 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 5.5 | 1668 | 87 |  |
| 19 | `DOC-2cde0c6d0c70b02b` | memo | 0.0909 | 0.0000 | ✓ | 9.1 | 2206 | 227 |  |
| 20 | `DOC-5b63f9fe205d564b` | email | 0.5303 | 0.1250 | ✓ | 9.7 | 1894 | 170 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-l2-marlin.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-l2-marlin
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-l2-marlin.yaml` | run spec |
| `reports/serving/sand032-l2-marlin.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-l2-marlin/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-l2-marlin/` | offline Braintrust-shaped rows — disposed after this report is committed |
