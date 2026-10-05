# Run report — `grid-20-insurance-claims-specialist-awq-1l4`

Dated cell stem: `RUN-20-INSURANCE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-20-insurance-claims-specialist-awq-1l4` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **20** |
| profile | `modal-vllm` |
| spec_hash | `b52b9ad6e910d3c15796e087dbce011b42ba7cbc241a8c3e2b655cc7a79b9ee4` |
| dataset fingerprint | `6c72fe4bf896` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **20 / 0 / 20** |
| **overall_extraction_score** | **0.683625** |
| schema_valid_rate | 0.300000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 37.793 |
| gpu_seconds | 38.078 |
| estimated GPU cost | 0.008462 |
| **GPU $/doc** | **0.0004231** |
| latency p50 / max (s) | 13.183466 / 24.811473 |
| prompt / completion tokens | 60771 / 7765 |
| concurrency speedup (Σlat/wall) | 7.11 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-edc5811634a19b7a` | True | 0.805600 | 11.9 | 2835 | 292 | None |
| 2 | `DOC-dcb4333f78bfe249` | True | 0.636300 | 13.2 | 2934 | 345 | None |
| 3 | `DOC-c0e145a5a0a0d4bd` | True | 0.793000 | 13.2 | 2833 | 347 | None |
| 4 | `DOC-4fd4cf5db3cfdb47` | True | 0.683900 | 13.4 | 2940 | 354 | None |
| 5 | `DOC-d5e1b8ed3350fb36` | True | 0.629000 | 14.6 | 2969 | 370 | None |
| 6 | `DOC-4dda6e74e78edd70` | True | 0.642800 | 14.9 | 2949 | 375 | None |
| 7 | `DOC-a1a2afde18ded42d` | True | 0.688500 | 16.1 | 3086 | 396 | None |
| 8 | `DOC-576c9233159914e3` | True | 0.682500 | 19.0 | 3080 | 496 | None |
| 9 | `DOC-b3be1f4b2b6142ed` | True | 0.695500 | 10.1 | 2815 | 289 | None |
| 10 | `DOC-596b1f881ecf4a8a` | True | 0.716300 | 9.7 | 2806 | 305 | None |
| 11 | `DOC-c0d9bf1e6be4ad51` | True | 0.701500 | 10.2 | 2808 | 314 | None |
| 12 | `DOC-85e24caa52979f50` | True | 0.711400 | 13.0 | 3121 | 368 | None |
| 13 | `DOC-df5ebe3e7263b6c6` | True | 0.638500 | 9.3 | 2815 | 288 | None |
| 14 | `DOC-a0be2aba09a3f580` | True | 0.691300 | 14.1 | 3095 | 367 | None |
| 15 | `DOC-17abdc452037b6eb` | True | 0.704100 | 15.8 | 3129 | 433 | None |
| 16 | `DOC-4348717727f6d6b4` | True | 0.645600 | 13.2 | 3004 | 408 | None |
| 17 | `DOC-01f1577c446c646d` | True | 0.599300 | 10.0 | 2868 | 332 | None |
| 18 | `DOC-4e21681f375a247d` | True | 0.641100 | 10.8 | 2985 | 347 | None |
| 19 | `DOC-ab3b194998a42322` | True | 0.613100 | 11.7 | 3016 | 371 | None |
| 20 | `DOC-0966e6d5a9e7bd71` | True | 0.753200 | 24.8 | 4683 | 968 | None |
