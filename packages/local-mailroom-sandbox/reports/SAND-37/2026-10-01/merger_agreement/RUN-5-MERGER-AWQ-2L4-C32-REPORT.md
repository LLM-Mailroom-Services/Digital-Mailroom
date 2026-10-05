# Run report — `sand40-check-5-merger-specialist-awq-2l4`

Dated cell stem: `RUN-5-MERGER-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand40-check-5-merger-specialist-awq-2l4` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_maud_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **5** |
| profile | `modal-vllm` |
| spec_hash | `596b9a2c722cc9b6bda926ed815eaa7aa7f4322f82d20a555e9c650929ff53cb` |
| dataset fingerprint | `d411e98fb6b8` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **5 / 0 / 5** |
| **overall_extraction_score** | **0.136225** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 284.493 |
| gpu_seconds | 284.852 |
| estimated GPU cost | 0.126601 |
| **GPU $/doc** | **0.025320** |
| latency p50 / max (s) | 268.796788 / 465.657994 |
| prompt / completion tokens | 556273 / 24996 |
| concurrency speedup (Σlat/wall) | 5.70 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-f4e726a7f2c25494` | True | 0.133333 | 181.2 | 80639 | 3891 | None |
| 2 | `DOC-1e016055aa435e71` | True | 0.125000 | 247.7 | 124347 | 4470 | None |
| 3 | `DOC-52f9a5be69429299` | True | 0.235294 | 268.8 | 119128 | 5814 | None |
| 4 | `DOC-d554890e66786170` | True | 0.187500 | 458.0 | 109746 | 5154 | None |
| 5 | `DOC-5fa0ba13cf68b593` | True | 0 | 465.7 | 122413 | 5667 | None |
