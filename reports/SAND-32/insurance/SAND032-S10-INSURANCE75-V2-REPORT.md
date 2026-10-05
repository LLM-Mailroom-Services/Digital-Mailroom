# Run report — `sand032-s10-insurance75-v2`

SAND-032 Modal × vLLM specialist extract: **75 insurance_claim docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s10-insurance75-v2` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v2_evalenv` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=16 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 75 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `eea4a5641e42` |
| git | `02954ee (dirty)` |
| spec_hash | `333aee1056dd2bb242f30e2639b63e5298cd0e872b3bd96637834f88adeaea94` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **75 / 75** (errors 0) |
| **overall_extraction_score** | **0.6675** (sd 0.0685, min 0.5331, max 0.8455) |
| schema_valid_rate | 0.187 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 145.814 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.441 s |
| latency p50 / p95 / max | 13.08 / 24.43 / 41.05 s |
| prompt / completion tokens | 247122 / 28677 |
| throughput | 1891.4 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.032403 |
| **$ per doc (busy)** | **0.000432** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.2 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790586975.98`: requests Δ 75 (cumulative 150), measured TTFT mean 1.029 s (vLLM histogram, cumulative), prefix-cache hit 57.4%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 1099.8 s over wall 145.8 s = **7.54×** effective parallelism at c8 (94% of the ideal 8×).
- **Tail:** slowest doc `DOC-0966e6d5a9e7bd71` (property) 41.0 s = 28% of wall — p95/p50 = 1.87×.
- **Prompt length vs latency:** Pearson r = 0.75 across 75 docs (prefill-bound).
- **Decode budget:** mean completion 382 tok/doc, mean prompt 3295 tok/doc.
- **Subclass spread:** best `auto` 0.721 (n=24), worst `pde` 0.590 (n=8).
- **Field-level extraction:** 0/75 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s10-insurance75-v2-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s10-insurance75-v2-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| auto | 24 | 0.7211 |
| carrier | 12 | 0.6395 |
| property | 12 | 0.6708 |
| outpatient | 11 | 0.6213 |
| inpatient | 8 | 0.6845 |
| pde | 8 | 0.5900 |
| **total** | **75** | **0.6675** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c0e145a5a0a0d4bd` | auto | 0.7930 | 0.6667 | ✗ | 13.1 | 2866 | 348 |  |
| 2 | `DOC-884dc887726dcfa5` | auto | 0.8000 | 0.6667 | ✗ | 13.1 | 2866 | 336 |  |
| 3 | `DOC-ee3512878a0003b7` | auto | 0.7930 | 0.6667 | ✗ | 13.1 | 2864 | 347 |  |
| 4 | `DOC-8dcc97d49f2004f5` | auto | 0.7786 | 0.6667 | ✗ | 13.1 | 2868 | 348 |  |
| 5 | `DOC-edc5811634a19b7a` | auto | 0.8141 | 0.6667 | ✗ | 13.1 | 2868 | 359 |  |
| 6 | `DOC-dc33a3e5a8cf5b6b` | auto | 0.7967 | 0.6667 | ✗ | 13.3 | 2865 | 368 |  |
| 7 | `DOC-4cd6ca1171e8885e` | auto | 0.7750 | 0.6667 | ✗ | 13.5 | 2865 | 369 |  |
| 8 | `DOC-bf5c2cc12aca8aad` | auto | 0.8455 | 0.7027 | ✗ | 16.1 | 2867 | 387 |  |
| 9 | `DOC-d5e1b8ed3350fb36` | carrier | 0.6325 | 0.5806 | ✗ | 12.1 | 3002 | 334 |  |
| 10 | `DOC-2d2ec2092b012662` | auto | 0.7930 | 0.6486 | ✗ | 12.3 | 2864 | 343 |  |
| 11 | `DOC-8cf0d471d8ec695d` | auto | 0.7781 | 0.6285 | ✗ | 12.4 | 2863 | 343 |  |
| 12 | `DOC-2d574972cb7a2f63` | carrier | 0.6360 | 0.5294 | ✗ | 12.2 | 3013 | 346 |  |
| 13 | `DOC-bce319dabbc42e89` | auto | 0.7857 | 0.6667 | ✗ | 12.5 | 2864 | 353 |  |
| 14 | `DOC-4dda6e74e78edd70` | carrier | 0.6387 | 0.5294 | ✗ | 13.2 | 2982 | 362 |  |
| 15 | `DOC-b1fad3c1c6ab0f6a` | carrier | 0.6442 | 0.5454 | ✗ | 13.1 | 2982 | 361 |  |
| 16 | `DOC-dcb4333f78bfe249` | carrier | 0.6411 | 0.5806 | ✗ | 11.0 | 2967 | 332 |  |
| 17 | `DOC-9f75d0ce11867685` | carrier | 0.6345 | 0.5806 | ✗ | 11.0 | 3077 | 323 |  |
| 18 | `DOC-e7bc347246615526` | carrier | 0.6377 | 0.5806 | ✗ | 12.2 | 2982 | 333 |  |
| 19 | `DOC-4fd4cf5db3cfdb47` | carrier | 0.6398 | 0.5806 | ✗ | 12.4 | 2973 | 333 |  |
| 20 | `DOC-c89c9134db9e8f1e` | carrier | 0.6398 | 0.5806 | ✗ | 12.0 | 3035 | 334 |  |
| 21 | `DOC-fa698a867428a0ed` | carrier | 0.6353 | 0.5294 | ✗ | 12.1 | 3049 | 335 |  |
| 22 | `DOC-28295fb236ac02ca` | carrier | 0.6462 | 0.5143 | ✗ | 11.6 | 2992 | 338 |  |
| 23 | `DOC-1e95a2ae82adc61c` | inpatient | 0.6928 | 0.5294 | ✓ | 13.5 | 3176 | 360 |  |
| 24 | `DOC-3ddb0ec69ce4f93f` | carrier | 0.6487 | 0.5454 | ✗ | 15.3 | 2982 | 368 |  |
| 25 | `DOC-b3be1f4b2b6142ed` | auto | 0.6955 | 0.5883 | ✗ | 9.2 | 2848 | 287 |  |
| 26 | `DOC-e572745d557c7fbf` | inpatient | 0.6747 | 0.4706 | ✗ | 13.8 | 3158 | 364 |  |
| 27 | `DOC-a0be2aba09a3f580` | inpatient | 0.6842 | 0.5454 | ✗ | 10.9 | 3128 | 335 |  |
| 28 | `DOC-2435c398b95844bc` | inpatient | 0.6879 | 0.4865 | ✓ | 15.2 | 3113 | 398 |  |
| 29 | `DOC-85e24caa52979f50` | inpatient | 0.6836 | 0.5000 | ✓ | 16.3 | 3154 | 432 |  |
| 30 | `DOC-17abdc452037b6eb` | inpatient | 0.6921 | 0.5000 | ✓ | 16.6 | 3162 | 445 |  |
| 31 | `DOC-576c9233159914e3` | inpatient | 0.6834 | 0.4865 | ✓ | 18.2 | 3113 | 477 |  |
| 32 | `DOC-a1a2afde18ded42d` | inpatient | 0.6774 | 0.4615 | ✓ | 18.3 | 3119 | 482 |  |
| 33 | `DOC-7eb9512b93dd2f13` | auto | 0.6154 | 0.5294 | ✗ | 11.1 | 2840 | 303 |  |
| 34 | `DOC-7a128ee6e786bd0e` | auto | 0.6154 | 0.5454 | ✗ | 10.6 | 2841 | 290 |  |
| 35 | `DOC-c0d9bf1e6be4ad51` | auto | 0.6348 | 0.5625 | ✗ | 10.9 | 2841 | 302 |  |
| 36 | `DOC-e0c3e056397d7806` | auto | 0.6375 | 0.5294 | ✗ | 10.9 | 2845 | 297 |  |
| 37 | `DOC-63692b8a349be3ad` | auto | 0.6154 | 0.5294 | ✗ | 10.9 | 2841 | 299 |  |
| 38 | `DOC-596b1f881ecf4a8a` | auto | 0.7163 | 0.5883 | ✗ | 10.8 | 2839 | 304 |  |
| 39 | `DOC-b28fe495a873ca59` | auto | 0.6895 | 0.6452 | ✗ | 9.5 | 2840 | 271 |  |
| 40 | `DOC-db1d2b3ea4d2d24f` | auto | 0.6154 | 0.5294 | ✗ | 11.1 | 2837 | 297 |  |
| 41 | `DOC-df5ebe3e7263b6c6` | auto | 0.6314 | 0.5625 | ✗ | 10.8 | 2848 | 284 |  |
| 42 | `DOC-826b2ac305c2b791` | auto | 0.6955 | 0.5883 | ✗ | 10.2 | 2843 | 273 |  |
| 43 | `DOC-d6d57b7a18431923` | auto | 0.7020 | 0.6452 | ✗ | 10.0 | 2836 | 273 |  |
| 44 | `DOC-b6993f654cb64a38` | auto | 0.6895 | 0.6452 | ✗ | 10.6 | 2843 | 274 |  |
| 45 | `DOC-aacaf03452045b89` | outpatient | 0.6131 | 0.4849 | ✗ | 13.2 | 3014 | 354 |  |
| 46 | `DOC-4348717727f6d6b4` | outpatient | 0.6206 | 0.4849 | ✗ | 11.1 | 3037 | 329 |  |
| 47 | `DOC-c7f433bb70f6ab0e` | outpatient | 0.6357 | 0.4849 | ✗ | 13.4 | 3019 | 376 |  |
| 48 | `DOC-1bc5f212af3bd4c2` | outpatient | 0.6279 | 0.4849 | ✗ | 15.4 | 3023 | 413 |  |
| 49 | `DOC-ab3b194998a42322` | outpatient | 0.6413 | 0.5000 | ✗ | 12.0 | 3049 | 337 |  |
| 50 | `DOC-fc5aa23171d955cf` | outpatient | 0.6131 | 0.4849 | ✗ | 12.7 | 3005 | 359 |  |
| 51 | `DOC-79244cf752911808` | outpatient | 0.6176 | 0.4849 | ✗ | 11.9 | 3002 | 333 |  |
| 52 | `DOC-d62e0d8ac987119d` | outpatient | 0.6176 | 0.4849 | ✗ | 15.5 | 3064 | 421 |  |
| 53 | `DOC-c6339c641d801de5` | outpatient | 0.6152 | 0.4849 | ✗ | 11.1 | 3056 | 316 |  |
| 54 | `DOC-1f15cce85d6c9f8f` | outpatient | 0.6138 | 0.4572 | ✗ | 13.6 | 3045 | 373 |  |
| 55 | `DOC-4e21681f375a247d` | outpatient | 0.6188 | 0.4849 | ✗ | 13.5 | 3018 | 373 |  |
| 56 | `DOC-27b23fd94cc70d9d` | pde | 0.5844 | 0.5517 | ✗ | 13.1 | 2923 | 370 |  |
| 57 | `DOC-a0c5db2835e31ef6` | pde | 0.6010 | 0.5517 | ✗ | 12.8 | 2904 | 334 |  |
| 58 | `DOC-01f1577c446c646d` | pde | 0.5993 | 0.5517 | ✗ | 12.3 | 2901 | 332 |  |
| 59 | `DOC-804fbeed2ab25ae8` | pde | 0.5809 | 0.5333 | ✗ | 14.0 | 2906 | 340 |  |
| 60 | `DOC-13597dd5f0ca00c4` | pde | 0.5855 | 0.5517 | ✗ | 13.7 | 2921 | 330 |  |
| 61 | `DOC-9178d6cdb14bfac9` | pde | 0.5853 | 0.5517 | ✗ | 15.5 | 2905 | 337 |  |
| 62 | `DOC-f80fe4950664c6e0` | pde | 0.5952 | 0.4849 | ✗ | 17.3 | 2917 | 360 |  |
| 63 | `DOC-b199013b1823372d` | pde | 0.5886 | 0.5000 | ✗ | 17.5 | 2915 | 370 |  |
| 64 | `DOC-81a444ef841aea5f` | property | 0.5579 | 0.3889 | ✗ | 23.6 | 4920 | 520 |  |
| 65 | `DOC-91fe413a7105d6fc` | property | 0.7369 | 0.5405 | ✓ | 22.1 | 5139 | 499 |  |
| 66 | `DOC-65bd322c23c62250` | property | 0.6398 | 0.4210 | ✓ | 25.8 | 4654 | 569 |  |
| 67 | `DOC-d3f320a3ba9c105b` | property | 0.7438 | 0.5143 | ✓ | 21.0 | 5742 | 446 |  |
| 68 | `DOC-4df9e8f7fd1c31c3` | property | 0.6718 | 0.4737 | ✓ | 28.1 | 4916 | 604 |  |
| 69 | `DOC-e08d7fd014fde496` | property | 0.6087 | 0.4445 | ✗ | 22.9 | 4520 | 510 |  |
| 70 | `DOC-cdd4f26b4f9db00c` | property | 0.6548 | 0.4445 | ✗ | 24.4 | 4822 | 564 |  |
| 71 | `DOC-0bdda3ecc67bae80` | property | 0.7223 | 0.5000 | ✓ | 18.0 | 5031 | 410 |  |
| 72 | `DOC-0966e6d5a9e7bd71` | property | 0.7351 | 0.4865 | ✓ | 41.0 | 4716 | 970 |  |
| 73 | `DOC-06844413e427f8c2` | property | 0.7598 | 0.5556 | ✓ | 16.2 | 5369 | 512 |  |
| 74 | `DOC-009ee40e247a0a6e` | property | 0.5331 | 0.3784 | ✗ | 20.1 | 4721 | 582 |  |
| 75 | `DOC-db02c129ee1d5261` | property | 0.6856 | 0.4878 | ✓ | 23.4 | 6327 | 687 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s10-insurance75-v2.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s10-insurance75-v2
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s10-insurance75-v2.yaml` | run spec |
| `reports/serving/sand032-s10-insurance75-v2.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s10-insurance75-v2/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s10-insurance75-v2/` | offline Braintrust-shaped rows — disposed after this report is committed |
