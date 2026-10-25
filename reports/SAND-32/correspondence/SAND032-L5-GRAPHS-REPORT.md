# Run report — `sand032-l5-graphs`

SAND-032 Modal × vLLM specialist extract: **20 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-l5-graphs` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 20 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `0ec3314ab111` |
| git | `e9550a1 (dirty)` |
| spec_hash | `d93edb320d8658c3da355caae1e5b2b25918422bf173f05aeb35e4502bfa8581` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **20 / 20** (errors 0) |
| **overall_extraction_score** | **0.2841** (sd 0.2267, min 0.0000, max 0.7255) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 17.980 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 215.7 s |
| preflight probe (engine answering) | 213.320 s |
| latency p50 / p95 / max | 6.41 / 10.15 / 11.84 s |
| prompt / completion tokens | 37212 / 3030 |
| throughput | 2238.2 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.003996 |
| **$ per doc (busy)** | **0.000200** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.15 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 20 (cumulative 20), measured TTFT mean 1.398 s (vLLM histogram, cumulative), prefix-cache hit 58.8%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 130.1 s over wall 18.0 s = **7.24×** effective parallelism at c8 (90% of the ideal 8×).
- **Tail:** slowest doc `DOC-2431095adda97989` (memo) 11.8 s = 66% of wall — p95/p50 = 1.58×.
- **Prompt length vs latency:** Pearson r = 0.58 across 20 docs (prefill-bound).
- **Decode budget:** mean completion 152 tok/doc, mean prompt 1861 tok/doc.
- **Subclass spread:** best `notice` 0.603 (n=2), worst `letter` 0.089 (n=1).
- **Field-level extraction:** 12/20 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 216 s (driver stamps); preflight probe measured 213.3 s once the engine answered.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-l5-graphs-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-l5-graphs-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 11 | 0.2190 |
| memo | 5 | 0.3626 |
| notice | 2 | 0.6025 |
| press_release | 1 | 0.1667 |
| letter | 1 | 0.0889 |
| **total** | **20** | **0.2841** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 6.9 | 1698 | 103 |  |
| 2 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 6.9 | 1685 | 115 |  |
| 3 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 6.9 | 1707 | 106 |  |
| 4 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 7.9 | 1779 | 134 |  |
| 5 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 8.5 | 1996 | 152 |  |
| 6 | `DOC-a318b50872273528` | email | 0.0889 | 0.0000 | ✓ | 9.5 | 2028 | 187 |  |
| 7 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 10.2 | 2025 | 198 |  |
| 8 | `DOC-2431095adda97989` | memo | 0.5086 | 0.1112 | ✓ | 11.8 | 2075 | 257 |  |
| 9 | `DOC-16dfd03aed14e557` | email | 0.0784 | 0.0000 | ✓ | 3.9 | 1674 | 107 |  |
| 10 | `DOC-c4debd478f2c06e0` | email | 0.2045 | 0.0000 | ✓ | 5.5 | 1936 | 139 |  |
| 11 | `DOC-38265bcc6ecfecc3` | email | 0.0784 | 0.0000 | ✓ | 5.4 | 1729 | 144 |  |
| 12 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 6.4 | 1739 | 157 |  |
| 13 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 6.4 | 1954 | 159 |  |
| 14 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 2.7 | 1668 | 84 |  |
| 15 | `DOC-d3d85dc1b1514bec` | notice | 0.5384 | 0.1333 | ✓ | 5.9 | 1913 | 179 |  |
| 16 | `DOC-21460a9f6d7e6348` | memo | 0.7255 | 0.2499 | ✓ | 4.2 | 1806 | 129 |  |
| 17 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 4.2 | 1724 | 132 |  |
| 18 | `DOC-2cde0c6d0c70b02b` | memo | 0.0909 | 0.0000 | ✓ | 7.4 | 2206 | 225 |  |
| 19 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 5.0 | 1976 | 155 |  |
| 20 | `DOC-5b63f9fe205d564b` | email | 0.5800 | 0.1250 | ✓ | 4.6 | 1894 | 168 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-l5-graphs.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-l5-graphs
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-l5-graphs.yaml` | run spec |
| `reports/serving/sand032-l5-graphs.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-l5-graphs/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-l5-graphs/` | offline Braintrust-shaped rows — disposed after this report is committed |
