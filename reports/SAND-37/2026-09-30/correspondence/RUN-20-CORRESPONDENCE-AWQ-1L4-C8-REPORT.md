# Run report — `grid-20-correspondence-specialist-awq-1l4`

Dated cell stem: `RUN-20-CORRESPONDENCE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-20-correspondence-specialist-awq-1l4` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **20** |
| profile | `modal-vllm` |
| spec_hash | `db94f6be60731e6859897b39824b98c8dbb3a5259729eb75826fe69eb4e52445` |
| dataset fingerprint | `0ec3314ab111` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **20 / 0 / 20** |
| **overall_extraction_score** | **0.326850** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 10.051 |
| gpu_seconds | 10.385 |
| estimated GPU cost | 0.002308 |
| **GPU $/doc** | **0.0001154** |
| latency p50 / max (s) | 5.759837 / 12.243275 |
| prompt / completion tokens | 47832 / 2710 |
| concurrency speedup (Σlat/wall) | 11.21 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-1d5664e2c826ad07` | True | 0.388900 | 5.8 | 2216 | 104 | None |
| 2 | `DOC-f36a37e1a9c1351e` | True | 0.083300 | 5.8 | 2238 | 104 | None |
| 3 | `DOC-c2826f69ed293da4` | True | 0.049400 | 5.8 | 2229 | 104 | None |
| 4 | `DOC-c71d3ca0b727a0d4` | True | 0.333300 | 5.8 | 2310 | 128 | None |
| 5 | `DOC-38c54645bf0e601a` | True | 0.370400 | 5.9 | 2556 | 132 | None |
| 6 | `DOC-44b1e5a60b363d3e` | True | 0.333300 | 6.1 | 2527 | 141 | None |
| 7 | `DOC-a318b50872273528` | True | 0.681800 | 7.9 | 2559 | 164 | None |
| 8 | `DOC-16dfd03aed14e557` | True | 0 | 3.6 | 2205 | 76 | None |
| 9 | `DOC-38265bcc6ecfecc3` | True | 0.121200 | 4.9 | 2260 | 113 | None |
| 10 | `DOC-cb4f8fb4ccb52f44` | True | 0.333300 | 5.0 | 2270 | 118 | None |
| 11 | `DOC-c4debd478f2c06e0` | True | 0.511900 | 5.9 | 2467 | 137 | None |
| 12 | `DOC-690cb07fef21747b` | True | 0.083300 | 5.9 | 2485 | 140 | None |
| 13 | `DOC-2431095adda97989` | True | 0.175200 | 12.2 | 2606 | 296 | None |
| 14 | `DOC-2cde0c6d0c70b02b` | True | 0.078400 | 7.0 | 2737 | 180 | None |
| 15 | `DOC-d3d85dc1b1514bec` | True | 0.538400 | 5.7 | 2444 | 169 | None |
| 16 | `DOC-edd0a288e32f0d3b` | True | 0.666700 | 4.5 | 2507 | 132 | None |
| 17 | `DOC-5adf644f3cb1d34e` | True | 0 | 2.6 | 2199 | 76 | None |
| 18 | `DOC-21460a9f6d7e6348` | True | 0.784300 | 4.1 | 2337 | 123 | None |
| 19 | `DOC-c4074ed5b08f097e` | True | 0.382700 | 4.1 | 2255 | 128 | None |
| 20 | `DOC-5b63f9fe205d564b` | True | 0.621200 | 4.2 | 2425 | 145 | None |
