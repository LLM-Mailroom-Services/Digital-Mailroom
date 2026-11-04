# Correspondence — 2× L4 · C16 · n=50

**Run:** `sand42-50-correspondence-specialist-awq-2l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | correspondence_specialist |
| Prompt | correspondence_specialist_simplified |
| Temperature | 0.1 (vendored call site) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 12,000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 50 docs (fingerprint a00ba5dc0159) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand42-50-correspondence-specialist-awq-2l4-c16` |
| GPUs / replicas | 2 |
| Concurrency | 16 (8 per replica) |
| Documents | 50 |
| Spec hash | 49141e59… |
| **Time** |  |
| Wall (busy) | 40.76 s |
| GPU seconds | 42.54 s |
| Cold boot | 0.32 s |
| **Cost** |  |
| Busy-window GPU $ | $0.018116 |
| Billed GPU $ | $0.018907 |
| Billed seconds | 42.54 s |
| Idle $ | $0.007220 (16.24 s) |
| Cost per document | $0.000378 |
| Cost per ok document | $0.000378 |
| Cost per 1M tokens | $0.1377 |
| **Tokens** |  |
| Prompt tokens | 129,444 |
| Completion tokens | 7,845 (5.7%) |
| Total tokens | 137,289 |
| Tokens per document | 2,746 |
| Per document: instructions + template | 2,241 (81.6%) |
| Per document: document text | 348 (12.7%) |
| Per document: output | 157 (5.7%) |
| Instruction tokens per model call | 2,241 over 50 calls |
| Token split basis | fit across documents, 4.38 chars/token |
| Completion p95 / max (ok docs) | 223 / 231 |
| **Throughput** |  |
| Tokens / second | 3,368.2 |
| Tokens / second per L4 | 1,684.1 |
| Documents / minute | 73.60 |
| **Latency (per document, ok rows)** |  |
| Mean | 7.85 s |
| p50 | 6.90 s |
| p95 | 13.32 s |
| Max | 13.47 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 9.62× of 16 |
| Slot occupancy | 60.1% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 18 / 32 |
| Mean TTFT per replica | 0.376 s / 2.215 s |
| Prefix-cache hit per replica | 63.3% / 61.7% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 12 samples · serving-replica nvidia-smi |
| GPU utilization | 64.5 % mean (p95 98.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 58.1 W (min 29.8 / max 72.8) of 72 W cap |
| GPU memory bandwidth | 62.3 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,682 MHz (min 1,095 / max 2,040) |
| GPU temperature | 58.7 C (min 50.0 / max 66.0) |
| GPU memory used | 20,996 MiB (min 20,996 / max 20,997) |
| **Quality** |  |
| Overall extraction score | 0.3899 (sd 0.249) |
| Score min / max | 0.0278 / 0.8611 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Correspondence run dashboard](sand42-50-correspondence-specialist-awq-2l4-c16.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-bcc74152bde91996` | yes | 0.8095 | 4.7 | 2211 | 121 | — |
| 2 | `DOC-2a7acfac00e67bac` | yes | 0.0278 | 10.0 | 2256 | 120 | — |
| 3 | `DOC-3433644b29e318b3` | yes | 0.4967 | 10.0 | 2311 | 123 | — |
| 4 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 10.2 | 2310 | 128 | — |
| 5 | `DOC-a21b03af9a6afc21` | yes | 0.8246 | 10.2 | 2412 | 130 | — |
| 6 | `DOC-3c85eb56a4145e0c` | yes | 0.7143 | 10.3 | 2357 | 134 | — |
| 7 | `DOC-6bdc0c7c153547b6` | yes | 0.6147 | 5.7 | 2480 | 224 | — |
| 8 | `DOC-fcab49d5955c76c0` | yes | 0.0606 | 10.6 | 2332 | 136 | — |
| 9 | `DOC-275198e372250586` | yes | 0.1587 | 11.6 | 2880 | 151 | — |
| 10 | `DOC-8ca6802d3a0f5d1a` | yes | 0.8148 | 11.7 | 3289 | 153 | — |
| 11 | `DOC-1de496e8c9350155` | yes | 0.3696 | 11.8 | 2314 | 153 | — |
| 12 | `DOC-0dfd9710f2380220` | yes | 0.2050 | 12.3 | 2367 | 169 | — |
| 13 | `DOC-d9937f535b7c22f3` | yes | 0.3333 | 12.5 | 2447 | 173 | — |
| 14 | `DOC-b7f699fd18d0f80c` | yes | 0.5185 | 13.2 | 2731 | 189 | — |
| 15 | `DOC-fc6108235411ca8e` | yes | 0.0606 | 13.3 | 2465 | 198 | — |
| 16 | `DOC-3a21b2695c19d388` | yes | 0.0952 | 13.4 | 2766 | 199 | — |
| 17 | `DOC-af2b2b54e31214cc` | yes | 0.3636 | 13.5 | 2822 | 202 | — |
| 18 | `DOC-e7b6158bfb232964` | yes | 0.5000 | 4.8 | 2246 | 115 | — |
| 19 | `DOC-ede2172372d1f296` | yes | 0.1111 | 5.6 | 2282 | 140 | — |
| 20 | `DOC-4fa7aa63b169fea8` | yes | 0.3333 | 5.3 | 2523 | 142 | — |
| 21 | `DOC-5cdfee2b0ef0a218` | yes | 0.5362 | 6.4 | 2263 | 156 | — |
| 22 | `DOC-8674660f9ccc8243` | yes | 0.5362 | 5.3 | 2377 | 142 | — |
| 23 | `DOC-bdf1d75db5874068` | yes | 0.7778 | 6.8 | 2839 | 167 | — |
| 24 | `DOC-25958c023112a96e` | yes | 0.6667 | 6.9 | 2242 | 172 | — |
| 25 | `DOC-ba3217c0524a9577` | yes | 0.6667 | 4.8 | 2368 | 132 | — |
| 26 | `DOC-4ea9a8cde42f450b` | yes | 0.4667 | 6.2 | 2309 | 152 | — |
| 27 | `DOC-5cef7d1205cc37d5` | yes | 0.1945 | 6.2 | 2581 | 150 | — |
| 28 | `DOC-b78953fa896bdeb9` | yes | 0.5754 | 6.9 | 2441 | 172 | — |
| 29 | `DOC-38a7cb4be93dbecd` | yes | 0.7407 | 8.8 | 2625 | 231 | — |
| 30 | `DOC-9417d989cb45b287` | yes | 0.0556 | 3.8 | 2212 | 89 | — |
| 31 | `DOC-3fd5fb2e4b505b04` | yes | 0.7647 | 6.9 | 2584 | 184 | — |
| 32 | `DOC-80c4ee15e95f8cc6` | yes | 0.0494 | 7.0 | 2631 | 166 | — |
| 33 | `DOC-8b2609c15d1d37af` | yes | 0.4286 | 7.4 | 2604 | 204 | — |
| 34 | `DOC-44dd971367dd458a` | yes | 0.6222 | 4.5 | 2298 | 113 | — |
| 35 | `DOC-a7e5e24fade86aae` | yes | 0.4545 | 6.4 | 3230 | 158 | — |
| 36 | `DOC-315b7ca63910e311` | yes | 0.1939 | 10.2 | 2607 | 223 | — |
| 37 | `DOC-65c30d7452215c4b` | yes | 0.1333 | 7.1 | 2272 | 131 | — |
| 38 | `DOC-f64e409a607594bb` | yes | 0.1768 | 3.8 | 2264 | 104 | — |
| 39 | `DOC-537e1f953940c39c` | yes | 0.2333 | 8.7 | 2600 | 181 | — |
| 40 | `DOC-fe0e62a4596a649b` | yes | 0.0606 | 6.9 | 2255 | 132 | — |
| 41 | `DOC-5feb4a34e13ce77a` | yes | 0.1000 | 6.3 | 2415 | 182 | — |
| 42 | `DOC-aff14c55ba2c4d16` | yes | 0.0769 | 7.4 | 3394 | 148 | — |
| 43 | `DOC-62d410af6bdd29f8` | yes | 0.2286 | 6.1 | 2520 | 182 | — |
| 44 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 5.6 | 2255 | 132 | — |
| 45 | `DOC-20dc95a39ec83250` | yes | 0.1911 | 7.7 | 2422 | 167 | — |
| 46 | `DOC-851611e86c9e36d0` | yes | 0.5146 | 4.5 | 2806 | 141 | — |
| 47 | `DOC-90326221a1667d50` | yes | 0.3333 | 6.6 | 3495 | 153 | — |
| 48 | `DOC-6823b2f649cf1d0a` | yes | 0.4074 | 5.8 | 4888 | 144 | — |
| 49 | `DOC-f8fb6b01de0fc173` | yes | 0.8611 | 5.3 | 3169 | 156 | — |
| 50 | `DOC-e1e0cc74e784a403` | yes | 0.3212 | 5.1 | 2677 | 181 | — |

_Generated 2026-10-13T04:33:02+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-correspondence-specialist-awq-2l4-c16.card.json`._
