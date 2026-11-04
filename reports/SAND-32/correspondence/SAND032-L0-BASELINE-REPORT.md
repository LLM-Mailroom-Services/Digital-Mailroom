# Run report — `sand032-l0-baseline`

SAND-032 Modal × vLLM specialist extract: **20 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-l0-baseline` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=32768`, quant=`awq`, gpu_util=0.9, max_num_seqs=6 |
| engine flags | prefix_caching=on, enforce_eager=on, kv_cache_dtype=`auto`, thinking=default, cudagraph sizes=—, max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 20 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `0ec3314ab111` |
| git | `59595c7` |
| spec_hash | `cbd4b421e83966d2f1a4c14e078ac084ba0e5a1731f0acccbb1810120ee73628` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **20 / 20** (errors 0) |
| **overall_extraction_score** | **0.2787** (sd 0.2179, min 0.0000, max 0.7843) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 31.878 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.385 s |
| latency p50 / p95 / max | 10.29 / 14.57 / 16.67 s |
| prompt / completion tokens | 37132 / 3070 |
| throughput | 1261.1 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.007084 |
| **$ per doc (busy)** | **0.000354** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.15 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790545371.85`: requests Δ 20 (cumulative 20), measured TTFT mean 3.066 s (vLLM histogram, cumulative), prefix-cache hit 59.0%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 216.7 s over wall 31.9 s = **6.80×** effective parallelism at c8 (85% of the ideal 8×).
- **Tail:** slowest doc `DOC-2431095adda97989` (memo) 16.7 s = 52% of wall — p95/p50 = 1.42×.
- **Prompt length vs latency:** Pearson r = 0.41 across 20 docs (not prefill-dominated).
- **Decode budget:** mean completion 154 tok/doc, mean prompt 1857 tok/doc.
- **Subclass spread:** best `notice` 0.551 (n=2), worst `letter` 0.099 (n=1).
- **Field-level extraction:** 12/20 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-l0-baseline-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-l0-baseline-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 11 | 0.2131 |
| memo | 5 | 0.3722 |
| notice | 2 | 0.5513 |
| letter | 1 | 0.0988 |
| press_release | 1 | 0.1667 |
| **total** | **20** | **0.2787** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 8.8 | 1694 | 112 |  |
| 2 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 9.1 | 1775 | 128 |  |
| 3 | `DOC-44b1e5a60b363d3e` | letter | 0.0988 | 0.0000 | ✓ | 10.6 | 1992 | 158 |  |
| 4 | `DOC-a318b50872273528` | email | 0.2222 | 0.0000 | ✓ | 12.3 | 2024 | 193 |  |
| 5 | `DOC-38c54645bf0e601a` | email | 0.2399 | 0.0000 | ✓ | 12.9 | 2021 | 205 |  |
| 6 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 14.1 | 1681 | 113 |  |
| 7 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 14.6 | 1703 | 108 |  |
| 8 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 16.7 | 2071 | 281 |  |
| 9 | `DOC-16dfd03aed14e557` | email | 0.0000 | 0.0000 | ✓ | 5.5 | 1670 | 77 |  |
| 10 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 10.0 | 1735 | 161 |  |
| 11 | `DOC-c4debd478f2c06e0` | email | 0.5101 | 0.1333 | ✓ | 10.3 | 1932 | 135 |  |
| 12 | `DOC-690cb07fef21747b` | email | 0.1754 | 0.0000 | ✓ | 10.9 | 1950 | 167 |  |
| 13 | `DOC-38265bcc6ecfecc3` | email | 0.1111 | 0.0000 | ✓ | 9.9 | 1725 | 156 |  |
| 14 | `DOC-2cde0c6d0c70b02b` | memo | 0.4133 | 0.1250 | ✓ | 10.9 | 2202 | 162 |  |
| 15 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 6.5 | 1664 | 76 |  |
| 16 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2354 | ✓ | 9.4 | 1972 | 144 |  |
| 17 | `DOC-21460a9f6d7e6348` | memo | 0.7843 | 0.2105 | ✓ | 9.4 | 1802 | 173 |  |
| 18 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1176 | ✓ | 10.1 | 1720 | 155 |  |
| 19 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1176 | ✓ | 14.5 | 1909 | 217 |  |
| 20 | `DOC-5b63f9fe205d564b` | email | 0.5303 | 0.1112 | ✓ | 10.3 | 1890 | 149 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-l0-baseline.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-l0-baseline
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-l0-baseline.yaml` | run spec |
| `reports/serving/sand032-l0-baseline.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-l0-baseline/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-l0-baseline/` | offline Braintrust-shaped rows — disposed after this report is committed |
