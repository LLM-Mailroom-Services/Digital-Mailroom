# Run report — `sand032-s4-corr20-bf16`

SAND-032 Modal × vLLM specialist extract: **20 correspondence docs** on **Qwen/Qwen3-8B** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s4-corr20-bf16` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=16384`, quant=`bf16`, gpu_util=0.9, max_num_seqs=6 |
| engine flags | prefix_caching=on, enforce_eager=on, kv_cache_dtype=`auto`, thinking=off, cudagraph sizes=—, max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 20 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `0ec3314ab111` |
| git | `d79d863 (dirty)` |
| spec_hash | `f10e21794729d863243cc3b9b3c19795ab8537186abe36e39307198eeb778de3` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **20 / 20** (errors 0) |
| **overall_extraction_score** | **0.2742** (sd 0.2227, min 0.0000, max 0.7451) |
| schema_valid_rate | 0.950 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 46.905 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 136.3 s |
| preflight probe (engine answering) | 133.877 s |
| latency p50 / p95 / max | 14.02 / 23.77 / 30.55 s |
| prompt / completion tokens | 37212 / 3096 |
| throughput | 859.4 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.010423 |
| **$ per doc (busy)** | **0.000521** |
| fleet window deploy→stop (upper est.) | 210 s → 0.0466 USD |
| cost cap | $0.2 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790547979.44`: requests Δ 20 (cumulative 20), measured TTFT mean 3.980 s (vLLM histogram, cumulative), prefix-cache hit 58.8%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 312.1 s over wall 46.9 s = **6.65×** effective parallelism at c8 (83% of the ideal 8×).
- **Tail:** slowest doc `DOC-2431095adda97989` (memo) 30.6 s = 65% of wall — p95/p50 = 1.70×.
- **Prompt length vs latency:** Pearson r = 0.73 across 20 docs (prefill-bound).
- **Decode budget:** mean completion 155 tok/doc, mean prompt 1861 tok/doc.
- **Subclass spread:** best `notice` 0.551 (n=2), worst `letter` 0.089 (n=1).
- **Field-level extraction:** 12/20 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 136 s (driver stamps); preflight probe measured 133.9 s once the engine answered.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s4-corr20-bf16-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s4-corr20-bf16-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 11 | 0.2134 |
| memo | 5 | 0.3643 |
| notice | 2 | 0.5513 |
| press_release | 1 | 0.1228 |
| letter | 1 | 0.0889 |
| **total** | **20** | **0.2742** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 11.3 | 1685 | 115 |  |
| 2 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 11.3 | 1698 | 114 |  |
| 3 | `DOC-f36a37e1a9c1351e` | press_release | 0.1228 | 0.0000 | ✗ | 11.3 | 1707 | 115 |  |
| 4 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 12.6 | 1779 | 132 |  |
| 5 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 14.8 | 1996 | 159 |  |
| 6 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 18.5 | 2025 | 213 |  |
| 7 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 11.4 | 1954 | 139 |  |
| 8 | `DOC-a318b50872273528` | email | 0.0833 | 0.0000 | ✓ | 23.8 | 2028 | 170 |  |
| 9 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 13.0 | 1739 | 169 |  |
| 10 | `DOC-c4debd478f2c06e0` | email | 0.2273 | 0.0000 | ✓ | 14.9 | 1936 | 154 |  |
| 11 | `DOC-16dfd03aed14e557` | email | 0.0000 | 0.0000 | ✓ | 14.0 | 1674 | 76 |  |
| 12 | `DOC-38265bcc6ecfecc3` | email | 0.0784 | 0.0000 | ✓ | 17.7 | 1729 | 156 |  |
| 13 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 30.6 | 2075 | 255 |  |
| 14 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 7.7 | 1668 | 84 |  |
| 15 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 13.9 | 1976 | 155 |  |
| 16 | `DOC-21460a9f6d7e6348` | memo | 0.7451 | 0.2499 | ✓ | 14.1 | 1806 | 131 |  |
| 17 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1250 | ✓ | 13.8 | 1724 | 135 |  |
| 18 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1112 | ✓ | 18.0 | 1913 | 225 |  |
| 19 | `DOC-2cde0c6d0c70b02b` | memo | 0.4133 | 0.1176 | ✓ | 23.1 | 2206 | 243 |  |
| 20 | `DOC-5b63f9fe205d564b` | email | 0.5800 | 0.1250 | ✓ | 16.6 | 1894 | 156 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s4-corr20-bf16.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s4-corr20-bf16
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s4-corr20-bf16.yaml` | run spec |
| `reports/serving/sand032-s4-corr20-bf16.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s4-corr20-bf16/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s4-corr20-bf16/` | offline Braintrust-shaped rows — disposed after this report is committed |
