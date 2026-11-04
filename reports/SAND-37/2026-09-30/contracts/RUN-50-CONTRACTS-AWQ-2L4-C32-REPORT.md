# Run report — `grid-50-contracts-specialist-awq-2l4-rerun`

Dated cell stem: `RUN-50-CONTRACTS-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-contracts-specialist-awq-2l4-rerun` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `3b6ca5ace37de7103b5ab6eea78c7dd9a36652e02c25b4c0d14a5aad244b367d` |
| dataset fingerprint | `c29633d769b5` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **49 / 1 / 50** |
| **overall_extraction_score** | **0.501727** |
| schema_valid_rate | 1.000000 |
| error_count | 1 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 312.765 |
| gpu_seconds | 313.054 |
| estimated GPU cost | 0.139135 |
| **GPU $/doc** | **0.00283949** |
| latency p50 / max (s) | 103.347807 / 213.616248 |
| prompt / completion tokens | 360560 / 76386 |
| concurrency speedup (Σlat/wall) | 16.35 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-98ff556893f1a98f` | True | 0.857100 | 36.4 | 3200 | 395 | None |
| 2 | `DOC-adad5ef793c0e409` | True | 0.518500 | 54.0 | 8247 | 741 | None |
| 3 | `DOC-2e3e2bb13d6c83ca` | True | — | 58.2 | 13464 | 558 | None |
| 4 | `DOC-ee4369c8980926dc` | True | 0.521700 | 77.0 | 7993 | 1182 | None |
| 5 | `DOC-34904aee099a62c7` | True | 0.636400 | 77.3 | 6946 | 1198 | None |
| 6 | `DOC-f717fb61aa615da0` | True | 0.444400 | 80.3 | 8165 | 1211 | None |
| 7 | `DOC-25f822c661011bfe` | True | 0.437500 | 80.8 | 7821 | 1236 | None |
| 8 | `DOC-9696c5996f24d85d` | True | — | 81.4 | 4377 | 959 | None |
| 9 | `DOC-440a54573c24b918` | True | 0.571400 | 86.9 | 3493 | 1039 | None |
| 10 | `DOC-ade03c57c5f78e21` | True | 0.750000 | 101.1 | 4093 | 1242 | None |
| 11 | `DOC-09c0c774c3e5ec74` | True | 0.272700 | 103.3 | 8507 | 1264 | None |
| 12 | `DOC-55df050fcb737129` | True | 0.666700 | 103.3 | 5461 | 1621 | None |
| 13 | `DOC-2ca7b08d2d439f1e` | True | — | 108.4 | 7616 | 1320 | None |
| 14 | `DOC-5892b6dc609c8d0f` | True | — | 109.3 | 7606 | 1703 | None |
| 15 | `DOC-770401d1d47fd744` | True | 0.666700 | 112.3 | 7751 | 1376 | None |
| 16 | `DOC-c30c293d38a2cd8b` | True | 0.720000 | 113.4 | 9794 | 804 | None |
| 17 | `DOC-ba6d7a0ea5100bbb` | True | 0.666700 | 116.1 | 7887 | 1790 | None |
| 18 | `DOC-83320eec5eec6235` | True | 0.769200 | 119.0 | 7706 | 1417 | None |
| 19 | `DOC-4be26020b0470e43` | True | 0.571400 | 120.4 | 7501 | 1451 | None |
| 20 | `DOC-c7f557969d953fae` | True | — | 120.6 | 8119 | 1433 | None |
| 21 | `DOC-93e9bb030e2b282d` | True | 0.769200 | 68.1 | 8560 | 1126 | None |
| 22 | `DOC-c68a4dd90660c113` | True | 0.560000 | 88.0 | 7851 | 1525 | None |
| 23 | `DOC-99ca00712a84f039` | True | 0.571400 | 126.0 | 5337 | 1952 | None |
| 24 | `DOC-e235bc9735f96335` | True | 0.758600 | 129.8 | 7449 | 1549 | None |
| 25 | `DOC-6712aa595cfe3e2c` | True | 0.555600 | 133.8 | 7666 | 2125 | None |
| 26 | `DOC-962cc639f3ebee80` | True | — | 133.9 | 7359 | 1640 | None |
| 27 | `DOC-9b569749ea3d6f42` | True | — | 136.8 | 11640 | 1667 | None |
| 28 | `DOC-15262384b17086bb` | True | 0.560000 | 137.4 | 8178 | 2201 | None |
| 29 | `DOC-54ad252b1e5e8d58` | True | 0.785700 | 138.0 | 8244 | 1696 | None |
| 30 | `DOC-d66d8f6c92207c3c` | True | 0.625000 | 140.4 | 4746 | 1776 | None |
| 31 | `DOC-c2ac5762c7f227fa` | True | — | 147.3 | 8143 | 1932 | None |
| 32 | `DOC-fca31a55b1d526ea` | True | 0.833300 | 156.6 | 5459 | 2688 | None |
| 33 | `DOC-ea746c407db93af2` | True | — | 157.6 | 4804 | 1225 | None |
| 34 | `DOC-364e40f0752551a3` | True | 0.457100 | 61.0 | 10159 | 956 | None |
| 35 | `DOC-0de76b97986b57b3` | True | 0.588200 | 86.2 | 7735 | 1729 | None |
| 36 | `DOC-f9b36fee351217c2` | True | 0.631600 | 94.3 | 7931 | 1870 | None |
| 37 | `DOC-01633b99e74dc9f2` | True | 0.470600 | 52.4 | 8129 | 1209 | None |
| 38 | `DOC-03f1f6c0db99e651` | True | 0.615400 | 115.8 | 7683 | 1347 | None |
| 39 | `DOC-e853a8ab86c5a54d` | True | 0.588200 | 90.9 | 4692 | 1350 | None |
| 40 | `DOC-9a2c7cc21a860fc4` | True | 0.714300 | 83.7 | 7027 | 1868 | None |
| 41 | `DOC-dfa5c8eb1e7b837c` | True | 0.818200 | 77.6 | 6055 | 1527 | None |
| 42 | `DOC-8a776dec500b074c` | True | 0.344800 | 109.5 | 8308 | 1721 | None |
| 43 | `DOC-06229aa6571f9d46` | True | 0.631600 | 107.7 | 6154 | 1718 | None |
| 44 | `DOC-561364d531fca179` | True | 0.666700 | 77.7 | 7519 | 1917 | None |
| 45 | `DOC-d1c45d175a8abeb5` | True | 0.631600 | 79.2 | 6851 | 1836 | None |
| 46 | `DOC-e492894fbfa36087` | True | 0.500000 | 92.8 | 8030 | 2232 | None |
| 47 | `DOC-4ab8d1d37d3af05c` | True | 0.571400 | 118.2 | 7678 | 2727 | None |
| 48 | `DOC-f333c4b8048d5d8c` | True | 0.631600 | 98.8 | 7940 | 2422 | None |
| 49 | `DOC-9e063c6e3baf1233` | True | 0.634100 | 213.6 | 7486 | 2915 | None |
| 50 | `DOC-a2ce7adbf6f5cb8d` | False | — | 239.9 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=6729, total_tokens=14921, completion_tokens_details=None, prompt_tokens_details=None) |
