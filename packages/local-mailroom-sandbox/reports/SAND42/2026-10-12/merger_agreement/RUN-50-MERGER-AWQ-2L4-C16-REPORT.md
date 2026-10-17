# Run report — `sand42-50-merger-specialist-awq-2l4-c16`

Dated cell stem: `RUN-50-MERGER-AWQ-2L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-merger-specialist-awq-2l4-c16` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `6dc161524d1ffab88e74391de05addb94fc31f7598ed3050de488275f98b65d7` |
| dataset fingerprint | `aa4e596805e7` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.025420** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 2097.456 |
| gpu_seconds | 2097.750 |
| estimated GPU cost | 0.932333 |
| **GPU $/doc** | **0.018647** |
| latency p50 / max (s) | 579.439597 / 1378.287742 |
| prompt / completion tokens | 4867606 / 299311 |
| concurrency speedup (Σlat/wall) | 14.25 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-4f45bef14dcd1dbf` | True | 0.062500 | 363.3 | 70774 | 3044 | None |
| 2 | `DOC-0a733ab86f2390ae` | True | 0.066667 | 472.6 | 81545 | 4512 | None |
| 3 | `DOC-dc7f18df501aec90` | True | 0.066667 | 483.3 | 83008 | 4460 | None |
| 4 | `DOC-eb2b56fe30dc35f4` | True | 0.058824 | 501.8 | 85298 | 4393 | None |
| 5 | `DOC-9420b777a4b0784c` | True | 0 | 558.2 | 98627 | 5401 | None |
| 6 | `DOC-5f5d40f6b2c338ac` | True | 0 | 565.6 | 109887 | 6036 | None |
| 7 | `DOC-c96b9c7e12f91576` | True | 0 | 591.6 | 92490 | 5489 | None |
| 8 | `DOC-30eda1e78a5f6fb5` | True | 0 | 595.1 | 107499 | 5858 | None |
| 9 | `DOC-b03c0d2bbbb9659e` | True | 0 | 596.2 | 113393 | 5851 | None |
| 10 | `DOC-45f801408be08af6` | True | 0.133333 | 647.0 | 109920 | 5874 | None |
| 11 | `DOC-71bc59dd305ee8ed` | True | 0.076923 | 730.2 | 109675 | 8931 | None |
| 12 | `DOC-e8538f75b0f993e6` | True | 0 | 732.8 | 113280 | 7220 | None |
| 13 | `DOC-882fabf7aba36941` | True | 0 | 751.8 | 92325 | 7510 | None |
| 14 | `DOC-511062d64bc9afc6` | True | 0 | 442.3 | 97584 | 5312 | None |
| 15 | `DOC-d4b1a7a2b981fbf4` | True | 0.058824 | 895.6 | 81817 | 8182 | None |
| 16 | `DOC-f90cc5fb2ceac154` | True | 0.050000 | 482.6 | 93747 | 5434 | None |
| 17 | `DOC-5f8ef95caa2fd349` | True | 0.058824 | 501.3 | 104105 | 6905 | None |
| 18 | `DOC-52f9a5be69429299` | True | 0 | 1047.8 | 103918 | 6065 | None |
| 19 | `DOC-1e016055aa435e71` | True | 0 | 500.4 | 109137 | 7159 | None |
| 20 | `DOC-26933c93d649fa3f` | True | 0 | 1087.1 | 96354 | 5216 | None |
| 21 | `DOC-0534799ed39ca0db` | True | 0.055556 | 491.4 | 92828 | 6047 | None |
| 22 | `DOC-63beb09b179ea4ee` | True | 0.058824 | 523.6 | 83572 | 5176 | None |
| 23 | `DOC-bec74557186e9409` | True | 0 | 550.4 | 78918 | 5798 | None |
| 24 | `DOC-c6b5f7ea5f718c28` | True | 0.058824 | 367.2 | 82765 | 3793 | None |
| 25 | `DOC-72b0b8c8385edd48` | True | 0 | 389.7 | 84431 | 4977 | None |
| 26 | `DOC-2b9f668ab6cb8901` | True | 0.052632 | 567.3 | 90831 | 5263 | None |
| 27 | `DOC-fe9a8b51344d67d9` | True | 0 | 710.3 | 130099 | 7211 | None |
| 28 | `DOC-37bc3c44ae2c4ef6` | True | 0 | 674.1 | 90012 | 6633 | None |
| 29 | `DOC-297745a521cd1e8c` | True | 0 | 598.8 | 103150 | 7034 | None |
| 30 | `DOC-386ac6d669b7731c` | True | 0 | 647.3 | 93831 | 5593 | None |
| 31 | `DOC-9d34581755c603a3` | True | 0 | 440.6 | 94942 | 4304 | None |
| 32 | `DOC-26fa94f698c37fc5` | True | 0.058824 | 607.8 | 79931 | 5939 | None |
| 33 | `DOC-7e2818ceb0167d5a` | True | 0 | 675.5 | 78432 | 7566 | None |
| 34 | `DOC-fcaddb5bdc94ce63` | True | 0.058824 | 617.0 | 82656 | 6019 | None |
| 35 | `DOC-1cd38a83b224335d` | True | 0 | 409.4 | 78294 | 3592 | None |
| 36 | `DOC-ab735131c00271bc` | True | 0.055556 | 397.5 | 81228 | 3898 | None |
| 37 | `DOC-ac48214468deb8dd` | True | 0.058824 | 613.3 | 72887 | 6544 | None |
| 38 | `DOC-0070a4e34dddbfd5` | True | 0 | 650.8 | 85209 | 6368 | None |
| 39 | `DOC-e6c8852b877c4598` | True | 0.055556 | 625.1 | 104093 | 6755 | None |
| 40 | `DOC-f449b47c7269f288` | True | 0.062500 | 335.8 | 95394 | 4346 | None |
| 41 | `DOC-b3d0149fd994357a` | True | 0 | 510.0 | 78500 | 5472 | None |
| 42 | `DOC-f9870e3b8fd141b0` | True | 0 | 792.0 | 134889 | 8626 | None |
| 43 | `DOC-ab5578f1f9f04244` | True | 0 | 1378.3 | 132059 | 8245 | None |
| 44 | `DOC-169bbcdc5d9e609c` | True | 0 | 667.1 | 134911 | 9088 | None |
| 45 | `DOC-f09307ad314d386f` | True | 0 | 399.3 | 103329 | 5958 | None |
| 46 | `DOC-ff3ceb691481f1bd` | True | 0 | 318.2 | 91432 | 5343 | None |
| 47 | `DOC-23f224263f6974c5` | True | 0 | 279.6 | 83736 | 5269 | None |
| 48 | `DOC-681bc6115b882191` | True | 0 | 330.1 | 120554 | 5735 | None |
| 49 | `DOC-03712a2b0a99a314` | True | 0 | 1013.6 | 119367 | 6279 | None |
| 50 | `DOC-5d30efc302f3c431` | True | 0.062500 | 750.8 | 130943 | 7588 | None |
