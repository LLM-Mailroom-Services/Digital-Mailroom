# Run report — `sand42-50-contracts-specialist-awq-1l4-c16`

Dated cell stem: `RUN-50-CONTRACTS-AWQ-1L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-contracts-specialist-awq-1l4-c16` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `630a7ebd89f0f3070416706fc458a10f4cc2d06f0ad0ab35eb06ccbe8b233c3d` |
| dataset fingerprint | `5344b28a3033` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.603704** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 1012.399 |
| gpu_seconds | 1012.772 |
| estimated GPU cost | 0.225060 |
| **GPU $/doc** | **0.0045012** |
| latency p50 / max (s) | 167.855964 / 906.099674 |
| prompt / completion tokens | 831734 / 132891 |
| concurrency speedup (Σlat/wall) | 12.53 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-268df6c8fabb385a` | True | 0.666700 | 106.9 | 5201 | 965 | None |
| 2 | `DOC-f5a54932794ef16e` | True | 0.666700 | 122.4 | 5302 | 1154 | None |
| 3 | `DOC-eaa14fe106140524` | True | 0.666700 | 133.9 | 7001 | 1293 | None |
| 4 | `DOC-385a86c69f8e562c` | True | 0.727300 | 140.8 | 6560 | 1406 | None |
| 5 | `DOC-593f2c6de770b84c` | True | 0.736800 | 150.6 | 9228 | 1544 | None |
| 6 | `DOC-a7ea445212692b88` | True | 0.689700 | 161.7 | 9369 | 1665 | None |
| 7 | `DOC-3c07c9ccd9a01d6e` | True | 0.818200 | 169.8 | 7428 | 1733 | None |
| 8 | `DOC-1843cfdaf5db1840` | True | 0.272700 | 49.5 | 7407 | 632 | None |
| 9 | `DOC-cbc1f0d62edbb23e` | True | 0.545500 | 89.8 | 4155 | 1065 | None |
| 10 | `DOC-2c3a9c3168cd0e3a` | True | 0.666700 | 72.7 | 3385 | 858 | None |
| 11 | `DOC-e235bc9735f96335` | True | 0.642900 | 207.7 | 10699 | 2170 | None |
| 12 | `DOC-81c4ce12d907380c` | True | 0.571400 | 90.9 | 7047 | 972 | None |
| 13 | `DOC-e4272758b561f8cd` | True | 0.555600 | 247.6 | 6987 | 2571 | None |
| 14 | `DOC-f8b0d4bcbac60ca2` | True | 0.428600 | 116.6 | 3824 | 1269 | None |
| 15 | `DOC-0752e0811f5f5eb7` | True | 0.400000 | 297.8 | 41619 | 3141 | None |
| 16 | `DOC-b83763aeff114369` | True | 0.666700 | 139.6 | 7446 | 1541 | None |
| 17 | `DOC-4fb6419e37bff201` | True | 0.785700 | 387.1 | 22234 | 4079 | None |
| 18 | `DOC-e998c563b82122b9` | True | 0.526300 | 145.6 | 10006 | 1519 | None |
| 19 | `DOC-035731e655e67aab` | True | 0.600000 | 166.0 | 5207 | 1814 | None |
| 20 | `DOC-9cee2e10b449a71c` | True | 0.750000 | 266.2 | 21752 | 2865 | None |
| 21 | `DOC-70f90b46b2c4f1a6` | True | 0.857100 | 35.0 | 3154 | 443 | None |
| 22 | `DOC-812192e392d8d410` | True | 0.600000 | 268.6 | 5551 | 2885 | None |
| 23 | `DOC-1e22a2d4068b8650` | True | 0.714300 | 207.1 | 7587 | 2192 | None |
| 24 | `DOC-27b649fe2f6fae8e` | True | 0.736800 | 169.7 | 5464 | 1701 | None |
| 25 | `DOC-1ddc9333769d27e4` | True | 0.533300 | 109.9 | 4450 | 1160 | None |
| 26 | `DOC-9a36838df2878b37` | True | 0.381000 | 330.6 | 8142 | 3560 | None |
| 27 | `DOC-fe06800cc62e5e19` | True | 0.631600 | 92.0 | 8619 | 957 | None |
| 28 | `DOC-d6b6b418dd211b76` | True | 0.500000 | 78.7 | 7293 | 921 | None |
| 29 | `DOC-73055dbb1e9f5f2f` | True | 0.585400 | 548.1 | 49409 | 5809 | None |
| 30 | `DOC-62b300182901e850` | True | 0.666700 | 163.6 | 33346 | 1754 | None |
| 31 | `DOC-1266801f2faad19f` | True | 0.684200 | 351.6 | 33383 | 3754 | None |
| 32 | `DOC-472f423cdf0819ef` | True | 0.571400 | 117.3 | 4656 | 1362 | None |
| 33 | `DOC-e0d31c39359cb803` | True | 0.500000 | 110.1 | 6879 | 1239 | None |
| 34 | `DOC-c9d4c4f8ff433527` | True | 0.444400 | 124.7 | 7730 | 1372 | None |
| 35 | `DOC-3f4003eb02433292` | True | 0.347800 | 111.3 | 4421 | 1212 | None |
| 36 | `DOC-4b57f485708ab60b` | True | 0.600000 | 116.8 | 6639 | 1257 | None |
| 37 | `DOC-dfb4e69a3ab10dc9` | True | 0.500000 | 268.7 | 7378 | 2933 | None |
| 38 | `DOC-8993ad1085e08bd0` | True | 0.723400 | 401.5 | 22402 | 4364 | None |
| 39 | `DOC-dfd20f94bb76b6e4` | True | 0.636400 | 183.5 | 21000 | 2163 | None |
| 40 | `DOC-01849fa3020a5ac1` | True | 0.444400 | 92.9 | 4173 | 1149 | None |
| 41 | `DOC-e218d39bb2f3c5ef` | True | 0.421100 | 198.0 | 19923 | 2309 | None |
| 42 | `DOC-53e364f030a30b5c` | True | 0.758600 | 751.8 | 94991 | 8149 | None |
| 43 | `DOC-e29140d2e8e989be` | True | 0.680000 | 791.9 | 45485 | 8921 | None |
| 44 | `DOC-aca7df716d7eef00` | True | 0.697700 | 318.5 | 36448 | 4318 | None |
| 45 | `DOC-8f737e9fec8f24f0` | True | 0.545500 | 409.4 | 35815 | 5275 | None |
| 46 | `DOC-712c3f92a0a56b77` | True | 0.384600 | 651.4 | 56227 | 8257 | None |
| 47 | `DOC-6b67382dcf833c5b` | True | 0.478300 | 228.6 | 24554 | 3772 | None |
| 48 | `DOC-2b510409d3b9a4a6` | True | 0.731700 | 872.4 | 21668 | 10739 | None |
| 49 | `DOC-a6f559e4010fc8d1` | True | 0.588200 | 906.1 | 31544 | 3691 | None |
| 50 | `DOC-dbe52fd78e44b0ef` | True | 0.857100 | 416.7 | 11546 | 1017 | None |
