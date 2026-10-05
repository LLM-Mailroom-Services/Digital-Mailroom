# Run report — `sand40-probe-20-contracts-specialist-awq-2l4-64k`

Dated cell stem: `RUN-20-CONTRACTS-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand40-probe-20-contracts-specialist-awq-2l4-64k` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **20** |
| profile | `modal-vllm` |
| spec_hash | `664d03167434b5098b75297caefba5f7c08f61888fa01a8f8ba5275dc2a7213d` |
| dataset fingerprint | `704bac6c015d` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **20 / 0 / 20** |
| **overall_extraction_score** | **0.569795** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 105.569 |
| gpu_seconds | 105.728 |
| estimated GPU cost | 0.046990 |
| **GPU $/doc** | **0.0023495** |
| latency p50 / max (s) | 94.926445 / 135.374952 |
| prompt / completion tokens | 142889 / 33650 |
| concurrency speedup (Σlat/wall) | 17.37 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-98ff556893f1a98f` | True | 0.857100 | 29.8 | 2506 | 361 | None |
| 2 | `DOC-440a54573c24b918` | True | 0.800000 | 39.8 | 2799 | 608 | None |
| 3 | `DOC-ade03c57c5f78e21` | True | 0.428600 | 67.6 | 3399 | 1379 | None |
| 4 | `DOC-d1c45d175a8abeb5` | True | 0.714300 | 75.1 | 6157 | 911 | None |
| 5 | `DOC-9e063c6e3baf1233` | True | 0.620700 | 76.6 | 6792 | 1606 | None |
| 6 | `DOC-9696c5996f24d85d` | True | — | 83.4 | 3683 | 1078 | None |
| 7 | `DOC-adad5ef793c0e409` | True | 0.580600 | 83.7 | 8759 | 1819 | None |
| 8 | `DOC-06229aa6571f9d46` | True | 0.782600 | 90.3 | 5460 | 2021 | None |
| 9 | `DOC-dfa5c8eb1e7b837c` | True | 0.750000 | 90.6 | 5361 | 2029 | None |
| 10 | `DOC-ba6d7a0ea5100bbb` | True | 0.777800 | 94.9 | 7587 | 1334 | None |
| 11 | `DOC-c68a4dd90660c113` | True | 0.705900 | 95.0 | 12194 | 2183 | None |
| 12 | `DOC-5892b6dc609c8d0f` | True | — | 96.4 | 6912 | 1384 | None |
| 13 | `DOC-a2ce7adbf6f5cb8d` | True | 0.814800 | 98.3 | 6035 | 2300 | None |
| 14 | `DOC-55df050fcb737129` | True | 0.413800 | 99.8 | 4767 | 1469 | None |
| 15 | `DOC-2ca7b08d2d439f1e` | True | — | 109.9 | 8413 | 1729 | None |
| 16 | `DOC-6712aa595cfe3e2c` | True | 0.631600 | 111.5 | 9648 | 1769 | None |
| 17 | `DOC-99ca00712a84f039` | True | 0.615400 | 112.4 | 4643 | 2902 | None |
| 18 | `DOC-f9b36fee351217c2` | True | 0.526300 | 114.5 | 7237 | 1853 | None |
| 19 | `DOC-c30c293d38a2cd8b` | True | 0.709700 | 128.9 | 25772 | 2330 | None |
| 20 | `DOC-fca31a55b1d526ea` | True | 0.666700 | 135.4 | 4765 | 2585 | None |
