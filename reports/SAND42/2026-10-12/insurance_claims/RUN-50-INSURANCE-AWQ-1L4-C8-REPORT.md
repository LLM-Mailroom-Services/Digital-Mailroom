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
| **overall_extraction_score** | **0.668108** |
| schema_valid_rate | 0.260000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 147.735 |
| gpu_seconds | 148.152 |
| estimated GPU cost | 0.032923 |
| **GPU $/doc** | **0.00065846** |
| latency p50 / max (s) | 14.013857 / 64.335598 |
| prompt / completion tokens | 165315 / 22190 |
| concurrency speedup (Σlat/wall) | 5.61 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-2a33a6c34834e769` | True | 0.629800 | 13.4 | 2953 | 337 | None |
| 2 | `DOC-2a55a2b5324659f8` | True | 0.809800 | 13.4 | 2865 | 345 | None |
| 3 | `DOC-629fb5789dfd10ca` | True | 0.797900 | 13.4 | 2836 | 349 | None |
| 4 | `DOC-158c0b74df673b81` | True | 0.644200 | 13.5 | 2939 | 350 | None |
| 5 | `DOC-e7c196f508907c6f` | True | 0.783000 | 14.0 | 2834 | 366 | None |
| 6 | `DOC-e2a58ed4c02470c0` | True | 0.780500 | 16.0 | 2835 | 373 | None |
| 7 | `DOC-991cb72cb83c7a6c` | True | 0.644200 | 16.0 | 2941 | 374 | None |
| 8 | `DOC-2aea7f6dc44b37e1` | True | 0.774100 | 16.3 | 2835 | 387 | None |
| 9 | `DOC-9ba0a3d4c680b976` | True | 0.639800 | 12.8 | 2982 | 334 | None |
| 10 | `DOC-997823d9605a4a59` | True | 0.639800 | 13.3 | 2973 | 355 | None |
| 11 | `DOC-968c9605eab0a87d` | True | 0.644200 | 13.8 | 2942 | 354 | None |
| 12 | `DOC-9a6f58879fcb3367` | True | 0.644200 | 15.1 | 2946 | 374 | None |
| 13 | `DOC-ef79520b2f50217b` | True | 0.689200 | 13.5 | 3138 | 382 | None |
| 14 | `DOC-5c4e70db54374e72` | True | 0.687400 | 14.2 | 3151 | 398 | None |
| 15 | `DOC-2435c398b95844bc` | True | 0.687900 | 16.8 | 3080 | 469 | None |
| 16 | `DOC-5b1e8e2aed95c089` | True | 0.687300 | 20.4 | 3123 | 543 | None |
| 17 | `DOC-00d28a1df0e3f6ba` | True | 0.697100 | 9.1 | 2812 | 261 | None |
| 18 | `DOC-728d06b610b25244` | True | 0.704300 | 9.1 | 2804 | 273 | None |
| 19 | `DOC-9051d4cf8d7ab452` | True | 0.710000 | 13.1 | 3115 | 352 | None |
| 20 | `DOC-5060222215c75aa6` | True | 0.674500 | 9.7 | 2801 | 287 | None |
| 21 | `DOC-e4b1466ee8d1ff19` | True | 0.703700 | 14.9 | 3113 | 400 | None |
| 22 | `DOC-00ccdcb0154a8629` | True | 0.622800 | 10.3 | 2812 | 281 | None |
| 23 | `DOC-f5e6c0de5f1d8593` | True | 0.716900 | 11.2 | 2812 | 307 | None |
| 24 | `DOC-d8df43ed4d8faf89` | True | 0.688800 | 18.7 | 3107 | 528 | None |
| 25 | `DOC-c34baab0b5fe378a` | True | 0.689900 | 10.8 | 2807 | 280 | None |
| 26 | `DOC-cbfcdb6f42cf2ae6` | True | 0.687200 | 10.7 | 2806 | 275 | None |
| 27 | `DOC-6f6fc9762418a70f` | True | 0.704800 | 11.5 | 2811 | 294 | None |
| 28 | `DOC-29e384939c31d44a` | True | 0.613100 | 13.8 | 3010 | 371 | None |
| 29 | `DOC-2d7cc160b78a69c5` | True | 0.644200 | 14.1 | 2979 | 396 | None |
| 30 | `DOC-87c0c53132830a6c` | True | 0.613100 | 13.0 | 2993 | 374 | None |
| 31 | `DOC-0cdb706a0cdbe3b6` | True | 0.626500 | 12.9 | 2981 | 381 | None |
| 32 | `DOC-4e21681f375a247d` | True | 0.618800 | 13.1 | 2985 | 379 | None |
| 33 | `DOC-27b23fd94cc70d9d` | True | 0.605200 | 12.0 | 2890 | 353 | None |
| 34 | `DOC-364435343e0a2250` | True | 0.647400 | 13.8 | 3020 | 393 | None |
| 35 | `DOC-3ae2dc5d624e2120` | True | 0.599900 | 12.4 | 2871 | 333 | None |
| 36 | `DOC-7bd9dbc1b39ad41d` | True | 0.603100 | 24.3 | 3171 | 655 | None |
| 37 | `DOC-93c8d133c296d536` | True | 0.579600 | 14.2 | 2879 | 334 | None |
| 38 | `DOC-44bcd388c4710b71` | True | 0.566300 | 15.2 | 2884 | 343 | None |
| 39 | `DOC-91da307f80433ae3` | True | 0.579600 | 15.8 | 2894 | 358 | None |
| 40 | `DOC-90338506fc792f32` | True | 0.579600 | 17.6 | 2882 | 355 | None |
| 41 | `DOC-164aa748f84cef54` | True | 0.589900 | 19.8 | 2911 | 403 | None |
| 42 | `DOC-7f1f866b022cee63` | True | 0.787300 | 23.3 | 4985 | 509 | None |
| 43 | `DOC-73d64bbeb296bd95` | True | 0.602300 | 26.9 | 4524 | 573 | None |
| 44 | `DOC-384665a051d0fcd6` | True | 0.680200 | 22.0 | 5208 | 498 | None |
| 45 | `DOC-85314478b81710d9` | True | 0.628700 | 18.5 | 5285 | 422 | None |
| 46 | `DOC-ab18f15b7a51f1ab` | True | 0.741400 | 21.0 | 5538 | 499 | None |
| 47 | `DOC-6dcc0b9ba494c25b` | True | 0.746700 | 17.9 | 5114 | 532 | None |
| 48 | `DOC-5b97ae3f8558703c` | True | 0.691200 | 17.6 | 4565 | 599 | None |
| 49 | `DOC-1076ac5b4b0df386` | True | 0.591600 | 40.7 | 4482 | 1375 | None |
| 50 | `DOC-02f77aa77391a8c2` | True | 0.686400 | 64.3 | 5091 | 2127 | None |
