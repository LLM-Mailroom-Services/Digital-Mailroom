# Run report — `sand42-50-merger-specialist-awq-2l4-c8`

Dated cell stem: `RUN-50-MERGER-AWQ-2L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-merger-specialist-awq-2l4-c8` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `b1dc72159d3e4d3c593caf3a5c475284848e615d4b6fb599238734980951611a` |
| dataset fingerprint | `aa4e596805e7` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.028499** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 2887.103 |
| gpu_seconds | 2887.473 |
| estimated GPU cost | 1.283321 |
| **GPU $/doc** | **0.025666** |
| latency p50 / max (s) | 359.111248 / 970.461714 |
| prompt / completion tokens | 4867606 / 322630 |
| concurrency speedup (Σlat/wall) | 7.43 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-d4b1a7a2b981fbf4` | True | 0 | 295.3 | 81817 | 4545 | None |
| 2 | `DOC-26933c93d649fa3f` | True | 0.062500 | 322.4 | 96354 | 4739 | None |
| 3 | `DOC-c96b9c7e12f91576` | True | 0 | 333.6 | 92490 | 6619 | None |
| 4 | `DOC-5f5d40f6b2c338ac` | True | 0 | 338.8 | 109887 | 4772 | None |
| 5 | `DOC-0a733ab86f2390ae` | True | 0 | 358.1 | 81545 | 6125 | None |
| 6 | `DOC-45f801408be08af6` | True | 0 | 427.4 | 109920 | 6249 | None |
| 7 | `DOC-4f45bef14dcd1dbf` | True | 0.062500 | 246.0 | 70774 | 3906 | None |
| 8 | `DOC-eb2b56fe30dc35f4` | True | 0.117647 | 628.0 | 85298 | 4482 | None |
| 9 | `DOC-9420b777a4b0784c` | True | 0 | 360.6 | 98627 | 6158 | None |
| 10 | `DOC-e8538f75b0f993e6` | True | 0 | 329.0 | 113280 | 6573 | None |
| 11 | `DOC-b03c0d2bbbb9659e` | True | 0.055556 | 501.6 | 113393 | 8326 | None |
| 12 | `DOC-882fabf7aba36941` | True | 0 | 282.2 | 92325 | 5553 | None |
| 13 | `DOC-511062d64bc9afc6` | True | 0 | 291.9 | 97584 | 4639 | None |
| 14 | `DOC-dc7f18df501aec90` | True | 0.066667 | 970.5 | 83008 | 3969 | None |
| 15 | `DOC-52f9a5be69429299` | True | 0 | 657.7 | 103918 | 10606 | None |
| 16 | `DOC-30eda1e78a5f6fb5` | True | 0 | 430.5 | 107499 | 8083 | None |
| 17 | `DOC-71bc59dd305ee8ed` | True | 0.230769 | 767.1 | 109675 | 6673 | None |
| 18 | `DOC-f90cc5fb2ceac154` | True | 0 | 308.3 | 93747 | 5227 | None |
| 19 | `DOC-ab5578f1f9f04244` | True | 0 | 439.1 | 132059 | 7877 | None |
| 20 | `DOC-1e016055aa435e71` | True | 0 | 334.4 | 109137 | 5155 | None |
| 21 | `DOC-63beb09b179ea4ee` | True | 0.058824 | 302.4 | 83572 | 6319 | None |
| 22 | `DOC-bec74557186e9409` | True | 0 | 366.0 | 78918 | 6147 | None |
| 23 | `DOC-fe9a8b51344d67d9` | True | 0 | 340.1 | 130099 | 6329 | None |
| 24 | `DOC-5f8ef95caa2fd349` | True | 0 | 576.5 | 104105 | 8739 | None |
| 25 | `DOC-2b9f668ab6cb8901` | True | 0.052632 | 323.7 | 90831 | 5243 | None |
| 26 | `DOC-0534799ed39ca0db` | True | 0.055556 | 401.3 | 92828 | 6511 | None |
| 27 | `DOC-7e2818ceb0167d5a` | True | 0.055556 | 204.6 | 78432 | 4327 | None |
| 28 | `DOC-37bc3c44ae2c4ef6` | True | 0 | 478.4 | 90012 | 7749 | None |
| 29 | `DOC-72b0b8c8385edd48` | True | 0.055556 | 275.9 | 84431 | 5479 | None |
| 30 | `DOC-26fa94f698c37fc5` | True | 0.058824 | 228.9 | 79931 | 4257 | None |
| 31 | `DOC-297745a521cd1e8c` | True | 0 | 547.3 | 103150 | 10273 | None |
| 32 | `DOC-c6b5f7ea5f718c28` | True | 0.058824 | 552.9 | 82765 | 4430 | None |
| 33 | `DOC-03712a2b0a99a314` | True | 0.058824 | 437.0 | 119367 | 7899 | None |
| 34 | `DOC-0070a4e34dddbfd5` | True | 0.058824 | 311.7 | 85209 | 5373 | None |
| 35 | `DOC-ac48214468deb8dd` | True | 0.058824 | 304.1 | 72887 | 5627 | None |
| 36 | `DOC-9d34581755c603a3` | True | 0 | 251.5 | 94942 | 4483 | None |
| 37 | `DOC-386ac6d669b7731c` | True | 0.076923 | 783.9 | 93831 | 8246 | None |
| 38 | `DOC-e6c8852b877c4598` | True | 0 | 414.3 | 104093 | 7128 | None |
| 39 | `DOC-1cd38a83b224335d` | True | 0.058824 | 213.3 | 78294 | 3584 | None |
| 40 | `DOC-f9870e3b8fd141b0` | True | 0 | 687.6 | 134889 | 7509 | None |
| 41 | `DOC-169bbcdc5d9e609c` | True | 0 | 356.9 | 134911 | 6060 | None |
| 42 | `DOC-fcaddb5bdc94ce63` | True | 0 | 702.4 | 82656 | 6424 | None |
| 43 | `DOC-f449b47c7269f288` | True | 0.062500 | 299.8 | 95394 | 5384 | None |
| 44 | `DOC-f09307ad314d386f` | True | 0 | 359.9 | 103329 | 6709 | None |
| 45 | `DOC-5d30efc302f3c431` | True | 0 | 521.5 | 130943 | 9344 | None |
| 46 | `DOC-ff3ceb691481f1bd` | True | 0 | 333.7 | 91432 | 6132 | None |
| 47 | `DOC-681bc6115b882191` | True | 0 | 358.3 | 120554 | 6773 | None |
| 48 | `DOC-23f224263f6974c5` | True | 0 | 360.5 | 83736 | 8100 | None |
| 49 | `DOC-b3d0149fd994357a` | True | 0.058824 | 747.2 | 78500 | 9715 | None |
| 50 | `DOC-ab735131c00271bc` | True | 0 | 786.1 | 81228 | 12061 | None |
