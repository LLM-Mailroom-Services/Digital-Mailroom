# Run report — `sand42-50-insurance-claims-specialist-awq-1l4-c16`

Dated cell stem: `RUN-50-INSURANCE-AWQ-1L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-insurance-claims-specialist-awq-1l4-c16` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `4ea90e8ac5b2c245d6182f4f9cc5e8f4342c704f6c9bc5faf2a4ea12f91ce8e6` |
| dataset fingerprint | `f4fdcee45e7f` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.664678** |
| schema_valid_rate | 0.280000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 72.235 |
| gpu_seconds | 72.520 |
| estimated GPU cost | 0.016116 |
| **GPU $/doc** | **0.00032232** |
| latency p50 / max (s) | 20.477881 / 47.697135 |
| prompt / completion tokens | 165315 / 20749 |
| concurrency speedup (Σlat/wall) | 15.13 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-9ba0a3d4c680b976` | True | 0.639800 | 19.1 | 2982 | 334 | None |
| 2 | `DOC-2aea7f6dc44b37e1` | True | 0.774100 | 19.1 | 2835 | 353 | None |
| 3 | `DOC-2a33a6c34834e769` | True | 0.629800 | 19.1 | 2953 | 341 | None |
| 4 | `DOC-629fb5789dfd10ca` | True | 0.794400 | 19.1 | 2836 | 353 | None |
| 5 | `DOC-2a55a2b5324659f8` | True | 0.809800 | 19.1 | 2865 | 346 | None |
| 6 | `DOC-e7c196f508907c6f` | True | 0.783000 | 19.2 | 2834 | 360 | None |
| 7 | `DOC-997823d9605a4a59` | True | 0.644200 | 19.2 | 2973 | 364 | None |
| 8 | `DOC-158c0b74df673b81` | True | 0.644200 | 19.2 | 2939 | 367 | None |
| 9 | `DOC-9a6f58879fcb3367` | True | 0.644200 | 19.4 | 2946 | 374 | None |
| 10 | `DOC-968c9605eab0a87d` | True | 0.644200 | 19.4 | 2942 | 367 | None |
| 11 | `DOC-e2a58ed4c02470c0` | True | 0.767100 | 19.5 | 2835 | 366 | None |
| 12 | `DOC-991cb72cb83c7a6c` | True | 0.644200 | 20.5 | 2941 | 374 | None |
| 13 | `DOC-5c4e70db54374e72` | True | 0.687400 | 24.3 | 3151 | 404 | None |
| 14 | `DOC-ef79520b2f50217b` | True | 0.689200 | 24.4 | 3138 | 401 | None |
| 15 | `DOC-2435c398b95844bc` | True | 0.689800 | 27.5 | 3080 | 476 | None |
| 16 | `DOC-5b1e8e2aed95c089` | True | 0.682600 | 30.3 | 3123 | 548 | None |
| 17 | `DOC-6f6fc9762418a70f` | True | 0.710200 | 14.0 | 2811 | 255 | None |
| 18 | `DOC-00d28a1df0e3f6ba` | True | 0.697100 | 14.6 | 2812 | 259 | None |
| 19 | `DOC-728d06b610b25244` | True | 0.704300 | 15.6 | 2804 | 273 | None |
| 20 | `DOC-cbfcdb6f42cf2ae6` | True | 0.694600 | 15.3 | 2806 | 272 | None |
| 21 | `DOC-00ccdcb0154a8629` | True | 0.622800 | 15.8 | 2812 | 281 | None |
| 22 | `DOC-5060222215c75aa6` | True | 0.674500 | 17.2 | 2801 | 293 | None |
| 23 | `DOC-c34baab0b5fe378a` | True | 0.623200 | 17.0 | 2807 | 294 | None |
| 24 | `DOC-f5e6c0de5f1d8593` | True | 0.645000 | 17.4 | 2812 | 297 | None |
| 25 | `DOC-29e384939c31d44a` | True | 0.613100 | 16.3 | 3010 | 306 | None |
| 26 | `DOC-9051d4cf8d7ab452` | True | 0.710000 | 20.4 | 3115 | 352 | None |
| 27 | `DOC-e4b1466ee8d1ff19` | True | 0.703700 | 22.9 | 3113 | 402 | None |
| 28 | `DOC-7bd9dbc1b39ad41d` | True | 0.629800 | 19.1 | 3171 | 379 | None |
| 29 | `DOC-2d7cc160b78a69c5` | True | 0.644200 | 20.9 | 2979 | 396 | None |
| 30 | `DOC-87c0c53132830a6c` | True | 0.626500 | 21.5 | 2993 | 397 | None |
| 31 | `DOC-d8df43ed4d8faf89` | True | 0.688800 | 31.7 | 3107 | 528 | None |
| 32 | `DOC-0cdb706a0cdbe3b6` | True | 0.626500 | 23.0 | 2981 | 381 | None |
| 33 | `DOC-93c8d133c296d536` | True | 0.566300 | 21.0 | 2879 | 328 | None |
| 34 | `DOC-3ae2dc5d624e2120` | True | 0.599900 | 22.9 | 2871 | 347 | None |
| 35 | `DOC-27b23fd94cc70d9d` | True | 0.605200 | 23.1 | 2890 | 353 | None |
| 36 | `DOC-44bcd388c4710b71` | True | 0.566300 | 23.1 | 2884 | 346 | None |
| 37 | `DOC-364435343e0a2250` | True | 0.647400 | 26.1 | 3020 | 393 | None |
| 38 | `DOC-4e21681f375a247d` | True | 0.642600 | 26.3 | 2985 | 400 | None |
| 39 | `DOC-91da307f80433ae3` | True | 0.579600 | 24.0 | 2894 | 370 | None |
| 40 | `DOC-90338506fc792f32` | True | 0.582300 | 23.8 | 2882 | 372 | None |
| 41 | `DOC-164aa748f84cef54` | True | 0.589900 | 24.7 | 2911 | 404 | None |
| 42 | `DOC-7f1f866b022cee63` | True | 0.787300 | 26.6 | 4985 | 509 | None |
| 43 | `DOC-73d64bbeb296bd95` | True | 0.602300 | 29.6 | 4524 | 578 | None |
| 44 | `DOC-85314478b81710d9` | True | 0.633200 | 19.4 | 5285 | 436 | None |
| 45 | `DOC-384665a051d0fcd6` | True | 0.683100 | 24.9 | 5208 | 529 | None |
| 46 | `DOC-ab18f15b7a51f1ab` | True | 0.741400 | 22.3 | 5538 | 495 | None |
| 47 | `DOC-1076ac5b4b0df386` | True | 0.623600 | 18.1 | 4482 | 442 | None |
| 48 | `DOC-6dcc0b9ba494c25b` | True | 0.756900 | 19.2 | 5114 | 539 | None |
| 49 | `DOC-5b97ae3f8558703c` | True | 0.557900 | 29.4 | 4565 | 1009 | None |
| 50 | `DOC-02f77aa77391a8c2` | True | 0.686400 | 47.7 | 5091 | 1406 | None |
