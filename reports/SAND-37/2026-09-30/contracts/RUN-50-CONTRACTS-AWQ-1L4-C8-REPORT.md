# Run report — `grid-50-contracts-specialist-awq-1l4`

Dated cell stem: `RUN-50-CONTRACTS-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-contracts-specialist-awq-1l4` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `663799cfa33002afefc8f0fa58347c73d8aea83261d957751ab5b3ebabf323fe` |
| dataset fingerprint | `c29633d769b5` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **47 / 3 / 50** |
| **overall_extraction_score** | **0.499504** |
| schema_valid_rate | 1.000000 |
| error_count | 3 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 655.158 |
| gpu_seconds | 655.603 |
| estimated GPU cost | 0.145690 |
| **GPU $/doc** | **0.00309979** |
| latency p50 / max (s) | 68.152166 / 134.226871 |
| prompt / completion tokens | 342770 / 74037 |
| concurrency speedup (Σlat/wall) | 5.04 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-ea746c407db93af2` | True | — | 45.7 | 4804 | 884 | None |
| 2 | `DOC-2ca7b08d2d439f1e` | True | — | 46.2 | 7616 | 909 | None |
| 3 | `DOC-5892b6dc609c8d0f` | True | — | 64.6 | 7606 | 1216 | None |
| 4 | `DOC-962cc639f3ebee80` | True | — | 68.9 | 7359 | 1312 | None |
| 5 | `DOC-9696c5996f24d85d` | True | — | 72.7 | 4377 | 1339 | None |
| 6 | `DOC-9b569749ea3d6f42` | True | — | 81.5 | 11640 | 1493 | None |
| 7 | `DOC-c7f557969d953fae` | True | — | 83.3 | 8119 | 1558 | None |
| 8 | `DOC-2e3e2bb13d6c83ca` | True | — | 66.1 | 13464 | 1314 | None |
| 9 | `DOC-25f822c661011bfe` | True | 0.466700 | 44.1 | 7821 | 886 | None |
| 10 | `DOC-ba6d7a0ea5100bbb` | True | 0.714300 | 61.2 | 7887 | 1227 | None |
| 11 | `DOC-6712aa595cfe3e2c` | True | 0.470600 | 52.9 | 7666 | 1121 | None |
| 12 | `DOC-98ff556893f1a98f` | True | 0.750000 | 22.3 | 3200 | 510 | None |
| 13 | `DOC-54ad252b1e5e8d58` | True | 0.592600 | 77.6 | 8244 | 1717 | None |
| 14 | `DOC-e235bc9735f96335` | True | 0.583300 | 49.3 | 7449 | 1154 | None |
| 15 | `DOC-c30c293d38a2cd8b` | True | 0.740700 | 41.0 | 9794 | 929 | None |
| 16 | `DOC-9e063c6e3baf1233` | True | 0.571400 | 104.0 | 7486 | 2312 | None |
| 17 | `DOC-440a54573c24b918` | True | 0.500000 | 40.6 | 3493 | 948 | None |
| 18 | `DOC-ade03c57c5f78e21` | True | 0.625000 | 51.8 | 4093 | 1212 | None |
| 19 | `DOC-09c0c774c3e5ec74` | True | 0.709700 | 54.6 | 8507 | 1299 | None |
| 20 | `DOC-4be26020b0470e43` | True | 0.571400 | 66.1 | 7501 | 1591 | None |
| 21 | `DOC-ee4369c8980926dc` | True | 0.588200 | 96.9 | 7993 | 2228 | None |
| 22 | `DOC-99ca00712a84f039` | True | 0.631600 | 74.5 | 5337 | 1750 | None |
| 23 | `DOC-34904aee099a62c7` | True | 0.592600 | 100.6 | 6946 | 2286 | None |
| 24 | `DOC-83320eec5eec6235` | True | 0.717900 | 71.5 | 7706 | 1591 | None |
| 25 | `DOC-f717fb61aa615da0` | True | 0.642900 | 30.0 | 8165 | 661 | None |
| 26 | `DOC-15262384b17086bb` | True | 0.666700 | 81.6 | 8178 | 1858 | None |
| 27 | `DOC-fca31a55b1d526ea` | True | 0.727300 | 61.5 | 5459 | 1397 | None |
| 28 | `DOC-770401d1d47fd744` | True | 0.645200 | 68.5 | 7751 | 1483 | None |
| 29 | `DOC-55df050fcb737129` | True | 0.571400 | 81.3 | 5461 | 1870 | None |
| 30 | `DOC-d66d8f6c92207c3c` | True | 0.761900 | 78.8 | 4746 | 1768 | None |
| 31 | `DOC-c68a4dd90660c113` | True | 0.615400 | 81.1 | 7851 | 1782 | None |
| 32 | `DOC-c2ac5762c7f227fa` | False | — | 373.2 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=8143, total_tokens=16335, completion_tokens_details=None, prompt_tokens_details=None) |
| 33 | `DOC-06229aa6571f9d46` | True | 0.625000 | 35.2 | 6154 | 790 | None |
| 34 | `DOC-8a776dec500b074c` | True | 0.344800 | 53.8 | 8308 | 1138 | None |
| 35 | `DOC-93e9bb030e2b282d` | True | 0.758600 | 97.9 | 8560 | 2088 | None |
| 36 | `DOC-f9b36fee351217c2` | True | 0.342900 | 103.0 | 7931 | 2248 | None |
| 37 | `DOC-adad5ef793c0e409` | False | — | 371.5 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=8247, total_tokens=16439, completion_tokens_details=None, prompt_tokens_details=None) |
| 38 | `DOC-03f1f6c0db99e651` | True | 0.615400 | 128.6 | 7683 | 2829 | None |
| 39 | `DOC-364e40f0752551a3` | True | 0.421100 | 55.8 | 10159 | 1318 | None |
| 40 | `DOC-4ab8d1d37d3af05c` | True | 0.620700 | 108.9 | 7678 | 2430 | None |
| 41 | `DOC-e853a8ab86c5a54d` | True | 0.521700 | 69.9 | 4692 | 1558 | None |
| 42 | `DOC-9a2c7cc21a860fc4` | True | 0.714300 | 79.4 | 7027 | 1796 | None |
| 43 | `DOC-e492894fbfa36087` | True | 0.370400 | 66.6 | 8030 | 1530 | None |
| 44 | `DOC-dfa5c8eb1e7b837c` | True | 0.800000 | 68.2 | 6055 | 1632 | None |
| 45 | `DOC-a2ce7adbf6f5cb8d` | True | 0.736800 | 67.1 | 6729 | 1675 | None |
| 46 | `DOC-0de76b97986b57b3` | True | 0.588200 | 134.2 | 7735 | 3207 | None |
| 47 | `DOC-561364d531fca179` | True | 0.560000 | 49.6 | 7519 | 1292 | None |
| 48 | `DOC-d1c45d175a8abeb5` | True | 0.400000 | 53.5 | 6851 | 1510 | None |
| 49 | `DOC-f333c4b8048d5d8c` | True | 0.600000 | 108.9 | 7940 | 3391 | None |
| 50 | `DOC-01633b99e74dc9f2` | False | — | 224.7 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=8129, total_tokens=16321, completion_tokens_details=None, prompt_tokens_details=None) |
