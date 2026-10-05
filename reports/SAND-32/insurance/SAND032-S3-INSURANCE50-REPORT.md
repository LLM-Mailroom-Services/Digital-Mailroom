# Run report — `sand032-s3-insurance50`

SAND-032 Modal × vLLM specialist extract: **50 insurance_claim docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 32** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s3-insurance50` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_simplified` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `b53ba23fea0a` |
| git | `b9d2832 (dirty)` |
| spec_hash | `5ced9757ad230bb3adc108121b01ac79350219477f8d6366f616cd88b6d888f4` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **50 / 50** (errors 0) |
| **overall_extraction_score** | **0.6881** (sd 0.0648, min 0.5827, max 0.8056) |
| schema_valid_rate | 0.220 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 60.689 s |
| concurrency | 32 (16 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.169 s |
| latency p50 / p95 / max | 19.68 / 34.13 / 42.36 s |
| prompt / completion tokens | 163779 / 20819 |
| throughput | 3041.7 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.026973 |
| **$ per doc (busy)** | **0.000539** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.6 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 23 (cumulative 227), measured TTFT mean 0.914 s (vLLM histogram, cumulative), prefix-cache hit 71.6%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790546749.43`: requests Δ 27 (cumulative 93), measured TTFT mean 2.071 s (vLLM histogram, cumulative), prefix-cache hit 55.1%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 1072.7 s over wall 60.7 s = **17.68×** effective parallelism at c32 (55% of the ideal 32×).
- **Tail:** slowest doc `DOC-d3f320a3ba9c105b` (property) 42.4 s = 70% of wall — p95/p50 = 1.73×.
- **Prompt length vs latency:** Pearson r = 0.46 across 50 docs (not prefill-dominated).
- **Decode budget:** mean completion 416 tok/doc, mean prompt 3276 tok/doc.
- **Subclass spread:** best `auto` 0.744 (n=19), worst `pde` 0.593 (n=5).
- **Field-level extraction:** 0/50 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s3-insurance50-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s3-insurance50-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| auto | 19 | 0.7441 |
| property | 8 | 0.6825 |
| inpatient | 7 | 0.6900 |
| carrier | 6 | 0.6389 |
| outpatient | 5 | 0.6355 |
| pde | 5 | 0.5934 |
| **total** | **50** | **0.6881** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-7a128ee6e786bd0e` | auto | 0.7024 | 0.6060 | ✗ | 14.9 | 2808 | 251 |  |
| 2 | `DOC-826b2ac305c2b791` | auto | 0.6955 | 0.5883 | ✗ | 14.9 | 2810 | 283 |  |
| 3 | `DOC-db1d2b3ea4d2d24f` | auto | 0.7417 | 0.6285 | ✗ | 14.9 | 2804 | 285 |  |
| 4 | `DOC-b28fe495a873ca59` | auto | 0.6895 | 0.6452 | ✗ | 15.4 | 2807 | 271 |  |
| 5 | `DOC-d6d57b7a18431923` | auto | 0.6959 | 0.5883 | ✗ | 16.3 | 2803 | 282 |  |
| 6 | `DOC-ee3512878a0003b7` | auto | 0.7930 | 0.7059 | ✗ | 16.7 | 2831 | 332 |  |
| 7 | `DOC-b3be1f4b2b6142ed` | auto | 0.6955 | 0.5883 | ✗ | 16.8 | 2815 | 287 |  |
| 8 | `DOC-4fd4cf5db3cfdb47` | carrier | 0.6398 | 0.5806 | ✗ | 16.9 | 2940 | 333 |  |
| 9 | `DOC-dcb4333f78bfe249` | carrier | 0.6411 | 0.5806 | ✗ | 16.9 | 2934 | 332 |  |
| 10 | `DOC-d5e1b8ed3350fb36` | carrier | 0.6325 | 0.5806 | ✗ | 16.9 | 2969 | 334 |  |
| 11 | `DOC-df5ebe3e7263b6c6` | auto | 0.6385 | 0.5806 | ✗ | 17.4 | 2815 | 288 |  |
| 12 | `DOC-596b1f881ecf4a8a` | auto | 0.7163 | 0.5883 | ✗ | 18.3 | 2806 | 305 |  |
| 13 | `DOC-c0e145a5a0a0d4bd` | auto | 0.7930 | 0.6667 | ✗ | 18.3 | 2833 | 347 |  |
| 14 | `DOC-edc5811634a19b7a` | auto | 0.8056 | 0.6667 | ✗ | 18.3 | 2835 | 350 |  |
| 15 | `DOC-9f75d0ce11867685` | carrier | 0.6387 | 0.5454 | ✗ | 18.3 | 3044 | 350 |  |
| 16 | `DOC-c0d9bf1e6be4ad51` | auto | 0.7015 | 0.5883 | ✗ | 18.8 | 2808 | 311 |  |
| 17 | `DOC-fa698a867428a0ed` | carrier | 0.6387 | 0.5294 | ✗ | 19.8 | 3016 | 335 |  |
| 18 | `DOC-bf5c2cc12aca8aad` | auto | 0.7830 | 0.6667 | ✗ | 20.7 | 2834 | 362 |  |
| 19 | `DOC-2d2ec2092b012662` | auto | 0.7930 | 0.6667 | ✗ | 21.3 | 2831 | 345 |  |
| 20 | `DOC-884dc887726dcfa5` | auto | 0.7375 | 0.6111 | ✗ | 22.8 | 2833 | 350 |  |
| 21 | `DOC-bce319dabbc42e89` | auto | 0.7991 | 0.6667 | ✗ | 22.8 | 2831 | 350 |  |
| 22 | `DOC-8dcc97d49f2004f5` | auto | 0.7786 | 0.6667 | ✗ | 23.8 | 2835 | 371 |  |
| 23 | `DOC-a0be2aba09a3f580` | inpatient | 0.6885 | 0.5000 | ✓ | 23.8 | 3095 | 372 |  |
| 24 | `DOC-a1a2afde18ded42d` | inpatient | 0.6885 | 0.5000 | ✓ | 24.2 | 3086 | 381 |  |
| 25 | `DOC-dc33a3e5a8cf5b6b` | auto | 0.8056 | 0.6667 | ✗ | 25.2 | 2832 | 369 |  |
| 26 | `DOC-4dda6e74e78edd70` | carrier | 0.6428 | 0.5294 | ✗ | 25.2 | 2949 | 375 |  |
| 27 | `DOC-85e24caa52979f50` | inpatient | 0.7002 | 0.5000 | ✓ | 25.7 | 3121 | 386 |  |
| 28 | `DOC-1e95a2ae82adc61c` | inpatient | 0.6901 | 0.4865 | ✓ | 26.1 | 3143 | 396 |  |
| 29 | `DOC-2435c398b95844bc` | inpatient | 0.6990 | 0.4865 | ✓ | 26.2 | 3080 | 401 |  |
| 30 | `DOC-576c9233159914e3` | inpatient | 0.6825 | 0.4615 | ✓ | 26.9 | 3080 | 466 |  |
| 31 | `DOC-ab3b194998a42322` | outpatient | 0.6176 | 0.4572 | ✗ | 17.3 | 3016 | 340 |  |
| 32 | `DOC-4cd6ca1171e8885e` | auto | 0.7729 | 0.7059 | ✗ | 32.7 | 2832 | 352 |  |
| 33 | `DOC-a0c5db2835e31ef6` | pde | 0.6010 | 0.5161 | ✗ | 16.9 | 2871 | 340 |  |
| 34 | `DOC-804fbeed2ab25ae8` | pde | 0.5928 | 0.5161 | ✓ | 17.0 | 2873 | 347 |  |
| 35 | `DOC-4348717727f6d6b4` | outpatient | 0.6456 | 0.5333 | ✗ | 19.4 | 3004 | 364 |  |
| 36 | `DOC-b199013b1823372d` | pde | 0.5827 | 0.5000 | ✗ | 17.5 | 2882 | 366 |  |
| 37 | `DOC-01f1577c446c646d` | pde | 0.5993 | 0.5161 | ✗ | 17.7 | 2868 | 349 |  |
| 38 | `DOC-f80fe4950664c6e0` | pde | 0.5910 | 0.5000 | ✗ | 17.6 | 2884 | 344 |  |
| 39 | `DOC-1bc5f212af3bd4c2` | outpatient | 0.6454 | 0.4849 | ✗ | 19.8 | 2990 | 413 |  |
| 40 | `DOC-4e21681f375a247d` | outpatient | 0.6426 | 0.5333 | ✗ | 18.6 | 2985 | 379 |  |
| 41 | `DOC-d62e0d8ac987119d` | outpatient | 0.6265 | 0.4706 | ✗ | 20.1 | 3031 | 393 |  |
| 42 | `DOC-17abdc452037b6eb` | inpatient | 0.6810 | 0.4615 | ✓ | 37.8 | 3129 | 511 |  |
| 43 | `DOC-91fe413a7105d6fc` | property | 0.7444 | 0.5405 | ✗ | 20.3 | 5106 | 498 |  |
| 44 | `DOC-e08d7fd014fde496` | property | 0.6087 | 0.4445 | ✗ | 21.8 | 4487 | 511 |  |
| 45 | `DOC-06844413e427f8c2` | property | 0.7631 | 0.5556 | ✓ | 19.6 | 5336 | 562 |  |
| 46 | `DOC-009ee40e247a0a6e` | property | 0.6083 | 0.4324 | ✗ | 22.1 | 4688 | 576 |  |
| 47 | `DOC-db02c129ee1d5261` | property | 0.6856 | 0.5000 | ✗ | 24.8 | 6294 | 694 |  |
| 48 | `DOC-4df9e8f7fd1c31c3` | property | 0.6718 | 0.5000 | ✓ | 31.0 | 4883 | 942 |  |
| 49 | `DOC-0966e6d5a9e7bd71` | property | 0.7490 | 0.5263 | ✓ | 34.1 | 4683 | 986 |  |
| 50 | `DOC-d3f320a3ba9c105b` | property | 0.6294 | 0.3461 | ✗ | 42.4 | 5709 | 1352 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s3-insurance50.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s3-insurance50
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s3-insurance50.yaml` | run spec |
| `reports/serving/sand032-s3-insurance50.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s3-insurance50/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s3-insurance50/` | offline Braintrust-shaped rows — disposed after this report is committed |
