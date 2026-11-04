# Run report — `sand40-50-merger-specialist-awq-2l4`

Dated cell stem: `RUN-50-MERGER-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand40-50-merger-specialist-awq-2l4` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_maud_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `9200d91b723c264b72e5dd25689063ad9886ae108d3ad14320f2c8ebd49b65b9` |
| dataset fingerprint | `23c90708536e` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.139237** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 1658.838 |
| gpu_seconds | 1659.183 |
| estimated GPU cost | 0.737415 |
| **GPU $/doc** | **0.014748** |
| latency p50 / max (s) | 1044.398393 / 2264.440750 |
| prompt / completion tokens | 5334445 / 278545 |
| concurrency speedup (Σlat/wall) | 33.77 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-37026835107f9684` | True | 0 | 605.6 | 97353 | 3463 | None |
| 2 | `DOC-62456d43b50f73fa` | True | 0.062500 | 662.4 | 79234 | 4416 | None |
| 3 | `DOC-8c661a1693d4655b` | True | 0.266667 | 681.3 | 79942 | 4853 | None |
| 4 | `DOC-5fbb9ee2f4b4b114` | True | 0 | 707.8 | 90100 | 3861 | None |
| 5 | `DOC-0a733ab86f2390ae` | True | 0.066667 | 711.3 | 93375 | 4593 | None |
| 6 | `DOC-eac7882cff200545` | True | 0.058824 | 711.5 | 64843 | 3560 | None |
| 7 | `DOC-1252fb5690e17c7b` | True | 0.111111 | 720.4 | 79209 | 4123 | None |
| 8 | `DOC-038a485469f83c9a` | True | 0.250000 | 739.6 | 75770 | 4639 | None |
| 9 | `DOC-8a0bdfe3d16c33b2` | True | 0.117647 | 794.6 | 114164 | 4235 | None |
| 10 | `DOC-7430de65e5471741` | True | 0.263158 | 804.8 | 89823 | 4145 | None |
| 11 | `DOC-be8461dd68cfe458` | True | 0.066667 | 805.5 | 98287 | 4989 | None |
| 12 | `DOC-fc07b37a0f0d1234` | True | 0.250000 | 998.4 | 92499 | 6645 | None |
| 13 | `DOC-c96b9c7e12f91576` | True | 0.176471 | 1018.5 | 106010 | 5889 | None |
| 14 | `DOC-d01014aed8ad8824` | True | 0.125000 | 1043.1 | 95120 | 6382 | None |
| 15 | `DOC-74a69c5b3cdf1afc` | True | 0.333333 | 1045.7 | 149473 | 6495 | None |
| 16 | `DOC-52f9a5be69429299` | True | 0.235294 | 1090.6 | 119128 | 6446 | None |
| 17 | `DOC-882fabf7aba36941` | True | 0.058824 | 1099.6 | 105845 | 6656 | None |
| 18 | `DOC-45f801408be08af6` | True | 0.266667 | 1166.1 | 125130 | 7164 | None |
| 19 | `DOC-c1d57615929b483e` | True | 0.062500 | 1197.9 | 148410 | 6948 | None |
| 20 | `DOC-63beb09b179ea4ee` | True | 0.235294 | 549.6 | 95402 | 3690 | None |
| 21 | `DOC-d554890e66786170` | True | 0.250000 | 1259.6 | 109746 | 6844 | None |
| 22 | `DOC-d0495abfa5f3d8ee` | True | 0.312500 | 1339.8 | 81246 | 3903 | None |
| 23 | `DOC-f546c7d6cf2e77e2` | True | 0 | 309.8 | 33384 | 1839 | None |
| 24 | `DOC-f4e726a7f2c25494` | True | 0.200000 | 1421.9 | 80639 | 3783 | None |
| 25 | `DOC-eb2b56fe30dc35f4` | True | 0.117647 | 1432.2 | 97128 | 3740 | None |
| 26 | `DOC-1e016055aa435e71` | True | 0.250000 | 853.4 | 124347 | 5939 | None |
| 27 | `DOC-26fa94f698c37fc5` | True | 0 | 675.4 | 91761 | 4482 | None |
| 28 | `DOC-ecf69d7e102ef62a` | True | 0.214286 | 1530.2 | 108695 | 4967 | None |
| 29 | `DOC-2f9cf3ce009aaaf0` | True | 0.058824 | 899.9 | 122240 | 6343 | None |
| 30 | `DOC-5c44797b6add60e4` | True | 0.133333 | 870.6 | 92646 | 4066 | None |
| 31 | `DOC-5fa0ba13cf68b593` | True | 0.133333 | 1673.2 | 122413 | 6436 | None |
| 32 | `DOC-169bbcdc5d9e609c` | True | 0.076923 | 692.3 | 153501 | 6094 | None |
| 33 | `DOC-bec74557186e9409` | True | 0 | 1096.3 | 90748 | 5792 | None |
| 34 | `DOC-fd6090e354177e5b` | True | 0.055556 | 766.0 | 105237 | 5145 | None |
| 35 | `DOC-fcaddb5bdc94ce63` | True | 0.117647 | 757.7 | 94486 | 4002 | None |
| 36 | `DOC-4ab4ecd86ecf275d` | True | 0.125000 | 1787.2 | 223834 | 13241 | None |
| 37 | `DOC-b866e2b4f5059213` | True | 0.277778 | 677.7 | 124671 | 5110 | None |
| 38 | `DOC-3927f91bc3daffc3` | True | 0.187500 | 1879.6 | 126652 | 7345 | None |
| 39 | `DOC-03712a2b0a99a314` | True | 0.117647 | 1102.7 | 136267 | 6124 | None |
| 40 | `DOC-2b9f668ab6cb8901` | True | 0.052632 | 1218.9 | 104351 | 3790 | None |
| 41 | `DOC-30eda1e78a5f6fb5` | True | 0.166667 | 1938.9 | 122709 | 6047 | None |
| 42 | `DOC-d5c4f12f934de48e` | True | 0.157895 | 1305.9 | 136741 | 7534 | None |
| 43 | `DOC-8f599c800d19fd92` | True | 0.133333 | 2041.5 | 92531 | 5569 | None |
| 44 | `DOC-8fe2855a2310cdbe` | True | 0.176471 | 1305.5 | 134602 | 7517 | None |
| 45 | `DOC-511062d64bc9afc6` | True | 0.187500 | 2067.4 | 111104 | 10629 | None |
| 46 | `DOC-f099c5c73d56631e` | True | 0 | 1379.5 | 134674 | 7154 | None |
| 47 | `DOC-ab735131c00271bc` | True | 0.111111 | 1018.8 | 93058 | 5461 | None |
| 48 | `DOC-15f85636d1eb6b77` | True | 0.066667 | 2121.1 | 75525 | 4226 | None |
| 49 | `DOC-d1e355800bff0425` | True | 0.125000 | 1177.9 | 103125 | 8012 | None |
| 50 | `DOC-f90cc5fb2ceac154` | True | 0.150000 | 2264.4 | 107267 | 4219 | None |
