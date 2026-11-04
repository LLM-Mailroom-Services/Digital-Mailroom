# Merger Agreements — 2× L4 · C32 · n=50

**Run:** `sand40-50-merger-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | merger_agreement_specialist |
| Prompt | merger_agreement_specialist_maud_v1 |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 6,144 |
| Input cap (max_input_chars) | 54,000 |
| Optimized long-document settings | yes |
| top_p | 0.8 |
| top_k | 20 |
| presence_penalty | 1.0 |
| Length re-samples | 1 |
| Chunk window (chars) | 47000 |
| Chunk overlap (chars) | 6500 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 50 docs (fingerprint 23c90708536e) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand40-50-merger-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | 9200d91b… |
| **Time** |  |
| Wall (busy) | 1,658.84 s |
| GPU seconds | 1,659.18 s |
| Cold boot | 0.34 s |
| **Cost** |  |
| Busy-window GPU $ | $0.737261 |
| Billed GPU $ (incl. boot) | $0.737415 |
| Idle $ | not captured |
| Cost per document | $0.014745 |
| Cost per ok document | $0.014745 |
| Cost per 1M tokens | $0.1313 |
| **Tokens** |  |
| Prompt tokens | 5,334,445 |
| Completion tokens | 278,545 (5.0%) |
| Total tokens | 5,612,990 |
| Tokens per document | 112,260 |
| Per document: instructions + template | 19,669 (17.5%) |
| Per document: document text | 87,019 (77.5%) |
| Per document: output | 5,571 (5.0%) |
| Instruction tokens per model call | 2,484 over 396 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 8,012 / 13,241 |
| **Throughput** |  |
| Tokens / second | 3,383.7 |
| Tokens / second per L4 | 1,691.8 |
| Documents / minute | 1.81 |
| **Latency (per document, ok rows)** |  |
| Mean | 1,120.40 s |
| p50 | 1,044.40 s |
| p95 | 2,067.44 s |
| Max | 2,264.44 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 33.77× of 32 |
| Slot occupancy | 105.5% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 199 / 219 |
| Mean TTFT per replica | 12.717 s / 9.086 s |
| Prefix-cache hit per replica | 27.6% / 28.8% |
| Preemptions per replica (this run) | 8 / 0 |
| Length-capped finishes per replica (this run) | 14 / 9 |
| **Quality** |  |
| Overall extraction score | 0.1392 (sd 0.090) |
| Score min / max | 0.0000 / 0.3333 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 561 / 817 (68.7%) |
| Micro accuracy | 14.0% |
| Precision on answered | 20.3% |
| Clean subset | 46 / 351 |
| Suite field score (mean) | not captured |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-37026835107f9684` | yes | 0.0000 | 605.6 | 97353 | 3463 | — |
| 2 | `DOC-62456d43b50f73fa` | yes | 0.0625 | 662.4 | 79234 | 4416 | — |
| 3 | `DOC-8c661a1693d4655b` | yes | 0.2667 | 681.3 | 79942 | 4853 | — |
| 4 | `DOC-5fbb9ee2f4b4b114` | yes | 0.0000 | 707.8 | 90100 | 3861 | — |
| 5 | `DOC-0a733ab86f2390ae` | yes | 0.0667 | 711.3 | 93375 | 4593 | — |
| 6 | `DOC-eac7882cff200545` | yes | 0.0588 | 711.5 | 64843 | 3560 | — |
| 7 | `DOC-1252fb5690e17c7b` | yes | 0.1111 | 720.4 | 79209 | 4123 | — |
| 8 | `DOC-038a485469f83c9a` | yes | 0.2500 | 739.6 | 75770 | 4639 | — |
| 9 | `DOC-8a0bdfe3d16c33b2` | yes | 0.1176 | 794.6 | 114164 | 4235 | — |
| 10 | `DOC-7430de65e5471741` | yes | 0.2632 | 804.8 | 89823 | 4145 | — |
| 11 | `DOC-be8461dd68cfe458` | yes | 0.0667 | 805.5 | 98287 | 4989 | — |
| 12 | `DOC-fc07b37a0f0d1234` | yes | 0.2500 | 998.4 | 92499 | 6645 | — |
| 13 | `DOC-c96b9c7e12f91576` | yes | 0.1765 | 1,018.5 | 106010 | 5889 | — |
| 14 | `DOC-d01014aed8ad8824` | yes | 0.1250 | 1,043.1 | 95120 | 6382 | — |
| 15 | `DOC-74a69c5b3cdf1afc` | yes | 0.3333 | 1,045.7 | 149473 | 6495 | — |
| 16 | `DOC-52f9a5be69429299` | yes | 0.2353 | 1,090.6 | 119128 | 6446 | — |
| 17 | `DOC-882fabf7aba36941` | yes | 0.0588 | 1,099.6 | 105845 | 6656 | — |
| 18 | `DOC-45f801408be08af6` | yes | 0.2667 | 1,166.1 | 125130 | 7164 | — |
| 19 | `DOC-c1d57615929b483e` | yes | 0.0625 | 1,197.9 | 148410 | 6948 | — |
| 20 | `DOC-63beb09b179ea4ee` | yes | 0.2353 | 549.6 | 95402 | 3690 | — |
| 21 | `DOC-d554890e66786170` | yes | 0.2500 | 1,259.6 | 109746 | 6844 | — |
| 22 | `DOC-d0495abfa5f3d8ee` | yes | 0.3125 | 1,339.8 | 81246 | 3903 | — |
| 23 | `DOC-f546c7d6cf2e77e2` | yes | 0.0000 | 309.8 | 33384 | 1839 | — |
| 24 | `DOC-f4e726a7f2c25494` | yes | 0.2000 | 1,421.9 | 80639 | 3783 | — |
| 25 | `DOC-eb2b56fe30dc35f4` | yes | 0.1176 | 1,432.2 | 97128 | 3740 | — |
| 26 | `DOC-1e016055aa435e71` | yes | 0.2500 | 853.4 | 124347 | 5939 | — |
| 27 | `DOC-26fa94f698c37fc5` | yes | 0.0000 | 675.4 | 91761 | 4482 | — |
| 28 | `DOC-ecf69d7e102ef62a` | yes | 0.2143 | 1,530.2 | 108695 | 4967 | — |
| 29 | `DOC-2f9cf3ce009aaaf0` | yes | 0.0588 | 899.9 | 122240 | 6343 | — |
| 30 | `DOC-5c44797b6add60e4` | yes | 0.1333 | 870.6 | 92646 | 4066 | — |
| 31 | `DOC-5fa0ba13cf68b593` | yes | 0.1333 | 1,673.2 | 122413 | 6436 | — |
| 32 | `DOC-169bbcdc5d9e609c` | yes | 0.0769 | 692.3 | 153501 | 6094 | — |
| 33 | `DOC-bec74557186e9409` | yes | 0.0000 | 1,096.3 | 90748 | 5792 | — |
| 34 | `DOC-fd6090e354177e5b` | yes | 0.0556 | 766.0 | 105237 | 5145 | — |
| 35 | `DOC-fcaddb5bdc94ce63` | yes | 0.1176 | 757.7 | 94486 | 4002 | — |
| 36 | `DOC-4ab4ecd86ecf275d` | yes | 0.1250 | 1,787.2 | 223834 | 13241 | — |
| 37 | `DOC-b866e2b4f5059213` | yes | 0.2778 | 677.7 | 124671 | 5110 | — |
| 38 | `DOC-3927f91bc3daffc3` | yes | 0.1875 | 1,879.6 | 126652 | 7345 | — |
| 39 | `DOC-03712a2b0a99a314` | yes | 0.1176 | 1,102.7 | 136267 | 6124 | — |
| 40 | `DOC-2b9f668ab6cb8901` | yes | 0.0526 | 1,218.9 | 104351 | 3790 | — |
| 41 | `DOC-30eda1e78a5f6fb5` | yes | 0.1667 | 1,938.9 | 122709 | 6047 | — |
| 42 | `DOC-d5c4f12f934de48e` | yes | 0.1579 | 1,305.9 | 136741 | 7534 | — |
| 43 | `DOC-8f599c800d19fd92` | yes | 0.1333 | 2,041.5 | 92531 | 5569 | — |
| 44 | `DOC-8fe2855a2310cdbe` | yes | 0.1765 | 1,305.5 | 134602 | 7517 | — |
| 45 | `DOC-511062d64bc9afc6` | yes | 0.1875 | 2,067.4 | 111104 | 10629 | — |
| 46 | `DOC-f099c5c73d56631e` | yes | 0.0000 | 1,379.5 | 134674 | 7154 | — |
| 47 | `DOC-ab735131c00271bc` | yes | 0.1111 | 1,018.8 | 93058 | 5461 | — |
| 48 | `DOC-15f85636d1eb6b77` | yes | 0.0667 | 2,121.1 | 75525 | 4226 | — |
| 49 | `DOC-d1e355800bff0425` | yes | 0.1250 | 1,177.9 | 103125 | 8012 | — |
| 50 | `DOC-f90cc5fb2ceac154` | yes | 0.1500 | 2,264.4 | 107267 | 4219 | — |

_Generated 2026-10-01T06:44:51+00:00 by `sandbox run card`. Machine-readable twin: `sand40-50-merger-specialist-awq-2l4.card.json`._
