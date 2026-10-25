# Correspondence — 2× L4 · C8 · n=50

**Run:** `sand42-50-correspondence-specialist-awq-2l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-correspondence-specialist-awq-2l4-c8` |
| GPUs / replicas | 2 |
| Concurrency | 8 (4 per replica) |
| Documents | 50 |
| Spec hash | 853a5c1c… |
| **Time** |  |
| Wall (busy) | 50.98 s |
| GPU seconds | 51.63 s |
| Cold boot | 0.25 s |
| **Cost** |  |
| Busy-window GPU $ | $0.022659 |
| Billed GPU $ | $0.022946 |
| Billed seconds | 51.63 s |
| Idle $ | $0.007589 (17.08 s) |
| Cost per document | $0.000459 |
| Cost per ok document | $0.000459 |
| Cost per 1M tokens | $0.1671 |
| **Tokens** |  |
| Prompt tokens | 129,444 |
| Completion tokens | 7,847 (5.7%) |
| Total tokens | 137,291 |
| Tokens per document | 2,746 |
| Per document: instructions + template | 2,241 (81.6%) |
| Per document: document text | 348 (12.7%) |
| Per document: output | 157 (5.7%) |
| Instruction tokens per model call | 2,241 over 50 calls |
| Token split basis | fit across documents, 4.38 chars/token |
| Completion p95 / max (ok docs) | 225 / 274 |
| **Throughput** |  |
| Tokens / second | 2,692.9 |
| Tokens / second per L4 | 1,346.5 |
| Documents / minute | 58.84 |
| **Latency (per document, ok rows)** |  |
| Mean | 5.42 s |
| p50 | 5.33 s |
| p95 | 8.33 s |
| Max | 8.53 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 5.32× of 8 |
| Slot occupancy | 66.5% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 30 / 20 |
| Mean TTFT per replica | 0.580 s / 0.517 s |
| Prefix-cache hit per replica | 65.2% / 58.3% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 15 samples · serving-replica nvidia-smi |
| GPU utilization | 65.0 % mean (p95 99.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 59.8 W (min 28.4 / max 72.5) of 72 W cap |
| GPU memory bandwidth | 57.8 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,685 MHz (min 1,140 / max 2,040) |
| GPU temperature | 62.9 C (min 46.0 / max 75.0) |
| GPU memory used | 20,992 MiB (min 20,790 / max 21,024) |
| **Quality** |  |
| Overall extraction score | 0.3763 (sd 0.242) |
| Score min / max | 0.0278 / 0.8246 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Correspondence run dashboard](sand42-50-correspondence-specialist-awq-2l4-c8.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-2a7acfac00e67bac` | yes | 0.0278 | 6.0 | 2256 | 120 | — |
| 2 | `DOC-a21b03af9a6afc21` | yes | 0.8246 | 6.1 | 2412 | 130 | — |
| 3 | `DOC-3c85eb56a4145e0c` | yes | 0.7143 | 6.1 | 2357 | 129 | — |
| 4 | `DOC-fcab49d5955c76c0` | yes | 0.0606 | 6.1 | 2332 | 136 | — |
| 5 | `DOC-d9937f535b7c22f3` | yes | 0.3333 | 7.2 | 2447 | 174 | — |
| 6 | `DOC-0dfd9710f2380220` | yes | 0.2050 | 7.3 | 2367 | 157 | — |
| 7 | `DOC-fc6108235411ca8e` | yes | 0.0606 | 8.5 | 2465 | 198 | — |
| 8 | `DOC-3a21b2695c19d388` | yes | 0.1212 | 8.5 | 2766 | 199 | — |
| 9 | `DOC-3433644b29e318b3` | yes | 0.4967 | 4.3 | 2311 | 123 | — |
| 10 | `DOC-1de496e8c9350155` | yes | 0.3696 | 4.5 | 2314 | 131 | — |
| 11 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 3.9 | 2310 | 128 | — |
| 12 | `DOC-af2b2b54e31214cc` | yes | 0.3636 | 6.0 | 2822 | 178 | — |
| 13 | `DOC-b7f699fd18d0f80c` | yes | 0.5185 | 6.0 | 2731 | 179 | — |
| 14 | `DOC-bcc74152bde91996` | yes | 0.8095 | 3.7 | 2211 | 121 | — |
| 15 | `DOC-275198e372250586` | yes | 0.1587 | 5.0 | 2880 | 150 | — |
| 16 | `DOC-8ca6802d3a0f5d1a` | yes | 0.8148 | 5.4 | 3289 | 163 | — |
| 17 | `DOC-5cdfee2b0ef0a218` | yes | 0.5362 | 5.0 | 2263 | 146 | — |
| 18 | `DOC-e7b6158bfb232964` | yes | 0.5000 | 3.4 | 2246 | 118 | — |
| 19 | `DOC-ede2172372d1f296` | yes | 0.1111 | 4.6 | 2282 | 140 | — |
| 20 | `DOC-6bdc0c7c153547b6` | yes | 0.7451 | 6.6 | 2480 | 225 | — |
| 21 | `DOC-25958c023112a96e` | yes | 0.6667 | 5.1 | 2242 | 172 | — |
| 22 | `DOC-4fa7aa63b169fea8` | yes | 0.3333 | 4.6 | 2523 | 150 | — |
| 23 | `DOC-38a7cb4be93dbecd` | yes | 0.7407 | 7.2 | 2625 | 231 | — |
| 24 | `DOC-8674660f9ccc8243` | yes | 0.5362 | 4.4 | 2377 | 142 | — |
| 25 | `DOC-4ea9a8cde42f450b` | yes | 0.4667 | 4.8 | 2309 | 150 | — |
| 26 | `DOC-bdf1d75db5874068` | yes | 0.7778 | 8.3 | 2839 | 274 | — |
| 27 | `DOC-b78953fa896bdeb9` | yes | 0.5754 | 5.3 | 2441 | 169 | — |
| 28 | `DOC-ba3217c0524a9577` | yes | 0.3333 | 4.3 | 2368 | 124 | — |
| 29 | `DOC-5cef7d1205cc37d5` | yes | 0.1667 | 4.5 | 2581 | 140 | — |
| 30 | `DOC-9417d989cb45b287` | yes | 0.0556 | 2.7 | 2212 | 89 | — |
| 31 | `DOC-3fd5fb2e4b505b04` | yes | 0.7647 | 6.2 | 2584 | 184 | — |
| 32 | `DOC-65c30d7452215c4b` | yes | 0.1333 | 3.9 | 2272 | 129 | — |
| 33 | `DOC-80c4ee15e95f8cc6` | yes | 0.0494 | 5.2 | 2631 | 152 | — |
| 34 | `DOC-537e1f953940c39c` | yes | 0.2333 | 5.7 | 2600 | 181 | — |
| 35 | `DOC-a7e5e24fade86aae` | yes | 0.4545 | 5.2 | 3230 | 158 | — |
| 36 | `DOC-315b7ca63910e311` | yes | 0.1939 | 7.2 | 2607 | 223 | — |
| 37 | `DOC-8b2609c15d1d37af` | yes | 0.4286 | 7.4 | 2604 | 204 | — |
| 38 | `DOC-44dd971367dd458a` | yes | 0.6222 | 3.9 | 2298 | 113 | — |
| 39 | `DOC-aff14c55ba2c4d16` | yes | 0.0769 | 5.3 | 3394 | 150 | — |
| 40 | `DOC-20dc95a39ec83250` | yes | 0.1911 | 5.4 | 2422 | 168 | — |
| 41 | `DOC-fe0e62a4596a649b` | yes | 0.0606 | 5.5 | 2255 | 132 | — |
| 42 | `DOC-5feb4a34e13ce77a` | yes | 0.1000 | 5.7 | 2415 | 182 | — |
| 43 | `DOC-f64e409a607594bb` | yes | 0.1768 | 3.4 | 2264 | 108 | — |
| 44 | `DOC-62d410af6bdd29f8` | yes | 0.2286 | 5.6 | 2520 | 192 | — |
| 45 | `DOC-90326221a1667d50` | yes | 0.3333 | 6.2 | 3495 | 153 | — |
| 46 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 5.2 | 2255 | 132 | — |
| 47 | `DOC-6823b2f649cf1d0a` | yes | 0.4074 | 5.3 | 4888 | 143 | — |
| 48 | `DOC-851611e86c9e36d0` | yes | 0.5146 | 4.4 | 2806 | 141 | — |
| 49 | `DOC-f8fb6b01de0fc173` | yes | 0.5278 | 4.3 | 3169 | 142 | — |
| 50 | `DOC-e1e0cc74e784a403` | yes | 0.1768 | 4.7 | 2677 | 174 | — |

_Generated 2026-10-13T04:32:56+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-correspondence-specialist-awq-2l4-c8.card.json`._
