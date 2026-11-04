# Run report — `sand42-50-contracts-specialist-awq-1l4-c8`

Dated cell stem: `RUN-50-CONTRACTS-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-contracts-specialist-awq-1l4-c8` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `b01173a2eacc23710ab86350a616c0277f8f2f59ac2c44c8a7e0ac367d82a885` |
| dataset fingerprint | `83eb6b1f2c7e` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.521058** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 865.606 |
| gpu_seconds | 865.983 |
| estimated GPU cost | 0.192441 |
| **GPU $/doc** | **0.00384882** |
| latency p50 / max (s) | 94.476106 / 687.818112 |
| prompt / completion tokens | 799423 / 129558 |
| concurrency speedup (Σlat/wall) | 7.99 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-6b4cc54c8c4d796f` | True | — | 38.9 | 4015 | 714 | None |
| 2 | `DOC-a9850db362f57916` | True | — | 46.9 | 6764 | 863 | None |
| 3 | `DOC-b1aba7df0380a1b2` | True | — | 62.2 | 5032 | 1235 | None |
| 4 | `DOC-fc9671ccde642e8d` | True | — | 68.8 | 7936 | 1330 | None |
| 5 | `DOC-f5a54932794ef16e` | True | 0.666700 | 75.3 | 5302 | 1413 | None |
| 6 | `DOC-3c07c9ccd9a01d6e` | True | 0.631600 | 92.0 | 7428 | 1668 | None |
| 7 | `DOC-03529267ee75444d` | True | 0.571400 | 75.1 | 10583 | 1312 | None |
| 8 | `DOC-e235bc9735f96335` | True | 0.521700 | 62.9 | 10699 | 1068 | None |
| 9 | `DOC-6671a684f52f82a9` | True | 0.416700 | 96.3 | 11320 | 1614 | None |
| 10 | `DOC-385a86c69f8e562c` | True | 0.615400 | 125.7 | 6560 | 2278 | None |
| 11 | `DOC-b87880882e5fe354` | True | — | 187.9 | 19278 | 3412 | None |
| 12 | `DOC-0752e0811f5f5eb7` | True | 0.381000 | 196.8 | 41619 | 3560 | None |
| 13 | `DOC-0812d9d3e2b1baa0` | True | 0.444400 | 145.5 | 18679 | 2591 | None |
| 14 | `DOC-593f2c6de770b84c` | True | 0.666700 | 147.2 | 9228 | 2702 | None |
| 15 | `DOC-e4272758b561f8cd` | True | 0.555600 | 82.7 | 6987 | 1493 | None |
| 16 | `DOC-f8b0d4bcbac60ca2` | True | 0.500000 | 74.5 | 3824 | 1332 | None |
| 17 | `DOC-81c4ce12d907380c` | True | 0.571400 | 83.3 | 7047 | 1477 | None |
| 18 | `DOC-4fb6419e37bff201` | True | 0.687500 | 216.7 | 22234 | 3912 | None |
| 19 | `DOC-b83763aeff114369` | True | 0.620700 | 93.8 | 7446 | 1776 | None |
| 20 | `DOC-9a36838df2878b37` | True | 0.434800 | 66.4 | 8142 | 1255 | None |
| 21 | `DOC-2b510409d3b9a4a6` | True | 0.687500 | 282.1 | 21668 | 5164 | None |
| 22 | `DOC-812192e392d8d410` | True | 0.600000 | 155.3 | 5551 | 2834 | None |
| 23 | `DOC-9cee2e10b449a71c` | True | 0.756800 | 194.8 | 21752 | 3597 | None |
| 24 | `DOC-73055dbb1e9f5f2f` | True | 0.711100 | 316.4 | 49409 | 5774 | None |
| 25 | `DOC-e998c563b82122b9` | True | 0.526300 | 95.1 | 10006 | 1653 | None |
| 26 | `DOC-1e22a2d4068b8650` | True | 0.714300 | 92.3 | 7587 | 1592 | None |
| 27 | `DOC-27b649fe2f6fae8e` | True | 0.777800 | 85.0 | 5464 | 1480 | None |
| 28 | `DOC-70f90b46b2c4f1a6` | True | 0.666700 | 17.8 | 3154 | 361 | None |
| 29 | `DOC-035731e655e67aab` | True | 0.476200 | 151.4 | 5207 | 2775 | None |
| 30 | `DOC-e29140d2e8e989be` | True | 0.500000 | 521.8 | 45485 | 9573 | None |
| 31 | `DOC-1266801f2faad19f` | True | 0.682900 | 219.6 | 33383 | 3969 | None |
| 32 | `DOC-1ddc9333769d27e4` | True | 0.571400 | 73.3 | 4450 | 1332 | None |
| 33 | `DOC-712c3f92a0a56b77` | True | 0.444400 | 271.6 | 56227 | 4948 | None |
| 34 | `DOC-62b300182901e850` | True | 0.545500 | 136.0 | 33346 | 2527 | None |
| 35 | `DOC-dfb4e69a3ab10dc9` | True | 0.526300 | 72.6 | 7378 | 1289 | None |
| 36 | `DOC-fe06800cc62e5e19` | True | 0.636400 | 84.1 | 8619 | 1580 | None |
| 37 | `DOC-472f423cdf0819ef` | True | 0.750000 | 57.8 | 4656 | 1107 | None |
| 38 | `DOC-186145066ab191fa` | True | 0.500000 | 44.8 | 3718 | 921 | None |
| 39 | `DOC-f45b328fd8a54c8b` | True | 0.625000 | 52.4 | 4608 | 1077 | None |
| 40 | `DOC-c9d4c4f8ff433527` | True | 0.521700 | 73.1 | 7730 | 1402 | None |
| 41 | `DOC-8993ad1085e08bd0` | True | 0.769200 | 262.4 | 22402 | 4965 | None |
| 42 | `DOC-4b57f485708ab60b` | True | 0.400000 | 78.8 | 6639 | 1473 | None |
| 43 | `DOC-8f737e9fec8f24f0` | True | 0.500000 | 218.0 | 35815 | 4013 | None |
| 44 | `DOC-e0d31c39359cb803` | True | 0.270300 | 118.6 | 6879 | 2351 | None |
| 45 | `DOC-01849fa3020a5ac1` | True | 0.500000 | 52.6 | 4173 | 1117 | None |
| 46 | `DOC-be1eccde5bae9c82` | True | 0.480000 | 101.8 | 9330 | 2092 | None |
| 47 | `DOC-e218d39bb2f3c5ef` | True | 0.400000 | 140.5 | 19923 | 2967 | None |
| 48 | `DOC-dfd20f94bb76b6e4` | True | 0.692300 | 114.4 | 21000 | 2574 | None |
| 49 | `DOC-53e364f030a30b5c` | True | 0.717000 | 687.8 | 94991 | 13151 | None |
| 50 | `DOC-dbe52fd78e44b0ef` | True | 0.818200 | 102.9 | 18750 | 2895 | None |
