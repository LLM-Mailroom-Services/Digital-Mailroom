# Run report — `sand42-50-insurance-claims-specialist-awq-1l4-c8`

Dated cell stem: `RUN-50-INSURANCE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-insurance-claims-specialist-awq-1l4-c8` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `8f77e131022df5bb6cc49edf9d6e778d89e451b09b73fa9d7ca98b53d3647bb5` |
| dataset fingerprint | `f4fdcee45e7f` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.669514** |
| schema_valid_rate | 0.300000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 100.814 |
| gpu_seconds | 101.285 |
| estimated GPU cost | 0.022508 |
| **GPU $/doc** | **0.00045016** |
| latency p50 / max (s) | 13.578094 / 45.852576 |
| prompt / completion tokens | 165315 / 21251 |
| concurrency speedup (Σlat/wall) | 7.80 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-2a33a6c34834e769` | True | 0.629800 | 13.2 | 2953 | 341 | None |
| 2 | `DOC-e7c196f508907c6f` | True | 0.783000 | 13.2 | 2834 | 362 | None |
| 3 | `DOC-158c0b74df673b81` | True | 0.644200 | 13.2 | 2939 | 362 | None |
| 4 | `DOC-629fb5789dfd10ca` | True | 0.797900 | 13.2 | 2836 | 361 | None |
| 5 | `DOC-2a55a2b5324659f8` | True | 0.809800 | 13.2 | 2865 | 347 | None |
| 6 | `DOC-e2a58ed4c02470c0` | True | 0.767100 | 13.3 | 2835 | 366 | None |
| 7 | `DOC-991cb72cb83c7a6c` | True | 0.644200 | 13.4 | 2941 | 374 | None |
| 8 | `DOC-2aea7f6dc44b37e1` | True | 0.774100 | 13.7 | 2835 | 387 | None |
| 9 | `DOC-9ba0a3d4c680b976` | True | 0.639800 | 12.5 | 2982 | 334 | None |
| 10 | `DOC-968c9605eab0a87d` | True | 0.644200 | 13.0 | 2942 | 354 | None |
| 11 | `DOC-9a6f58879fcb3367` | True | 0.648700 | 14.3 | 2946 | 375 | None |
| 12 | `DOC-997823d9605a4a59` | True | 0.644200 | 14.5 | 2973 | 382 | None |
| 13 | `DOC-ef79520b2f50217b` | True | 0.689200 | 14.2 | 3138 | 390 | None |
| 14 | `DOC-2435c398b95844bc` | True | 0.679500 | 17.8 | 3080 | 478 | None |
| 15 | `DOC-5b1e8e2aed95c089` | True | 0.687300 | 19.9 | 3123 | 542 | None |
| 16 | `DOC-5c4e70db54374e72` | True | 0.676300 | 21.0 | 3151 | 573 | None |
| 17 | `DOC-00d28a1df0e3f6ba` | True | 0.697100 | 9.1 | 2812 | 261 | None |
| 18 | `DOC-5060222215c75aa6` | True | 0.741200 | 10.1 | 2801 | 296 | None |
| 19 | `DOC-9051d4cf8d7ab452` | True | 0.710000 | 13.4 | 3115 | 366 | None |
| 20 | `DOC-728d06b610b25244` | True | 0.704300 | 9.6 | 2804 | 273 | None |
| 21 | `DOC-e4b1466ee8d1ff19` | True | 0.697000 | 16.3 | 3113 | 468 | None |
| 22 | `DOC-00ccdcb0154a8629` | True | 0.622800 | 9.8 | 2812 | 281 | None |
| 23 | `DOC-f5e6c0de5f1d8593` | True | 0.706000 | 11.4 | 2812 | 327 | None |
| 24 | `DOC-d8df43ed4d8faf89` | True | 0.688800 | 18.3 | 3107 | 529 | None |
| 25 | `DOC-c34baab0b5fe378a` | True | 0.623200 | 10.7 | 2807 | 286 | None |
| 26 | `DOC-cbfcdb6f42cf2ae6` | True | 0.687200 | 10.7 | 2806 | 285 | None |
| 27 | `DOC-6f6fc9762418a70f` | True | 0.712300 | 11.4 | 2811 | 310 | None |
| 28 | `DOC-29e384939c31d44a` | True | 0.613100 | 11.4 | 3010 | 306 | None |
| 29 | `DOC-2d7cc160b78a69c5` | True | 0.618300 | 13.1 | 2979 | 371 | None |
| 30 | `DOC-0cdb706a0cdbe3b6` | True | 0.613100 | 12.6 | 2981 | 363 | None |
| 31 | `DOC-87c0c53132830a6c` | True | 0.626500 | 14.1 | 2993 | 410 | None |
| 32 | `DOC-4e21681f375a247d` | True | 0.642600 | 13.5 | 2985 | 400 | None |
| 33 | `DOC-364435343e0a2250` | True | 0.647400 | 13.2 | 3020 | 393 | None |
| 34 | `DOC-27b23fd94cc70d9d` | True | 0.605200 | 11.8 | 2890 | 353 | None |
| 35 | `DOC-3ae2dc5d624e2120` | True | 0.599900 | 12.5 | 2871 | 347 | None |
| 36 | `DOC-7bd9dbc1b39ad41d` | True | 0.603600 | 22.0 | 3171 | 625 | None |
| 37 | `DOC-93c8d133c296d536` | True | 0.566300 | 14.0 | 2879 | 338 | None |
| 38 | `DOC-91da307f80433ae3` | True | 0.579600 | 15.5 | 2894 | 358 | None |
| 39 | `DOC-44bcd388c4710b71` | True | 0.583700 | 16.9 | 2884 | 374 | None |
| 40 | `DOC-90338506fc792f32` | True | 0.595600 | 17.6 | 2882 | 367 | None |
| 41 | `DOC-164aa748f84cef54` | True | 0.581000 | 19.0 | 2911 | 394 | None |
| 42 | `DOC-73d64bbeb296bd95` | True | 0.619800 | 24.6 | 4524 | 544 | None |
| 43 | `DOC-7f1f866b022cee63` | True | 0.730900 | 22.5 | 4985 | 500 | None |
| 44 | `DOC-384665a051d0fcd6` | True | 0.679800 | 21.8 | 5208 | 505 | None |
| 45 | `DOC-85314478b81710d9` | True | 0.684400 | 17.2 | 5285 | 421 | None |
| 46 | `DOC-ab18f15b7a51f1ab` | True | 0.744600 | 20.5 | 5538 | 495 | None |
| 47 | `DOC-1076ac5b4b0df386` | True | 0.656900 | 16.2 | 4482 | 429 | None |
| 48 | `DOC-6dcc0b9ba494c25b` | True | 0.746700 | 18.8 | 5114 | 576 | None |
| 49 | `DOC-02f77aa77391a8c2` | True | 0.696300 | 45.9 | 5091 | 1369 | None |
| 50 | `DOC-5b97ae3f8558703c` | True | 0.691200 | 27.1 | 4565 | 1003 | None |
