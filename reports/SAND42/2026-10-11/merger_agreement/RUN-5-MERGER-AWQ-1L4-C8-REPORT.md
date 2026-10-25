# Run report — `sand42-check-5-merger-specialist-awq-1l4-c8`

Dated cell stem: `RUN-5-MERGER-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-check-5-merger-specialist-awq-1l4-c8` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **5** |
| profile | `modal-vllm` |
| spec_hash | `d90678b71c629b3cf24655180557a56b4ead7b2aef26c29fbbeaae597fc6ee5b` |
| dataset fingerprint | `a8953394973e` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **5 / 0 / 5** |
| **overall_extraction_score** | **0.015385** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 100.256 |
| gpu_seconds | 100.556 |
| estimated GPU cost | 0.022346 |
| **GPU $/doc** | **0.0044692** |
| latency p50 / max (s) | 357.269877 / 434.479779 |
| prompt / completion tokens | 464217 / 31545 |
| concurrency speedup (Σlat/wall) | 18.69 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-45f801408be08af6` | True | 0 | 334.2 | 109920 | 5153 | None |
| 2 | `DOC-eb2b56fe30dc35f4` | True | 0 | 337.5 | 85298 | 5274 | None |
| 3 | `DOC-ff3ceb691481f1bd` | True | 0 | 357.3 | 91432 | 5651 | None |
| 4 | `DOC-23f224263f6974c5` | True | 0 | 410.8 | 83736 | 7288 | None |
| 5 | `DOC-386ac6d669b7731c` | True | 0.076923 | 434.5 | 93831 | 8179 | None |
