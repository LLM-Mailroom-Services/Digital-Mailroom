# Merger Agreements — 2× L4 · C16 · n=50

**Run:** `sand42-50-merger-specialist-awq-2l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-merger-specialist-awq-2l4-c16` |
| GPUs / replicas | 2 |
| Concurrency | 16 (8 per replica) |
| Documents | 50 |
| Spec hash | 6dc16152… |
| **Time** |  |
| Wall (busy) | 2,866.64 s |
| GPU seconds | 2,097.14 s |
| Cold boot | 0.29 s |
| **Cost** |  |
| Busy-window GPU $ | $1.274062 |
| Billed GPU $ | $0.932060 |
| Billed seconds | 2,097.14 s |
| Idle $ | $0.444105 (999.24 s) |
| Cost per document | $0.018641 |
| Cost per ok document | $0.018641 |
| Cost per 1M tokens | $0.1804 |
| **Tokens** |  |
| Prompt tokens | 4,867,606 |
| Completion tokens | 299,311 (5.8%) |
| Total tokens | 5,166,917 |
| Tokens per document | 103,338 |
| Per document: instructions + template | 6,178 (6.0%) |
| Per document: document text | 91,174 (88.2%) |
| Per document: output | 5,986 (5.8%) |
| Instruction tokens per model call | 750 over 412 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 8,626 / 9,088 |
| **Throughput** |  |
| Tokens / second | 1,802.4 |
| Tokens / second per L4 | 901.2 |
| Documents / minute | 1.05 |
| **Latency (per document, ok rows)** |  |
| Mean | 597.57 s |
| p50 | 579.44 s |
| p95 | 1,047.76 s |
| Max | 1,378.29 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 10.42× of 16 |
| Slot occupancy | 65.1% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 185 / 232 |
| Mean TTFT per replica | 3.490 s / 5.299 s |
| Prefix-cache hit per replica | 16.7% / 17.9% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 2 / 3 |
| **GPU hardware (nvidia-smi)** | 675 samples · serving-replica nvidia-smi |
| GPU utilization | 93.1 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 99.6 % |
| GPU power draw | 69.6 W (min 30.5 / max 74.2) of 72 W cap |
| GPU memory bandwidth | 74.5 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,314 MHz (min 915 / max 2,040) |
| GPU temperature | 75.6 C (min 58.0 / max 82.0) |
| GPU memory used | 21,001 MiB (min 20,997 / max 21,002) |
| **Quality** |  |
| Overall extraction score | 0.0254 (sd 0.033) |
| Score min / max | 0.0000 / 0.1333 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 280 / 811 (34.5%) |
| Micro accuracy | 2.6% |
| Precision on answered | 7.5% |
| Clean subset | 17 / 343 |
| Suite field score (mean) | not captured |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Merger Agreements run dashboard](sand42-50-merger-specialist-awq-2l4-c16.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-4f45bef14dcd1dbf` | yes | 0.0625 | 363.3 | 70774 | 3044 | — |
| 2 | `DOC-0a733ab86f2390ae` | yes | 0.0667 | 472.6 | 81545 | 4512 | — |
| 3 | `DOC-dc7f18df501aec90` | yes | 0.0667 | 483.3 | 83008 | 4460 | — |
| 4 | `DOC-eb2b56fe30dc35f4` | yes | 0.0588 | 501.8 | 85298 | 4393 | — |
| 5 | `DOC-9420b777a4b0784c` | yes | 0.0000 | 558.2 | 98627 | 5401 | — |
| 6 | `DOC-5f5d40f6b2c338ac` | yes | 0.0000 | 565.6 | 109887 | 6036 | — |
| 7 | `DOC-c96b9c7e12f91576` | yes | 0.0000 | 591.6 | 92490 | 5489 | — |
| 8 | `DOC-30eda1e78a5f6fb5` | yes | 0.0000 | 595.1 | 107499 | 5858 | — |
| 9 | `DOC-b03c0d2bbbb9659e` | yes | 0.0000 | 596.2 | 113393 | 5851 | — |
| 10 | `DOC-45f801408be08af6` | yes | 0.1333 | 647.0 | 109920 | 5874 | — |
| 11 | `DOC-71bc59dd305ee8ed` | yes | 0.0769 | 730.2 | 109675 | 8931 | — |
| 12 | `DOC-e8538f75b0f993e6` | yes | 0.0000 | 732.8 | 113280 | 7220 | — |
| 13 | `DOC-882fabf7aba36941` | yes | 0.0000 | 751.8 | 92325 | 7510 | — |
| 14 | `DOC-511062d64bc9afc6` | yes | 0.0000 | 442.3 | 97584 | 5312 | — |
| 15 | `DOC-d4b1a7a2b981fbf4` | yes | 0.0588 | 895.6 | 81817 | 8182 | — |
| 16 | `DOC-f90cc5fb2ceac154` | yes | 0.0500 | 482.6 | 93747 | 5434 | — |
| 17 | `DOC-5f8ef95caa2fd349` | yes | 0.0588 | 501.3 | 104105 | 6905 | — |
| 18 | `DOC-52f9a5be69429299` | yes | 0.0000 | 1,047.8 | 103918 | 6065 | — |
| 19 | `DOC-1e016055aa435e71` | yes | 0.0000 | 500.4 | 109137 | 7159 | — |
| 20 | `DOC-26933c93d649fa3f` | yes | 0.0000 | 1,087.1 | 96354 | 5216 | — |
| 21 | `DOC-0534799ed39ca0db` | yes | 0.0556 | 491.4 | 92828 | 6047 | — |
| 22 | `DOC-63beb09b179ea4ee` | yes | 0.0588 | 523.6 | 83572 | 5176 | — |
| 23 | `DOC-bec74557186e9409` | yes | 0.0000 | 550.4 | 78918 | 5798 | — |
| 24 | `DOC-c6b5f7ea5f718c28` | yes | 0.0588 | 367.2 | 82765 | 3793 | — |
| 25 | `DOC-72b0b8c8385edd48` | yes | 0.0000 | 389.7 | 84431 | 4977 | — |
| 26 | `DOC-2b9f668ab6cb8901` | yes | 0.0526 | 567.3 | 90831 | 5263 | — |
| 27 | `DOC-fe9a8b51344d67d9` | yes | 0.0000 | 710.3 | 130099 | 7211 | — |
| 28 | `DOC-37bc3c44ae2c4ef6` | yes | 0.0000 | 674.1 | 90012 | 6633 | — |
| 29 | `DOC-297745a521cd1e8c` | yes | 0.0000 | 598.8 | 103150 | 7034 | — |
| 30 | `DOC-386ac6d669b7731c` | yes | 0.0000 | 647.3 | 93831 | 5593 | — |
| 31 | `DOC-9d34581755c603a3` | yes | 0.0000 | 440.6 | 94942 | 4304 | — |
| 32 | `DOC-26fa94f698c37fc5` | yes | 0.0588 | 607.8 | 79931 | 5939 | — |
| 33 | `DOC-7e2818ceb0167d5a` | yes | 0.0000 | 675.5 | 78432 | 7566 | — |
| 34 | `DOC-fcaddb5bdc94ce63` | yes | 0.0588 | 617.0 | 82656 | 6019 | — |
| 35 | `DOC-1cd38a83b224335d` | yes | 0.0000 | 409.4 | 78294 | 3592 | — |
| 36 | `DOC-ab735131c00271bc` | yes | 0.0556 | 397.5 | 81228 | 3898 | — |
| 37 | `DOC-ac48214468deb8dd` | yes | 0.0588 | 613.3 | 72887 | 6544 | — |
| 38 | `DOC-0070a4e34dddbfd5` | yes | 0.0000 | 650.8 | 85209 | 6368 | — |
| 39 | `DOC-e6c8852b877c4598` | yes | 0.0556 | 625.1 | 104093 | 6755 | — |
| 40 | `DOC-f449b47c7269f288` | yes | 0.0625 | 335.8 | 95394 | 4346 | — |
| 41 | `DOC-b3d0149fd994357a` | yes | 0.0000 | 510.0 | 78500 | 5472 | — |
| 42 | `DOC-f9870e3b8fd141b0` | yes | 0.0000 | 792.0 | 134889 | 8626 | — |
| 43 | `DOC-ab5578f1f9f04244` | yes | 0.0000 | 1,378.3 | 132059 | 8245 | — |
| 44 | `DOC-169bbcdc5d9e609c` | yes | 0.0000 | 667.1 | 134911 | 9088 | — |
| 45 | `DOC-f09307ad314d386f` | yes | 0.0000 | 399.3 | 103329 | 5958 | — |
| 46 | `DOC-ff3ceb691481f1bd` | yes | 0.0000 | 318.2 | 91432 | 5343 | — |
| 47 | `DOC-23f224263f6974c5` | yes | 0.0000 | 279.6 | 83736 | 5269 | — |
| 48 | `DOC-681bc6115b882191` | yes | 0.0000 | 330.1 | 120554 | 5735 | — |
| 49 | `DOC-03712a2b0a99a314` | yes | 0.0000 | 1,013.6 | 119367 | 6279 | — |
| 50 | `DOC-5d30efc302f3c431` | yes | 0.0625 | 750.8 | 130943 | 7588 | — |

_Generated 2026-10-13T04:33:05+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-merger-specialist-awq-2l4-c16.card.json`._
