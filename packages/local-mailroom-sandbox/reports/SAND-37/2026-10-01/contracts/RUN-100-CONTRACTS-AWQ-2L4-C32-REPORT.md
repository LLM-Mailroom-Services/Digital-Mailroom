# Run report — `sand40-100-contracts-specialist-awq-2l4`

Dated cell stem: `RUN-100-CONTRACTS-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand40-100-contracts-specialist-awq-2l4` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **100** |
| profile | `modal-vllm` |
| spec_hash | `1ce35cb08739b9a3ffdb8c9cba8407b6cfcb76c681c83bd642c6002823c1558a` |
| dataset fingerprint | `6d82d7d13fa4` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **99 / 1 / 100** |
| **overall_extraction_score** | **0.506606** |
| schema_valid_rate | 1.000000 |
| error_count | 1 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 460.624 |
| gpu_seconds | 460.924 |
| estimated GPU cost | 0.204855 |
| **GPU $/doc** | **0.00206924** |
| latency p50 / max (s) | 96.142515 / 203.954011 |
| prompt / completion tokens | 707289 / 146665 |
| concurrency speedup (Σlat/wall) | 21.70 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-98ff556893f1a98f` | True | 0.857100 | 40.6 | 3200 | 383 | None |
| 2 | `DOC-56d6a0f676f98474` | True | — | 50.4 | 6868 | 574 | None |
| 3 | `DOC-10357f1d86b3081e` | True | — | 66.2 | 3687 | 838 | None |
| 4 | `DOC-25f822c661011bfe` | True | 0.428600 | 71.3 | 7821 | 874 | None |
| 5 | `DOC-ea746c407db93af2` | True | — | 78.8 | 4804 | 997 | None |
| 6 | `DOC-2e3e2bb13d6c83ca` | True | — | 81.4 | 13464 | 996 | None |
| 7 | `DOC-1afbdbce947fcbb2` | True | — | 83.1 | 8609 | 1076 | None |
| 8 | `DOC-5892b6dc609c8d0f` | True | — | 85.0 | 7606 | 1034 | None |
| 9 | `DOC-adad5ef793c0e409` | True | 0.400000 | 91.3 | 8247 | 1149 | None |
| 10 | `DOC-54ad252b1e5e8d58` | True | 0.692300 | 95.1 | 8244 | 1274 | None |
| 11 | `DOC-6712aa595cfe3e2c` | True | 0.470600 | 99.1 | 7666 | 1273 | None |
| 12 | `DOC-e3f6015e5645a811` | True | 0.600000 | 100.2 | 4436 | 1334 | None |
| 13 | `DOC-a05bef17a3ab844f` | True | — | 102.4 | 7959 | 1327 | None |
| 14 | `DOC-78a0da18d0ba811a` | True | — | 104.7 | 7869 | 1348 | None |
| 15 | `DOC-c7f557969d953fae` | True | — | 106.4 | 8119 | 1358 | None |
| 16 | `DOC-440a54573c24b918` | True | 0.444400 | 59.5 | 3493 | 939 | None |
| 17 | `DOC-e3afd3d853d33152` | True | 0.727300 | 110.3 | 8334 | 1428 | None |
| 18 | `DOC-9696c5996f24d85d` | True | — | 113.3 | 4377 | 1472 | None |
| 19 | `DOC-7523d051bc56169f` | True | — | 114.4 | 8145 | 1464 | None |
| 20 | `DOC-2f88403fb6616a82` | True | 0.615400 | 118.3 | 9168 | 701 | None |
| 21 | `DOC-c2ac5762c7f227fa` | True | — | 120.2 | 8143 | 1558 | None |
| 22 | `DOC-c30c293d38a2cd8b` | True | 0.636400 | 81.0 | 9794 | 1249 | None |
| 23 | `DOC-ab9afe870c6269b2` | True | — | 125.5 | 7429 | 1594 | None |
| 24 | `DOC-3893bdb61733ec56` | True | — | 126.0 | 4378 | 1238 | None |
| 25 | `DOC-ba6d7a0ea5100bbb` | True | 0.600000 | 130.1 | 7887 | 1686 | None |
| 26 | `DOC-2ca7b08d2d439f1e` | True | — | 138.9 | 7616 | 1824 | None |
| 27 | `DOC-eb9157e3710cc477` | True | 0.400000 | 139.3 | 7668 | 1830 | None |
| 28 | `DOC-9adf4d68fa5bec24` | True | 0.640000 | 141.8 | 8104 | 1848 | None |
| 29 | `DOC-9e063c6e3baf1233` | True | 0.516100 | 145.8 | 7486 | 1909 | None |
| 30 | `DOC-8978696bf49c6085` | True | 0.888900 | 52.0 | 3678 | 695 | None |
| 31 | `DOC-9b569749ea3d6f42` | True | — | 153.2 | 11640 | 1978 | None |
| 32 | `DOC-dbfa4f9eb3f16433` | True | 0.642900 | 159.3 | 6748 | 2103 | None |
| 33 | `DOC-ee4369c8980926dc` | True | 0.592600 | 88.1 | 7993 | 1256 | None |
| 34 | `DOC-e235bc9735f96335` | True | 0.823500 | 159.5 | 7449 | 2161 | None |
| 35 | `DOC-3b768dc1c4ebdc47` | True | 0.533300 | 86.1 | 4521 | 1217 | None |
| 36 | `DOC-ade03c57c5f78e21` | True | 0.533300 | 99.2 | 4093 | 1239 | None |
| 37 | `DOC-83320eec5eec6235` | True | 0.666700 | 55.1 | 7706 | 778 | None |
| 38 | `DOC-680704693a37b610` | True | 0.444400 | 78.8 | 7946 | 1110 | None |
| 39 | `DOC-962cc639f3ebee80` | True | — | 176.5 | 7359 | 1491 | None |
| 40 | `DOC-eba7f7faca68e78c` | True | 0.666700 | 95.3 | 6334 | 1370 | None |
| 41 | `DOC-77929aef8be50b00` | True | 0.454500 | 101.2 | 7594 | 1387 | None |
| 42 | `DOC-47d391f2646c0506` | True | 0.465100 | 90.4 | 7764 | 1171 | None |
| 43 | `DOC-39aa396025b48de0` | True | 0.428600 | 107.4 | 8078 | 1332 | None |
| 44 | `DOC-15262384b17086bb` | True | 0.500000 | 77.2 | 8178 | 1123 | None |
| 45 | `DOC-0812d9d3e2b1baa0` | True | 0.551700 | 204.0 | 7992 | 2226 | None |
| 46 | `DOC-027cf1502fa9fdcc` | True | 0.758600 | 80.1 | 8708 | 1170 | None |
| 47 | `DOC-4be26020b0470e43` | True | 0.600000 | 99.9 | 7501 | 1488 | None |
| 48 | `DOC-770401d1d47fd744` | True | 0.642900 | 82.7 | 7751 | 1236 | None |
| 49 | `DOC-030e70e9a17a085b` | True | 0.555600 | 108.3 | 4681 | 1645 | None |
| 50 | `DOC-f717fb61aa615da0` | True | 0.444400 | 83.5 | 8165 | 1250 | None |
| 51 | `DOC-4a5a0ac3eb60f76d` | True | 0.810800 | 96.1 | 8299 | 1328 | None |
| 52 | `DOC-a937a4b1b32c1c28` | True | 0.800000 | 105.8 | 8080 | 1573 | None |
| 53 | `DOC-55df050fcb737129` | True | 0.521700 | 78.4 | 5461 | 1235 | None |
| 54 | `DOC-2b56dc54d52da61b` | True | 0.640000 | 125.7 | 7887 | 1812 | None |
| 55 | `DOC-544b860c51e741e5` | True | 0.571400 | 91.1 | 7125 | 1340 | None |
| 56 | `DOC-ebb7fd616e84c91e` | True | 0.640000 | 115.4 | 8095 | 1679 | None |
| 57 | `DOC-09c0c774c3e5ec74` | True | 0.774200 | 127.6 | 8507 | 1862 | None |
| 58 | `DOC-a81d2badffc32bac` | True | 0.695700 | 83.5 | 7092 | 1093 | None |
| 59 | `DOC-9cb5ebeb3a84c3c6` | True | 0.600000 | 139.8 | 6938 | 2002 | None |
| 60 | `DOC-99ca00712a84f039` | True | 0.608700 | 136.1 | 5337 | 1990 | None |
| 61 | `DOC-34904aee099a62c7` | True | 0.666700 | 154.9 | 6946 | 2240 | None |
| 62 | `DOC-b508180128034504` | True | 0.875000 | 90.7 | 4243 | 1366 | None |
| 63 | `DOC-9baab4e28bbe8197` | True | 0.689700 | 99.5 | 8403 | 1464 | None |
| 64 | `DOC-8a776dec500b074c` | True | 0.344800 | 63.0 | 8308 | 904 | None |
| 65 | `DOC-472f423cdf0819ef` | True | 0.571400 | 84.6 | 4656 | 1208 | None |
| 66 | `DOC-93e9bb030e2b282d` | True | 0.640000 | 92.6 | 8560 | 1352 | None |
| 67 | `DOC-1952785cfa159000` | True | 0.645200 | 99.3 | 7282 | 1449 | None |
| 68 | `DOC-114e6a1b3555fd5e` | True | 0.592600 | 110.8 | 7879 | 1557 | None |
| 69 | `DOC-d9ed2885226fee7d` | True | 0.705900 | 93.2 | 7225 | 1364 | None |
| 70 | `DOC-03f1f6c0db99e651` | True | 0.533300 | 93.9 | 7683 | 1392 | None |
| 71 | `DOC-46041078786dff15` | True | 0.666700 | 74.8 | 7593 | 1113 | None |
| 72 | `DOC-13000a5067f49a46` | True | 0.240000 | 49.2 | 8391 | 700 | None |
| 73 | `DOC-d66d8f6c92207c3c` | True | 0.625000 | 122.3 | 4746 | 1863 | None |
| 74 | `DOC-c68a4dd90660c113` | True | 0.592600 | 116.6 | 7851 | 1649 | None |
| 75 | `DOC-f9b36fee351217c2` | True | 0.625000 | 103.1 | 7931 | 1609 | None |
| 76 | `DOC-06229aa6571f9d46` | True | 0.588200 | 78.4 | 6154 | 1227 | None |
| 77 | `DOC-9458a1486b686af6` | True | 0.533300 | 98.4 | 7142 | 1554 | None |
| 78 | `DOC-ddf429892b0d1563` | True | 0.666700 | 64.6 | 5661 | 1011 | None |
| 79 | `DOC-364e40f0752551a3` | True | 0.444400 | 61.8 | 10159 | 1020 | None |
| 80 | `DOC-f3686fdab1f1c6d3` | True | 0.833300 | 65.8 | 4783 | 1117 | None |
| 81 | `DOC-9a2c7cc21a860fc4` | True | 0.714300 | 96.3 | 7027 | 1646 | None |
| 82 | `DOC-01633b99e74dc9f2` | True | 0.500000 | 54.9 | 8129 | 915 | None |
| 83 | `DOC-e492894fbfa36087` | True | 0.518500 | 85.1 | 8030 | 1367 | None |
| 84 | `DOC-fca31a55b1d526ea` | True | 0.833300 | 173.4 | 5459 | 2679 | None |
| 85 | `DOC-d9372c268e93e88d` | True | 0.500000 | 51.0 | 5373 | 1124 | None |
| 86 | `DOC-4ab8d1d37d3af05c` | True | 0.640000 | 116.5 | 7678 | 2015 | None |
| 87 | `DOC-5750e41138d4168c` | True | 0.634100 | 197.6 | 8072 | 3235 | None |
| 88 | `DOC-c6761beeb32fb09c` | True | 0.666700 | 94.9 | 6750 | 1803 | None |
| 89 | `DOC-9f2b783b62276136` | True | 0.470600 | 102.7 | 6260 | 1951 | None |
| 90 | `DOC-d03ba995666cd696` | True | 0.666700 | 77.0 | 5162 | 1573 | None |
| 91 | `DOC-be1eccde5bae9c82` | True | 0.620700 | 91.4 | 8834 | 1927 | None |
| 92 | `DOC-e853a8ab86c5a54d` | True | 0.666700 | 112.4 | 4692 | 2206 | None |
| 93 | `DOC-dfa5c8eb1e7b837c` | True | 0.800000 | 104.7 | 6055 | 2106 | None |
| 94 | `DOC-f333c4b8048d5d8c` | True | 0.555600 | 84.4 | 7940 | 1877 | None |
| 95 | `DOC-c3f54a20515b5efd` | True | 0.700000 | 82.6 | 6077 | 1812 | None |
| 96 | `DOC-561364d531fca179` | True | 0.709700 | 84.9 | 7519 | 2060 | None |
| 97 | `DOC-a2ce7adbf6f5cb8d` | True | 0.833300 | 91.4 | 6729 | 2202 | None |
| 98 | `DOC-0de76b97986b57b3` | True | 0.588200 | 128.5 | 7735 | 2751 | None |
| 99 | `DOC-d1c45d175a8abeb5` | True | 0.571400 | 89.9 | 6851 | 2342 | None |
| 100 | `DOC-202288d54af09ad2` | False | — | 255.2 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=7113, total_tokens=15305, completion_tokens_details=None, prompt_tokens_details=None) |
