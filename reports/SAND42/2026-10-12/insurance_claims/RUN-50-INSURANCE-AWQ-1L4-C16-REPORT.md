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
| **overall_extraction_score** | **0.667332** |
| schema_valid_rate | 0.340000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 107.332 |
| gpu_seconds | 107.643 |
| estimated GPU cost | 0.023921 |
| **GPU $/doc** | **0.00047842** |
| latency p50 / max (s) | 21.412539 / 48.613538 |
| prompt / completion tokens | 165315 / 21216 |
| concurrency speedup (Σlat/wall) | 10.43 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-2a33a6c34834e769` | True | 0.629800 | 18.6 | 2953 | 337 | None |
| 2 | `DOC-2a55a2b5324659f8` | True | 0.809800 | 18.6 | 2865 | 346 | None |
| 3 | `DOC-9ba0a3d4c680b976` | True | 0.639800 | 18.6 | 2982 | 334 | None |
| 4 | `DOC-629fb5789dfd10ca` | True | 0.794400 | 18.8 | 2836 | 352 | None |
| 5 | `DOC-2aea7f6dc44b37e1` | True | 0.774100 | 19.0 | 2835 | 353 | None |
| 6 | `DOC-997823d9605a4a59` | True | 0.639800 | 19.9 | 2973 | 361 | None |
| 7 | `DOC-e2a58ed4c02470c0` | True | 0.781200 | 21.3 | 2835 | 365 | None |
| 8 | `DOC-e7c196f508907c6f` | True | 0.783000 | 21.4 | 2834 | 361 | None |
| 9 | `DOC-9a6f58879fcb3367` | True | 0.644200 | 21.4 | 2946 | 370 | None |
| 10 | `DOC-968c9605eab0a87d` | True | 0.644200 | 21.4 | 2942 | 367 | None |
| 11 | `DOC-991cb72cb83c7a6c` | True | 0.644200 | 21.5 | 2941 | 367 | None |
| 12 | `DOC-158c0b74df673b81` | True | 0.644200 | 21.5 | 2939 | 367 | None |
| 13 | `DOC-ef79520b2f50217b` | True | 0.689200 | 24.1 | 3138 | 390 | None |
| 14 | `DOC-2435c398b95844bc` | True | 0.687900 | 26.7 | 3080 | 455 | None |
| 15 | `DOC-5b1e8e2aed95c089` | True | 0.687300 | 29.7 | 3123 | 532 | None |
| 16 | `DOC-5c4e70db54374e72` | True | 0.676300 | 29.9 | 3151 | 542 | None |
| 17 | `DOC-6f6fc9762418a70f` | True | 0.704800 | 11.6 | 2811 | 238 | None |
| 18 | `DOC-00d28a1df0e3f6ba` | True | 0.697100 | 14.3 | 2812 | 259 | None |
| 19 | `DOC-728d06b610b25244` | True | 0.704300 | 14.4 | 2804 | 273 | None |
| 20 | `DOC-cbfcdb6f42cf2ae6` | True | 0.687200 | 13.9 | 2806 | 275 | None |
| 21 | `DOC-00ccdcb0154a8629` | True | 0.622800 | 14.1 | 2812 | 281 | None |
| 22 | `DOC-5060222215c75aa6` | True | 0.741200 | 16.5 | 2801 | 296 | None |
| 23 | `DOC-c34baab0b5fe378a` | True | 0.623200 | 15.4 | 2807 | 293 | None |
| 24 | `DOC-f5e6c0de5f1d8593` | True | 0.695500 | 15.7 | 2812 | 301 | None |
| 25 | `DOC-29e384939c31d44a` | True | 0.613100 | 15.9 | 3010 | 306 | None |
| 26 | `DOC-9051d4cf8d7ab452` | True | 0.732200 | 20.2 | 3115 | 341 | None |
| 27 | `DOC-e4b1466ee8d1ff19` | True | 0.703700 | 23.1 | 3113 | 400 | None |
| 28 | `DOC-2d7cc160b78a69c5` | True | 0.644200 | 20.2 | 2979 | 396 | None |
| 29 | `DOC-d8df43ed4d8faf89` | True | 0.688800 | 29.7 | 3107 | 524 | None |
| 30 | `DOC-0cdb706a0cdbe3b6` | True | 0.613100 | 20.7 | 2981 | 363 | None |
| 31 | `DOC-87c0c53132830a6c` | True | 0.626500 | 23.3 | 2993 | 397 | None |
| 32 | `DOC-93c8d133c296d536` | True | 0.582900 | 20.9 | 2879 | 340 | None |
| 33 | `DOC-27b23fd94cc70d9d` | True | 0.605200 | 22.1 | 2890 | 362 | None |
| 34 | `DOC-3ae2dc5d624e2120` | True | 0.599900 | 21.2 | 2871 | 347 | None |
| 35 | `DOC-364435343e0a2250` | True | 0.647400 | 25.9 | 3020 | 393 | None |
| 36 | `DOC-91da307f80433ae3` | True | 0.579600 | 24.3 | 2894 | 358 | None |
| 37 | `DOC-4e21681f375a247d` | True | 0.642600 | 27.5 | 2985 | 412 | None |
| 38 | `DOC-90338506fc792f32` | True | 0.595600 | 23.9 | 2882 | 367 | None |
| 39 | `DOC-44bcd388c4710b71` | True | 0.583700 | 24.3 | 2884 | 374 | None |
| 40 | `DOC-7bd9dbc1b39ad41d` | True | 0.603600 | 36.0 | 3171 | 630 | None |
| 41 | `DOC-164aa748f84cef54` | True | 0.589900 | 25.2 | 2911 | 410 | None |
| 42 | `DOC-73d64bbeb296bd95` | True | 0.597600 | 28.8 | 4524 | 534 | None |
| 43 | `DOC-7f1f866b022cee63` | True | 0.782500 | 26.8 | 4985 | 504 | None |
| 44 | `DOC-85314478b81710d9` | True | 0.628700 | 19.4 | 5285 | 441 | None |
| 45 | `DOC-ab18f15b7a51f1ab` | True | 0.744600 | 23.7 | 5538 | 532 | None |
| 46 | `DOC-384665a051d0fcd6` | True | 0.680100 | 26.7 | 5208 | 591 | None |
| 47 | `DOC-1076ac5b4b0df386` | True | 0.573500 | 19.5 | 4482 | 502 | None |
| 48 | `DOC-6dcc0b9ba494c25b` | True | 0.817800 | 21.3 | 5114 | 570 | None |
| 49 | `DOC-5b97ae3f8558703c` | True | 0.557900 | 31.9 | 4565 | 1005 | None |
| 50 | `DOC-02f77aa77391a8c2` | True | 0.686400 | 48.6 | 5091 | 1402 | None |
