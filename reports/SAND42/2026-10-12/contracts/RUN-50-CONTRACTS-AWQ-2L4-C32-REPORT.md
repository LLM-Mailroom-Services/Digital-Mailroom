# Run report — `sand42-50-contracts-specialist-awq-2l4-c32`

Dated cell stem: `RUN-50-CONTRACTS-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-contracts-specialist-awq-2l4-c32` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `f11ad4ea08f3c19664adb26dea60a556982d0f6d74fe38a61b565224f56d7c18` |
| dataset fingerprint | `5344b28a3033` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.622072** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 783.144 |
| gpu_seconds | 783.551 |
| estimated GPU cost | 0.348245 |
| **GPU $/doc** | **0.0069649** |
| latency p50 / max (s) | 171.433898 / 768.144146 |
| prompt / completion tokens | 792747 / 133634 |
| concurrency speedup (Σlat/wall) | 15.15 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-f8b0d4bcbac60ca2` | True | 0.750000 | 64.7 | 3824 | 574 | None |
| 2 | `DOC-2c3a9c3168cd0e3a` | True | 0.600000 | 83.4 | 3385 | 877 | None |
| 3 | `DOC-27b649fe2f6fae8e` | True | 0.750000 | 90.0 | 5464 | 979 | None |
| 4 | `DOC-f5a54932794ef16e` | True | 0.666700 | 95.8 | 5302 | 1069 | None |
| 5 | `DOC-eaa14fe106140524` | True | 0.625000 | 103.2 | 7001 | 1079 | None |
| 6 | `DOC-268df6c8fabb385a` | True | 0.666700 | 108.9 | 5201 | 1186 | None |
| 7 | `DOC-1843cfdaf5db1840` | True | 0.600000 | 117.2 | 7407 | 1323 | None |
| 8 | `DOC-9a36838df2878b37` | True | 0.521700 | 124.9 | 8142 | 1374 | None |
| 9 | `DOC-e4272758b561f8cd` | True | 0.750000 | 134.8 | 6987 | 1494 | None |
| 10 | `DOC-593f2c6de770b84c` | True | 0.727300 | 138.6 | 9228 | 1570 | None |
| 11 | `DOC-70f90b46b2c4f1a6` | True | 0.750000 | 60.7 | 3154 | 507 | None |
| 12 | `DOC-3c07c9ccd9a01d6e` | True | 0.705900 | 151.8 | 7428 | 1663 | None |
| 13 | `DOC-b83763aeff114369` | True | 0.689700 | 157.0 | 7446 | 1846 | None |
| 14 | `DOC-385a86c69f8e562c` | True | 0.666700 | 160.8 | 6560 | 1759 | None |
| 15 | `DOC-1ddc9333769d27e4` | True | 0.571400 | 76.0 | 4450 | 932 | None |
| 16 | `DOC-a7ea445212692b88` | True | 0.666700 | 171.4 | 9369 | 2031 | None |
| 17 | `DOC-035731e655e67aab` | True | 0.500000 | 171.5 | 5207 | 2055 | None |
| 18 | `DOC-81c4ce12d907380c` | True | 0.571400 | 188.9 | 7047 | 2134 | None |
| 19 | `DOC-cbc1f0d62edbb23e` | True | 0.500000 | 200.6 | 4155 | 2258 | None |
| 20 | `DOC-c9d4c4f8ff433527` | True | 0.588200 | 69.2 | 7730 | 970 | None |
| 21 | `DOC-e998c563b82122b9` | True | 0.526300 | 207.7 | 10006 | 1731 | None |
| 22 | `DOC-dfb4e69a3ab10dc9` | True | 0.413800 | 118.9 | 7378 | 1541 | None |
| 23 | `DOC-e235bc9735f96335` | True | 0.571400 | 232.3 | 10699 | 2887 | None |
| 24 | `DOC-d6b6b418dd211b76` | True | 0.545500 | 126.0 | 7293 | 1826 | None |
| 25 | `DOC-e0d31c39359cb803` | True | 0.631600 | 111.2 | 6879 | 1684 | None |
| 26 | `DOC-1e22a2d4068b8650` | True | 0.714300 | 255.7 | 7587 | 3320 | None |
| 27 | `DOC-62b300182901e850` | True | 0.625000 | 192.2 | 33346 | 2152 | None |
| 28 | `DOC-8993ad1085e08bd0` | True | 0.842100 | 258.2 | 22402 | 3204 | None |
| 29 | `DOC-fe06800cc62e5e19` | True | 0.689700 | 153.2 | 8619 | 1595 | None |
| 30 | `DOC-472f423cdf0819ef` | True | 0.750000 | 167.2 | 4656 | 1850 | None |
| 31 | `DOC-812192e392d8d410` | True | 0.600000 | 289.9 | 5551 | 3333 | None |
| 32 | `DOC-dbe52fd78e44b0ef` | True | 0.869600 | 129.3 | 18750 | 2320 | None |
| 33 | `DOC-4b57f485708ab60b` | True | 0.533300 | 153.6 | 6639 | 1543 | None |
| 34 | `DOC-9cee2e10b449a71c` | True | 0.787900 | 325.6 | 21752 | 3518 | None |
| 35 | `DOC-01849fa3020a5ac1` | True | 0.500000 | 142.8 | 4173 | 1563 | None |
| 36 | `DOC-0752e0811f5f5eb7` | True | 0.444400 | 332.4 | 41619 | 4048 | None |
| 37 | `DOC-e218d39bb2f3c5ef` | True | 0.333300 | 188.1 | 19923 | 2839 | None |
| 38 | `DOC-3f4003eb02433292` | True | 0.307700 | 197.4 | 4421 | 2365 | None |
| 39 | `DOC-1266801f2faad19f` | True | 0.681800 | 362.3 | 33383 | 4725 | None |
| 40 | `DOC-712c3f92a0a56b77` | True | 0.473700 | 376.6 | 56227 | 4260 | None |
| 41 | `DOC-73055dbb1e9f5f2f` | True | 0.413800 | 385.6 | 49409 | 4564 | None |
| 42 | `DOC-4fb6419e37bff201` | True | 0.758600 | 430.4 | 22234 | 6594 | None |
| 43 | `DOC-6b67382dcf833c5b` | True | 0.800000 | 260.0 | 24554 | 3711 | None |
| 44 | `DOC-aca7df716d7eef00` | True | 0.821400 | 353.1 | 36448 | 5855 | None |
| 45 | `DOC-2b510409d3b9a4a6` | True | 0.333300 | 550.7 | 9632 | 1525 | None |
| 46 | `DOC-a6f559e4010fc8d1` | True | 0.642900 | 592.6 | 31544 | 2859 | None |
| 47 | `DOC-8f737e9fec8f24f0` | True | 0.571400 | 520.9 | 23191 | 1822 | None |
| 48 | `DOC-dfd20f94bb76b6e4` | True | 0.592600 | 481.5 | 11041 | 1892 | None |
| 49 | `DOC-e29140d2e8e989be` | True | 0.666700 | 735.1 | 33913 | 7745 | None |
| 50 | `DOC-53e364f030a30b5c` | True | 0.794100 | 768.1 | 94991 | 17083 | None |
