# Merger Agreements — 2× L4 · C32 · n=50

**Run:** `sand42-50-merger-specialist-awq-2l4-c32` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-merger-specialist-awq-2l4-c32` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | a96e6fbc… |
| **Time** |  |
| Wall (busy) | 1,972.33 s |
| GPU seconds | 1,939.24 s |
| Cold boot | 0.52 s |
| **Cost** |  |
| Busy-window GPU $ | $0.876590 |
| Billed GPU $ | $0.861885 |
| Billed seconds | 1,939.24 s |
| Idle $ | $0.215793 (485.53 s) |
| Cost per document | $0.017238 |
| Cost per ok document | $0.017238 |
| Cost per 1M tokens | $0.1660 |
| **Tokens** |  |
| Prompt tokens | 4,867,606 |
| Completion tokens | 323,439 (6.2%) |
| Total tokens | 5,191,045 |
| Tokens per document | 103,821 |
| Per document: instructions + template | 6,178 (6.0%) |
| Per document: document text | 91,174 (87.8%) |
| Per document: output | 6,469 (6.2%) |
| Instruction tokens per model call | 750 over 412 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 10,698 / 12,533 |
| **Throughput** |  |
| Tokens / second | 2,631.9 |
| Tokens / second per L4 | 1,316.0 |
| Documents / minute | 1.52 |
| **Latency (per document, ok rows)** |  |
| Mean | 951.55 s |
| p50 | 935.46 s |
| p95 | 1,491.48 s |
| Max | 1,630.02 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 24.12× of 32 |
| Slot occupancy | 75.4% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 207 / 209 |
| Mean TTFT per replica | 12.094 s / 8.542 s |
| Prefix-cache hit per replica | 16.8% / 18.0% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 2 / 2 |
| **GPU hardware (nvidia-smi)** | 588 samples · serving-replica nvidia-smi |
| GPU utilization | 95.1 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 99.2 % |
| GPU power draw | 70.1 W (min 28.6 / max 73.7) of 72 W cap |
| GPU memory bandwidth | 73.5 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,296 MHz (min 945 / max 2,040) |
| GPU temperature | 75.9 C (min 46.0 / max 85.0) |
| GPU memory used | 21,026 MiB (min 21,026 / max 21,026) |
| **Quality** |  |
| Overall extraction score | 0.0209 (sd 0.029) |
| Score min / max | 0.0000 / 0.0769 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 260 / 811 (32.1%) |
| Micro accuracy | 2.1% |
| Precision on answered | 6.5% |
| Clean subset | 16 / 343 |
| Suite field score (mean) | not captured |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Merger Agreements run dashboard](sand42-50-merger-specialist-awq-2l4-c32.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-26933c93d649fa3f` | yes | 0.0625 | 575.6 | 96354 | 3350 | — |
| 2 | `DOC-eb2b56fe30dc35f4` | yes | 0.0000 | 715.2 | 85298 | 4537 | — |
| 3 | `DOC-dc7f18df501aec90` | yes | 0.0000 | 715.4 | 83008 | 4374 | — |
| 4 | `DOC-63beb09b179ea4ee` | yes | 0.0588 | 743.8 | 83572 | 4931 | — |
| 5 | `DOC-4f45bef14dcd1dbf` | yes | 0.0625 | 751.9 | 70774 | 3881 | — |
| 6 | `DOC-bec74557186e9409` | yes | 0.0000 | 798.3 | 78918 | 5295 | — |
| 7 | `DOC-511062d64bc9afc6` | yes | 0.0000 | 822.0 | 97584 | 4954 | — |
| 8 | `DOC-72b0b8c8385edd48` | yes | 0.0000 | 840.3 | 84431 | 5131 | — |
| 9 | `DOC-7e2818ceb0167d5a` | yes | 0.0556 | 884.1 | 78432 | 5022 | — |
| 10 | `DOC-0534799ed39ca0db` | yes | 0.0556 | 931.0 | 92828 | 5876 | — |
| 11 | `DOC-1e016055aa435e71` | yes | 0.0000 | 939.9 | 109137 | 6060 | — |
| 12 | `DOC-2b9f668ab6cb8901` | yes | 0.0526 | 969.0 | 90831 | 5361 | — |
| 13 | `DOC-37bc3c44ae2c4ef6` | yes | 0.0000 | 978.1 | 90012 | 5687 | — |
| 14 | `DOC-5f5d40f6b2c338ac` | yes | 0.0000 | 989.7 | 109887 | 6851 | — |
| 15 | `DOC-9420b777a4b0784c` | yes | 0.0000 | 1,025.8 | 98627 | 6406 | — |
| 16 | `DOC-30eda1e78a5f6fb5` | yes | 0.0000 | 1,039.4 | 107499 | 5905 | — |
| 17 | `DOC-386ac6d669b7731c` | yes | 0.0769 | 1,051.8 | 93831 | 5997 | — |
| 18 | `DOC-e8538f75b0f993e6` | yes | 0.0000 | 1,070.4 | 113280 | 6492 | — |
| 19 | `DOC-882fabf7aba36941` | yes | 0.0000 | 1,082.1 | 92325 | 6292 | — |
| 20 | `DOC-d4b1a7a2b981fbf4` | yes | 0.0000 | 1,097.5 | 81817 | 6520 | — |
| 21 | `DOC-5f8ef95caa2fd349` | yes | 0.0000 | 1,126.0 | 104105 | 7488 | — |
| 22 | `DOC-71bc59dd305ee8ed` | yes | 0.0769 | 1,134.9 | 109675 | 6972 | — |
| 23 | `DOC-45f801408be08af6` | yes | 0.0000 | 1,177.9 | 109920 | 6735 | — |
| 24 | `DOC-b03c0d2bbbb9659e` | yes | 0.0000 | 1,179.4 | 113393 | 7114 | — |
| 25 | `DOC-297745a521cd1e8c` | yes | 0.0000 | 1,314.5 | 103150 | 8886 | — |
| 26 | `DOC-ab5578f1f9f04244` | yes | 0.0000 | 1,339.5 | 132059 | 8481 | — |
| 27 | `DOC-26fa94f698c37fc5` | yes | 0.0588 | 630.9 | 79931 | 4932 | — |
| 28 | `DOC-c6b5f7ea5f718c28` | yes | 0.0588 | 1,366.3 | 82765 | 8948 | — |
| 29 | `DOC-52f9a5be69429299` | yes | 0.0000 | 1,381.3 | 103918 | 9635 | — |
| 30 | `DOC-fcaddb5bdc94ce63` | yes | 0.0588 | 689.9 | 82656 | 4668 | — |
| 31 | `DOC-0a733ab86f2390ae` | yes | 0.0667 | 1,490.0 | 81545 | 4595 | — |
| 32 | `DOC-c96b9c7e12f91576` | yes | 0.0000 | 1,491.5 | 92490 | 10698 | — |
| 33 | `DOC-9d34581755c603a3` | yes | 0.0000 | 652.2 | 94942 | 4530 | — |
| 34 | `DOC-b3d0149fd994357a` | yes | 0.0588 | 583.3 | 78500 | 4951 | — |
| 35 | `DOC-ab735131c00271bc` | yes | 0.0000 | 568.8 | 81228 | 4608 | — |
| 36 | `DOC-ac48214468deb8dd` | yes | 0.0000 | 745.3 | 72887 | 5864 | — |
| 37 | `DOC-1cd38a83b224335d` | yes | 0.0588 | 626.2 | 78294 | 4974 | — |
| 38 | `DOC-169bbcdc5d9e609c` | yes | 0.0000 | 687.2 | 134911 | 6038 | — |
| 39 | `DOC-fe9a8b51344d67d9` | yes | 0.0000 | 1,577.9 | 130099 | 10957 | — |
| 40 | `DOC-e6c8852b877c4598` | yes | 0.0556 | 792.5 | 104093 | 6485 | — |
| 41 | `DOC-f90cc5fb2ceac154` | yes | 0.0000 | 1,630.0 | 93747 | 5823 | — |
| 42 | `DOC-681bc6115b882191` | yes | 0.0000 | 600.3 | 120554 | 6170 | — |
| 43 | `DOC-ff3ceb691481f1bd` | yes | 0.0000 | 613.2 | 91432 | 6404 | — |
| 44 | `DOC-f9870e3b8fd141b0` | yes | 0.0000 | 941.0 | 134889 | 8014 | — |
| 45 | `DOC-f449b47c7269f288` | yes | 0.0625 | 682.5 | 95394 | 7002 | — |
| 46 | `DOC-23f224263f6974c5` | yes | 0.0000 | 625.2 | 83736 | 6817 | — |
| 47 | `DOC-f09307ad314d386f` | yes | 0.0000 | 727.0 | 103329 | 8452 | — |
| 48 | `DOC-5d30efc302f3c431` | yes | 0.0625 | 785.5 | 130943 | 9253 | — |
| 49 | `DOC-0070a4e34dddbfd5` | yes | 0.0000 | 1,049.7 | 85209 | 6490 | — |
| 50 | `DOC-03712a2b0a99a314` | yes | 0.0000 | 1,346.2 | 119367 | 12533 | — |

_Generated 2026-10-13T04:33:11+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-merger-specialist-awq-2l4-c32.card.json`._
