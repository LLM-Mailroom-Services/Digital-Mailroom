# Run report — `sand42-50-insurance-claims-specialist-awq-2l4-c16`

Dated cell stem: `RUN-50-INSURANCE-AWQ-2L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-insurance-claims-specialist-awq-2l4-c16` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `1f035de493e44fb9ca7b22cc498ef9ef271d782f34ed9651d4433e51e173b753` |
| dataset fingerprint | `f4fdcee45e7f` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.669744** |
| schema_valid_rate | 0.300000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 89.490 |
| gpu_seconds | 89.803 |
| estimated GPU cost | 0.039912 |
| **GPU $/doc** | **0.00079824** |
| latency p50 / max (s) | 16.153659 / 39.504756 |
| prompt / completion tokens | 165315 / 20434 |
| concurrency speedup (Σlat/wall) | 9.29 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-ef79520b2f50217b` | True | 0.689200 | 11.2 | 3138 | 390 | None |
| 2 | `DOC-2a33a6c34834e769` | True | 0.633800 | 17.5 | 2953 | 329 | None |
| 3 | `DOC-997823d9605a4a59` | True | 0.639800 | 17.7 | 2973 | 336 | None |
| 4 | `DOC-9ba0a3d4c680b976` | True | 0.639800 | 17.8 | 2982 | 334 | None |
| 5 | `DOC-2a55a2b5324659f8` | True | 0.809800 | 18.0 | 2865 | 345 | None |
| 6 | `DOC-2aea7f6dc44b37e1` | True | 0.774100 | 19.0 | 2835 | 353 | None |
| 7 | `DOC-629fb5789dfd10ca` | True | 0.797900 | 19.0 | 2836 | 349 | None |
| 8 | `DOC-9a6f58879fcb3367` | True | 0.648700 | 19.2 | 2946 | 360 | None |
| 9 | `DOC-e7c196f508907c6f` | True | 0.783000 | 19.3 | 2834 | 367 | None |
| 10 | `DOC-158c0b74df673b81` | True | 0.644200 | 19.7 | 2939 | 362 | None |
| 11 | `DOC-e2a58ed4c02470c0` | True | 0.794600 | 20.0 | 2835 | 368 | None |
| 12 | `DOC-968c9605eab0a87d` | True | 0.644200 | 20.1 | 2942 | 367 | None |
| 13 | `DOC-991cb72cb83c7a6c` | True | 0.644200 | 20.2 | 2941 | 374 | None |
| 14 | `DOC-5c4e70db54374e72` | True | 0.687400 | 21.6 | 3151 | 399 | None |
| 15 | `DOC-2435c398b95844bc` | True | 0.687900 | 22.8 | 3080 | 444 | None |
| 16 | `DOC-9051d4cf8d7ab452` | True | 0.710000 | 13.4 | 3115 | 352 | None |
| 17 | `DOC-5b1e8e2aed95c089` | True | 0.682500 | 26.0 | 3123 | 549 | None |
| 18 | `DOC-5060222215c75aa6` | True | 0.674500 | 9.0 | 2801 | 245 | None |
| 19 | `DOC-00d28a1df0e3f6ba` | True | 0.697100 | 10.2 | 2812 | 259 | None |
| 20 | `DOC-728d06b610b25244` | True | 0.704300 | 9.2 | 2804 | 273 | None |
| 21 | `DOC-6f6fc9762418a70f` | True | 0.704800 | 9.3 | 2811 | 289 | None |
| 22 | `DOC-f5e6c0de5f1d8593` | True | 0.645000 | 10.2 | 2812 | 309 | None |
| 23 | `DOC-00ccdcb0154a8629` | True | 0.622800 | 11.3 | 2812 | 281 | None |
| 24 | `DOC-c34baab0b5fe378a` | True | 0.689900 | 11.0 | 2807 | 280 | None |
| 25 | `DOC-cbfcdb6f42cf2ae6` | True | 0.687200 | 10.8 | 2806 | 285 | None |
| 26 | `DOC-e4b1466ee8d1ff19` | True | 0.703700 | 15.0 | 3113 | 392 | None |
| 27 | `DOC-2d7cc160b78a69c5` | True | 0.644200 | 12.4 | 2979 | 378 | None |
| 28 | `DOC-29e384939c31d44a` | True | 0.622000 | 14.5 | 3010 | 382 | None |
| 29 | `DOC-87c0c53132830a6c` | True | 0.626500 | 14.4 | 2993 | 401 | None |
| 30 | `DOC-d8df43ed4d8faf89` | True | 0.688800 | 19.8 | 3107 | 529 | None |
| 31 | `DOC-0cdb706a0cdbe3b6` | True | 0.626500 | 14.6 | 2981 | 366 | None |
| 32 | `DOC-3ae2dc5d624e2120` | True | 0.599900 | 13.8 | 2871 | 341 | None |
| 33 | `DOC-27b23fd94cc70d9d` | True | 0.605200 | 14.4 | 2890 | 353 | None |
| 34 | `DOC-4e21681f375a247d` | True | 0.642600 | 16.4 | 2985 | 400 | None |
| 35 | `DOC-93c8d133c296d536` | True | 0.566300 | 13.3 | 2879 | 325 | None |
| 36 | `DOC-364435343e0a2250` | True | 0.647400 | 15.9 | 3020 | 393 | None |
| 37 | `DOC-7bd9dbc1b39ad41d` | True | 0.608100 | 23.6 | 3171 | 601 | None |
| 38 | `DOC-91da307f80433ae3` | True | 0.579600 | 15.8 | 2894 | 358 | None |
| 39 | `DOC-44bcd388c4710b71` | True | 0.566300 | 15.2 | 2884 | 343 | None |
| 40 | `DOC-90338506fc792f32` | True | 0.590300 | 15.2 | 2882 | 371 | None |
| 41 | `DOC-164aa748f84cef54` | True | 0.589900 | 16.7 | 2911 | 403 | None |
| 42 | `DOC-7f1f866b022cee63` | True | 0.787300 | 18.6 | 4985 | 508 | None |
| 43 | `DOC-85314478b81710d9` | True | 0.628700 | 14.2 | 5285 | 426 | None |
| 44 | `DOC-73d64bbeb296bd95` | True | 0.619800 | 20.9 | 4524 | 544 | None |
| 45 | `DOC-384665a051d0fcd6` | True | 0.680200 | 17.1 | 5208 | 498 | None |
| 46 | `DOC-ab18f15b7a51f1ab` | True | 0.744600 | 17.8 | 5538 | 523 | None |
| 47 | `DOC-1076ac5b4b0df386` | True | 0.572200 | 15.8 | 4482 | 502 | None |
| 48 | `DOC-6dcc0b9ba494c25b` | True | 0.813300 | 15.9 | 5114 | 561 | None |
| 49 | `DOC-5b97ae3f8558703c` | True | 0.691200 | 17.2 | 4565 | 577 | None |
| 50 | `DOC-02f77aa77391a8c2` | True | 0.705900 | 39.5 | 5091 | 1360 | None |
