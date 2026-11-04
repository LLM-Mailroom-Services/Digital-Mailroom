# Run report — `sand032-s10-corr75-v2`

SAND-032 Modal × vLLM specialist extract: **75 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s10-corr75-v2` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v2_evalenv` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=16 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 75 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `7bdd96d5b20d` |
| git | `02954ee` |
| spec_hash | `5cbd245cbca7db2057b70f32141786c473e892c474d18099b92ccc8cd5716819` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **75 / 75** (errors 0) |
| **overall_extraction_score** | **0.3446** (sd 0.2038, min 0.0000, max 0.8205) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 74.337 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 180.5 s |
| preflight probe (engine answering) | 177.864 s |
| latency p50 / p95 / max | 6.82 / 13.60 / 16.35 s |
| prompt / completion tokens | 214492 / 12304 |
| throughput | 3050.9 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.016519 |
| **$ per doc (busy)** | **0.000220** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.15 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790586975.98`: requests Δ 75 (cumulative 75), measured TTFT mean 1.026 s (vLLM histogram, cumulative), prefix-cache hit 59.1%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 581.0 s over wall 74.3 s = **7.82×** effective parallelism at c8 (98% of the ideal 8×).
- **Tail:** slowest doc `DOC-8c312283e2533866` (press_release) 16.3 s = 22% of wall — p95/p50 = 1.99×.
- **Prompt length vs latency:** Pearson r = 0.48 across 75 docs (not prefill-dominated).
- **Decode budget:** mean completion 164 tok/doc, mean prompt 2860 tok/doc.
- **Subclass spread:** best `meeting_request` 0.667 (n=1), worst `demand` 0.293 (n=5).
- **Field-level extraction:** 28/75 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 181 s (driver stamps); preflight probe measured 177.9 s once the engine answered.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s10-corr75-v2-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s10-corr75-v2-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 40 | 0.3101 |
| memo | 9 | 0.3000 |
| press_release | 7 | 0.4315 |
| notice | 7 | 0.4836 |
| letter | 6 | 0.3669 |
| demand | 5 | 0.2927 |
| meeting_request | 1 | 0.6667 |
| **total** | **75** | **0.3446** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.0494 | 0.0000 | ✓ | 10.1 | 2266 | 96 |  |
| 2 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1818 | ✓ | 10.1 | 2253 | 101 |  |
| 3 | `DOC-f49b5cc25d9cb557` | letter | 0.4167 | 0.1428 | ✓ | 10.5 | 2564 | 126 |  |
| 4 | `DOC-0ab974301d63024f` | letter | 0.5000 | 0.1666 | ✓ | 10.6 | 2320 | 126 |  |
| 5 | `DOC-eaeffa14c92e7cd8` | press_release | 0.3810 | 0.1112 | ✓ | 13.3 | 3080 | 165 |  |
| 6 | `DOC-a318b50872273528` | email | 0.3485 | 0.0000 | ✓ | 13.4 | 2596 | 164 |  |
| 7 | `DOC-ab94c5d183e5f7ca` | notice | 0.1067 | 0.0000 | ✓ | 13.6 | 6207 | 169 |  |
| 8 | `DOC-383b9badb01a1a00` | email | 0.3333 | 0.1053 | ✓ | 15.2 | 5397 | 200 |  |
| 9 | `DOC-f36a37e1a9c1351e` | press_release | 0.0833 | 0.0000 | ✓ | 5.9 | 2275 | 106 |  |
| 10 | `DOC-38c54645bf0e601a` | email | 0.3704 | 0.1333 | ✓ | 5.4 | 2593 | 132 |  |
| 11 | `DOC-8754555168547e16` | email | 0.2641 | 0.0000 | ✓ | 10.6 | 3199 | 233 |  |
| 12 | `DOC-a763315b8f7cb96e` | email | 0.5000 | 0.0953 | ✓ | 8.6 | 2705 | 208 |  |
| 13 | `DOC-e624b1b9823e53f5` | memo | 0.5425 | 0.1112 | ✓ | 11.4 | 2954 | 259 |  |
| 14 | `DOC-9be315cbfa0fbd19` | email | 0.1605 | 0.0000 | ✓ | 12.9 | 4402 | 294 |  |
| 15 | `DOC-e72ff16f78525d0f` | email | 0.4444 | 0.1250 | ✓ | 9.9 | 2811 | 252 |  |
| 16 | `DOC-553256644e7b4547` | email | 0.3333 | 0.1428 | ✓ | 4.8 | 2341 | 119 |  |
| 17 | `DOC-c45ecc852b2cb0f4` | meeting_request | 0.6667 | 0.2499 | ✓ | 5.8 | 2391 | 148 |  |
| 18 | `DOC-c71d3ca0b727a0d4` | email | 0.3333 | 0.1428 | ✓ | 5.1 | 2347 | 129 |  |
| 19 | `DOC-b5d016f4b2abaa39` | email | 0.3333 | 0.1818 | ✓ | 4.0 | 2271 | 104 |  |
| 20 | `DOC-9ec94a2619e46dfb` | email | 0.4000 | 0.1333 | ✓ | 6.2 | 2310 | 143 |  |
| 21 | `DOC-8c312283e2533866` | press_release | 0.4737 | 0.1333 | ✓ | 16.3 | 2636 | 415 |  |
| 22 | `DOC-cb4f8fb4ccb52f44` | email | 0.3333 | 0.1428 | ✓ | 5.3 | 2307 | 123 |  |
| 23 | `DOC-228e51bba45b5c7d` | email | 0.2582 | 0.0000 | ✓ | 7.2 | 3074 | 174 |  |
| 24 | `DOC-f4b4c8c623ccb915` | press_release | 0.1067 | 0.0000 | ✓ | 16.3 | 4931 | 431 |  |
| 25 | `DOC-44b1e5a60b363d3e` | letter | 0.3333 | 0.1333 | ✓ | 7.8 | 2564 | 163 |  |
| 26 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 11.1 | 2643 | 270 |  |
| 27 | `DOC-19d9fd70a08d306b` | notice | 0.3333 | 0.1176 | ✓ | 7.0 | 3007 | 175 |  |
| 28 | `DOC-314aa51db90c8c92` | memo | 0.3333 | 0.1000 | ✓ | 8.9 | 3109 | 229 |  |
| 29 | `DOC-99c7dacadccd6e78` | press_release | 0.5088 | 0.1250 | ✓ | 5.7 | 2364 | 138 |  |
| 30 | `DOC-8eed243667c985bd` | email | 0.3333 | 0.1333 | ✓ | 6.2 | 2717 | 150 |  |
| 31 | `DOC-bc3f4676ac0c2e16` | letter | 0.3333 | 0.1176 | ✓ | 6.4 | 3926 | 147 |  |
| 32 | `DOC-2bdbf0be591edea6` | memo | 0.0800 | 0.0000 | ✓ | 4.4 | 2297 | 117 |  |
| 33 | `DOC-1dcf4dfd5ec6defb` | email | 0.5278 | 0.0953 | ✓ | 12.2 | 3570 | 309 |  |
| 34 | `DOC-4eb0e9385b81cc4b` | email | 0.2281 | 0.0000 | ✓ | 6.2 | 2352 | 138 |  |
| 35 | `DOC-c4debd478f2c06e0` | email | 0.4217 | 0.1428 | ✓ | 5.8 | 2504 | 132 |  |
| 36 | `DOC-9d0aa39a8ac68936` | email | 0.3333 | 0.2222 | ✓ | 4.1 | 2239 | 87 |  |
| 37 | `DOC-47647a5fdcd45666` | email | 0.3333 | 0.1333 | ✓ | 5.3 | 2484 | 130 |  |
| 38 | `DOC-690cb07fef21747b` | email | 0.0833 | 0.0000 | ✓ | 6.1 | 2522 | 139 |  |
| 39 | `DOC-36b9a080db747f3d` | demand | 0.0667 | 0.0000 | ✓ | 6.0 | 3426 | 147 |  |
| 40 | `DOC-91f5631a20c62dc5` | email | 0.6877 | 0.1176 | ✓ | 8.8 | 2490 | 215 |  |
| 41 | `DOC-d3e421962da61b35` | notice | 0.7917 | 0.2354 | ✓ | 7.2 | 2697 | 168 |  |
| 42 | `DOC-38265bcc6ecfecc3` | email | 0.0000 | 0.0000 | ✓ | 4.5 | 2297 | 94 |  |
| 43 | `DOC-cc6e6dece6a787c2` | demand | 0.4709 | 0.1250 | ✓ | 6.9 | 2358 | 185 |  |
| 44 | `DOC-20b4e31d9a4bf994` | email | 0.2844 | 0.0000 | ✓ | 5.5 | 2423 | 123 |  |
| 45 | `DOC-16dfd03aed14e557` | email | 0.0000 | 0.0000 | ✓ | 3.5 | 2242 | 76 |  |
| 46 | `DOC-d0c241ea24439be2` | email | 0.5101 | 0.2222 | ✓ | 4.5 | 2361 | 95 |  |
| 47 | `DOC-4ab559dfb4d79b6d` | email | 0.3333 | 0.1538 | ✓ | 6.1 | 2325 | 128 |  |
| 48 | `DOC-cd6877aeb3f2f7e4` | email | 0.1569 | 0.0000 | ✓ | 6.7 | 2831 | 153 |  |
| 49 | `DOC-a8efd6e4c4d49aaf` | email | 0.2190 | 0.0000 | ✓ | 8.7 | 2508 | 180 |  |
| 50 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2857 | ✓ | 6.8 | 2544 | 134 |  |
| 51 | `DOC-21460a9f6d7e6348` | memo | 0.7255 | 0.2354 | ✓ | 7.4 | 2374 | 132 |  |
| 52 | `DOC-d3d85dc1b1514bec` | notice | 0.8205 | 0.2354 | ✓ | 9.0 | 2481 | 175 |  |
| 53 | `DOC-2cde0c6d0c70b02b` | memo | 0.0784 | 0.0000 | ✓ | 9.5 | 2774 | 180 |  |
| 54 | `DOC-9b2bc061621a56be` | email | 0.3011 | 0.0000 | ✓ | 9.6 | 2611 | 179 |  |
| 55 | `DOC-f6a9a00e53cc7973` | notice | 0.3333 | 0.1250 | ✓ | 8.4 | 7451 | 145 |  |
| 56 | `DOC-e25814bd08d418aa` | email | 0.2467 | 0.0000 | ✓ | 10.2 | 2590 | 207 |  |
| 57 | `DOC-8c7847bfbb91d578` | demand | 0.0000 | 0.0000 | ✓ | 6.5 | 3292 | 141 |  |
| 58 | `DOC-d6e2bbd8c5e394a4` | demand | 0.8095 | 0.3636 | ✓ | 4.9 | 2300 | 123 |  |
| 59 | `DOC-6aa30fb5a4e67d76` | email | 0.2696 | 0.0000 | ✓ | 8.2 | 3249 | 170 |  |
| 60 | `DOC-595ab9fc19465909` | notice | 0.3333 | 0.1112 | ✓ | 6.3 | 2408 | 152 |  |
| 61 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 3.7 | 2236 | 76 |  |
| 62 | `DOC-a6fff0ef0e406461` | email | 0.3810 | 0.1250 | ✓ | 6.6 | 2411 | 156 |  |
| 63 | `DOC-ee6bae4d269c1911` | memo | 0.3333 | 0.1112 | ✓ | 10.7 | 3398 | 255 |  |
| 64 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1666 | ✓ | 5.7 | 2292 | 128 |  |
| 65 | `DOC-76375ebb4cd91de9` | letter | 0.1111 | 0.0000 | ✓ | 8.8 | 3084 | 214 |  |
| 66 | `DOC-ff15276697cdfbb2` | demand | 0.1162 | 0.0000 | ✓ | 8.1 | 2890 | 163 |  |
| 67 | `DOC-95a872ee4ff237d5` | email | 0.2034 | 0.0000 | ✓ | 6.7 | 2747 | 138 |  |
| 68 | `DOC-8ce704cea54b1469` | press_release | 0.6667 | 0.2354 | ✓ | 7.9 | 3233 | 165 |  |
| 69 | `DOC-96438076efc6cc7b` | email | 0.3333 | 0.1333 | ✓ | 6.4 | 2346 | 142 |  |
| 70 | `DOC-9422c8775b387935` | press_release | 0.8000 | 0.2222 | ✓ | 7.0 | 3156 | 159 |  |
| 71 | `DOC-1f3f868558fc4a6e` | email | 0.3810 | 0.1666 | ✓ | 4.5 | 2413 | 113 |  |
| 72 | `DOC-c01ab1c1c673f355` | letter | 0.5069 | 0.1333 | ✓ | 5.5 | 2431 | 130 |  |
| 73 | `DOC-17ac4251c7d94cea` | email | 0.1212 | 0.0000 | ✓ | 3.7 | 2298 | 112 |  |
| 74 | `DOC-f7af031d61f7d7f5` | email | 0.3333 | 0.1176 | ✓ | 5.9 | 4535 | 158 |  |
| 75 | `DOC-5b63f9fe205d564b` | email | 0.5800 | 0.1112 | ✓ | 4.5 | 2462 | 152 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s10-corr75-v2.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s10-corr75-v2
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s10-corr75-v2.yaml` | run spec |
| `reports/serving/sand032-s10-corr75-v2.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s10-corr75-v2/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s10-corr75-v2/` | offline Braintrust-shaped rows — disposed after this report is committed |
