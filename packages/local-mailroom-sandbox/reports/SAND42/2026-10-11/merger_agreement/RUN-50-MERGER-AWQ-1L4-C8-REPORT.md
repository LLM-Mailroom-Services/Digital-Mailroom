# Run report — `sand42-50-merger-specialist-awq-1l4-c8`

Dated cell stem: `RUN-50-MERGER-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-merger-specialist-awq-1l4-c8` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `d573b8a97de755baf612379dd1363d3061d9e6f91acbb0810cab6e90df71b932` |
| dataset fingerprint | `aa4e596805e7` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.020734** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 4207.675 |
| gpu_seconds | 637.381 |
| estimated GPU cost | 0.141640 |
| **GPU $/doc** | **0.0028328** |
| latency p50 / max (s) | 574.873879 / 1627.900910 |
| prompt / completion tokens | 4867606 / 317040 |
| concurrency speedup (Σlat/wall) | 8.28 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-dc7f18df501aec90` | True | 0.133333 | 434.3 | 83008 | 4647 | None |
| 2 | `DOC-c96b9c7e12f91576` | True | 0 | 445.2 | 92490 | 4713 | None |
| 3 | `DOC-d4b1a7a2b981fbf4` | True | 0 | 504.5 | 81817 | 5049 | None |
| 4 | `DOC-26933c93d649fa3f` | True | 0 | 520.7 | 96354 | 5229 | None |
| 5 | `DOC-0a733ab86f2390ae` | True | 0 | 525.2 | 81545 | 4845 | None |
| 6 | `DOC-45f801408be08af6` | True | 0 | 630.2 | 109920 | 6269 | None |
| 7 | `DOC-4f45bef14dcd1dbf` | True | 0 | 316.3 | 70774 | 3535 | None |
| 8 | `DOC-eb2b56fe30dc35f4` | True | 0 | 984.4 | 85298 | 5607 | None |
| 9 | `DOC-52f9a5be69429299` | True | 0 | 556.2 | 103918 | 6522 | None |
| 10 | `DOC-9420b777a4b0784c` | True | 0 | 615.0 | 98627 | 7222 | None |
| 11 | `DOC-b03c0d2bbbb9659e` | True | 0.055556 | 549.0 | 113393 | 6341 | None |
| 12 | `DOC-5f5d40f6b2c338ac` | True | 0 | 1136.1 | 109887 | 6310 | None |
| 13 | `DOC-882fabf7aba36941` | True | 0 | 365.3 | 92325 | 4183 | None |
| 14 | `DOC-e8538f75b0f993e6` | True | 0 | 753.3 | 113280 | 8172 | None |
| 15 | `DOC-511062d64bc9afc6` | True | 0 | 532.4 | 97584 | 5597 | None |
| 16 | `DOC-30eda1e78a5f6fb5` | True | 0.055556 | 615.4 | 107499 | 6532 | None |
| 17 | `DOC-1e016055aa435e71` | True | 0 | 428.5 | 109137 | 4207 | None |
| 18 | `DOC-f90cc5fb2ceac154` | True | 0 | 493.3 | 93747 | 5674 | None |
| 19 | `DOC-5f8ef95caa2fd349` | True | 0 | 603.8 | 104105 | 6560 | None |
| 20 | `DOC-71bc59dd305ee8ed` | True | 0.076923 | 1212.5 | 109675 | 8024 | None |
| 21 | `DOC-63beb09b179ea4ee` | True | 0.058824 | 577.1 | 83572 | 5566 | None |
| 22 | `DOC-37bc3c44ae2c4ef6` | True | 0 | 496.6 | 90012 | 5281 | None |
| 23 | `DOC-0534799ed39ca0db` | True | 0.055556 | 540.8 | 92828 | 5967 | None |
| 24 | `DOC-bec74557186e9409` | True | 0 | 804.5 | 78918 | 9710 | None |
| 25 | `DOC-ab5578f1f9f04244` | True | 0 | 1227.2 | 132059 | 9515 | None |
| 26 | `DOC-297745a521cd1e8c` | True | 0 | 709.8 | 103150 | 7546 | None |
| 27 | `DOC-2b9f668ab6cb8901` | True | 0.052632 | 803.3 | 90831 | 4250 | None |
| 28 | `DOC-386ac6d669b7731c` | True | 0.076923 | 415.3 | 93831 | 5142 | None |
| 29 | `DOC-fe9a8b51344d67d9` | True | 0 | 987.0 | 130099 | 12554 | None |
| 30 | `DOC-7e2818ceb0167d5a` | True | 0.055556 | 512.3 | 78432 | 6153 | None |
| 31 | `DOC-26fa94f698c37fc5` | True | 0.058824 | 352.9 | 79931 | 4228 | None |
| 32 | `DOC-72b0b8c8385edd48` | True | 0 | 788.2 | 84431 | 8606 | None |
| 33 | `DOC-fcaddb5bdc94ce63` | True | 0 | 520.1 | 82656 | 5381 | None |
| 34 | `DOC-ac48214468deb8dd` | True | 0.058824 | 394.4 | 72887 | 4632 | None |
| 35 | `DOC-c6b5f7ea5f718c28` | True | 0.058824 | 1079.7 | 82765 | 7967 | None |
| 36 | `DOC-f9870e3b8fd141b0` | True | 0 | 720.7 | 134889 | 7810 | None |
| 37 | `DOC-b3d0149fd994357a` | True | 0 | 343.7 | 78500 | 5261 | None |
| 38 | `DOC-5d30efc302f3c431` | True | 0.062500 | 288.7 | 130943 | 9312 | None |
| 39 | `DOC-9d34581755c603a3` | True | 0 | 902.5 | 94942 | 3760 | None |
| 40 | `DOC-03712a2b0a99a314` | True | 0.058824 | 1627.9 | 119367 | 7250 | None |
| 41 | `DOC-0070a4e34dddbfd5` | True | 0 | 1482.7 | 85209 | 5797 | None |
| 42 | `DOC-1cd38a83b224335d` | True | 0 | 906.0 | 78294 | 3181 | None |
| 43 | `DOC-e6c8852b877c4598` | True | 0 | 1307.5 | 104093 | 5925 | None |
| 44 | `DOC-f449b47c7269f288` | True | 0.062500 | 407.3 | 95394 | 5332 | None |
| 45 | `DOC-ab735131c00271bc` | True | 0.055556 | 1027.4 | 81228 | 4908 | None |
| 46 | `DOC-169bbcdc5d9e609c` | True | 0 | 1324.9 | 134911 | 9408 | None |
| 47 | `DOC-ff3ceb691481f1bd` | True | 0 | 487.1 | 91432 | 7018 | None |
| 48 | `DOC-23f224263f6974c5` | True | 0 | 326.9 | 83736 | 5723 | None |
| 49 | `DOC-f09307ad314d386f` | True | 0 | 678.5 | 103329 | 11556 | None |
| 50 | `DOC-681bc6115b882191` | True | 0 | 572.6 | 120554 | 7063 | None |
