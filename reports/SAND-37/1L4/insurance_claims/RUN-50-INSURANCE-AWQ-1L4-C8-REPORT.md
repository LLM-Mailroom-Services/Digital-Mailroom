# Run report — `grid-50-insurance-claims-specialist-awq-1l4`

Dated cell stem: `RUN-50-INSURANCE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-insurance-claims-specialist-awq-1l4` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `01f8863ba2d59587dcc935b03f3399d165b2a0183e64ccfd070d8118edff1570` |
| dataset fingerprint | `b53ba23fea0a` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.683800** |
| schema_valid_rate | 0.200000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 87.417 |
| gpu_seconds | 87.739 |
| estimated GPU cost | 0.019498 |
| **GPU $/doc** | **0.00038996** |
| latency p50 / max (s) | 13.958155 / 36.729685 |
| prompt / completion tokens | 162525 / 19876 |
| concurrency speedup (Σlat/wall) | 8.65 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-ee3512878a0003b7` | True | 0.793000 | 12.8 | 2831 | 332 | None |
| 2 | `DOC-edc5811634a19b7a` | True | 0.805600 | 12.8 | 2835 | 342 | None |
| 3 | `DOC-dc33a3e5a8cf5b6b` | True | 0.801200 | 12.8 | 2832 | 342 | None |
| 4 | `DOC-c0e145a5a0a0d4bd` | True | 0.793000 | 12.8 | 2833 | 346 | None |
| 5 | `DOC-4cd6ca1171e8885e` | True | 0.772900 | 12.9 | 2832 | 352 | None |
| 6 | `DOC-bf5c2cc12aca8aad` | True | 0.783000 | 13.0 | 2834 | 357 | None |
| 7 | `DOC-8dcc97d49f2004f5` | True | 0.790800 | 15.4 | 2835 | 367 | None |
| 8 | `DOC-884dc887726dcfa5` | True | 0.800000 | 16.8 | 2833 | 403 | None |
| 9 | `DOC-2d2ec2092b012662` | True | 0.800000 | 12.4 | 2831 | 340 | None |
| 10 | `DOC-fa698a867428a0ed` | True | 0.645300 | 10.1 | 3016 | 335 | None |
| 11 | `DOC-dcb4333f78bfe249` | True | 0.641100 | 12.6 | 2934 | 350 | None |
| 12 | `DOC-bce319dabbc42e89` | True | 0.785700 | 14.0 | 2831 | 359 | None |
| 13 | `DOC-4fd4cf5db3cfdb47` | True | 0.630900 | 14.1 | 2940 | 364 | None |
| 14 | `DOC-4dda6e74e78edd70` | True | 0.638700 | 14.8 | 2949 | 369 | None |
| 15 | `DOC-d5e1b8ed3350fb36` | True | 0.629000 | 15.4 | 2969 | 372 | None |
| 16 | `DOC-9f75d0ce11867685` | True | 0.638700 | 13.3 | 3044 | 342 | None |
| 17 | `DOC-b3be1f4b2b6142ed` | True | 0.695500 | 8.5 | 2815 | 286 | None |
| 18 | `DOC-1e95a2ae82adc61c` | True | 0.681700 | 14.2 | 3143 | 376 | None |
| 19 | `DOC-a1a2afde18ded42d` | True | 0.684300 | 14.8 | 3086 | 396 | None |
| 20 | `DOC-a0be2aba09a3f580` | True | 0.688500 | 12.1 | 3095 | 375 | None |
| 21 | `DOC-85e24caa52979f50` | True | 0.683600 | 13.4 | 3121 | 392 | None |
| 22 | `DOC-17abdc452037b6eb` | True | 0.693000 | 14.3 | 3129 | 410 | None |
| 23 | `DOC-2435c398b95844bc` | True | 0.679500 | 17.2 | 3080 | 481 | None |
| 24 | `DOC-576c9233159914e3` | True | 0.682500 | 18.9 | 3080 | 505 | None |
| 25 | `DOC-7a128ee6e786bd0e` | True | 0.702400 | 9.2 | 2808 | 251 | None |
| 26 | `DOC-c0d9bf1e6be4ad51` | True | 0.701500 | 11.6 | 2808 | 314 | None |
| 27 | `DOC-b28fe495a873ca59` | True | 0.689500 | 10.7 | 2807 | 287 | None |
| 28 | `DOC-db1d2b3ea4d2d24f` | True | 0.675000 | 10.5 | 2804 | 286 | None |
| 29 | `DOC-596b1f881ecf4a8a` | True | 0.649600 | 10.9 | 2806 | 300 | None |
| 30 | `DOC-df5ebe3e7263b6c6` | True | 0.706700 | 10.8 | 2815 | 283 | None |
| 31 | `DOC-d6d57b7a18431923` | True | 0.695900 | 10.2 | 2803 | 276 | None |
| 32 | `DOC-826b2ac305c2b791` | True | 0.695500 | 10.6 | 2810 | 281 | None |
| 33 | `DOC-1bc5f212af3bd4c2` | True | 0.613800 | 14.2 | 2990 | 392 | None |
| 34 | `DOC-ab3b194998a42322` | True | 0.613100 | 12.4 | 3016 | 370 | None |
| 35 | `DOC-4e21681f375a247d` | True | 0.618800 | 12.2 | 2985 | 369 | None |
| 36 | `DOC-a0c5db2835e31ef6` | True | 0.601000 | 10.7 | 2871 | 345 | None |
| 37 | `DOC-4348717727f6d6b4` | True | 0.633100 | 13.9 | 3004 | 402 | None |
| 38 | `DOC-d62e0d8ac987119d` | True | 0.613100 | 16.9 | 3031 | 397 | None |
| 39 | `DOC-804fbeed2ab25ae8` | True | 0.580900 | 15.3 | 2873 | 349 | None |
| 40 | `DOC-01f1577c446c646d` | True | 0.599300 | 15.5 | 2868 | 355 | None |
| 41 | `DOC-b199013b1823372d` | True | 0.582700 | 17.7 | 2882 | 359 | None |
| 42 | `DOC-f80fe4950664c6e0` | True | 0.595200 | 18.5 | 2884 | 366 | None |
| 43 | `DOC-91fe413a7105d6fc` | True | 0.682200 | 24.2 | 5106 | 495 | None |
| 44 | `DOC-e08d7fd014fde496` | True | 0.608700 | 20.7 | 4487 | 528 | None |
| 45 | `DOC-4df9e8f7fd1c31c3` | True | 0.605100 | 27.8 | 4883 | 624 | None |
| 46 | `DOC-db02c129ee1d5261` | True | 0.743900 | 22.0 | 5515 | 576 | None |
| 47 | `DOC-d3f320a3ba9c105b` | True | 0.618700 | 26.7 | 5234 | 708 | None |
| 48 | `DOC-009ee40e247a0a6e` | True | 0.608300 | 18.3 | 4688 | 558 | None |
| 49 | `DOC-06844413e427f8c2` | True | 0.765300 | 18.2 | 5336 | 556 | None |
| 50 | `DOC-0966e6d5a9e7bd71` | True | 0.753200 | 36.7 | 4683 | 956 | None |
