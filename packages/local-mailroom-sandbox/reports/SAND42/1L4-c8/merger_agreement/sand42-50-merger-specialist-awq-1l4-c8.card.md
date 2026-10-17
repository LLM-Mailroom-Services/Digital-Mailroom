# Merger Agreements — 1× L4 · C8 · n=50

**Run:** `sand42-50-merger-specialist-awq-1l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-merger-specialist-awq-1l4-c8` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | d573b8a9… |
| **Time** |  |
| Wall (busy) | 4,657.53 s |
| GPU seconds | 4,483.58 s |
| Cold boot | 0.30 s |
| **Cost** |  |
| Busy-window GPU $ | $1.035006 |
| Billed GPU $ | $0.996352 |
| Billed seconds | 4,483.58 s |
| Idle $ | $0.139893 (629.52 s) |
| Cost per document | $0.019927 |
| Cost per ok document | $0.019927 |
| Cost per 1M tokens | $0.1921 |
| **Tokens** |  |
| Prompt tokens | 4,867,606 |
| Completion tokens | 318,047 (6.1%) |
| Total tokens | 5,185,653 |
| Tokens per document | 103,713 |
| Per document: instructions + template | 6,178 (6.0%) |
| Per document: document text | 91,174 (87.9%) |
| Per document: output | 6,361 (6.1%) |
| Instruction tokens per model call | 750 over 412 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 9,310 / 16,821 |
| **Throughput** |  |
| Tokens / second | 1,113.4 |
| Tokens / second per L4 | 1,113.4 |
| Documents / minute | 0.64 |
| **Latency (per document, ok rows)** |  |
| Mean | 644.48 s |
| p50 | 547.44 s |
| p95 | 1,370.22 s |
| Max | 1,477.39 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 6.92× of 8 |
| Slot occupancy | 86.5% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 422 |
| Mean TTFT per replica | 3.773 s |
| Prefix-cache hit per replica | 19.6% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 4 |
| **GPU hardware (nvidia-smi)** | 747 samples · serving-replica nvidia-smi |
| GPU utilization | 88.7 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 99.9 % |
| GPU power draw | 67.5 W (min 28.1 / max 74.7) of 72 W cap |
| GPU memory bandwidth | 70.8 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,368 MHz (min 945 / max 2,040) |
| GPU temperature | 73.9 C (min 48.0 / max 84.0) |
| GPU memory used | 21,028 MiB (min 21,028 / max 21,028) |
| **Quality** |  |
| Overall extraction score | 0.0273 (sd 0.041) |
| Score min / max | 0.0000 / 0.2000 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 302 / 811 (37.2%) |
| Micro accuracy | 2.7% |
| Precision on answered | 7.3% |
| Clean subset | 19 / 343 |
| Suite field score (mean) | not captured |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Merger Agreements run dashboard](sand42-50-merger-specialist-awq-1l4-c8.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-5f5d40f6b2c338ac` | yes | 0.0000 | 400.5 | 109887 | 3890 | — |
| 2 | `DOC-d4b1a7a2b981fbf4` | yes | 0.0000 | 405.8 | 81817 | 4011 | — |
| 3 | `DOC-26933c93d649fa3f` | yes | 0.0625 | 472.0 | 96354 | 4723 | — |
| 4 | `DOC-45f801408be08af6` | yes | 0.0000 | 495.6 | 109920 | 5035 | — |
| 5 | `DOC-c96b9c7e12f91576` | yes | 0.0000 | 533.4 | 92490 | 5596 | — |
| 6 | `DOC-eb2b56fe30dc35f4` | yes | 0.0000 | 540.3 | 85298 | 5695 | — |
| 7 | `DOC-dc7f18df501aec90` | yes | 0.1333 | 549.0 | 83008 | 5788 | — |
| 8 | `DOC-0a733ab86f2390ae` | yes | 0.0000 | 576.1 | 81545 | 6082 | — |
| 9 | `DOC-4f45bef14dcd1dbf` | yes | 0.0625 | 398.8 | 70774 | 4526 | — |
| 10 | `DOC-9420b777a4b0784c` | yes | 0.0000 | 566.3 | 98627 | 6586 | — |
| 11 | `DOC-b03c0d2bbbb9659e` | yes | 0.0000 | 562.8 | 113393 | 6560 | — |
| 12 | `DOC-71bc59dd305ee8ed` | yes | 0.0769 | 539.1 | 109675 | 6153 | — |
| 13 | `DOC-e8538f75b0f993e6` | yes | 0.0000 | 545.9 | 113280 | 6287 | — |
| 14 | `DOC-882fabf7aba36941` | yes | 0.0000 | 556.6 | 92325 | 6383 | — |
| 15 | `DOC-30eda1e78a5f6fb5` | yes | 0.0000 | 564.5 | 107499 | 6456 | — |
| 16 | `DOC-52f9a5be69429299` | yes | 0.0000 | 783.5 | 103918 | 9106 | — |
| 17 | `DOC-ab5578f1f9f04244` | yes | 0.2000 | 465.5 | 132059 | 5157 | — |
| 18 | `DOC-f90cc5fb2ceac154` | yes | 0.0000 | 439.9 | 93747 | 4994 | — |
| 19 | `DOC-bec74557186e9409` | yes | 0.0000 | 464.9 | 78918 | 5436 | — |
| 20 | `DOC-1e016055aa435e71` | yes | 0.0000 | 581.9 | 109137 | 6679 | — |
| 21 | `DOC-5f8ef95caa2fd349` | yes | 0.0000 | 718.2 | 104105 | 8146 | — |
| 22 | `DOC-fe9a8b51344d67d9` | yes | 0.0000 | 626.6 | 130099 | 6935 | — |
| 23 | `DOC-511062d64bc9afc6` | yes | 0.0000 | 969.9 | 97584 | 5378 | — |
| 24 | `DOC-0534799ed39ca0db` | yes | 0.0556 | 420.2 | 92828 | 4697 | — |
| 25 | `DOC-63beb09b179ea4ee` | yes | 0.0000 | 807.4 | 83572 | 8778 | — |
| 26 | `DOC-37bc3c44ae2c4ef6` | yes | 0.0000 | 570.9 | 90012 | 6405 | — |
| 27 | `DOC-c6b5f7ea5f718c28` | yes | 0.0588 | 407.5 | 82765 | 4944 | — |
| 28 | `DOC-72b0b8c8385edd48` | yes | 0.0556 | 410.9 | 84431 | 4972 | — |
| 29 | `DOC-297745a521cd1e8c` | yes | 0.0000 | 594.0 | 103150 | 6973 | — |
| 30 | `DOC-2b9f668ab6cb8901` | yes | 0.0526 | 723.1 | 90831 | 8406 | — |
| 31 | `DOC-7e2818ceb0167d5a` | yes | 0.0556 | 533.2 | 78432 | 6421 | — |
| 32 | `DOC-26fa94f698c37fc5` | yes | 0.0588 | 380.6 | 79931 | 4539 | — |
| 33 | `DOC-386ac6d669b7731c` | yes | 0.0769 | 1,306.2 | 93831 | 8926 | — |
| 34 | `DOC-fcaddb5bdc94ce63` | yes | 0.0588 | 961.1 | 82656 | 5028 | — |
| 35 | `DOC-0070a4e34dddbfd5` | yes | 0.0000 | 1,043.9 | 85209 | 6587 | — |
| 36 | `DOC-03712a2b0a99a314` | yes | 0.0588 | 1,421.4 | 119367 | 6301 | — |
| 37 | `DOC-ac48214468deb8dd` | yes | 0.0588 | 1,103.0 | 72887 | 6372 | — |
| 38 | `DOC-9d34581755c603a3` | yes | 0.0000 | 972.0 | 94942 | 4427 | — |
| 39 | `DOC-b3d0149fd994357a` | yes | 0.0000 | 332.7 | 78500 | 3800 | — |
| 40 | `DOC-f9870e3b8fd141b0` | yes | 0.0000 | 1,370.2 | 134889 | 7124 | — |
| 41 | `DOC-ab735131c00271bc` | yes | 0.0556 | 386.4 | 81228 | 4726 | — |
| 42 | `DOC-1cd38a83b224335d` | yes | 0.0588 | 457.0 | 78294 | 5507 | — |
| 43 | `DOC-f449b47c7269f288` | yes | 0.0625 | 376.3 | 95394 | 4436 | — |
| 44 | `DOC-169bbcdc5d9e609c` | yes | 0.0000 | 726.9 | 134911 | 8536 | — |
| 45 | `DOC-e6c8852b877c4598` | yes | 0.0000 | 1,477.4 | 104093 | 10821 | — |
| 46 | `DOC-ff3ceb691481f1bd` | yes | 0.0000 | 410.0 | 91432 | 5729 | — |
| 47 | `DOC-f09307ad314d386f` | yes | 0.0000 | 461.5 | 103329 | 6672 | — |
| 48 | `DOC-23f224263f6974c5` | yes | 0.0000 | 297.1 | 83736 | 5187 | — |
| 49 | `DOC-681bc6115b882191` | yes | 0.0000 | 444.2 | 120554 | 9310 | — |
| 50 | `DOC-5d30efc302f3c431` | yes | 0.0625 | 1,071.9 | 130943 | 16821 | — |

_Generated 2026-10-13T04:32:46+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-merger-specialist-awq-1l4-c8.card.json`._
