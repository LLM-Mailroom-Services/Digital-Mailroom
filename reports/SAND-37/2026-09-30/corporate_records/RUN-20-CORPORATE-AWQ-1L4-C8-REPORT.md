# Run report — `grid-20-corporate-records-specialist-awq-1l4`

Dated cell stem: `RUN-20-CORPORATE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-20-corporate-records-specialist-awq-1l4` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **20** |
| profile | `modal-vllm` |
| spec_hash | `c13d7e794b017dd592f8174dec8b7d502e8501ea6e118db537df1c777ab6276e` |
| dataset fingerprint | `49db8ebd55c5` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **20 / 0 / 20** |
| **overall_extraction_score** | **0.459190** |
| schema_valid_rate | 0.950000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 23.359 |
| gpu_seconds | 23.658 |
| estimated GPU cost | 0.005257 |
| **GPU $/doc** | **0.00026285** |
| latency p50 / max (s) | 14.396627 / 20.709734 |
| prompt / completion tokens | 97183 / 3608 |
| concurrency speedup (Σlat/wall) | 12.18 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-db84eb3d59faee66` | True | 0.081300 | 14.4 | 2644 | 173 | None |
| 2 | `DOC-732b812b7d9d9653` | True | 0.888900 | 14.4 | 5572 | 165 | None |
| 3 | `DOC-9cd96711a8928ec5` | True | 0.359000 | 14.4 | 4953 | 169 | None |
| 4 | `DOC-c40a11ac7f2c7b5b` | True | 0.388900 | 14.4 | 2656 | 182 | None |
| 5 | `DOC-a14783cfd27c88c1` | True | 0.596200 | 14.5 | 4571 | 183 | None |
| 6 | `DOC-4a77d0b316e1cc01` | True | 0.697000 | 19.7 | 5497 | 204 | None |
| 7 | `DOC-263580addaac6d20` | True | 0.805600 | 20.5 | 5241 | 238 | None |
| 8 | `DOC-bda69bc956881bab` | True | 0.666700 | 20.7 | 7261 | 247 | None |
| 9 | `DOC-9bdcc670eb06437b` | True | 0.440200 | 12.6 | 2446 | 124 | None |
| 10 | `DOC-4042dc3ecd9ac9b4` | True | 0.149900 | 15.0 | 5283 | 157 | None |
| 11 | `DOC-08829e0f817f1211` | True | 0.452400 | 15.0 | 2947 | 162 | None |
| 12 | `DOC-9523246260be90e0` | True | 0.833300 | 17.5 | 5812 | 190 | None |
| 13 | `DOC-087da9fdf781f7db` | True | 0.435900 | 11.4 | 5240 | 133 | None |
| 14 | `DOC-a2110b2cebe63cb7` | True | 0.755600 | 13.3 | 5308 | 166 | None |
| 15 | `DOC-ef2f0660ed8b6f24` | True | 0.449700 | 20.0 | 6125 | 239 | None |
| 16 | `DOC-a973ebf005e0e785` | True | 0.427800 | 16.3 | 6146 | 234 | None |
| 17 | `DOC-36df577431fb1032` | True | 0.184600 | 9.0 | 5485 | 152 | None |
| 18 | `DOC-69ffaec3ba2b2cde` | True | 0.154700 | 7.8 | 5230 | 160 | None |
| 19 | `DOC-a52b3ad21666d339` | True | 0.169400 | 7.9 | 3538 | 169 | None |
| 20 | `DOC-5cc2960a21fca151` | True | 0.246700 | 5.9 | 5228 | 161 | None |
