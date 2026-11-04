# Run report — `sand032-s9-insurance50-bal`

SAND-032 Modal × vLLM specialist extract: **50 insurance_claim docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 64** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s9-insurance50-bal` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_simplified` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=32 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16, 32], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `b53ba23fea0a` |
| git | `37e5f98 (dirty)` |
| spec_hash | `4db70e9366c68d25a3130117f5f63fb08afedc9e00529541ec40e77f5bd2e703` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **50 / 50** (errors 0) |
| **overall_extraction_score** | **0.6821** (sd 0.0647, min 0.5691, max 0.8056) |
| schema_valid_rate | 0.180 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 52.809 s |
| concurrency | 64 (32 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.329 s |
| latency p50 / p95 / max | 26.96 / 40.55 / 52.75 s |
| prompt / completion tokens | 163779 / 21131 |
| throughput | 3501.5 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.023471 |
| **$ per doc (busy)** | **0.000469** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.6 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790582921.77`: requests Δ 25 (cumulative 76), measured TTFT mean 6.027 s (vLLM histogram, cumulative), prefix-cache hit 50.8%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790582929.28`: requests Δ 25 (cumulative 74), measured TTFT mean 5.784 s (vLLM histogram, cumulative), prefix-cache hit 52.3%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 1414.5 s over wall 52.8 s = **26.79×** effective parallelism at c64 (42% of the ideal 64×).
- **Tail:** slowest doc `DOC-d3f320a3ba9c105b` (property) 52.8 s = 100% of wall — p95/p50 = 1.50×.
- **Prompt length vs latency:** Pearson r = 0.81 across 50 docs (prefill-bound).
- **Decode budget:** mean completion 423 tok/doc, mean prompt 3276 tok/doc.
- **Subclass spread:** best `auto` 0.737 (n=19), worst `pde` 0.592 (n=5).
- **Field-level extraction:** 0/50 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s9-insurance50-bal-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s9-insurance50-bal-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| auto | 19 | 0.7371 |
| property | 8 | 0.6584 |
| inpatient | 7 | 0.6912 |
| carrier | 6 | 0.6466 |
| pde | 5 | 0.5918 |
| outpatient | 5 | 0.6311 |
| **total** | **50** | **0.6821** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-b28fe495a873ca59` | auto | 0.6895 | 0.5883 | ✗ | 23.4 | 2807 | 286 |  |
| 2 | `DOC-db1d2b3ea4d2d24f` | auto | 0.6750 | 0.5714 | ✗ | 23.4 | 2804 | 286 |  |
| 3 | `DOC-826b2ac305c2b791` | auto | 0.6955 | 0.5883 | ✗ | 23.4 | 2810 | 281 |  |
| 4 | `DOC-7a128ee6e786bd0e` | auto | 0.7024 | 0.6060 | ✗ | 23.5 | 2808 | 292 |  |
| 5 | `DOC-d6d57b7a18431923` | auto | 0.6959 | 0.6452 | ✗ | 23.7 | 2803 | 276 |  |
| 6 | `DOC-df5ebe3e7263b6c6` | auto | 0.6385 | 0.5806 | ✗ | 24.8 | 2815 | 286 |  |
| 7 | `DOC-b3be1f4b2b6142ed` | auto | 0.6955 | 0.5883 | ✗ | 24.8 | 2815 | 289 |  |
| 8 | `DOC-596b1f881ecf4a8a` | auto | 0.6496 | 0.5625 | ✗ | 24.9 | 2806 | 300 |  |
| 9 | `DOC-c0d9bf1e6be4ad51` | auto | 0.7015 | 0.5883 | ✗ | 25.1 | 2808 | 311 |  |
| 10 | `DOC-ee3512878a0003b7` | auto | 0.8000 | 0.6667 | ✗ | 25.3 | 2831 | 340 |  |
| 11 | `DOC-dc33a3e5a8cf5b6b` | auto | 0.8056 | 0.6667 | ✗ | 25.6 | 2832 | 344 |  |
| 12 | `DOC-9f75d0ce11867685` | carrier | 0.6345 | 0.5294 | ✗ | 25.7 | 3044 | 338 |  |
| 13 | `DOC-884dc887726dcfa5` | auto | 0.7375 | 0.6111 | ✗ | 26.0 | 2833 | 350 |  |
| 14 | `DOC-a0c5db2835e31ef6` | pde | 0.6010 | 0.5333 | ✗ | 26.0 | 2871 | 348 |  |
| 15 | `DOC-dcb4333f78bfe249` | carrier | 0.6363 | 0.5143 | ✗ | 26.0 | 2934 | 347 |  |
| 16 | `DOC-ab3b194998a42322` | outpatient | 0.6131 | 0.4572 | ✗ | 26.1 | 3016 | 345 |  |
| 17 | `DOC-fa698a867428a0ed` | carrier | 0.6353 | 0.5294 | ✗ | 26.1 | 3016 | 334 |  |
| 18 | `DOC-bf5c2cc12aca8aad` | auto | 0.7830 | 0.6667 | ✗ | 26.2 | 2834 | 357 |  |
| 19 | `DOC-01f1577c446c646d` | pde | 0.5993 | 0.5333 | ✗ | 26.3 | 2868 | 357 |  |
| 20 | `DOC-a0be2aba09a3f580` | inpatient | 0.6885 | 0.5000 | ✓ | 26.4 | 3095 | 372 |  |
| 21 | `DOC-d5e1b8ed3350fb36` | carrier | 0.6290 | 0.5294 | ✗ | 26.5 | 2969 | 373 |  |
| 22 | `DOC-8dcc97d49f2004f5` | auto | 0.7786 | 0.6667 | ✗ | 26.6 | 2835 | 364 |  |
| 23 | `DOC-4dda6e74e78edd70` | carrier | 0.6428 | 0.5294 | ✗ | 26.6 | 2949 | 375 |  |
| 24 | `DOC-c0e145a5a0a0d4bd` | auto | 0.7930 | 0.6667 | ✗ | 26.6 | 2833 | 343 |  |
| 25 | `DOC-804fbeed2ab25ae8` | pde | 0.5809 | 0.5333 | ✗ | 26.9 | 2873 | 349 |  |
| 26 | `DOC-2d2ec2092b012662` | auto | 0.8000 | 0.6667 | ✗ | 27.0 | 2831 | 342 |  |
| 27 | `DOC-85e24caa52979f50` | inpatient | 0.7114 | 0.5000 | ✓ | 27.0 | 3121 | 379 |  |
| 28 | `DOC-a1a2afde18ded42d` | inpatient | 0.6843 | 0.5000 | ✓ | 27.1 | 3086 | 382 |  |
| 29 | `DOC-4fd4cf5db3cfdb47` | carrier | 0.7017 | 0.5883 | ✗ | 27.2 | 2940 | 367 |  |
| 30 | `DOC-4cd6ca1171e8885e` | auto | 0.7729 | 0.6667 | ✗ | 27.2 | 2832 | 355 |  |
| 31 | `DOC-b199013b1823372d` | pde | 0.5827 | 0.5161 | ✗ | 27.5 | 2882 | 359 |  |
| 32 | `DOC-bce319dabbc42e89` | auto | 0.7857 | 0.6667 | ✗ | 27.6 | 2831 | 359 |  |
| 33 | `DOC-f80fe4950664c6e0` | pde | 0.5952 | 0.5333 | ✗ | 27.6 | 2884 | 358 |  |
| 34 | `DOC-d62e0d8ac987119d` | outpatient | 0.6265 | 0.4572 | ✗ | 27.8 | 3031 | 417 |  |
| 35 | `DOC-edc5811634a19b7a` | auto | 0.8056 | 0.6486 | ✗ | 28.0 | 2835 | 377 |  |
| 36 | `DOC-1e95a2ae82adc61c` | inpatient | 0.6901 | 0.4865 | ✓ | 28.1 | 3143 | 379 |  |
| 37 | `DOC-4348717727f6d6b4` | outpatient | 0.6456 | 0.5161 | ✗ | 28.3 | 3004 | 399 |  |
| 38 | `DOC-4e21681f375a247d` | outpatient | 0.6426 | 0.4706 | ✗ | 29.0 | 2985 | 412 |  |
| 39 | `DOC-1bc5f212af3bd4c2` | outpatient | 0.6279 | 0.4706 | ✗ | 29.1 | 2990 | 415 |  |
| 40 | `DOC-576c9233159914e3` | inpatient | 0.6822 | 0.4737 | ✓ | 29.4 | 3080 | 477 |  |
| 41 | `DOC-17abdc452037b6eb` | inpatient | 0.6921 | 0.5143 | ✓ | 29.8 | 3129 | 439 |  |
| 42 | `DOC-91fe413a7105d6fc` | property | 0.7444 | 0.5405 | ✗ | 30.0 | 5106 | 498 |  |
| 43 | `DOC-e08d7fd014fde496` | property | 0.6087 | 0.4445 | ✗ | 30.1 | 4487 | 509 |  |
| 44 | `DOC-2435c398b95844bc` | inpatient | 0.6898 | 0.4865 | ✓ | 31.7 | 3080 | 515 |  |
| 45 | `DOC-06844413e427f8c2` | property | 0.6990 | 0.5143 | ✗ | 32.8 | 5336 | 544 |  |
| 46 | `DOC-009ee40e247a0a6e` | property | 0.5691 | 0.4210 | ✗ | 35.1 | 4688 | 638 |  |
| 47 | `DOC-db02c129ee1d5261` | property | 0.6856 | 0.5000 | ✗ | 36.5 | 6294 | 694 |  |
| 48 | `DOC-4df9e8f7fd1c31c3` | property | 0.6718 | 0.5000 | ✓ | 40.5 | 4883 | 940 |  |
| 49 | `DOC-0966e6d5a9e7bd71` | property | 0.6592 | 0.4445 | ✓ | 41.3 | 4683 | 960 |  |
| 50 | `DOC-d3f320a3ba9c105b` | property | 0.6294 | 0.3461 | ✗ | 52.8 | 5709 | 1374 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s9-insurance50-bal.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s9-insurance50-bal
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s9-insurance50-bal.yaml` | run spec |
| `reports/serving/sand032-s9-insurance50-bal.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s9-insurance50-bal/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s9-insurance50-bal/` | offline Braintrust-shaped rows — disposed after this report is committed |
