# Run report — `sand42-50-contracts-specialist-awq-2l4-c8`

Dated cell stem: `RUN-50-CONTRACTS-AWQ-2L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-contracts-specialist-awq-2l4-c8` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `c1b846e76dbc48058acd686ffe6e284fbc73af4ead4cc0cc0dc45c7d600024e5` |
| dataset fingerprint | `5344b28a3033` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.624102** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 1032.791 |
| gpu_seconds | 1033.123 |
| estimated GPU cost | 0.459166 |
| **GPU $/doc** | **0.00918332** |
| latency p50 / max (s) | 75.563159 / 840.162988 |
| prompt / completion tokens | 800404 / 127141 |
| concurrency speedup (Σlat/wall) | 6.33 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-593f2c6de770b84c` | True | 0.818200 | 39.1 | 9228 | 1435 | None |
| 2 | `DOC-e235bc9735f96335` | True | 0.530600 | 53.2 | 10699 | 980 | None |
| 3 | `DOC-f5a54932794ef16e` | True | 0.666700 | 58.9 | 5302 | 1076 | None |
| 4 | `DOC-385a86c69f8e562c` | True | 0.526300 | 71.8 | 6560 | 1319 | None |
| 5 | `DOC-268df6c8fabb385a` | True | 0.666700 | 39.3 | 5201 | 952 | None |
| 6 | `DOC-3c07c9ccd9a01d6e` | True | 0.720000 | 114.2 | 7428 | 2425 | None |
| 7 | `DOC-a7ea445212692b88` | True | 0.733300 | 76.3 | 9369 | 1864 | None |
| 8 | `DOC-eaa14fe106140524` | True | 0.625000 | 48.8 | 7001 | 1341 | None |
| 9 | `DOC-4fb6419e37bff201` | True | 0.608700 | 200.1 | 22234 | 4639 | None |
| 10 | `DOC-e4272758b561f8cd` | True | 0.555600 | 95.3 | 6987 | 2296 | None |
| 11 | `DOC-1843cfdaf5db1840` | True | 0.600000 | 20.9 | 7407 | 559 | None |
| 12 | `DOC-cbc1f0d62edbb23e` | True | 0.500000 | 61.1 | 4155 | 1634 | None |
| 13 | `DOC-2c3a9c3168cd0e3a` | True | 0.666700 | 37.5 | 3385 | 1261 | None |
| 14 | `DOC-73055dbb1e9f5f2f` | True | 0.727300 | 196.3 | 49409 | 4771 | None |
| 15 | `DOC-f8b0d4bcbac60ca2` | True | 0.666700 | 36.9 | 3824 | 934 | None |
| 16 | `DOC-81c4ce12d907380c` | True | 0.571400 | 35.7 | 7047 | 935 | None |
| 17 | `DOC-0752e0811f5f5eb7` | True | 0.359000 | 324.4 | 41619 | 8121 | None |
| 18 | `DOC-e29140d2e8e989be` | True | 0.627500 | 328.9 | 45485 | 7891 | None |
| 19 | `DOC-b83763aeff114369` | True | 0.774200 | 68.5 | 7446 | 2138 | None |
| 20 | `DOC-9cee2e10b449a71c` | True | 0.736800 | 116.0 | 21752 | 2738 | None |
| 21 | `DOC-812192e392d8d410` | True | 0.600000 | 95.7 | 5551 | 2858 | None |
| 22 | `DOC-9a36838df2878b37` | True | 0.545500 | 70.8 | 8142 | 1606 | None |
| 23 | `DOC-2b510409d3b9a4a6` | True | 0.620700 | 395.2 | 12036 | 2673 | None |
| 24 | `DOC-e998c563b82122b9` | True | 0.500000 | 51.5 | 10006 | 1240 | None |
| 25 | `DOC-1e22a2d4068b8650` | True | 0.705900 | 61.9 | 7587 | 1619 | None |
| 26 | `DOC-27b649fe2f6fae8e` | True | 0.666700 | 50.5 | 5464 | 1180 | None |
| 27 | `DOC-70f90b46b2c4f1a6` | True | 0.666700 | 13.6 | 3154 | 444 | None |
| 28 | `DOC-035731e655e67aab` | True | 0.470600 | 120.4 | 5207 | 3045 | None |
| 29 | `DOC-1ddc9333769d27e4` | True | 0.615400 | 35.7 | 4450 | 1061 | None |
| 30 | `DOC-dfb4e69a3ab10dc9` | True | 0.521700 | 40.9 | 7378 | 1262 | None |
| 31 | `DOC-a6f559e4010fc8d1` | True | 0.774200 | 478.4 | 31544 | 3727 | None |
| 32 | `DOC-8993ad1085e08bd0` | True | 0.742900 | 143.7 | 22402 | 3411 | None |
| 33 | `DOC-712c3f92a0a56b77` | True | 0.384600 | 235.6 | 56227 | 6288 | None |
| 34 | `DOC-d6b6b418dd211b76` | True | 0.416700 | 23.6 | 7293 | 711 | None |
| 35 | `DOC-c9d4c4f8ff433527` | True | 0.750000 | 35.0 | 7730 | 995 | None |
| 36 | `DOC-472f423cdf0819ef` | True | 0.571400 | 74.8 | 4656 | 1777 | None |
| 37 | `DOC-fe06800cc62e5e19` | True | 0.625000 | 79.8 | 8619 | 1861 | None |
| 38 | `DOC-8f737e9fec8f24f0` | True | 0.785700 | 157.5 | 35815 | 3771 | None |
| 39 | `DOC-62b300182901e850` | True | 0.615400 | 224.6 | 33346 | 5513 | None |
| 40 | `DOC-3f4003eb02433292` | True | 0.750000 | 33.6 | 4421 | 849 | None |
| 41 | `DOC-e0d31c39359cb803` | True | 0.500000 | 62.0 | 6879 | 1703 | None |
| 42 | `DOC-1266801f2faad19f` | True | 0.702700 | 413.2 | 23527 | 2797 | None |
| 43 | `DOC-4b57f485708ab60b` | True | 0.545500 | 91.0 | 6639 | 2002 | None |
| 44 | `DOC-e218d39bb2f3c5ef` | True | 0.400000 | 92.5 | 19923 | 2690 | None |
| 45 | `DOC-dbe52fd78e44b0ef` | True | 0.750000 | 85.3 | 18750 | 2068 | None |
| 46 | `DOC-01849fa3020a5ac1` | True | 0.444400 | 33.1 | 4173 | 958 | None |
| 47 | `DOC-dfd20f94bb76b6e4` | True | 0.606100 | 98.0 | 21000 | 2458 | None |
| 48 | `DOC-6b67382dcf833c5b` | True | 0.714300 | 135.9 | 24554 | 3676 | None |
| 49 | `DOC-aca7df716d7eef00` | True | 0.840000 | 244.3 | 36448 | 6151 | None |
| 50 | `DOC-53e364f030a30b5c` | True | 0.692300 | 840.2 | 75945 | 7438 | None |
