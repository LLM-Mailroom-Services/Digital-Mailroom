# Run report — `sand032-s7-insurance50-seqs32`

SAND-032 Modal × vLLM specialist extract: **50 insurance_claim docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 64** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s7-insurance50-seqs32` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_simplified` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=32 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16, 32], max_inputs=64 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `b53ba23fea0a` |
| git | `b268ad4 (dirty)` |
| spec_hash | `dd56c64e5fbcc6b22ab16eed44353dbbea22b6cb081ad840d26b3f2d482ad31f` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **50 / 50** (errors 0) |
| **overall_extraction_score** | **0.6843** (sd 0.0655, min 0.5809, max 0.8056) |
| schema_valid_rate | 0.180 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 58.275 s |
| concurrency | 64 (32 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.435 s |
| latency p50 / p95 / max | 31.33 / 48.61 / 58.05 s |
| prompt / completion tokens | 163779 / 20820 |
| throughput | 3167.7 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.025900 |
| **$ per doc (busy)** | **0.000518** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.6 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790582397.24`: requests Δ 16 (cumulative 19), measured TTFT mean 4.575 s (vLLM histogram, cumulative), prefix-cache hit 49.0%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790582397.97`: requests Δ 34 (cumulative 131), measured TTFT mean 14.404 s (vLLM histogram, cumulative), prefix-cache hit 52.0%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 1527.3 s over wall 58.3 s = **26.21×** effective parallelism at c64 (41% of the ideal 64×).
- **Tail:** slowest doc `DOC-d3f320a3ba9c105b` (property) 58.1 s = 100% of wall — p95/p50 = 1.55×.
- **Prompt length vs latency:** Pearson r = 0.49 across 50 docs (not prefill-dominated).
- **Decode budget:** mean completion 416 tok/doc, mean prompt 3276 tok/doc.
- **Subclass spread:** best `auto` 0.737 (n=19), worst `pde` 0.592 (n=5).
- **Field-level extraction:** 0/50 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s7-insurance50-seqs32-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s7-insurance50-seqs32-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| auto | 19 | 0.7366 |
| property | 8 | 0.6778 |
| inpatient | 7 | 0.6923 |
| carrier | 6 | 0.6378 |
| pde | 5 | 0.5918 |
| outpatient | 5 | 0.6329 |
| **total** | **50** | **0.6843** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-db1d2b3ea4d2d24f` | auto | 0.6750 | 0.5714 | ✗ | 19.1 | 2804 | 286 |  |
| 2 | `DOC-b28fe495a873ca59` | auto | 0.6895 | 0.5883 | ✗ | 19.1 | 2807 | 286 |  |
| 3 | `DOC-d6d57b7a18431923` | auto | 0.6959 | 0.5883 | ✗ | 19.1 | 2803 | 290 |  |
| 4 | `DOC-df5ebe3e7263b6c6` | auto | 0.6240 | 0.5294 | ✗ | 19.2 | 2815 | 295 |  |
| 5 | `DOC-b3be1f4b2b6142ed` | auto | 0.6288 | 0.5294 | ✗ | 19.2 | 2815 | 294 |  |
| 6 | `DOC-4fd4cf5db3cfdb47` | carrier | 0.6398 | 0.5806 | ✗ | 20.4 | 2940 | 332 |  |
| 7 | `DOC-fa698a867428a0ed` | carrier | 0.6353 | 0.5294 | ✗ | 20.6 | 3016 | 335 |  |
| 8 | `DOC-9f75d0ce11867685` | carrier | 0.6387 | 0.5625 | ✗ | 20.8 | 3044 | 346 |  |
| 9 | `DOC-b199013b1823372d` | pde | 0.5827 | 0.5161 | ✗ | 20.7 | 2882 | 347 |  |
| 10 | `DOC-c0e145a5a0a0d4bd` | auto | 0.7930 | 0.6667 | ✗ | 20.9 | 2833 | 343 |  |
| 11 | `DOC-8dcc97d49f2004f5` | auto | 0.7908 | 0.6857 | ✗ | 21.2 | 2835 | 357 |  |
| 12 | `DOC-f80fe4950664c6e0` | pde | 0.5952 | 0.5333 | ✗ | 21.2 | 2884 | 360 |  |
| 13 | `DOC-85e24caa52979f50` | inpatient | 0.7114 | 0.5143 | ✓ | 21.8 | 3121 | 380 |  |
| 14 | `DOC-2435c398b95844bc` | inpatient | 0.6981 | 0.4865 | ✓ | 23.6 | 3080 | 458 |  |
| 15 | `DOC-06844413e427f8c2` | property | 0.7661 | 0.5556 | ✓ | 24.9 | 5336 | 510 |  |
| 16 | `DOC-826b2ac305c2b791` | auto | 0.6955 | 0.5883 | ✗ | 28.4 | 2810 | 280 |  |
| 17 | `DOC-db02c129ee1d5261` | property | 0.6961 | 0.5000 | ✗ | 29.4 | 6294 | 690 |  |
| 18 | `DOC-c0d9bf1e6be4ad51` | auto | 0.7015 | 0.5883 | ✗ | 29.4 | 2808 | 314 |  |
| 19 | `DOC-596b1f881ecf4a8a` | auto | 0.7163 | 0.5883 | ✗ | 30.0 | 2806 | 305 |  |
| 20 | `DOC-01f1577c446c646d` | pde | 0.5993 | 0.5517 | ✗ | 30.6 | 2868 | 332 |  |
| 21 | `DOC-dcb4333f78bfe249` | carrier | 0.6411 | 0.5806 | ✗ | 30.8 | 2934 | 332 |  |
| 22 | `DOC-ee3512878a0003b7` | auto | 0.7930 | 0.7059 | ✗ | 31.0 | 2831 | 332 |  |
| 23 | `DOC-dc33a3e5a8cf5b6b` | auto | 0.8056 | 0.6667 | ✗ | 31.1 | 2832 | 339 |  |
| 24 | `DOC-edc5811634a19b7a` | auto | 0.8056 | 0.6667 | ✗ | 31.3 | 2835 | 338 |  |
| 25 | `DOC-a0be2aba09a3f580` | inpatient | 0.6884 | 0.5000 | ✗ | 31.3 | 3095 | 343 |  |
| 26 | `DOC-804fbeed2ab25ae8` | pde | 0.5809 | 0.5333 | ✗ | 31.4 | 2873 | 349 |  |
| 27 | `DOC-2d2ec2092b012662` | auto | 0.8000 | 0.6667 | ✗ | 31.7 | 2831 | 342 |  |
| 28 | `DOC-884dc887726dcfa5` | auto | 0.7375 | 0.6111 | ✗ | 31.9 | 2833 | 350 |  |
| 29 | `DOC-4cd6ca1171e8885e` | auto | 0.7729 | 0.6667 | ✗ | 31.9 | 2832 | 355 |  |
| 30 | `DOC-bce319dabbc42e89` | auto | 0.7857 | 0.6667 | ✗ | 32.0 | 2831 | 353 |  |
| 31 | `DOC-ab3b194998a42322` | outpatient | 0.6176 | 0.4572 | ✗ | 31.8 | 3016 | 340 |  |
| 32 | `DOC-bf5c2cc12aca8aad` | auto | 0.7830 | 0.6667 | ✗ | 32.1 | 2834 | 357 |  |
| 33 | `DOC-d5e1b8ed3350fb36` | carrier | 0.6290 | 0.5143 | ✗ | 32.7 | 2969 | 362 |  |
| 34 | `DOC-d62e0d8ac987119d` | outpatient | 0.6131 | 0.4706 | ✗ | 33.2 | 3031 | 397 |  |
| 35 | `DOC-4dda6e74e78edd70` | carrier | 0.6428 | 0.5294 | ✗ | 33.4 | 2949 | 375 |  |
| 36 | `DOC-4348717727f6d6b4` | outpatient | 0.6456 | 0.4849 | ✗ | 33.4 | 3004 | 391 |  |
| 37 | `DOC-a1a2afde18ded42d` | inpatient | 0.6843 | 0.5000 | ✓ | 33.4 | 3086 | 382 |  |
| 38 | `DOC-4e21681f375a247d` | outpatient | 0.6426 | 0.4849 | ✗ | 33.5 | 2985 | 400 |  |
| 39 | `DOC-576c9233159914e3` | inpatient | 0.6798 | 0.4865 | ✓ | 34.7 | 3080 | 419 |  |
| 40 | `DOC-1bc5f212af3bd4c2` | outpatient | 0.6454 | 0.4572 | ✗ | 35.1 | 2990 | 435 |  |
| 41 | `DOC-17abdc452037b6eb` | inpatient | 0.6921 | 0.5143 | ✓ | 35.2 | 3129 | 448 |  |
| 42 | `DOC-1e95a2ae82adc61c` | inpatient | 0.6923 | 0.4865 | ✓ | 35.9 | 3143 | 465 |  |
| 43 | `DOC-91fe413a7105d6fc` | property | 0.6848 | 0.4865 | ✗ | 37.3 | 5106 | 524 |  |
| 44 | `DOC-e08d7fd014fde496` | property | 0.6087 | 0.4445 | ✗ | 37.4 | 4487 | 514 |  |
| 45 | `DOC-009ee40e247a0a6e` | property | 0.6083 | 0.4324 | ✗ | 38.7 | 4688 | 561 |  |
| 46 | `DOC-7a128ee6e786bd0e` | auto | 0.7024 | 0.6452 | ✗ | 39.0 | 2808 | 290 |  |
| 47 | `DOC-a0c5db2835e31ef6` | pde | 0.6010 | 0.5333 | ✗ | 41.0 | 2871 | 348 |  |
| 48 | `DOC-4df9e8f7fd1c31c3` | property | 0.6718 | 0.5143 | ✓ | 48.6 | 4883 | 933 |  |
| 49 | `DOC-0966e6d5a9e7bd71` | property | 0.7532 | 0.5263 | ✓ | 49.1 | 4683 | 968 |  |
| 50 | `DOC-d3f320a3ba9c105b` | property | 0.6333 | 0.3461 | ✗ | 58.1 | 5709 | 1338 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s7-insurance50-seqs32.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s7-insurance50-seqs32
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s7-insurance50-seqs32.yaml` | run spec |
| `reports/serving/sand032-s7-insurance50-seqs32.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s7-insurance50-seqs32/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s7-insurance50-seqs32/` | offline Braintrust-shaped rows — disposed after this report is committed |
