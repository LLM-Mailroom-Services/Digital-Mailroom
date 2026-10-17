# Run report — `sand42-50-merger-specialist-awq-2l4-c32`

Dated cell stem: `RUN-50-MERGER-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-merger-specialist-awq-2l4-c32` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `a96e6fbc7723e70b6791b0cc80dbf3a642d69d5e80343d13509bc338def6be2e` |
| dataset fingerprint | `aa4e596805e7` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.020855** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 1937.171 |
| gpu_seconds | 1937.693 |
| estimated GPU cost | 0.861197 |
| **GPU $/doc** | **0.017224** |
| latency p50 / max (s) | 935.459782 / 1630.016426 |
| prompt / completion tokens | 4867606 / 323439 |
| concurrency speedup (Σlat/wall) | 24.56 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-26933c93d649fa3f` | True | 0.062500 | 575.6 | 96354 | 3350 | None |
| 2 | `DOC-eb2b56fe30dc35f4` | True | 0 | 715.2 | 85298 | 4537 | None |
| 3 | `DOC-dc7f18df501aec90` | True | 0 | 715.4 | 83008 | 4374 | None |
| 4 | `DOC-63beb09b179ea4ee` | True | 0.058824 | 743.8 | 83572 | 4931 | None |
| 5 | `DOC-4f45bef14dcd1dbf` | True | 0.062500 | 751.9 | 70774 | 3881 | None |
| 6 | `DOC-bec74557186e9409` | True | 0 | 798.3 | 78918 | 5295 | None |
| 7 | `DOC-511062d64bc9afc6` | True | 0 | 822.0 | 97584 | 4954 | None |
| 8 | `DOC-72b0b8c8385edd48` | True | 0 | 840.3 | 84431 | 5131 | None |
| 9 | `DOC-7e2818ceb0167d5a` | True | 0.055556 | 884.1 | 78432 | 5022 | None |
| 10 | `DOC-0534799ed39ca0db` | True | 0.055556 | 931.0 | 92828 | 5876 | None |
| 11 | `DOC-1e016055aa435e71` | True | 0 | 939.9 | 109137 | 6060 | None |
| 12 | `DOC-2b9f668ab6cb8901` | True | 0.052632 | 969.0 | 90831 | 5361 | None |
| 13 | `DOC-37bc3c44ae2c4ef6` | True | 0 | 978.1 | 90012 | 5687 | None |
| 14 | `DOC-5f5d40f6b2c338ac` | True | 0 | 989.7 | 109887 | 6851 | None |
| 15 | `DOC-9420b777a4b0784c` | True | 0 | 1025.8 | 98627 | 6406 | None |
| 16 | `DOC-30eda1e78a5f6fb5` | True | 0 | 1039.4 | 107499 | 5905 | None |
| 17 | `DOC-386ac6d669b7731c` | True | 0.076923 | 1051.8 | 93831 | 5997 | None |
| 18 | `DOC-e8538f75b0f993e6` | True | 0 | 1070.4 | 113280 | 6492 | None |
| 19 | `DOC-882fabf7aba36941` | True | 0 | 1082.1 | 92325 | 6292 | None |
| 20 | `DOC-d4b1a7a2b981fbf4` | True | 0 | 1097.5 | 81817 | 6520 | None |
| 21 | `DOC-5f8ef95caa2fd349` | True | 0 | 1126.0 | 104105 | 7488 | None |
| 22 | `DOC-71bc59dd305ee8ed` | True | 0.076923 | 1134.9 | 109675 | 6972 | None |
| 23 | `DOC-45f801408be08af6` | True | 0 | 1177.9 | 109920 | 6735 | None |
| 24 | `DOC-b03c0d2bbbb9659e` | True | 0 | 1179.4 | 113393 | 7114 | None |
| 25 | `DOC-297745a521cd1e8c` | True | 0 | 1314.5 | 103150 | 8886 | None |
| 26 | `DOC-ab5578f1f9f04244` | True | 0 | 1339.5 | 132059 | 8481 | None |
| 27 | `DOC-26fa94f698c37fc5` | True | 0.058824 | 630.9 | 79931 | 4932 | None |
| 28 | `DOC-c6b5f7ea5f718c28` | True | 0.058824 | 1366.3 | 82765 | 8948 | None |
| 29 | `DOC-52f9a5be69429299` | True | 0 | 1381.3 | 103918 | 9635 | None |
| 30 | `DOC-fcaddb5bdc94ce63` | True | 0.058824 | 689.9 | 82656 | 4668 | None |
| 31 | `DOC-0a733ab86f2390ae` | True | 0.066667 | 1490.0 | 81545 | 4595 | None |
| 32 | `DOC-c96b9c7e12f91576` | True | 0 | 1491.5 | 92490 | 10698 | None |
| 33 | `DOC-9d34581755c603a3` | True | 0 | 652.2 | 94942 | 4530 | None |
| 34 | `DOC-b3d0149fd994357a` | True | 0.058824 | 583.3 | 78500 | 4951 | None |
| 35 | `DOC-ab735131c00271bc` | True | 0 | 568.8 | 81228 | 4608 | None |
| 36 | `DOC-ac48214468deb8dd` | True | 0 | 745.3 | 72887 | 5864 | None |
| 37 | `DOC-1cd38a83b224335d` | True | 0.058824 | 626.2 | 78294 | 4974 | None |
| 38 | `DOC-169bbcdc5d9e609c` | True | 0 | 687.2 | 134911 | 6038 | None |
| 39 | `DOC-fe9a8b51344d67d9` | True | 0 | 1577.9 | 130099 | 10957 | None |
| 40 | `DOC-e6c8852b877c4598` | True | 0.055556 | 792.5 | 104093 | 6485 | None |
| 41 | `DOC-f90cc5fb2ceac154` | True | 0 | 1630.0 | 93747 | 5823 | None |
| 42 | `DOC-681bc6115b882191` | True | 0 | 600.3 | 120554 | 6170 | None |
| 43 | `DOC-ff3ceb691481f1bd` | True | 0 | 613.2 | 91432 | 6404 | None |
| 44 | `DOC-f9870e3b8fd141b0` | True | 0 | 941.0 | 134889 | 8014 | None |
| 45 | `DOC-f449b47c7269f288` | True | 0.062500 | 682.5 | 95394 | 7002 | None |
| 46 | `DOC-23f224263f6974c5` | True | 0 | 625.2 | 83736 | 6817 | None |
| 47 | `DOC-f09307ad314d386f` | True | 0 | 727.0 | 103329 | 8452 | None |
| 48 | `DOC-5d30efc302f3c431` | True | 0.062500 | 785.5 | 130943 | 9253 | None |
| 49 | `DOC-0070a4e34dddbfd5` | True | 0 | 1049.7 | 85209 | 6490 | None |
| 50 | `DOC-03712a2b0a99a314` | True | 0 | 1346.2 | 119367 | 12533 | None |
