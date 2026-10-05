# Run report — `sand40-probe-20-merger-specialist-awq-2l4-64k`

Dated cell stem: `RUN-20-MERGER-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand40-probe-20-merger-specialist-awq-2l4-64k` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_maud_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **20** |
| profile | `modal-vllm` |
| spec_hash | `92316045bdcdfe24ebdda728287bea0fa0ec75ec3d152cc10fc0a62896ef98fc` |
| dataset fingerprint | `7e2b12cc13df` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **20 / 0 / 20** |
| **overall_extraction_score** | **0.123264** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 1472.968 |
| gpu_seconds | 1473.104 |
| estimated GPU cost | 0.654713 |
| **GPU $/doc** | **0.032736** |
| latency p50 / max (s) | 760.858609 / 1820.544089 |
| prompt / completion tokens | 1929564 / 85063 |
| concurrency speedup (Σlat/wall) | 11.12 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-d0495abfa5f3d8ee` | True | 0.125000 | 347.6 | 68549 | 1846 | None |
| 2 | `DOC-511062d64bc9afc6` | True | 0.250000 | 513.2 | 94360 | 3209 | None |
| 3 | `DOC-1e016055aa435e71` | True | 0 | 611.2 | 103239 | 2569 | None |
| 4 | `DOC-7430de65e5471741` | True | 0.210526 | 633.2 | 72975 | 3012 | None |
| 5 | `DOC-63beb09b179ea4ee` | True | 0.235294 | 675.5 | 78473 | 3509 | None |
| 6 | `DOC-d554890e66786170` | True | 0.125000 | 703.5 | 87818 | 3018 | None |
| 7 | `DOC-be8461dd68cfe458` | True | 0 | 704.5 | 80433 | 2940 | None |
| 8 | `DOC-30eda1e78a5f6fb5` | True | 0.166667 | 707.8 | 101577 | 6182 | None |
| 9 | `DOC-03712a2b0a99a314` | True | 0.117647 | 753.6 | 110354 | 4378 | None |
| 10 | `DOC-0a733ab86f2390ae` | True | 0.133333 | 755.4 | 76100 | 3508 | None |
| 11 | `DOC-ecf69d7e102ef62a` | True | 0.071429 | 766.3 | 92137 | 3870 | None |
| 12 | `DOC-8fe2855a2310cdbe` | True | 0.176471 | 801.7 | 109179 | 3882 | None |
| 13 | `DOC-c1d57615929b483e` | True | 0.062500 | 805.5 | 123059 | 3604 | None |
| 14 | `DOC-5fbb9ee2f4b4b114` | True | 0.176471 | 823.2 | 73208 | 4556 | None |
| 15 | `DOC-f4e726a7f2c25494` | True | 0 | 863.9 | 68218 | 3247 | None |
| 16 | `DOC-169bbcdc5d9e609c` | True | 0 | 927.5 | 128031 | 4247 | None |
| 17 | `DOC-5fa0ba13cf68b593` | True | 0.133333 | 1008.2 | 101133 | 3499 | None |
| 18 | `DOC-fcaddb5bdc94ce63` | True | 0.176471 | 1029.3 | 77230 | 2920 | None |
| 19 | `DOC-52f9a5be69429299` | True | 0.117647 | 1133.9 | 98158 | 8297 | None |
| 20 | `DOC-4ab4ecd86ecf275d` | True | 0.187500 | 1820.5 | 185333 | 12770 | None |
