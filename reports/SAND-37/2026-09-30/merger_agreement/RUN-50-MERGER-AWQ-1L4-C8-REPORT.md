# Run report — `grid-50-merger-specialist-awq-1l4`

Dated cell stem: `RUN-50-MERGER-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-merger-specialist-awq-1l4` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `318540cd982a6f3435b45a9ce428d290380f5e922b3e424c547d9330e353e9af` |
| dataset fingerprint | `23c90708536e` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **46 / 4 / 50** |
| **overall_extraction_score** | **0.047983** |
| schema_valid_rate | 1.000000 |
| error_count | 4 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 588.411 |
| gpu_seconds | 589.405 |
| estimated GPU cost | 0.130979 |
| **GPU $/doc** | **0.00284737** |
| latency p50 / max (s) | 51.255857 / 146.059443 |
| prompt / completion tokens | 428281 / 44106 |
| concurrency speedup (Σlat/wall) | 4.52 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c1d57615929b483e` | True | 0 | 52.6 | 9148 | 701 | None |
| 2 | `DOC-038a485469f83c9a` | True | 0.062500 | 61.6 | 9115 | 876 | None |
| 3 | `DOC-eb2b56fe30dc35f4` | True | 0.058824 | 62.0 | 8971 | 867 | None |
| 4 | `DOC-3927f91bc3daffc3` | True | 0.062500 | 69.4 | 9676 | 921 | None |
| 5 | `DOC-8c661a1693d4655b` | True | 0 | 69.6 | 9289 | 942 | None |
| 6 | `DOC-4ab4ecd86ecf275d` | True | 0.187500 | 76.0 | 9590 | 983 | None |
| 7 | `DOC-d554890e66786170` | True | 0.187500 | 82.2 | 10446 | 1067 | None |
| 8 | `DOC-c96b9c7e12f91576` | True | 0 | 45.4 | 9549 | 657 | None |
| 9 | `DOC-52f9a5be69429299` | True | 0 | 30.9 | 9517 | 546 | None |
| 10 | `DOC-0a733ab86f2390ae` | True | 0.133333 | 49.6 | 8841 | 708 | None |
| 11 | `DOC-62456d43b50f73fa` | True | 0.062500 | 49.9 | 9688 | 761 | None |
| 12 | `DOC-eac7882cff200545` | True | 0 | 62.9 | 9334 | 918 | None |
| 13 | `DOC-d0495abfa5f3d8ee` | True | 0.062500 | 59.1 | 9008 | 867 | None |
| 14 | `DOC-7430de65e5471741` | True | 0.052632 | 58.0 | 9060 | 962 | None |
| 15 | `DOC-d01014aed8ad8824` | True | 0.062500 | 47.5 | 9377 | 712 | None |
| 16 | `DOC-8f599c800d19fd92` | True | 0 | 49.8 | 9146 | 817 | None |
| 17 | `DOC-fc07b37a0f0d1234` | True | 0 | 45.6 | 9170 | 714 | None |
| 18 | `DOC-5fbb9ee2f4b4b114` | True | 0 | 42.3 | 9027 | 693 | None |
| 19 | `DOC-8a0bdfe3d16c33b2` | True | 0.058824 | 46.3 | 9360 | 732 | None |
| 20 | `DOC-37026835107f9684` | True | 0.083333 | 52.7 | 9439 | 853 | None |
| 21 | `DOC-15f85636d1eb6b77` | True | 0.066667 | 54.1 | 9514 | 889 | None |
| 22 | `DOC-511062d64bc9afc6` | True | 0.062500 | 45.2 | 9338 | 796 | None |
| 23 | `DOC-be8461dd68cfe458` | True | 0 | 109.7 | 9054 | 1798 | None |
| 24 | `DOC-5fa0ba13cf68b593` | True | 0 | 37.5 | 9125 | 628 | None |
| 25 | `DOC-f4e726a7f2c25494` | True | 0.066667 | 44.7 | 9345 | 792 | None |
| 26 | `DOC-74a69c5b3cdf1afc` | True | 0 | 83.8 | 10224 | 1455 | None |
| 27 | `DOC-1e016055aa435e71` | True | 0 | 36.3 | 9148 | 700 | None |
| 28 | `DOC-f90cc5fb2ceac154` | True | 0 | 57.4 | 9529 | 1071 | None |
| 29 | `DOC-1252fb5690e17c7b` | True | 0.055556 | 83.2 | 9296 | 1495 | None |
| 30 | `DOC-882fabf7aba36941` | True | 0 | 146.1 | 9595 | 2535 | None |
| 31 | `DOC-bec74557186e9409` | True | 0.071429 | 58.0 | 9430 | 1028 | None |
| 32 | `DOC-63beb09b179ea4ee` | True | 0.058824 | 52.4 | 9374 | 893 | None |
| 33 | `DOC-2f9cf3ce009aaaf0` | True | 0.058824 | 50.1 | 9043 | 842 | None |
| 34 | `DOC-2b9f668ab6cb8901` | True | 0.105263 | 44.3 | 8927 | 770 | None |
| 35 | `DOC-f099c5c73d56631e` | True | 0 | 44.3 | 9893 | 764 | None |
| 36 | `DOC-5c44797b6add60e4` | True | 0.066667 | 46.5 | 9230 | 866 | None |
| 37 | `DOC-8fe2855a2310cdbe` | True | 0.058824 | 60.4 | 9249 | 1070 | None |
| 38 | `DOC-03712a2b0a99a314` | True | 0 | 45.5 | 9286 | 788 | None |
| 39 | `DOC-fcaddb5bdc94ce63` | True | 0.058824 | 38.2 | 9123 | 723 | None |
| 40 | `DOC-d1e355800bff0425` | True | 0.062500 | 39.4 | 9196 | 740 | None |
| 41 | `DOC-fd6090e354177e5b` | True | 0 | 58.5 | 8909 | 1001 | None |
| 42 | `DOC-ab735131c00271bc` | True | 0.055556 | 34.2 | 8800 | 622 | None |
| 43 | `DOC-169bbcdc5d9e609c` | True | 0 | 45.1 | 9975 | 735 | None |
| 44 | `DOC-26fa94f698c37fc5` | True | 0.176471 | 122.4 | 9043 | 2242 | None |
| 45 | `DOC-45f801408be08af6` | False | — | 484.8 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=10160, total_tokens=18352, completion_tokens_details=None, prompt_tokens_details=None) |
| 46 | `DOC-f546c7d6cf2e77e2` | True | 0.052632 | 47.6 | 8785 | 946 | None |
| 47 | `DOC-b866e2b4f5059213` | True | 0.055556 | 63.9 | 9099 | 1620 | None |
| 48 | `DOC-30eda1e78a5f6fb5` | False | — | 408.0 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9124, total_tokens=17316, completion_tokens_details=None, prompt_tokens_details=None) |
| 49 | `DOC-ecf69d7e102ef62a` | False | — | 384.0 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9271, total_tokens=17463, completion_tokens_details=None, prompt_tokens_details=None) |
| 50 | `DOC-d5c4f12f934de48e` | False | — | 341.1 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9465, total_tokens=17657, completion_tokens_details=None, prompt_tokens_details=None) |
