# Contracts — 2× L4 · C32 · n=100

**Run:** `sand40-100-contracts-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | contracts_specialist |
| Prompt | contracts_specialist_v33_simplified |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 24,000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 100 docs (fingerprint 6d82d7d13fa4) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand40-100-contracts-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 100 |
| Spec hash | 1ce35cb0… |
| **Time** |  |
| Wall (busy) | 460.62 s |
| GPU seconds | 460.92 s |
| Cold boot | 0.30 s |
| **Cost** |  |
| Busy-window GPU $ | $0.204722 |
| Billed GPU $ (incl. boot) | $0.204855 |
| Idle $ | $0.065905 (148.29 s) |
| Cost per document | $0.002047 |
| Cost per ok document | $0.002068 |
| Cost per 1M tokens | $0.2397 |
| **Tokens** |  |
| Prompt tokens | 707,289 |
| Completion tokens | 146,665 (17.2%) |
| Total tokens | 853,954 |
| Tokens per document | 8,626 |
| Per document: instructions + template | 2,916 (33.8%) |
| Per document: document text | 4,229 (49.0%) |
| Per document: output | 1,481 (17.2%) |
| Instruction tokens per model call | 2,916 over 99 calls |
| Token split basis | fit across documents, 4.58 chars/token |
| Completion p95 / max (ok docs) | 2,226 / 3,235 |
| **Throughput** |  |
| Tokens / second | 1,853.9 |
| Tokens / second per L4 | 927.0 |
| Documents / minute | 13.03 |
| **Latency (per document, ok rows)** |  |
| Mean | 100.96 s |
| p50 | 96.14 s |
| p95 | 159.27 s |
| Max | 203.95 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 22.25× of 32 |
| Slot occupancy | 69.5% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 47 / 53 |
| Mean TTFT per replica | 3.224 s / 5.490 s |
| Prefix-cache hit per replica | 38.9% / 40.3% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 1 |
| **Quality** |  |
| Overall extraction score | 0.6116 (sd 0.127) |
| Score min / max | 0.2400 / 0.8889 |
| Scoring method | `suite+cuad` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 1 / 100 |
| **Clause scoring (CUAD)** |  |
| Docs with CUAD labels | 82 |
| Micro precision / recall / F1 | 0.684 / 0.548 / 0.608 |
| Metadata value checks | 156 / 237 |
| Suite field score (mean) | not captured |

## Errors

| Error | Count |
| --- | ---: |
| LengthFinishReasonError | 1 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-98ff556893f1a98f` | yes | 0.8571 | 40.6 | 3200 | 383 | — |
| 2 | `DOC-56d6a0f676f98474` | yes | — | 50.4 | 6868 | 574 | — |
| 3 | `DOC-10357f1d86b3081e` | yes | — | 66.2 | 3687 | 838 | — |
| 4 | `DOC-25f822c661011bfe` | yes | 0.4286 | 71.3 | 7821 | 874 | — |
| 5 | `DOC-ea746c407db93af2` | yes | — | 78.8 | 4804 | 997 | — |
| 6 | `DOC-2e3e2bb13d6c83ca` | yes | — | 81.4 | 13464 | 996 | — |
| 7 | `DOC-1afbdbce947fcbb2` | yes | — | 83.1 | 8609 | 1076 | — |
| 8 | `DOC-5892b6dc609c8d0f` | yes | — | 85.0 | 7606 | 1034 | — |
| 9 | `DOC-adad5ef793c0e409` | yes | 0.4000 | 91.3 | 8247 | 1149 | — |
| 10 | `DOC-54ad252b1e5e8d58` | yes | 0.6923 | 95.1 | 8244 | 1274 | — |
| 11 | `DOC-6712aa595cfe3e2c` | yes | 0.4706 | 99.1 | 7666 | 1273 | — |
| 12 | `DOC-e3f6015e5645a811` | yes | 0.6000 | 100.2 | 4436 | 1334 | — |
| 13 | `DOC-a05bef17a3ab844f` | yes | — | 102.4 | 7959 | 1327 | — |
| 14 | `DOC-78a0da18d0ba811a` | yes | — | 104.7 | 7869 | 1348 | — |
| 15 | `DOC-c7f557969d953fae` | yes | — | 106.4 | 8119 | 1358 | — |
| 16 | `DOC-440a54573c24b918` | yes | 0.4444 | 59.5 | 3493 | 939 | — |
| 17 | `DOC-e3afd3d853d33152` | yes | 0.7273 | 110.3 | 8334 | 1428 | — |
| 18 | `DOC-9696c5996f24d85d` | yes | — | 113.3 | 4377 | 1472 | — |
| 19 | `DOC-7523d051bc56169f` | yes | — | 114.4 | 8145 | 1464 | — |
| 20 | `DOC-2f88403fb6616a82` | yes | 0.6154 | 118.3 | 9168 | 701 | — |
| 21 | `DOC-c2ac5762c7f227fa` | yes | — | 120.2 | 8143 | 1558 | — |
| 22 | `DOC-c30c293d38a2cd8b` | yes | 0.6364 | 81.0 | 9794 | 1249 | — |
| 23 | `DOC-ab9afe870c6269b2` | yes | — | 125.5 | 7429 | 1594 | — |
| 24 | `DOC-3893bdb61733ec56` | yes | — | 126.0 | 4378 | 1238 | — |
| 25 | `DOC-ba6d7a0ea5100bbb` | yes | 0.6000 | 130.1 | 7887 | 1686 | — |
| 26 | `DOC-2ca7b08d2d439f1e` | yes | — | 138.9 | 7616 | 1824 | — |
| 27 | `DOC-eb9157e3710cc477` | yes | 0.4000 | 139.3 | 7668 | 1830 | — |
| 28 | `DOC-9adf4d68fa5bec24` | yes | 0.6400 | 141.8 | 8104 | 1848 | — |
| 29 | `DOC-9e063c6e3baf1233` | yes | 0.5161 | 145.8 | 7486 | 1909 | — |
| 30 | `DOC-8978696bf49c6085` | yes | 0.8889 | 52.0 | 3678 | 695 | — |
| 31 | `DOC-9b569749ea3d6f42` | yes | — | 153.2 | 11640 | 1978 | — |
| 32 | `DOC-dbfa4f9eb3f16433` | yes | 0.6429 | 159.3 | 6748 | 2103 | — |
| 33 | `DOC-ee4369c8980926dc` | yes | 0.5926 | 88.1 | 7993 | 1256 | — |
| 34 | `DOC-e235bc9735f96335` | yes | 0.8235 | 159.5 | 7449 | 2161 | — |
| 35 | `DOC-3b768dc1c4ebdc47` | yes | 0.5333 | 86.1 | 4521 | 1217 | — |
| 36 | `DOC-ade03c57c5f78e21` | yes | 0.5333 | 99.2 | 4093 | 1239 | — |
| 37 | `DOC-83320eec5eec6235` | yes | 0.6667 | 55.1 | 7706 | 778 | — |
| 38 | `DOC-680704693a37b610` | yes | 0.4444 | 78.8 | 7946 | 1110 | — |
| 39 | `DOC-962cc639f3ebee80` | yes | — | 176.5 | 7359 | 1491 | — |
| 40 | `DOC-eba7f7faca68e78c` | yes | 0.6667 | 95.3 | 6334 | 1370 | — |
| 41 | `DOC-77929aef8be50b00` | yes | 0.4545 | 101.2 | 7594 | 1387 | — |
| 42 | `DOC-47d391f2646c0506` | yes | 0.4651 | 90.4 | 7764 | 1171 | — |
| 43 | `DOC-39aa396025b48de0` | yes | 0.4286 | 107.4 | 8078 | 1332 | — |
| 44 | `DOC-15262384b17086bb` | yes | 0.5000 | 77.2 | 8178 | 1123 | — |
| 45 | `DOC-0812d9d3e2b1baa0` | yes | 0.5517 | 204.0 | 7992 | 2226 | — |
| 46 | `DOC-027cf1502fa9fdcc` | yes | 0.7586 | 80.1 | 8708 | 1170 | — |
| 47 | `DOC-4be26020b0470e43` | yes | 0.6000 | 99.9 | 7501 | 1488 | — |
| 48 | `DOC-770401d1d47fd744` | yes | 0.6429 | 82.7 | 7751 | 1236 | — |
| 49 | `DOC-030e70e9a17a085b` | yes | 0.5556 | 108.3 | 4681 | 1645 | — |
| 50 | `DOC-f717fb61aa615da0` | yes | 0.4444 | 83.5 | 8165 | 1250 | — |
| 51 | `DOC-4a5a0ac3eb60f76d` | yes | 0.8108 | 96.1 | 8299 | 1328 | — |
| 52 | `DOC-a937a4b1b32c1c28` | yes | 0.8000 | 105.8 | 8080 | 1573 | — |
| 53 | `DOC-55df050fcb737129` | yes | 0.5217 | 78.4 | 5461 | 1235 | — |
| 54 | `DOC-2b56dc54d52da61b` | yes | 0.6400 | 125.7 | 7887 | 1812 | — |
| 55 | `DOC-544b860c51e741e5` | yes | 0.5714 | 91.1 | 7125 | 1340 | — |
| 56 | `DOC-ebb7fd616e84c91e` | yes | 0.6400 | 115.4 | 8095 | 1679 | — |
| 57 | `DOC-09c0c774c3e5ec74` | yes | 0.7742 | 127.6 | 8507 | 1862 | — |
| 58 | `DOC-a81d2badffc32bac` | yes | 0.6957 | 83.5 | 7092 | 1093 | — |
| 59 | `DOC-9cb5ebeb3a84c3c6` | yes | 0.6000 | 139.8 | 6938 | 2002 | — |
| 60 | `DOC-99ca00712a84f039` | yes | 0.6087 | 136.1 | 5337 | 1990 | — |
| 61 | `DOC-34904aee099a62c7` | yes | 0.6667 | 154.9 | 6946 | 2240 | — |
| 62 | `DOC-b508180128034504` | yes | 0.8750 | 90.7 | 4243 | 1366 | — |
| 63 | `DOC-9baab4e28bbe8197` | yes | 0.6897 | 99.5 | 8403 | 1464 | — |
| 64 | `DOC-8a776dec500b074c` | yes | 0.3448 | 63.0 | 8308 | 904 | — |
| 65 | `DOC-472f423cdf0819ef` | yes | 0.5714 | 84.6 | 4656 | 1208 | — |
| 66 | `DOC-93e9bb030e2b282d` | yes | 0.6400 | 92.6 | 8560 | 1352 | — |
| 67 | `DOC-1952785cfa159000` | yes | 0.6452 | 99.3 | 7282 | 1449 | — |
| 68 | `DOC-114e6a1b3555fd5e` | yes | 0.5926 | 110.8 | 7879 | 1557 | — |
| 69 | `DOC-d9ed2885226fee7d` | yes | 0.7059 | 93.2 | 7225 | 1364 | — |
| 70 | `DOC-03f1f6c0db99e651` | yes | 0.5333 | 93.9 | 7683 | 1392 | — |
| 71 | `DOC-46041078786dff15` | yes | 0.6667 | 74.8 | 7593 | 1113 | — |
| 72 | `DOC-13000a5067f49a46` | yes | 0.2400 | 49.2 | 8391 | 700 | — |
| 73 | `DOC-d66d8f6c92207c3c` | yes | 0.6250 | 122.3 | 4746 | 1863 | — |
| 74 | `DOC-c68a4dd90660c113` | yes | 0.5926 | 116.6 | 7851 | 1649 | — |
| 75 | `DOC-f9b36fee351217c2` | yes | 0.6250 | 103.1 | 7931 | 1609 | — |
| 76 | `DOC-06229aa6571f9d46` | yes | 0.5882 | 78.4 | 6154 | 1227 | — |
| 77 | `DOC-9458a1486b686af6` | yes | 0.5333 | 98.4 | 7142 | 1554 | — |
| 78 | `DOC-ddf429892b0d1563` | yes | 0.6667 | 64.6 | 5661 | 1011 | — |
| 79 | `DOC-364e40f0752551a3` | yes | 0.4444 | 61.8 | 10159 | 1020 | — |
| 80 | `DOC-f3686fdab1f1c6d3` | yes | 0.8333 | 65.8 | 4783 | 1117 | — |
| 81 | `DOC-9a2c7cc21a860fc4` | yes | 0.7143 | 96.3 | 7027 | 1646 | — |
| 82 | `DOC-01633b99e74dc9f2` | yes | 0.5000 | 54.9 | 8129 | 915 | — |
| 83 | `DOC-e492894fbfa36087` | yes | 0.5185 | 85.1 | 8030 | 1367 | — |
| 84 | `DOC-fca31a55b1d526ea` | yes | 0.8333 | 173.4 | 5459 | 2679 | — |
| 85 | `DOC-d9372c268e93e88d` | yes | 0.5000 | 51.0 | 5373 | 1124 | — |
| 86 | `DOC-4ab8d1d37d3af05c` | yes | 0.6400 | 116.5 | 7678 | 2015 | — |
| 87 | `DOC-5750e41138d4168c` | yes | 0.6341 | 197.6 | 8072 | 3235 | — |
| 88 | `DOC-c6761beeb32fb09c` | yes | 0.6667 | 94.9 | 6750 | 1803 | — |
| 89 | `DOC-9f2b783b62276136` | yes | 0.4706 | 102.7 | 6260 | 1951 | — |
| 90 | `DOC-d03ba995666cd696` | yes | 0.6667 | 77.0 | 5162 | 1573 | — |
| 91 | `DOC-be1eccde5bae9c82` | yes | 0.6207 | 91.4 | 8834 | 1927 | — |
| 92 | `DOC-e853a8ab86c5a54d` | yes | 0.6667 | 112.4 | 4692 | 2206 | — |
| 93 | `DOC-dfa5c8eb1e7b837c` | yes | 0.8000 | 104.7 | 6055 | 2106 | — |
| 94 | `DOC-f333c4b8048d5d8c` | yes | 0.5556 | 84.4 | 7940 | 1877 | — |
| 95 | `DOC-c3f54a20515b5efd` | yes | 0.7000 | 82.6 | 6077 | 1812 | — |
| 96 | `DOC-561364d531fca179` | yes | 0.7097 | 84.9 | 7519 | 2060 | — |
| 97 | `DOC-a2ce7adbf6f5cb8d` | yes | 0.8333 | 91.4 | 6729 | 2202 | — |
| 98 | `DOC-0de76b97986b57b3` | yes | 0.5882 | 128.5 | 7735 | 2751 | — |
| 99 | `DOC-d1c45d175a8abeb5` | yes | 0.5714 | 89.9 | 6851 | 2342 | — |
| 100 | `DOC-202288d54af09ad2` | no | — | 255.2 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=7113, total_to |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `sand40-100-contracts-specialist-awq-2l4.card.json`._
