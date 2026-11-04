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
| dataset fingerprint | `5344b28a3033` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **43 / 7 / 50** |
| **overall_extraction_score** | **0.541009** |
| schema_valid_rate | 1.000000 |
| error_count | 7 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 914.174 |
| gpu_seconds | 914.503 |
| estimated GPU cost | 0.203223 |
| **GPU $/doc** | **0.00472612** |
| latency p50 / max (s) | 91.581425 / 625.866134 |
| prompt / completion tokens | 569440 / 91099 |
| concurrency speedup (Σlat/wall) | 6.74 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-593f2c6de770b84c` | True | 0.736800 | 71.7 | 9228 | 1137 | None |
| 2 | `DOC-385a86c69f8e562c` | True | 0.666700 | 84.3 | 6560 | 1357 | None |
| 3 | `DOC-3c07c9ccd9a01d6e` | True | 0.705900 | 89.2 | 7428 | 1408 | None |
| 4 | `DOC-f5a54932794ef16e` | True | 0.666700 | 97.0 | 5302 | 1519 | None |
| 5 | `DOC-268df6c8fabb385a` | True | 0.666700 | 56.3 | 5201 | 941 | None |
| 6 | `DOC-a7ea445212692b88` | True | 0.620700 | 97.9 | 9369 | 1714 | None |
| 7 | `DOC-4fb6419e37bff201` | True | 0.545500 | 249.5 | 22234 | 4297 | None |
| 8 | `DOC-73055dbb1e9f5f2f` | True | 0.650000 | 212.1 | 49409 | 3825 | None |
| 9 | `DOC-eaa14fe106140524` | True | 0.625000 | 88.5 | 7001 | 1533 | None |
| 10 | `DOC-a6f559e4010fc8d1` | True | 0.625000 | 229.3 | 43997 | 4238 | None |
| 11 | `DOC-cbc1f0d62edbb23e` | True | 0.500000 | 50.4 | 4155 | 1008 | None |
| 12 | `DOC-e29140d2e8e989be` | True | 0.604700 | 411.5 | 45485 | 7385 | None |
| 13 | `DOC-1843cfdaf5db1840` | True | 0.600000 | 65.6 | 7407 | 1330 | None |
| 14 | `DOC-2c3a9c3168cd0e3a` | True | 0.750000 | 54.8 | 3385 | 1174 | None |
| 15 | `DOC-e235bc9735f96335` | False | — | 452.1 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=10699, total_tokens=18891, completion_tokens_details=None, prompt_tokens_details=None) |
| 16 | `DOC-0752e0811f5f5eb7` | True | 0.413800 | 452.4 | 41619 | 8170 | None |
| 17 | `DOC-f8b0d4bcbac60ca2` | True | 0.727300 | 60.3 | 3824 | 1180 | None |
| 18 | `DOC-b83763aeff114369` | True | 0.666700 | 99.6 | 7446 | 1989 | None |
| 19 | `DOC-9a36838df2878b37` | True | 0.500000 | 91.6 | 8142 | 1766 | None |
| 20 | `DOC-81c4ce12d907380c` | True | 0.758600 | 127.7 | 7047 | 2381 | None |
| 21 | `DOC-812192e392d8d410` | True | 0.600000 | 139.0 | 5551 | 2737 | None |
| 22 | `DOC-e4272758b561f8cd` | False | — | 430.4 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=6987, total_tokens=15179, completion_tokens_details=None, prompt_tokens_details=None) |
| 23 | `DOC-9cee2e10b449a71c` | True | 0.685700 | 173.5 | 21752 | 3265 | None |
| 24 | `DOC-e998c563b82122b9` | True | 0.500000 | 86.2 | 10006 | 1701 | None |
| 25 | `DOC-27b649fe2f6fae8e` | True | 0.666700 | 74.0 | 5464 | 1532 | None |
| 26 | `DOC-1e22a2d4068b8650` | True | 0.714300 | 82.0 | 7587 | 1606 | None |
| 27 | `DOC-2b510409d3b9a4a6` | True | 0.647100 | 625.9 | 9632 | 3633 | None |
| 28 | `DOC-035731e655e67aab` | True | 0.470600 | 140.3 | 5207 | 2801 | None |
| 29 | `DOC-1266801f2faad19f` | True | 0.555600 | 162.3 | 33383 | 3063 | None |
| 30 | `DOC-70f90b46b2c4f1a6` | True | 0.666700 | 20.1 | 3154 | 388 | None |
| 31 | `DOC-1ddc9333769d27e4` | True | 0.571400 | 56.4 | 4450 | 1143 | None |
| 32 | `DOC-fe06800cc62e5e19` | True | 0.714300 | 75.2 | 8619 | 1451 | None |
| 33 | `DOC-dfb4e69a3ab10dc9` | True | 0.526300 | 101.0 | 7378 | 1935 | None |
| 34 | `DOC-8993ad1085e08bd0` | True | 0.717900 | 170.4 | 22402 | 3156 | None |
| 35 | `DOC-472f423cdf0819ef` | True | 0.571400 | 101.0 | 4656 | 1829 | None |
| 36 | `DOC-d6b6b418dd211b76` | True | 0.500000 | 67.2 | 7293 | 1211 | None |
| 37 | `DOC-62b300182901e850` | True | 0.615400 | 194.1 | 33346 | 3598 | None |
| 38 | `DOC-c9d4c4f8ff433527` | False | — | 50.7 | — | — | OpenAIModelNotFoundError: modal-http: invalid function call |
| 39 | `DOC-aca7df716d7eef00` | True | 0 | 83.2 | — | — | None |
| 40 | `DOC-3f4003eb02433292` | False | — | 41.4 | — | — | OpenAIModelNotFoundError: modal-http: invalid function call |
| 41 | `DOC-e218d39bb2f3c5ef` | True | 0 | 0.2 | — | — | None |
| 42 | `DOC-dfd20f94bb76b6e4` | True | 0 | 0.2 | — | — | None |
| 43 | `DOC-e0d31c39359cb803` | False | — | 43.7 | — | — | OpenAIModelNotFoundError: modal-http: invalid function call |
| 44 | `DOC-4b57f485708ab60b` | False | — | 13.9 | — | — | OpenAIModelNotFoundError: modal-http: invalid function call |
| 45 | `DOC-8f737e9fec8f24f0` | True | 0.583300 | 190.3 | 24509 | 3045 | None |
| 46 | `DOC-01849fa3020a5ac1` | False | — | 0.1 | — | — | OpenAIModelNotFoundError: modal-http: invalid function call |
| 47 | `DOC-53e364f030a30b5c` | True | 0.512800 | 589.8 | 48552 | 3584 | None |
| 48 | `DOC-6b67382dcf833c5b` | True | 0 | 0.2 | — | — | None |
| 49 | `DOC-dbe52fd78e44b0ef` | True | 0 | 0.4 | — | — | None |
| 50 | `DOC-712c3f92a0a56b77` | True | 0.413800 | 335.8 | 12260 | 1069 | None |
