# Run report — `sand42-50-insurance-claims-specialist-awq-2l4-c32`

Dated cell stem: `RUN-50-INSURANCE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-insurance-claims-specialist-awq-2l4-c32` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `676fd83f131d1e934335e7cf50d430c187ff134877993d5c13d4936caef819df` |
| dataset fingerprint | `f4fdcee45e7f` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.666248** |
| schema_valid_rate | 0.300000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 75.887 |
| gpu_seconds | 76.235 |
| estimated GPU cost | 0.033882 |
| **GPU $/doc** | **0.00067764** |
| latency p50 / max (s) | 23.959121 / 46.453676 |
| prompt / completion tokens | 165315 / 20600 |
| concurrency speedup (Σlat/wall) | 16.85 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-158c0b74df673b81` | True | 0.635300 | 12.0 | 2939 | 343 | None |
| 2 | `DOC-e7c196f508907c6f` | True | 0.783000 | 12.0 | 2834 | 362 | None |
| 3 | `DOC-997823d9605a4a59` | True | 0.644200 | 12.4 | 2973 | 382 | None |
| 4 | `DOC-ef79520b2f50217b` | True | 0.689200 | 12.9 | 3138 | 395 | None |
| 5 | `DOC-87c0c53132830a6c` | True | 0.626500 | 12.9 | 2993 | 397 | None |
| 6 | `DOC-00ccdcb0154a8629` | True | 0.622800 | 16.4 | 2812 | 285 | None |
| 7 | `DOC-5060222215c75aa6` | True | 0.674500 | 16.5 | 2801 | 287 | None |
| 8 | `DOC-728d06b610b25244` | True | 0.721800 | 16.5 | 2804 | 289 | None |
| 9 | `DOC-c34baab0b5fe378a` | True | 0.623200 | 18.4 | 2807 | 308 | None |
| 10 | `DOC-2a33a6c34834e769` | True | 0.629800 | 19.6 | 2953 | 337 | None |
| 11 | `DOC-9ba0a3d4c680b976` | True | 0.639800 | 20.0 | 2982 | 334 | None |
| 12 | `DOC-629fb5789dfd10ca` | True | 0.797900 | 20.7 | 2836 | 349 | None |
| 13 | `DOC-9051d4cf8d7ab452` | True | 0.710000 | 21.1 | 3115 | 352 | None |
| 14 | `DOC-9a6f58879fcb3367` | True | 0.644200 | 21.9 | 2946 | 357 | None |
| 15 | `DOC-968c9605eab0a87d` | True | 0.644200 | 22.5 | 2942 | 367 | None |
| 16 | `DOC-0cdb706a0cdbe3b6` | True | 0.617600 | 22.6 | 2981 | 366 | None |
| 17 | `DOC-2aea7f6dc44b37e1` | True | 0.774100 | 23.7 | 2835 | 387 | None |
| 18 | `DOC-e4b1466ee8d1ff19` | True | 0.703700 | 24.2 | 3113 | 400 | None |
| 19 | `DOC-2435c398b95844bc` | True | 0.679500 | 27.3 | 3080 | 485 | None |
| 20 | `DOC-3ae2dc5d624e2120` | True | 0.599900 | 14.7 | 2871 | 347 | None |
| 21 | `DOC-4e21681f375a247d` | True | 0.642600 | 16.3 | 2985 | 400 | None |
| 22 | `DOC-d8df43ed4d8faf89` | True | 0.688800 | 29.1 | 3107 | 529 | None |
| 23 | `DOC-5b1e8e2aed95c089` | True | 0.682500 | 30.5 | 3123 | 551 | None |
| 24 | `DOC-00d28a1df0e3f6ba` | True | 0.697100 | 31.3 | 2812 | 260 | None |
| 25 | `DOC-91da307f80433ae3` | True | 0.579600 | 15.3 | 2894 | 358 | None |
| 26 | `DOC-90338506fc792f32` | True | 0.582300 | 16.0 | 2882 | 385 | None |
| 27 | `DOC-f5e6c0de5f1d8593` | True | 0.716900 | 34.7 | 2812 | 307 | None |
| 28 | `DOC-cbfcdb6f42cf2ae6` | True | 0.620500 | 36.5 | 2806 | 290 | None |
| 29 | `DOC-991cb72cb83c7a6c` | True | 0.644200 | 36.7 | 2941 | 372 | None |
| 30 | `DOC-6f6fc9762418a70f` | True | 0.704800 | 36.6 | 2811 | 294 | None |
| 31 | `DOC-1076ac5b4b0df386` | True | 0.656900 | 14.4 | 4482 | 428 | None |
| 32 | `DOC-ab18f15b7a51f1ab` | True | 0.741400 | 17.0 | 5538 | 494 | None |
| 33 | `DOC-2a55a2b5324659f8` | True | 0.809800 | 39.6 | 2865 | 345 | None |
| 34 | `DOC-29e384939c31d44a` | True | 0.613100 | 39.6 | 3010 | 323 | None |
| 35 | `DOC-5c4e70db54374e72` | True | 0.687400 | 39.8 | 3151 | 399 | None |
| 36 | `DOC-e2a58ed4c02470c0` | True | 0.803600 | 40.1 | 2835 | 346 | None |
| 37 | `DOC-73d64bbeb296bd95` | True | 0.602300 | 20.6 | 4524 | 568 | None |
| 38 | `DOC-5b97ae3f8558703c` | True | 0.686400 | 16.8 | 4565 | 566 | None |
| 39 | `DOC-2d7cc160b78a69c5` | True | 0.644200 | 41.1 | 2979 | 378 | None |
| 40 | `DOC-27b23fd94cc70d9d` | True | 0.605200 | 29.5 | 2890 | 353 | None |
| 41 | `DOC-364435343e0a2250` | True | 0.647400 | 30.8 | 3020 | 393 | None |
| 42 | `DOC-93c8d133c296d536` | True | 0.566300 | 30.4 | 2879 | 320 | None |
| 43 | `DOC-44bcd388c4710b71` | True | 0.566300 | 28.8 | 2884 | 343 | None |
| 44 | `DOC-7bd9dbc1b39ad41d` | True | 0.603600 | 46.5 | 3171 | 625 | None |
| 45 | `DOC-164aa748f84cef54` | True | 0.589900 | 29.4 | 2911 | 410 | None |
| 46 | `DOC-7f1f866b022cee63` | True | 0.726100 | 31.2 | 4985 | 510 | None |
| 47 | `DOC-85314478b81710d9` | True | 0.618900 | 29.4 | 5285 | 443 | None |
| 48 | `DOC-384665a051d0fcd6` | True | 0.679800 | 31.6 | 5208 | 506 | None |
| 49 | `DOC-6dcc0b9ba494c25b` | True | 0.756900 | 30.9 | 5114 | 557 | None |
| 50 | `DOC-02f77aa77391a8c2` | True | 0.686400 | 39.6 | 5091 | 1418 | None |
