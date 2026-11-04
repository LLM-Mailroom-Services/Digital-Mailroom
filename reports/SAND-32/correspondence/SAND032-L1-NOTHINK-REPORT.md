# Run report — `sand032-l1-nothink`

SAND-032 Modal × vLLM specialist extract: **20 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-l1-nothink` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=32768`, quant=`awq`, gpu_util=0.9, max_num_seqs=6 |
| engine flags | prefix_caching=on, enforce_eager=on, kv_cache_dtype=`auto`, thinking=off, cudagraph sizes=—, max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 20 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `0ec3314ab111` |
| git | `59595c7 (dirty)` |
| spec_hash | `307eebeae638a2c988035eb00577a10b17a7863f0516ef41a26cf9943addd2ca` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **20 / 20** (errors 0) |
| **overall_extraction_score** | **0.2742** (sd 0.2213, min 0.0000, max 0.7255) |
| schema_valid_rate | 0.950 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 26.465 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 122.7 s |
| preflight probe (engine answering) | 120.412 s |
| latency p50 / p95 / max | 8.03 / 11.70 / 17.70 s |
| prompt / completion tokens | 37212 / 3127 |
| throughput | 1524.2 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.005881 |
| **$ per doc (busy)** | **0.000294** |
| fleet window deploy→stop (upper est.) | 175 s → 0.0389 USD |
| cost cap | $0.15 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790545849.33`: requests Δ 20 (cumulative 20), measured TTFT mean 2.513 s (vLLM histogram, cumulative), prefix-cache hit 58.8%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 174.5 s over wall 26.5 s = **6.59×** effective parallelism at c8 (82% of the ideal 8×).
- **Tail:** slowest doc `DOC-2431095adda97989` (memo) 17.7 s = 67% of wall — p95/p50 = 1.46×.
- **Prompt length vs latency:** Pearson r = 0.62 across 20 docs (prefill-bound).
- **Decode budget:** mean completion 156 tok/doc, mean prompt 1861 tok/doc.
- **Subclass spread:** best `notice` 0.551 (n=2), worst `letter` 0.089 (n=1).
- **Field-level extraction:** 12/20 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 123 s (driver stamps); preflight probe measured 120.4 s once the engine answered.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-l1-nothink-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-l1-nothink-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 11 | 0.2406 |
| memo | 5 | 0.2959 |
| notice | 2 | 0.5513 |
| letter | 1 | 0.0889 |
| press_release | 1 | 0.1667 |
| **total** | **20** | **0.2742** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✗ | 7.3 | 1698 | 109 |  |
| 2 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 7.3 | 1685 | 115 |  |
| 3 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 8.0 | 1779 | 134 |  |
| 4 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 9.1 | 1996 | 160 |  |
| 5 | `DOC-a318b50872273528` | email | 0.1167 | 0.0000 | ✓ | 9.8 | 2028 | 178 |  |
| 6 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 10.7 | 2025 | 199 |  |
| 7 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 11.7 | 1707 | 114 |  |
| 8 | `DOC-c4debd478f2c06e0` | email | 0.5101 | 0.1333 | ✓ | 5.9 | 1936 | 134 |  |
| 9 | `DOC-16dfd03aed14e557` | email | 0.0000 | 0.0000 | ✓ | 4.8 | 1674 | 76 |  |
| 10 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 7.8 | 1739 | 154 |  |
| 11 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 8.1 | 1954 | 159 |  |
| 12 | `DOC-38265bcc6ecfecc3` | email | 0.1111 | 0.0000 | ✓ | 7.3 | 1729 | 143 |  |
| 13 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 17.7 | 2075 | 269 |  |
| 14 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 4.6 | 1668 | 87 |  |
| 15 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 6.1 | 1724 | 134 |  |
| 16 | `DOC-2cde0c6d0c70b02b` | memo | 0.0909 | 0.0000 | ✓ | 11.2 | 2206 | 227 |  |
| 17 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 8.7 | 1976 | 183 |  |
| 18 | `DOC-21460a9f6d7e6348` | memo | 0.7255 | 0.2222 | ✓ | 7.4 | 1806 | 161 |  |
| 19 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1112 | ✓ | 11.1 | 1913 | 220 |  |
| 20 | `DOC-5b63f9fe205d564b` | email | 0.5303 | 0.1250 | ✓ | 10.0 | 1894 | 171 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-l1-nothink.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-l1-nothink
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-l1-nothink.yaml` | run spec |
| `reports/serving/sand032-l1-nothink.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-l1-nothink/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-l1-nothink/` | offline Braintrust-shaped rows — disposed after this report is committed |
