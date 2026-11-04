# Run report — `sand42-50-merger-specialist-awq-1l4-c16`

Dated cell stem: `RUN-50-MERGER-AWQ-1L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-merger-specialist-awq-1l4-c16` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `29ddbe9d7946d23eace974e2a75e18e764b809b64a1b5ffa049b85cb5e3c7b0c` |
| dataset fingerprint | `aa4e596805e7` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.027579** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 3607.518 |
| gpu_seconds | 3607.837 |
| estimated GPU cost | 0.801742 |
| **GPU $/doc** | **0.016035** |
| latency p50 / max (s) | 948.688197 / 2323.519688 |
| prompt / completion tokens | 4867606 / 291690 |
| concurrency speedup (Σlat/wall) | 14.81 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-dc7f18df501aec90` | True | 0 | 625.3 | 83008 | 3181 | None |
| 2 | `DOC-4f45bef14dcd1dbf` | True | 0.062500 | 734.3 | 70774 | 3876 | None |
| 3 | `DOC-26933c93d649fa3f` | True | 0.062500 | 766.5 | 96354 | 4055 | None |
| 4 | `DOC-eb2b56fe30dc35f4` | True | 0.058824 | 775.3 | 85298 | 4089 | None |
| 5 | `DOC-c96b9c7e12f91576` | True | 0 | 840.9 | 92490 | 4582 | None |
| 6 | `DOC-b03c0d2bbbb9659e` | True | 0.055556 | 898.8 | 113393 | 4893 | None |
| 7 | `DOC-5f5d40f6b2c338ac` | True | 0 | 939.0 | 109887 | 5186 | None |
| 8 | `DOC-d4b1a7a2b981fbf4` | True | 0.058824 | 950.3 | 81817 | 5265 | None |
| 9 | `DOC-71bc59dd305ee8ed` | True | 0.076923 | 968.1 | 109675 | 5281 | None |
| 10 | `DOC-45f801408be08af6` | True | 0 | 1072.2 | 109920 | 6020 | None |
| 11 | `DOC-30eda1e78a5f6fb5` | True | 0 | 1182.7 | 107499 | 6709 | None |
| 12 | `DOC-52f9a5be69429299` | True | 0 | 1237.6 | 103918 | 7035 | None |
| 13 | `DOC-882fabf7aba36941` | True | 0 | 1258.2 | 92325 | 7192 | None |
| 14 | `DOC-511062d64bc9afc6` | True | 0 | 745.5 | 97584 | 4689 | None |
| 15 | `DOC-e8538f75b0f993e6` | True | 0 | 1575.2 | 113280 | 9359 | None |
| 16 | `DOC-f90cc5fb2ceac154` | True | 0 | 821.8 | 93747 | 5365 | None |
| 17 | `DOC-1e016055aa435e71` | True | 0 | 793.7 | 109137 | 5044 | None |
| 18 | `DOC-bec74557186e9409` | True | 0 | 747.7 | 78918 | 4797 | None |
| 19 | `DOC-ab5578f1f9f04244` | True | 0 | 964.2 | 132059 | 6174 | None |
| 20 | `DOC-63beb09b179ea4ee` | True | 0.058824 | 804.3 | 83572 | 5196 | None |
| 21 | `DOC-0534799ed39ca0db` | True | 0.055556 | 856.0 | 92828 | 5611 | None |
| 22 | `DOC-5f8ef95caa2fd349` | True | 0.058824 | 1066.5 | 104105 | 6919 | None |
| 23 | `DOC-9420b777a4b0784c` | True | 0 | 2220.5 | 98627 | 5499 | None |
| 24 | `DOC-0a733ab86f2390ae` | True | 0.066667 | 2323.5 | 81545 | 6494 | None |
| 25 | `DOC-2b9f668ab6cb8901` | True | 0.052632 | 1316.9 | 90831 | 6649 | None |
| 26 | `DOC-37bc3c44ae2c4ef6` | True | 0 | 1459.0 | 90012 | 7127 | None |
| 27 | `DOC-fe9a8b51344d67d9` | True | 0 | 1583.6 | 130099 | 7714 | None |
| 28 | `DOC-297745a521cd1e8c` | True | 0 | 1325.4 | 103150 | 6797 | None |
| 29 | `DOC-386ac6d669b7731c` | True | 0.076923 | 1274.7 | 93831 | 6516 | None |
| 30 | `DOC-26fa94f698c37fc5` | True | 0 | 1043.9 | 79931 | 4331 | None |
| 31 | `DOC-72b0b8c8385edd48` | True | 0.055556 | 1135.6 | 84431 | 5272 | None |
| 32 | `DOC-ac48214468deb8dd` | True | 0 | 926.5 | 72887 | 3883 | None |
| 33 | `DOC-fcaddb5bdc94ce63` | True | 0.058824 | 1043.9 | 82656 | 4955 | None |
| 34 | `DOC-c6b5f7ea5f718c28` | True | 0 | 1562.0 | 82765 | 6661 | None |
| 35 | `DOC-9d34581755c603a3` | True | 0 | 669.4 | 94942 | 4264 | None |
| 36 | `DOC-03712a2b0a99a314` | True | 0.058824 | 1381.5 | 119367 | 6932 | None |
| 37 | `DOC-1cd38a83b224335d` | True | 0 | 631.6 | 78294 | 4103 | None |
| 38 | `DOC-b3d0149fd994357a` | True | 0 | 667.9 | 78500 | 4416 | None |
| 39 | `DOC-f9870e3b8fd141b0` | True | 0 | 1501.7 | 134889 | 6921 | None |
| 40 | `DOC-ab735131c00271bc` | True | 0.055556 | 725.4 | 81228 | 5141 | None |
| 41 | `DOC-f449b47c7269f288` | True | 0.062500 | 600.0 | 95394 | 4266 | None |
| 42 | `DOC-169bbcdc5d9e609c` | True | 0 | 855.5 | 134911 | 6240 | None |
| 43 | `DOC-ff3ceb691481f1bd` | True | 0 | 619.2 | 91432 | 4853 | None |
| 44 | `DOC-0070a4e34dddbfd5` | True | 0.176471 | 1565.1 | 85209 | 8957 | None |
| 45 | `DOC-f09307ad314d386f` | True | 0 | 726.7 | 103329 | 5927 | None |
| 46 | `DOC-23f224263f6974c5` | True | 0 | 658.6 | 83736 | 6172 | None |
| 47 | `DOC-7e2818ceb0167d5a` | True | 0.166667 | 1917.9 | 78432 | 6476 | None |
| 48 | `DOC-681bc6115b882191` | True | 0 | 756.1 | 120554 | 7662 | None |
| 49 | `DOC-5d30efc302f3c431` | True | 0 | 947.0 | 130943 | 10084 | None |
| 50 | `DOC-e6c8852b877c4598` | True | 0 | 1372.8 | 104093 | 6860 | None |
