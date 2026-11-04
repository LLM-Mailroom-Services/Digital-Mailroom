# Run report — `sand42-check-5-corporate-records-awq-1l4-c8`

Dated cell stem: `RUN-5-CORPORATE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-check-5-corporate-records-awq-1l4-c8` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **5** |
| profile | `modal-vllm` |
| spec_hash | `53132be4adb9daffc4ab11b8526b5d3d2163912fe597a59adf2c204fd35fd16c` |
| dataset fingerprint | `34c1303db918` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **5 / 0 / 5** |
| **overall_extraction_score** | **0.562480** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 1.323 |
| gpu_seconds | 1.668 |
| estimated GPU cost | 0.000371 |
| **GPU $/doc** | **7.42e-05** |
| latency p50 / max (s) | 11.019479 / 12.338814 |
| prompt / completion tokens | 20069 / 847 |
| concurrency speedup (Σlat/wall) | 42.64 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-f134b9491efc5c57` | True | 0.461500 | 11.0 | 2865 | 151 | None |
| 2 | `DOC-0a8eb16fff7e67ca` | True | 0.692300 | 11.0 | 5246 | 150 | None |
| 3 | `DOC-e478fa89043a29e3` | True | 0.820500 | 11.0 | 2910 | 151 | None |
| 4 | `DOC-37152a33cfb70d37` | True | 0.410300 | 11.0 | 2902 | 161 | None |
| 5 | `DOC-a973ebf005e0e785` | True | 0.427800 | 12.3 | 6146 | 234 | None |
