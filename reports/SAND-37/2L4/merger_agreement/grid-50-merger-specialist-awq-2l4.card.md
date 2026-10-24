# Merger Agreements — 2× L4 · C32 · n=50

**Run:** `grid-50-merger-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | merger_agreement_specialist |
| Prompt | merger_agreement_specialist_simplified |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 30,000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 50 docs (fingerprint 23c90708536e) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-50-merger-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | 0d3c431f… |
| **Time** |  |
| Wall (busy) | 340.85 s |
| GPU seconds | 341.26 s |
| Cold boot | 0.41 s |
| **Cost** |  |
| Busy-window GPU $ | $0.151488 |
| Billed GPU $ (incl. boot) | $0.151669 |
| Idle $ | $0.087496 (196.87 s) |
| Cost per document | $0.003030 |
| Cost per ok document | $0.003293 |
| Cost per 1M tokens | $0.3196 |
| **Tokens** |  |
| Prompt tokens | 429,708 |
| Completion tokens | 44,229 (9.3%) |
| Total tokens | 473,937 |
| Tokens per document | 10,303 |
| Per document: instructions + template | 2,675 (26.0%) |
| Per document: document text | 6,667 (64.7%) |
| Per document: output | 962 (9.3%) |
| Instruction tokens per model call | 2,675 over 46 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 1,543 / 2,852 |
| **Throughput** |  |
| Tokens / second | 1,390.5 |
| Tokens / second per L4 | 695.2 |
| Documents / minute | 8.80 |
| **Latency (per document, ok rows)** |  |
| Mean | 100.16 s |
| p50 | 92.49 s |
| p95 | 167.23 s |
| Max | 211.57 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 17.14× of 32 |
| Slot occupancy | 53.6% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 24 / 26 |
| Mean TTFT per replica | 9.740 s / 9.074 s |
| Prefix-cache hit per replica | 35.6% / 36.6% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 1 / 3 |
| **Quality** |  |
| Overall extraction score | 0.0351 (sd 0.041) |
| Score min / max | 0.0000 / 0.1333 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 4 / 50 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 174 / 747 (23.3%) |
| Micro accuracy | 3.5% |
| Precision on answered | 14.9% |
| Clean subset | 16 / 319 |
| Suite field score (mean) | not captured |

## Errors

| Error | Count |
| --- | ---: |
| LengthFinishReasonError | 4 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-0a733ab86f2390ae` | yes | 0.0667 | 75.2 | 8841 | 695 | — |
| 2 | `DOC-37026835107f9684` | yes | 0.0000 | 78.3 | 9439 | 681 | — |
| 3 | `DOC-511062d64bc9afc6` | yes | 0.0625 | 79.2 | 9338 | 686 | — |
| 4 | `DOC-52f9a5be69429299` | yes | 0.0000 | 80.4 | 9517 | 573 | — |
| 5 | `DOC-f90cc5fb2ceac154` | yes | 0.0000 | 82.4 | 9529 | 705 | — |
| 6 | `DOC-eac7882cff200545` | yes | 0.0000 | 86.3 | 9334 | 767 | — |
| 7 | `DOC-5fa0ba13cf68b593` | yes | 0.0000 | 86.8 | 9125 | 585 | — |
| 8 | `DOC-be8461dd68cfe458` | yes | 0.0667 | 92.0 | 9054 | 826 | — |
| 9 | `DOC-ecf69d7e102ef62a` | yes | 0.0000 | 92.4 | 9271 | 824 | — |
| 10 | `DOC-882fabf7aba36941` | yes | 0.0000 | 94.2 | 9595 | 848 | — |
| 11 | `DOC-62456d43b50f73fa` | yes | 0.0625 | 94.9 | 9688 | 860 | — |
| 12 | `DOC-d0495abfa5f3d8ee` | yes | 0.0625 | 92.6 | 9008 | 798 | — |
| 13 | `DOC-4ab4ecd86ecf275d` | yes | 0.0625 | 93.2 | 9590 | 814 | — |
| 14 | `DOC-c96b9c7e12f91576` | yes | 0.0000 | 93.7 | 9549 | 658 | — |
| 15 | `DOC-1252fb5690e17c7b` | yes | 0.0556 | 97.9 | 9296 | 711 | — |
| 16 | `DOC-74a69c5b3cdf1afc` | yes | 0.0667 | 106.3 | 10224 | 782 | — |
| 17 | `DOC-30eda1e78a5f6fb5` | yes | 0.0000 | 107.1 | 9124 | 795 | — |
| 18 | `DOC-c1d57615929b483e` | yes | 0.0000 | 110.9 | 9148 | 767 | — |
| 19 | `DOC-15f85636d1eb6b77` | yes | 0.0667 | 114.7 | 9514 | 771 | — |
| 20 | `DOC-8a0bdfe3d16c33b2` | yes | 0.0588 | 114.7 | 9360 | 988 | — |
| 21 | `DOC-f4e726a7f2c25494` | yes | 0.1333 | 115.3 | 9345 | 994 | — |
| 22 | `DOC-45f801408be08af6` | yes | 0.1333 | 119.5 | 10160 | 843 | — |
| 23 | `DOC-fc07b37a0f0d1234` | yes | 0.1250 | 125.7 | 9170 | 888 | — |
| 24 | `DOC-7430de65e5471741` | yes | 0.0000 | 130.2 | 9060 | 922 | — |
| 25 | `DOC-5fbb9ee2f4b4b114` | yes | 0.0000 | 131.5 | 9027 | 1316 | — |
| 26 | `DOC-038a485469f83c9a` | yes | 0.0625 | 133.5 | 9115 | 967 | — |
| 27 | `DOC-1e016055aa435e71` | yes | 0.0000 | 64.5 | 9148 | 790 | — |
| 28 | `DOC-8c661a1693d4655b` | yes | 0.0000 | 143.1 | 9289 | 1166 | — |
| 29 | `DOC-d5c4f12f934de48e` | yes | 0.1053 | 63.5 | 9465 | 881 | — |
| 30 | `DOC-f546c7d6cf2e77e2` | yes | 0.0526 | 41.0 | 8785 | 744 | — |
| 31 | `DOC-eb2b56fe30dc35f4` | yes | 0.0000 | 148.4 | 8971 | 1239 | — |
| 32 | `DOC-d1e355800bff0425` | yes | 0.0000 | 53.7 | 9196 | 797 | — |
| 33 | `DOC-fcaddb5bdc94ce63` | yes | 0.0588 | 56.9 | 9123 | 888 | — |
| 34 | `DOC-f099c5c73d56631e` | yes | 0.0000 | 72.4 | 9893 | 1195 | — |
| 35 | `DOC-fd6090e354177e5b` | yes | 0.0000 | 63.9 | 8909 | 1082 | — |
| 36 | `DOC-3927f91bc3daffc3` | yes | 0.0000 | 164.8 | 9676 | 916 | — |
| 37 | `DOC-8f599c800d19fd92` | yes | 0.0000 | 167.2 | 9146 | 1022 | — |
| 38 | `DOC-d554890e66786170` | yes | 0.0000 | 168.2 | 10446 | 1579 | — |
| 39 | `DOC-bec74557186e9409` | yes | 0.0000 | 90.9 | 9430 | 942 | — |
| 40 | `DOC-169bbcdc5d9e609c` | yes | 0.0769 | 71.8 | 9975 | 1395 | — |
| 41 | `DOC-2f9cf3ce009aaaf0` | yes | 0.0588 | 91.9 | 9043 | 991 | — |
| 42 | `DOC-5c44797b6add60e4` | yes | 0.0667 | 77.6 | 9230 | 1543 | — |
| 43 | `DOC-03712a2b0a99a314` | yes | 0.0000 | 80.9 | 9286 | 1014 | — |
| 44 | `DOC-ab735131c00271bc` | yes | 0.0556 | 73.9 | 8800 | 1051 | — |
| 45 | `DOC-b866e2b4f5059213` | yes | 0.0556 | 72.4 | 9099 | 1078 | — |
| 46 | `DOC-d01014aed8ad8824` | yes | 0.0000 | 211.6 | 9377 | 2852 | — |
| 47 | `DOC-63beb09b179ea4ee` | no | — | 263.2 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9374, total_to |
| 48 | `DOC-2b9f668ab6cb8901` | no | — | 329.3 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=8927, total_to |
| 49 | `DOC-8fe2855a2310cdbe` | no | — | 323.6 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9249, total_to |
| 50 | `DOC-26fa94f698c37fc5` | no | — | 319.8 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9043, total_to |

_Generated 2026-10-01T06:44:51+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-merger-specialist-awq-2l4.card.json`._
