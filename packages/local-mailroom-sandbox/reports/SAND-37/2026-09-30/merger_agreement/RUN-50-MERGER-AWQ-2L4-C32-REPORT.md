# Run report — `grid-50-merger-specialist-awq-2l4`

Dated cell stem: `RUN-50-MERGER-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-merger-specialist-awq-2l4` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `0d3c431fb803d3ed9c2afeb6a1f6233535aae1dd64314644b15035408e5f1113` |
| dataset fingerprint | `23c90708536e` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **46 / 4 / 50** |
| **overall_extraction_score** | **0.035119** |
| schema_valid_rate | 1.000000 |
| error_count | 4 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 340.849 |
| gpu_seconds | 341.256 |
| estimated GPU cost | 0.151669 |
| **GPU $/doc** | **0.00329715** |
| latency p50 / max (s) | 92.491563 / 211.573933 |
| prompt / completion tokens | 429708 / 44229 |
| concurrency speedup (Σlat/wall) | 13.52 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-0a733ab86f2390ae` | True | 0.066667 | 75.2 | 8841 | 695 | None |
| 2 | `DOC-37026835107f9684` | True | 0 | 78.3 | 9439 | 681 | None |
| 3 | `DOC-511062d64bc9afc6` | True | 0.062500 | 79.2 | 9338 | 686 | None |
| 4 | `DOC-52f9a5be69429299` | True | 0 | 80.4 | 9517 | 573 | None |
| 5 | `DOC-f90cc5fb2ceac154` | True | 0 | 82.4 | 9529 | 705 | None |
| 6 | `DOC-eac7882cff200545` | True | 0 | 86.3 | 9334 | 767 | None |
| 7 | `DOC-5fa0ba13cf68b593` | True | 0 | 86.8 | 9125 | 585 | None |
| 8 | `DOC-be8461dd68cfe458` | True | 0.066667 | 92.0 | 9054 | 826 | None |
| 9 | `DOC-ecf69d7e102ef62a` | True | 0 | 92.4 | 9271 | 824 | None |
| 10 | `DOC-882fabf7aba36941` | True | 0 | 94.2 | 9595 | 848 | None |
| 11 | `DOC-62456d43b50f73fa` | True | 0.062500 | 94.9 | 9688 | 860 | None |
| 12 | `DOC-d0495abfa5f3d8ee` | True | 0.062500 | 92.6 | 9008 | 798 | None |
| 13 | `DOC-4ab4ecd86ecf275d` | True | 0.062500 | 93.2 | 9590 | 814 | None |
| 14 | `DOC-c96b9c7e12f91576` | True | 0 | 93.7 | 9549 | 658 | None |
| 15 | `DOC-1252fb5690e17c7b` | True | 0.055556 | 97.9 | 9296 | 711 | None |
| 16 | `DOC-74a69c5b3cdf1afc` | True | 0.066667 | 106.3 | 10224 | 782 | None |
| 17 | `DOC-30eda1e78a5f6fb5` | True | 0 | 107.1 | 9124 | 795 | None |
| 18 | `DOC-c1d57615929b483e` | True | 0 | 110.9 | 9148 | 767 | None |
| 19 | `DOC-15f85636d1eb6b77` | True | 0.066667 | 114.7 | 9514 | 771 | None |
| 20 | `DOC-8a0bdfe3d16c33b2` | True | 0.058824 | 114.7 | 9360 | 988 | None |
| 21 | `DOC-f4e726a7f2c25494` | True | 0.133333 | 115.3 | 9345 | 994 | None |
| 22 | `DOC-45f801408be08af6` | True | 0.133333 | 119.5 | 10160 | 843 | None |
| 23 | `DOC-fc07b37a0f0d1234` | True | 0.125000 | 125.7 | 9170 | 888 | None |
| 24 | `DOC-7430de65e5471741` | True | 0 | 130.2 | 9060 | 922 | None |
| 25 | `DOC-5fbb9ee2f4b4b114` | True | 0 | 131.5 | 9027 | 1316 | None |
| 26 | `DOC-038a485469f83c9a` | True | 0.062500 | 133.5 | 9115 | 967 | None |
| 27 | `DOC-1e016055aa435e71` | True | 0 | 64.5 | 9148 | 790 | None |
| 28 | `DOC-8c661a1693d4655b` | True | 0 | 143.1 | 9289 | 1166 | None |
| 29 | `DOC-d5c4f12f934de48e` | True | 0.105263 | 63.5 | 9465 | 881 | None |
| 30 | `DOC-f546c7d6cf2e77e2` | True | 0.052632 | 41.0 | 8785 | 744 | None |
| 31 | `DOC-eb2b56fe30dc35f4` | True | 0 | 148.4 | 8971 | 1239 | None |
| 32 | `DOC-d1e355800bff0425` | True | 0 | 53.7 | 9196 | 797 | None |
| 33 | `DOC-fcaddb5bdc94ce63` | True | 0.058824 | 56.9 | 9123 | 888 | None |
| 34 | `DOC-f099c5c73d56631e` | True | 0 | 72.4 | 9893 | 1195 | None |
| 35 | `DOC-fd6090e354177e5b` | True | 0 | 63.9 | 8909 | 1082 | None |
| 36 | `DOC-3927f91bc3daffc3` | True | 0 | 164.8 | 9676 | 916 | None |
| 37 | `DOC-8f599c800d19fd92` | True | 0 | 167.2 | 9146 | 1022 | None |
| 38 | `DOC-d554890e66786170` | True | 0 | 168.2 | 10446 | 1579 | None |
| 39 | `DOC-bec74557186e9409` | True | 0 | 90.9 | 9430 | 942 | None |
| 40 | `DOC-169bbcdc5d9e609c` | True | 0.076923 | 71.8 | 9975 | 1395 | None |
| 41 | `DOC-2f9cf3ce009aaaf0` | True | 0.058824 | 91.9 | 9043 | 991 | None |
| 42 | `DOC-5c44797b6add60e4` | True | 0.066667 | 77.6 | 9230 | 1543 | None |
| 43 | `DOC-03712a2b0a99a314` | True | 0 | 80.9 | 9286 | 1014 | None |
| 44 | `DOC-ab735131c00271bc` | True | 0.055556 | 73.9 | 8800 | 1051 | None |
| 45 | `DOC-b866e2b4f5059213` | True | 0.055556 | 72.4 | 9099 | 1078 | None |
| 46 | `DOC-d01014aed8ad8824` | True | 0 | 211.6 | 9377 | 2852 | None |
| 47 | `DOC-63beb09b179ea4ee` | False | — | 263.2 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9374, total_tokens=17566, completion_tokens_details=None, prompt_tokens_details=None) |
| 48 | `DOC-2b9f668ab6cb8901` | False | — | 329.3 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=8927, total_tokens=17119, completion_tokens_details=None, prompt_tokens_details=None) |
| 49 | `DOC-8fe2855a2310cdbe` | False | — | 323.6 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9249, total_tokens=17441, completion_tokens_details=None, prompt_tokens_details=None) |
| 50 | `DOC-26fa94f698c37fc5` | False | — | 319.8 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9043, total_tokens=17235, completion_tokens_details=None, prompt_tokens_details=None) |
