# Run report — `sand42-50-insurance-claims-specialist-awq-2l4-c8`

Dated cell stem: `RUN-50-INSURANCE-AWQ-2L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-insurance-claims-specialist-awq-2l4-c8` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `9c87cb29fa61abbfab9d2fe5201b5101fd7498b483d22219cb9ffbfd1eda4177` |
| dataset fingerprint | `f4fdcee45e7f` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.665364** |
| schema_valid_rate | 0.280000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 108.858 |
| gpu_seconds | 109.185 |
| estimated GPU cost | 0.048527 |
| **GPU $/doc** | **0.00097054** |
| latency p50 / max (s) | 11.589337 / 38.329136 |
| prompt / completion tokens | 165315 / 20857 |
| concurrency speedup (Σlat/wall) | 5.85 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-2aea7f6dc44b37e1` | True | 0.774100 | 10.6 | 2835 | 353 | None |
| 2 | `DOC-991cb72cb83c7a6c` | True | 0.644200 | 10.6 | 2941 | 374 | None |
| 3 | `DOC-2a33a6c34834e769` | True | 0.629800 | 12.1 | 2953 | 337 | None |
| 4 | `DOC-2a55a2b5324659f8` | True | 0.809800 | 12.2 | 2865 | 346 | None |
| 5 | `DOC-629fb5789dfd10ca` | True | 0.794400 | 12.8 | 2836 | 353 | None |
| 6 | `DOC-e7c196f508907c6f` | True | 0.783000 | 12.9 | 2834 | 361 | None |
| 7 | `DOC-158c0b74df673b81` | True | 0.644200 | 13.1 | 2939 | 366 | None |
| 8 | `DOC-e2a58ed4c02470c0` | True | 0.780500 | 13.1 | 2835 | 370 | None |
| 9 | `DOC-997823d9605a4a59` | True | 0.639800 | 10.5 | 2973 | 355 | None |
| 10 | `DOC-968c9605eab0a87d` | True | 0.644200 | 10.5 | 2942 | 367 | None |
| 11 | `DOC-9ba0a3d4c680b976` | True | 0.639800 | 9.9 | 2982 | 334 | None |
| 12 | `DOC-9a6f58879fcb3367` | True | 0.644200 | 11.2 | 2946 | 374 | None |
| 13 | `DOC-ef79520b2f50217b` | True | 0.689200 | 11.3 | 3138 | 382 | None |
| 14 | `DOC-5c4e70db54374e72` | True | 0.691500 | 12.0 | 3151 | 404 | None |
| 15 | `DOC-2435c398b95844bc` | True | 0.687900 | 12.5 | 3080 | 453 | None |
| 16 | `DOC-5b1e8e2aed95c089` | True | 0.689600 | 15.2 | 3123 | 543 | None |
| 17 | `DOC-9051d4cf8d7ab452` | True | 0.724800 | 9.5 | 3115 | 307 | None |
| 18 | `DOC-00d28a1df0e3f6ba` | True | 0.697100 | 7.7 | 2812 | 259 | None |
| 19 | `DOC-5060222215c75aa6` | True | 0.674500 | 7.1 | 2801 | 245 | None |
| 20 | `DOC-728d06b610b25244` | True | 0.704300 | 7.9 | 2804 | 273 | None |
| 21 | `DOC-e4b1466ee8d1ff19` | True | 0.703700 | 11.8 | 3113 | 415 | None |
| 22 | `DOC-00ccdcb0154a8629` | True | 0.622800 | 8.4 | 2812 | 281 | None |
| 23 | `DOC-f5e6c0de5f1d8593` | True | 0.695500 | 9.0 | 2812 | 300 | None |
| 24 | `DOC-d8df43ed4d8faf89` | True | 0.688800 | 15.5 | 3107 | 529 | None |
| 25 | `DOC-c34baab0b5fe378a` | True | 0.689900 | 8.8 | 2807 | 299 | None |
| 26 | `DOC-6f6fc9762418a70f` | True | 0.704800 | 8.1 | 2811 | 285 | None |
| 27 | `DOC-cbfcdb6f42cf2ae6` | True | 0.620500 | 8.8 | 2806 | 290 | None |
| 28 | `DOC-29e384939c31d44a` | True | 0.613100 | 9.5 | 3010 | 306 | None |
| 29 | `DOC-2d7cc160b78a69c5` | True | 0.644200 | 11.1 | 2979 | 396 | None |
| 30 | `DOC-0cdb706a0cdbe3b6` | True | 0.613100 | 9.3 | 2981 | 312 | None |
| 31 | `DOC-87c0c53132830a6c` | True | 0.626500 | 11.2 | 2993 | 397 | None |
| 32 | `DOC-27b23fd94cc70d9d` | True | 0.605200 | 9.9 | 2890 | 353 | None |
| 33 | `DOC-4e21681f375a247d` | True | 0.642600 | 10.6 | 2985 | 382 | None |
| 34 | `DOC-364435343e0a2250` | True | 0.647400 | 11.4 | 3020 | 393 | None |
| 35 | `DOC-7bd9dbc1b39ad41d` | True | 0.603100 | 17.5 | 3171 | 626 | None |
| 36 | `DOC-3ae2dc5d624e2120` | True | 0.599900 | 10.7 | 2871 | 338 | None |
| 37 | `DOC-93c8d133c296d536` | True | 0.566300 | 10.8 | 2879 | 325 | None |
| 38 | `DOC-91da307f80433ae3` | True | 0.579600 | 12.2 | 2894 | 358 | None |
| 39 | `DOC-44bcd388c4710b71` | True | 0.566300 | 12.0 | 2884 | 346 | None |
| 40 | `DOC-90338506fc792f32` | True | 0.582300 | 12.9 | 2882 | 372 | None |
| 41 | `DOC-164aa748f84cef54` | True | 0.581000 | 14.7 | 2911 | 394 | None |
| 42 | `DOC-73d64bbeb296bd95` | True | 0.602300 | 18.1 | 4524 | 580 | None |
| 43 | `DOC-7f1f866b022cee63` | True | 0.730900 | 18.7 | 4985 | 508 | None |
| 44 | `DOC-384665a051d0fcd6` | True | 0.680200 | 18.5 | 5208 | 529 | None |
| 45 | `DOC-ab18f15b7a51f1ab` | True | 0.741400 | 15.0 | 5538 | 494 | None |
| 46 | `DOC-85314478b81710d9` | True | 0.628700 | 14.7 | 5285 | 426 | None |
| 47 | `DOC-1076ac5b4b0df386` | True | 0.572200 | 15.5 | 4482 | 508 | None |
| 48 | `DOC-6dcc0b9ba494c25b` | True | 0.813300 | 15.7 | 5114 | 557 | None |
| 49 | `DOC-02f77aa77391a8c2` | True | 0.691200 | 38.3 | 5091 | 1406 | None |
| 50 | `DOC-5b97ae3f8558703c` | True | 0.624500 | 25.6 | 4565 | 996 | None |
