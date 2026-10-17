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
| **overall_extraction_score** | **0.027299** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 4483.096 |
| gpu_seconds | 4483.401 |
| estimated GPU cost | 0.996311 |
| **GPU $/doc** | **0.019926** |
| latency p50 / max (s) | 547.443795 / 1477.394755 |
| prompt / completion tokens | 4867606 / 318047 |
| concurrency speedup (Σlat/wall) | 7.19 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-5f5d40f6b2c338ac` | True | 0 | 400.5 | 109887 | 3890 | None |
| 2 | `DOC-d4b1a7a2b981fbf4` | True | 0 | 405.8 | 81817 | 4011 | None |
| 3 | `DOC-26933c93d649fa3f` | True | 0.062500 | 472.0 | 96354 | 4723 | None |
| 4 | `DOC-45f801408be08af6` | True | 0 | 495.6 | 109920 | 5035 | None |
| 5 | `DOC-c96b9c7e12f91576` | True | 0 | 533.4 | 92490 | 5596 | None |
| 6 | `DOC-eb2b56fe30dc35f4` | True | 0 | 540.3 | 85298 | 5695 | None |
| 7 | `DOC-dc7f18df501aec90` | True | 0.133333 | 549.0 | 83008 | 5788 | None |
| 8 | `DOC-0a733ab86f2390ae` | True | 0 | 576.1 | 81545 | 6082 | None |
| 9 | `DOC-4f45bef14dcd1dbf` | True | 0.062500 | 398.8 | 70774 | 4526 | None |
| 10 | `DOC-9420b777a4b0784c` | True | 0 | 566.3 | 98627 | 6586 | None |
| 11 | `DOC-b03c0d2bbbb9659e` | True | 0 | 562.8 | 113393 | 6560 | None |
| 12 | `DOC-71bc59dd305ee8ed` | True | 0.076923 | 539.1 | 109675 | 6153 | None |
| 13 | `DOC-e8538f75b0f993e6` | True | 0 | 545.9 | 113280 | 6287 | None |
| 14 | `DOC-882fabf7aba36941` | True | 0 | 556.6 | 92325 | 6383 | None |
| 15 | `DOC-30eda1e78a5f6fb5` | True | 0 | 564.5 | 107499 | 6456 | None |
| 16 | `DOC-52f9a5be69429299` | True | 0 | 783.5 | 103918 | 9106 | None |
| 17 | `DOC-ab5578f1f9f04244` | True | 0.200000 | 465.5 | 132059 | 5157 | None |
| 18 | `DOC-f90cc5fb2ceac154` | True | 0 | 439.9 | 93747 | 4994 | None |
| 19 | `DOC-bec74557186e9409` | True | 0 | 464.9 | 78918 | 5436 | None |
| 20 | `DOC-1e016055aa435e71` | True | 0 | 581.9 | 109137 | 6679 | None |
| 21 | `DOC-5f8ef95caa2fd349` | True | 0 | 718.2 | 104105 | 8146 | None |
| 22 | `DOC-fe9a8b51344d67d9` | True | 0 | 626.6 | 130099 | 6935 | None |
| 23 | `DOC-511062d64bc9afc6` | True | 0 | 969.9 | 97584 | 5378 | None |
| 24 | `DOC-0534799ed39ca0db` | True | 0.055556 | 420.2 | 92828 | 4697 | None |
| 25 | `DOC-63beb09b179ea4ee` | True | 0 | 807.4 | 83572 | 8778 | None |
| 26 | `DOC-37bc3c44ae2c4ef6` | True | 0 | 570.9 | 90012 | 6405 | None |
| 27 | `DOC-c6b5f7ea5f718c28` | True | 0.058824 | 407.5 | 82765 | 4944 | None |
| 28 | `DOC-72b0b8c8385edd48` | True | 0.055556 | 410.9 | 84431 | 4972 | None |
| 29 | `DOC-297745a521cd1e8c` | True | 0 | 594.0 | 103150 | 6973 | None |
| 30 | `DOC-2b9f668ab6cb8901` | True | 0.052632 | 723.1 | 90831 | 8406 | None |
| 31 | `DOC-7e2818ceb0167d5a` | True | 0.055556 | 533.2 | 78432 | 6421 | None |
| 32 | `DOC-26fa94f698c37fc5` | True | 0.058824 | 380.6 | 79931 | 4539 | None |
| 33 | `DOC-386ac6d669b7731c` | True | 0.076923 | 1306.2 | 93831 | 8926 | None |
| 34 | `DOC-fcaddb5bdc94ce63` | True | 0.058824 | 961.1 | 82656 | 5028 | None |
| 35 | `DOC-0070a4e34dddbfd5` | True | 0 | 1043.9 | 85209 | 6587 | None |
| 36 | `DOC-03712a2b0a99a314` | True | 0.058824 | 1421.4 | 119367 | 6301 | None |
| 37 | `DOC-ac48214468deb8dd` | True | 0.058824 | 1103.0 | 72887 | 6372 | None |
| 38 | `DOC-9d34581755c603a3` | True | 0 | 972.0 | 94942 | 4427 | None |
| 39 | `DOC-b3d0149fd994357a` | True | 0 | 332.7 | 78500 | 3800 | None |
| 40 | `DOC-f9870e3b8fd141b0` | True | 0 | 1370.2 | 134889 | 7124 | None |
| 41 | `DOC-ab735131c00271bc` | True | 0.055556 | 386.4 | 81228 | 4726 | None |
| 42 | `DOC-1cd38a83b224335d` | True | 0.058824 | 457.0 | 78294 | 5507 | None |
| 43 | `DOC-f449b47c7269f288` | True | 0.062500 | 376.3 | 95394 | 4436 | None |
| 44 | `DOC-169bbcdc5d9e609c` | True | 0 | 726.9 | 134911 | 8536 | None |
| 45 | `DOC-e6c8852b877c4598` | True | 0 | 1477.4 | 104093 | 10821 | None |
| 46 | `DOC-ff3ceb691481f1bd` | True | 0 | 410.0 | 91432 | 5729 | None |
| 47 | `DOC-f09307ad314d386f` | True | 0 | 461.5 | 103329 | 6672 | None |
| 48 | `DOC-23f224263f6974c5` | True | 0 | 297.1 | 83736 | 5187 | None |
| 49 | `DOC-681bc6115b882191` | True | 0 | 444.2 | 120554 | 9310 | None |
| 50 | `DOC-5d30efc302f3c431` | True | 0.062500 | 1071.9 | 130943 | 16821 | None |
