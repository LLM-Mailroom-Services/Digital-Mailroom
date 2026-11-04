# Run report — `sand42-50-contracts-specialist-awq-2l4-c16`

Dated cell stem: `RUN-50-CONTRACTS-AWQ-2L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-contracts-specialist-awq-2l4-c16` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `333da915cf0328467194d6547a2e40db2e1c0a44ec2ca8bf1c896ebd09cf63f5` |
| dataset fingerprint | `5344b28a3033` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.604352** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 758.750 |
| gpu_seconds | 759.095 |
| estimated GPU cost | 0.337376 |
| **GPU $/doc** | **0.00674752** |
| latency p50 / max (s) | 102.765344 / 744.941311 |
| prompt / completion tokens | 803470 / 123073 |
| concurrency speedup (Σlat/wall) | 10.83 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-268df6c8fabb385a` | True | 0.666700 | 77.0 | 5201 | 938 | None |
| 2 | `DOC-e235bc9735f96335` | True | 0.511600 | 84.8 | 10699 | 1073 | None |
| 3 | `DOC-a7ea445212692b88` | True | 0.666700 | 88.6 | 9369 | 1911 | None |
| 4 | `DOC-e4272758b561f8cd` | True | 0.555600 | 98.5 | 6987 | 1280 | None |
| 5 | `DOC-f5a54932794ef16e` | True | 0.777800 | 107.1 | 5302 | 1377 | None |
| 6 | `DOC-eaa14fe106140524` | True | 0.625000 | 109.0 | 7001 | 1394 | None |
| 7 | `DOC-3c07c9ccd9a01d6e` | True | 0.705900 | 111.4 | 7428 | 1438 | None |
| 8 | `DOC-1843cfdaf5db1840` | True | 0.600000 | 44.8 | 7407 | 639 | None |
| 9 | `DOC-385a86c69f8e562c` | True | 0.615400 | 136.2 | 6560 | 1841 | None |
| 10 | `DOC-593f2c6de770b84c` | True | 0.750000 | 136.4 | 9228 | 1830 | None |
| 11 | `DOC-f8b0d4bcbac60ca2` | True | 0.545500 | 53.5 | 3824 | 1331 | None |
| 12 | `DOC-812192e392d8d410` | True | 0.571400 | 47.5 | 5551 | 1075 | None |
| 13 | `DOC-cbc1f0d62edbb23e` | True | 0.500000 | 84.0 | 4155 | 1874 | None |
| 14 | `DOC-2c3a9c3168cd0e3a` | True | 0.600000 | 86.1 | 3385 | 1330 | None |
| 15 | `DOC-0752e0811f5f5eb7` | True | 0.333300 | 177.8 | 41619 | 2658 | None |
| 16 | `DOC-73055dbb1e9f5f2f` | True | 0.466700 | 183.9 | 49409 | 3837 | None |
| 17 | `DOC-9a36838df2878b37` | True | 0.583300 | 67.2 | 8142 | 1382 | None |
| 18 | `DOC-035731e655e67aab` | True | 0.555600 | 57.0 | 5207 | 1327 | None |
| 19 | `DOC-b83763aeff114369` | True | 0.620700 | 97.3 | 7446 | 1550 | None |
| 20 | `DOC-4fb6419e37bff201` | True | 0.636400 | 229.7 | 22234 | 4098 | None |
| 21 | `DOC-27b649fe2f6fae8e` | True | 0.800000 | 58.3 | 5464 | 1316 | None |
| 22 | `DOC-70f90b46b2c4f1a6` | True | 0.571400 | 29.3 | 3154 | 485 | None |
| 23 | `DOC-e998c563b82122b9` | True | 0.526300 | 88.1 | 10006 | 1399 | None |
| 24 | `DOC-1e22a2d4068b8650` | True | 0.769200 | 78.9 | 7587 | 1716 | None |
| 25 | `DOC-9cee2e10b449a71c` | True | 0.777800 | 146.9 | 21752 | 2762 | None |
| 26 | `DOC-a6f559e4010fc8d1` | True | 0.625000 | 272.7 | 43997 | 4136 | None |
| 27 | `DOC-1ddc9333769d27e4` | True | 0.470600 | 70.3 | 4450 | 1147 | None |
| 28 | `DOC-dfb4e69a3ab10dc9` | True | 0.521700 | 76.1 | 7378 | 1307 | None |
| 29 | `DOC-472f423cdf0819ef` | True | 0.750000 | 80.5 | 4656 | 1339 | None |
| 30 | `DOC-fe06800cc62e5e19` | True | 0.620700 | 89.9 | 8619 | 1473 | None |
| 31 | `DOC-c9d4c4f8ff433527` | True | 0.526300 | 66.4 | 7730 | 964 | None |
| 32 | `DOC-e0d31c39359cb803` | True | 0.666700 | 63.8 | 6879 | 973 | None |
| 33 | `DOC-8993ad1085e08bd0` | True | 0.789500 | 191.5 | 22402 | 3630 | None |
| 34 | `DOC-d6b6b418dd211b76` | True | 0.482800 | 145.0 | 7293 | 2449 | None |
| 35 | `DOC-3f4003eb02433292` | True | 0.375000 | 95.6 | 4421 | 1664 | None |
| 36 | `DOC-62b300182901e850` | True | 0.454500 | 210.0 | 33346 | 3292 | None |
| 37 | `DOC-4b57f485708ab60b` | True | 0.600000 | 83.9 | 6639 | 1509 | None |
| 38 | `DOC-81c4ce12d907380c` | True | 0.571400 | 328.3 | 7047 | 5732 | None |
| 39 | `DOC-01849fa3020a5ac1` | True | 0.500000 | 47.2 | 4173 | 1077 | None |
| 40 | `DOC-dfd20f94bb76b6e4` | True | 0.583300 | 151.0 | 21000 | 3008 | None |
| 41 | `DOC-8f737e9fec8f24f0` | True | 0.695700 | 261.5 | 35815 | 4920 | None |
| 42 | `DOC-e218d39bb2f3c5ef` | True | 0.480000 | 159.3 | 19923 | 3585 | None |
| 43 | `DOC-712c3f92a0a56b77` | True | 0.578900 | 349.7 | 56227 | 6651 | None |
| 44 | `DOC-2b510409d3b9a4a6` | True | 0.461500 | 504.7 | 21668 | 8578 | None |
| 45 | `DOC-dbe52fd78e44b0ef` | True | 0.857100 | 146.5 | 18750 | 3000 | None |
| 46 | `DOC-6b67382dcf833c5b` | True | 0.785700 | 169.3 | 24554 | 3773 | None |
| 47 | `DOC-e29140d2e8e989be` | True | 0.700000 | 551.8 | 32801 | 3846 | None |
| 48 | `DOC-1266801f2faad19f` | True | 0.682900 | 486.9 | 23527 | 2771 | None |
| 49 | `DOC-aca7df716d7eef00` | True | 0.424200 | 391.3 | 24274 | 1588 | None |
| 50 | `DOC-53e364f030a30b5c` | True | 0.681800 | 744.9 | 81784 | 8800 | None |
