# Run report — `grid-50-insurance-claims-specialist-awq-2l4`

Dated cell stem: `RUN-50-INSURANCE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-insurance-claims-specialist-awq-2l4` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `cc07eba27c6af19ad7ced72f42ba4422c5f0280c85b55177b41a095a497ce7fa` |
| dataset fingerprint | `b53ba23fea0a` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.685896** |
| schema_valid_rate | 0.240000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 35.600 |
| gpu_seconds | 35.926 |
| estimated GPU cost | 0.015967 |
| **GPU $/doc** | **0.00031934** |
| latency p50 / max (s) | 19.635036 / 33.369161 |
| prompt / completion tokens | 162525 / 20014 |
| concurrency speedup (Σlat/wall) | 29.40 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-df5ebe3e7263b6c6` | True | 0.624000 | 15.3 | 2815 | 290 | None |
| 2 | `DOC-826b2ac305c2b791` | True | 0.695500 | 15.3 | 2810 | 283 | None |
| 3 | `DOC-db1d2b3ea4d2d24f` | True | 0.675000 | 15.3 | 2804 | 285 | None |
| 4 | `DOC-d6d57b7a18431923` | True | 0.695900 | 15.3 | 2803 | 290 | None |
| 5 | `DOC-b28fe495a873ca59` | True | 0.689500 | 16.5 | 2807 | 286 | None |
| 6 | `DOC-7a128ee6e786bd0e` | True | 0.702400 | 16.6 | 2808 | 293 | None |
| 7 | `DOC-596b1f881ecf4a8a` | True | 0.716300 | 16.7 | 2806 | 322 | None |
| 8 | `DOC-b3be1f4b2b6142ed` | True | 0.695500 | 17.1 | 2815 | 331 | None |
| 9 | `DOC-fa698a867428a0ed` | True | 0.635300 | 17.5 | 3016 | 335 | None |
| 10 | `DOC-ee3512878a0003b7` | True | 0.793000 | 17.5 | 2831 | 332 | None |
| 11 | `DOC-2d2ec2092b012662` | True | 0.800000 | 17.8 | 2831 | 340 | None |
| 12 | `DOC-dc33a3e5a8cf5b6b` | True | 0.805600 | 17.8 | 2832 | 342 | None |
| 13 | `DOC-c0d9bf1e6be4ad51` | True | 0.701500 | 18.0 | 2808 | 311 | None |
| 14 | `DOC-c0e145a5a0a0d4bd` | True | 0.793000 | 18.3 | 2833 | 342 | None |
| 15 | `DOC-9f75d0ce11867685` | True | 0.634500 | 19.1 | 3044 | 333 | None |
| 16 | `DOC-edc5811634a19b7a` | True | 0.805600 | 19.8 | 2835 | 338 | None |
| 17 | `DOC-8dcc97d49f2004f5` | True | 0.798600 | 19.9 | 2835 | 344 | None |
| 18 | `DOC-bce319dabbc42e89` | True | 0.799100 | 20.7 | 2831 | 350 | None |
| 19 | `DOC-4cd6ca1171e8885e` | True | 0.772900 | 21.9 | 2832 | 352 | None |
| 20 | `DOC-bf5c2cc12aca8aad` | True | 0.783000 | 22.0 | 2834 | 357 | None |
| 21 | `DOC-4fd4cf5db3cfdb47` | True | 0.683900 | 22.8 | 2940 | 357 | None |
| 22 | `DOC-884dc887726dcfa5` | True | 0.737500 | 23.4 | 2833 | 350 | None |
| 23 | `DOC-d5e1b8ed3350fb36` | True | 0.629000 | 23.8 | 2969 | 363 | None |
| 24 | `DOC-a1a2afde18ded42d` | True | 0.684300 | 24.4 | 3086 | 382 | None |
| 25 | `DOC-a0be2aba09a3f580` | True | 0.691300 | 25.0 | 3095 | 358 | None |
| 26 | `DOC-4dda6e74e78edd70` | True | 0.642800 | 25.5 | 2949 | 375 | None |
| 27 | `DOC-85e24caa52979f50` | True | 0.711400 | 25.7 | 3121 | 386 | None |
| 28 | `DOC-1e95a2ae82adc61c` | True | 0.681700 | 26.2 | 3143 | 395 | None |
| 29 | `DOC-2435c398b95844bc` | True | 0.700900 | 26.8 | 3080 | 459 | None |
| 30 | `DOC-17abdc452037b6eb` | True | 0.693000 | 26.8 | 3129 | 417 | None |
| 31 | `DOC-576c9233159914e3` | True | 0.682500 | 29.7 | 3080 | 505 | None |
| 32 | `DOC-ab3b194998a42322` | True | 0.613100 | 17.4 | 3016 | 338 | None |
| 33 | `DOC-dcb4333f78bfe249` | True | 0.641100 | 33.4 | 2934 | 332 | None |
| 34 | `DOC-a0c5db2835e31ef6` | True | 0.601000 | 16.8 | 2871 | 334 | None |
| 35 | `DOC-b199013b1823372d` | True | 0.582700 | 16.3 | 2882 | 343 | None |
| 36 | `DOC-804fbeed2ab25ae8` | True | 0.580900 | 16.8 | 2873 | 349 | None |
| 37 | `DOC-d62e0d8ac987119d` | True | 0.626500 | 19.4 | 3031 | 410 | None |
| 38 | `DOC-01f1577c446c646d` | True | 0.599300 | 18.2 | 2868 | 332 | None |
| 39 | `DOC-4e21681f375a247d` | True | 0.641100 | 18.4 | 2985 | 347 | None |
| 40 | `DOC-1bc5f212af3bd4c2` | True | 0.627900 | 20.1 | 2990 | 401 | None |
| 41 | `DOC-4348717727f6d6b4` | True | 0.645600 | 20.2 | 3004 | 383 | None |
| 42 | `DOC-f80fe4950664c6e0` | True | 0.595200 | 18.4 | 2884 | 366 | None |
| 43 | `DOC-91fe413a7105d6fc` | True | 0.692400 | 20.1 | 5106 | 491 | None |
| 44 | `DOC-db02c129ee1d5261` | True | 0.696100 | 19.2 | 5515 | 529 | None |
| 45 | `DOC-06844413e427f8c2` | True | 0.765300 | 19.2 | 5336 | 559 | None |
| 46 | `DOC-009ee40e247a0a6e` | True | 0.541700 | 21.1 | 4688 | 541 | None |
| 47 | `DOC-e08d7fd014fde496` | True | 0.671100 | 22.2 | 4487 | 554 | None |
| 48 | `DOC-d3f320a3ba9c105b` | True | 0.597600 | 24.9 | 5234 | 709 | None |
| 49 | `DOC-4df9e8f7fd1c31c3` | True | 0.668500 | 32.6 | 4883 | 937 | None |
| 50 | `DOC-0966e6d5a9e7bd71` | True | 0.753200 | 33.1 | 4683 | 956 | None |
