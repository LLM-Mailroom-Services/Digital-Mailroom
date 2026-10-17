# Correspondence — 1× L4 · C8 · n=50

**Run:** `sand42-noisefloor-correspondence-awq-1l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-noisefloor-correspondence-awq-1l4-c8` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | b0650f19… |
| **Time** |  |
| Wall (busy) | 58.40 s |
| GPU seconds | 58.65 s |
| Cold boot | 0.26 s |
| **Cost** |  |
| Busy-window GPU $ | $0.012978 |
| Billed GPU $ | $0.013032 |
| Billed seconds | 58.65 s |
| Idle $ | $0.003815 (17.17 s) |
| Cost per document | $0.000261 |
| Cost per ok document | $0.000261 |
| Cost per 1M tokens | $0.0950 |
| **Tokens** |  |
| Prompt tokens | 129,444 |
| Completion tokens | 7,788 (5.7%) |
| Total tokens | 137,232 |
| Tokens per document | 2,745 |
| Per document: instructions + template | 2,241 (81.7%) |
| Per document: document text | 348 (12.7%) |
| Per document: output | 156 (5.7%) |
| Instruction tokens per model call | 2,241 over 50 calls |
| Token split basis | fit across documents, 4.38 chars/token |
| Completion p95 / max (ok docs) | 204 / 290 |
| **Throughput** |  |
| Tokens / second | 2,349.8 |
| Tokens / second per L4 | 2,349.8 |
| Documents / minute | 51.37 |
| **Latency (per document, ok rows)** |  |
| Mean | 6.60 s |
| p50 | 6.65 s |
| p95 | 9.71 s |
| Max | 10.48 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 5.65× of 8 |
| Slot occupancy | 70.6% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 3.563 s |
| Prefix-cache hit per replica | 20.4% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **GPU hardware (nvidia-smi)** | 9 samples · serving-replica nvidia-smi |
| GPU utilization | 76.9 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 65.1 W (min 31.5 / max 73.3) of 72 W cap |
| GPU memory bandwidth | 68.4 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,497 MHz (min 1,050 / max 2,040) |
| GPU temperature | 72.9 C (min 66.0 / max 77.0) |
| GPU memory used | 21,028 MiB (min 21,028 / max 21,028) |
| **Quality** |  |
| Overall extraction score | 0.3855 (sd 0.241) |
| Score min / max | 0.0278 / 0.8246 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Correspondence run dashboard](sand42-noisefloor-correspondence-awq-1l4-c8.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-2a7acfac00e67bac` | yes | 0.0278 | 7.0 | 2256 | 120 | — |
| 2 | `DOC-fcab49d5955c76c0` | yes | 0.0606 | 7.0 | 2332 | 136 | — |
| 3 | `DOC-3c85eb56a4145e0c` | yes | 0.7143 | 7.0 | 2357 | 133 | — |
| 4 | `DOC-a21b03af9a6afc21` | yes | 0.8246 | 7.0 | 2412 | 130 | — |
| 5 | `DOC-0dfd9710f2380220` | yes | 0.2050 | 7.1 | 2367 | 157 | — |
| 6 | `DOC-d9937f535b7c22f3` | yes | 0.3333 | 8.9 | 2447 | 173 | — |
| 7 | `DOC-fc6108235411ca8e` | yes | 0.0606 | 9.7 | 2465 | 198 | — |
| 8 | `DOC-3a21b2695c19d388` | yes | 0.0952 | 9.7 | 2766 | 198 | — |
| 9 | `DOC-1de496e8c9350155` | yes | 0.3696 | 5.9 | 2314 | 131 | — |
| 10 | `DOC-3433644b29e318b3` | yes | 0.4967 | 6.0 | 2311 | 136 | — |
| 11 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 5.1 | 2310 | 128 | — |
| 12 | `DOC-275198e372250586` | yes | 0.1587 | 6.9 | 2880 | 150 | — |
| 13 | `DOC-bcc74152bde91996` | yes | 0.8095 | 4.4 | 2211 | 121 | — |
| 14 | `DOC-b7f699fd18d0f80c` | yes | 0.5185 | 8.1 | 2731 | 179 | — |
| 15 | `DOC-af2b2b54e31214cc` | yes | 0.3636 | 8.2 | 2822 | 182 | — |
| 16 | `DOC-8ca6802d3a0f5d1a` | yes | 0.8148 | 6.7 | 3289 | 163 | — |
| 17 | `DOC-5cdfee2b0ef0a218` | yes | 0.5362 | 6.0 | 2263 | 156 | — |
| 18 | `DOC-e7b6158bfb232964` | yes | 0.5000 | 3.9 | 2246 | 117 | — |
| 19 | `DOC-ede2172372d1f296` | yes | 0.1111 | 5.2 | 2282 | 140 | — |
| 20 | `DOC-25958c023112a96e` | yes | 0.6667 | 6.7 | 2242 | 170 | — |
| 21 | `DOC-6bdc0c7c153547b6` | yes | 0.7451 | 7.8 | 2480 | 199 | — |
| 22 | `DOC-38a7cb4be93dbecd` | yes | 0.7778 | 6.1 | 2625 | 159 | — |
| 23 | `DOC-4fa7aa63b169fea8` | yes | 0.3333 | 5.9 | 2523 | 161 | — |
| 24 | `DOC-8674660f9ccc8243` | yes | 0.5362 | 5.4 | 2377 | 142 | — |
| 25 | `DOC-bdf1d75db5874068` | yes | 0.7778 | 10.5 | 2839 | 290 | — |
| 26 | `DOC-4ea9a8cde42f450b` | yes | 0.4667 | 5.8 | 2309 | 156 | — |
| 27 | `DOC-ba3217c0524a9577` | yes | 0.3333 | 5.3 | 2368 | 124 | — |
| 28 | `DOC-b78953fa896bdeb9` | yes | 0.5754 | 6.9 | 2441 | 171 | — |
| 29 | `DOC-5cef7d1205cc37d5` | yes | 0.4722 | 5.6 | 2581 | 137 | — |
| 30 | `DOC-3fd5fb2e4b505b04` | yes | 0.7647 | 7.2 | 2584 | 184 | — |
| 31 | `DOC-9417d989cb45b287` | yes | 0.0556 | 3.9 | 2212 | 89 | — |
| 32 | `DOC-315b7ca63910e311` | yes | 0.1939 | 8.0 | 2607 | 208 | — |
| 33 | `DOC-65c30d7452215c4b` | yes | 0.1333 | 5.2 | 2272 | 132 | — |
| 34 | `DOC-80c4ee15e95f8cc6` | yes | 0.0494 | 7.0 | 2631 | 166 | — |
| 35 | `DOC-537e1f953940c39c` | yes | 0.2333 | 7.2 | 2600 | 172 | — |
| 36 | `DOC-a7e5e24fade86aae` | yes | 0.4545 | 7.1 | 3230 | 158 | — |
| 37 | `DOC-8b2609c15d1d37af` | yes | 0.4286 | 9.2 | 2604 | 204 | — |
| 38 | `DOC-aff14c55ba2c4d16` | yes | 0.0769 | 6.4 | 3394 | 150 | — |
| 39 | `DOC-44dd971367dd458a` | yes | 0.6222 | 4.9 | 2298 | 113 | — |
| 40 | `DOC-fe0e62a4596a649b` | yes | 0.0606 | 6.4 | 2255 | 132 | — |
| 41 | `DOC-90326221a1667d50` | yes | 0.3333 | 6.8 | 3495 | 157 | — |
| 42 | `DOC-20dc95a39ec83250` | yes | 0.1911 | 7.5 | 2422 | 167 | — |
| 43 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 5.2 | 2255 | 128 | — |
| 44 | `DOC-5feb4a34e13ce77a` | yes | 0.1000 | 8.3 | 2415 | 176 | — |
| 45 | `DOC-f64e409a607594bb` | yes | 0.1768 | 5.4 | 2264 | 108 | — |
| 46 | `DOC-62d410af6bdd29f8` | yes | 0.2286 | 7.6 | 2520 | 182 | — |
| 47 | `DOC-6823b2f649cf1d0a` | yes | 0.4074 | 6.2 | 4888 | 141 | — |
| 48 | `DOC-851611e86c9e36d0` | yes | 0.5146 | 4.9 | 2806 | 141 | — |
| 49 | `DOC-f8fb6b01de0fc173` | yes | 0.5278 | 4.4 | 3169 | 142 | — |
| 50 | `DOC-e1e0cc74e784a403` | yes | 0.3212 | 5.2 | 2677 | 181 | — |

_Generated 2026-10-12T20:21:24+00:00 by `sandbox run card`. Machine-readable twin: `sand42-noisefloor-correspondence-awq-1l4-c8.card.json`._
