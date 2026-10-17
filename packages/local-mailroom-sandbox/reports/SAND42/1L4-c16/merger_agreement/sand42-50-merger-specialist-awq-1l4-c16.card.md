# Merger Agreements — 1× L4 · C16 · n=50

**Run:** `sand42-50-merger-specialist-awq-1l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | merger_agreement_specialist |
| Prompt | merger_agreement_specialist_simplified |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 6,144 |
| Input cap (max_input_chars) | 54,000 |
| top_p | 0.8 |
| top_k | 20 |
| presence_penalty | 1.0 |
| Length re-samples | 1 |
| Chunk window (chars) | 47000 |
| Chunk overlap (chars) | 6500 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 50 docs (fingerprint aa4e596805e7) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand42-50-merger-specialist-awq-1l4-c16` |
| GPUs / replicas | 1 |
| Concurrency | 16 (16 per replica) |
| Documents | 50 |
| Spec hash | 29ddbe9d… |
| **Time** |  |
| Wall (busy) | 4,098.52 s |
| GPU seconds | 3,608.19 s |
| Cold boot | 0.32 s |
| **Cost** |  |
| Busy-window GPU $ | $0.910783 |
| Billed GPU $ | $0.801821 |
| Billed seconds | 3,608.19 s |
| Idle $ | $0.168615 (758.77 s) |
| Cost per document | $0.016036 |
| Cost per ok document | $0.016036 |
| Cost per 1M tokens | $0.1554 |
| **Tokens** |  |
| Prompt tokens | 4,867,606 |
| Completion tokens | 291,690 (5.7%) |
| Total tokens | 5,159,296 |
| Tokens per document | 103,186 |
| Per document: instructions + template | 6,178 (6.0%) |
| Per document: document text | 91,174 (88.4%) |
| Per document: output | 5,834 (5.7%) |
| Instruction tokens per model call | 750 over 412 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 8,957 / 10,084 |
| **Throughput** |  |
| Tokens / second | 1,258.8 |
| Tokens / second per L4 | 1,258.8 |
| Documents / minute | 0.73 |
| **Latency (per document, ok rows)** |  |
| Mean | 1,068.72 s |
| p50 | 948.69 s |
| p95 | 1,917.93 s |
| Max | 2,323.52 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 13.04× of 16 |
| Slot occupancy | 81.5% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 182 |
| Mean TTFT per replica | 7.252 s |
| Prefix-cache hit per replica | 12.5% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 2 |
| **GPU hardware (nvidia-smi)** | 552 samples · serving-replica nvidia-smi |
| GPU utilization | 98.8 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 93.1 % |
| GPU power draw | 71.8 W (min 27.4 / max 74.1) of 72 W cap |
| GPU memory bandwidth | 75.8 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,254 MHz (min 915 / max 2,040) |
| GPU temperature | 73.9 C (min 36.0 / max 81.0) |
| GPU memory used | 21,025 MiB (min 20,790 / max 21,026) |
| **Quality** |  |
| Overall extraction score | 0.0276 (sd 0.041) |
| Score min / max | 0.0000 / 0.1765 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 286 / 811 (35.3%) |
| Micro accuracy | 2.8% |
| Precision on answered | 8.0% |
| Clean subset | 16 / 343 |
| Suite field score (mean) | not captured |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Merger Agreements run dashboard](sand42-50-merger-specialist-awq-1l4-c16.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-dc7f18df501aec90` | yes | 0.0000 | 625.3 | 83008 | 3181 | — |
| 2 | `DOC-4f45bef14dcd1dbf` | yes | 0.0625 | 734.3 | 70774 | 3876 | — |
| 3 | `DOC-26933c93d649fa3f` | yes | 0.0625 | 766.5 | 96354 | 4055 | — |
| 4 | `DOC-eb2b56fe30dc35f4` | yes | 0.0588 | 775.3 | 85298 | 4089 | — |
| 5 | `DOC-c96b9c7e12f91576` | yes | 0.0000 | 840.9 | 92490 | 4582 | — |
| 6 | `DOC-b03c0d2bbbb9659e` | yes | 0.0556 | 898.8 | 113393 | 4893 | — |
| 7 | `DOC-5f5d40f6b2c338ac` | yes | 0.0000 | 939.0 | 109887 | 5186 | — |
| 8 | `DOC-d4b1a7a2b981fbf4` | yes | 0.0588 | 950.3 | 81817 | 5265 | — |
| 9 | `DOC-71bc59dd305ee8ed` | yes | 0.0769 | 968.1 | 109675 | 5281 | — |
| 10 | `DOC-45f801408be08af6` | yes | 0.0000 | 1,072.2 | 109920 | 6020 | — |
| 11 | `DOC-30eda1e78a5f6fb5` | yes | 0.0000 | 1,182.7 | 107499 | 6709 | — |
| 12 | `DOC-52f9a5be69429299` | yes | 0.0000 | 1,237.6 | 103918 | 7035 | — |
| 13 | `DOC-882fabf7aba36941` | yes | 0.0000 | 1,258.2 | 92325 | 7192 | — |
| 14 | `DOC-511062d64bc9afc6` | yes | 0.0000 | 745.5 | 97584 | 4689 | — |
| 15 | `DOC-e8538f75b0f993e6` | yes | 0.0000 | 1,575.2 | 113280 | 9359 | — |
| 16 | `DOC-f90cc5fb2ceac154` | yes | 0.0000 | 821.8 | 93747 | 5365 | — |
| 17 | `DOC-1e016055aa435e71` | yes | 0.0000 | 793.7 | 109137 | 5044 | — |
| 18 | `DOC-bec74557186e9409` | yes | 0.0000 | 747.7 | 78918 | 4797 | — |
| 19 | `DOC-ab5578f1f9f04244` | yes | 0.0000 | 964.2 | 132059 | 6174 | — |
| 20 | `DOC-63beb09b179ea4ee` | yes | 0.0588 | 804.3 | 83572 | 5196 | — |
| 21 | `DOC-0534799ed39ca0db` | yes | 0.0556 | 856.0 | 92828 | 5611 | — |
| 22 | `DOC-5f8ef95caa2fd349` | yes | 0.0588 | 1,066.5 | 104105 | 6919 | — |
| 23 | `DOC-9420b777a4b0784c` | yes | 0.0000 | 2,220.5 | 98627 | 5499 | — |
| 24 | `DOC-0a733ab86f2390ae` | yes | 0.0667 | 2,323.5 | 81545 | 6494 | — |
| 25 | `DOC-2b9f668ab6cb8901` | yes | 0.0526 | 1,316.9 | 90831 | 6649 | — |
| 26 | `DOC-37bc3c44ae2c4ef6` | yes | 0.0000 | 1,459.0 | 90012 | 7127 | — |
| 27 | `DOC-fe9a8b51344d67d9` | yes | 0.0000 | 1,583.6 | 130099 | 7714 | — |
| 28 | `DOC-297745a521cd1e8c` | yes | 0.0000 | 1,325.4 | 103150 | 6797 | — |
| 29 | `DOC-386ac6d669b7731c` | yes | 0.0769 | 1,274.7 | 93831 | 6516 | — |
| 30 | `DOC-26fa94f698c37fc5` | yes | 0.0000 | 1,043.9 | 79931 | 4331 | — |
| 31 | `DOC-72b0b8c8385edd48` | yes | 0.0556 | 1,135.6 | 84431 | 5272 | — |
| 32 | `DOC-ac48214468deb8dd` | yes | 0.0000 | 926.5 | 72887 | 3883 | — |
| 33 | `DOC-fcaddb5bdc94ce63` | yes | 0.0588 | 1,043.9 | 82656 | 4955 | — |
| 34 | `DOC-c6b5f7ea5f718c28` | yes | 0.0000 | 1,562.0 | 82765 | 6661 | — |
| 35 | `DOC-9d34581755c603a3` | yes | 0.0000 | 669.4 | 94942 | 4264 | — |
| 36 | `DOC-03712a2b0a99a314` | yes | 0.0588 | 1,381.5 | 119367 | 6932 | — |
| 37 | `DOC-1cd38a83b224335d` | yes | 0.0000 | 631.6 | 78294 | 4103 | — |
| 38 | `DOC-b3d0149fd994357a` | yes | 0.0000 | 667.9 | 78500 | 4416 | — |
| 39 | `DOC-f9870e3b8fd141b0` | yes | 0.0000 | 1,501.7 | 134889 | 6921 | — |
| 40 | `DOC-ab735131c00271bc` | yes | 0.0556 | 725.4 | 81228 | 5141 | — |
| 41 | `DOC-f449b47c7269f288` | yes | 0.0625 | 600.0 | 95394 | 4266 | — |
| 42 | `DOC-169bbcdc5d9e609c` | yes | 0.0000 | 855.5 | 134911 | 6240 | — |
| 43 | `DOC-ff3ceb691481f1bd` | yes | 0.0000 | 619.2 | 91432 | 4853 | — |
| 44 | `DOC-0070a4e34dddbfd5` | yes | 0.1765 | 1,565.1 | 85209 | 8957 | — |
| 45 | `DOC-f09307ad314d386f` | yes | 0.0000 | 726.7 | 103329 | 5927 | — |
| 46 | `DOC-23f224263f6974c5` | yes | 0.0000 | 658.6 | 83736 | 6172 | — |
| 47 | `DOC-7e2818ceb0167d5a` | yes | 0.1667 | 1,917.9 | 78432 | 6476 | — |
| 48 | `DOC-681bc6115b882191` | yes | 0.0000 | 756.1 | 120554 | 7662 | — |
| 49 | `DOC-5d30efc302f3c431` | yes | 0.0000 | 947.0 | 130943 | 10084 | — |
| 50 | `DOC-e6c8852b877c4598` | yes | 0.0000 | 1,372.8 | 104093 | 6860 | — |

_Generated 2026-10-13T04:32:52+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-merger-specialist-awq-1l4-c16.card.json`._
