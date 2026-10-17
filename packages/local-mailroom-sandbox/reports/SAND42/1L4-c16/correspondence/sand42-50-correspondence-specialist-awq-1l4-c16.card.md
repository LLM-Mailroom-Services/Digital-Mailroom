# Correspondence — 1× L4 · C16 · n=50

**Run:** `sand42-50-correspondence-specialist-awq-1l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-correspondence-specialist-awq-1l4-c16` |
| GPUs / replicas | 1 |
| Concurrency | 16 (16 per replica) |
| Documents | 50 |
| Spec hash | 6424743b… |
| **Time** |  |
| Wall (busy) | 47.27 s |
| GPU seconds | 48.34 s |
| Cold boot | 0.26 s |
| **Cost** |  |
| Busy-window GPU $ | $0.010504 |
| Billed GPU $ | $0.010742 |
| Billed seconds | 48.34 s |
| Idle $ | $0.003730 (16.78 s) |
| Cost per document | $0.000215 |
| Cost per ok document | $0.000215 |
| Cost per 1M tokens | $0.0783 |
| **Tokens** |  |
| Prompt tokens | 129,444 |
| Completion tokens | 7,783 (5.7%) |
| Total tokens | 137,227 |
| Tokens per document | 2,745 |
| Per document: instructions + template | 2,241 (81.7%) |
| Per document: document text | 348 (12.7%) |
| Per document: output | 156 (5.7%) |
| Instruction tokens per model call | 2,241 over 50 calls |
| Token split basis | fit across documents, 4.38 chars/token |
| Completion p95 / max (ok docs) | 223 / 271 |
| **Throughput** |  |
| Tokens / second | 2,903.2 |
| Tokens / second per L4 | 2,903.2 |
| Documents / minute | 63.47 |
| **Latency (per document, ok rows)** |  |
| Mean | 9.75 s |
| p50 | 9.63 s |
| p95 | 14.43 s |
| Max | 17.19 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 10.32× of 16 |
| Slot occupancy | 64.5% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 1.532 s |
| Prefix-cache hit per replica | 63.6% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **GPU hardware (nvidia-smi)** | 8 samples · serving-replica nvidia-smi |
| GPU utilization | 61.8 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 59.0 W (min 31.1 / max 72.1) of 72 W cap |
| GPU memory bandwidth | 44.1 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,575 MHz (min 1,140 / max 2,040) |
| GPU temperature | 68.5 C (min 61.0 / max 73.0) |
| GPU memory used | 20,996 MiB (min 20,790 / max 21,026) |
| **Quality** |  |
| Overall extraction score | 0.3788 (sd 0.240) |
| Score min / max | 0.0278 / 0.8148 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Correspondence run dashboard](sand42-50-correspondence-specialist-awq-1l4-c16.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 9.6 | 2310 | 128 | — |
| 2 | `DOC-1de496e8c9350155` | yes | 0.3696 | 9.6 | 2314 | 131 | — |
| 3 | `DOC-3433644b29e318b3` | yes | 0.4967 | 9.6 | 2311 | 123 | — |
| 4 | `DOC-fcab49d5955c76c0` | yes | 0.0606 | 9.6 | 2332 | 136 | — |
| 5 | `DOC-2a7acfac00e67bac` | yes | 0.0278 | 9.6 | 2256 | 120 | — |
| 6 | `DOC-a21b03af9a6afc21` | yes | 0.7368 | 9.6 | 2412 | 118 | — |
| 7 | `DOC-bcc74152bde91996` | yes | 0.8095 | 9.6 | 2211 | 121 | — |
| 8 | `DOC-3c85eb56a4145e0c` | yes | 0.7143 | 9.6 | 2357 | 129 | — |
| 9 | `DOC-275198e372250586` | yes | 0.1587 | 9.9 | 2880 | 150 | — |
| 10 | `DOC-8ca6802d3a0f5d1a` | yes | 0.8148 | 9.9 | 3289 | 153 | — |
| 11 | `DOC-0dfd9710f2380220` | yes | 0.2050 | 10.1 | 2367 | 156 | — |
| 12 | `DOC-d9937f535b7c22f3` | yes | 0.3333 | 12.8 | 2447 | 170 | — |
| 13 | `DOC-af2b2b54e31214cc` | yes | 0.3636 | 13.0 | 2822 | 177 | — |
| 14 | `DOC-b7f699fd18d0f80c` | yes | 0.5185 | 13.3 | 2731 | 189 | — |
| 15 | `DOC-fc6108235411ca8e` | yes | 0.0606 | 14.4 | 2465 | 198 | — |
| 16 | `DOC-3a21b2695c19d388` | yes | 0.0952 | 14.5 | 2766 | 198 | — |
| 17 | `DOC-e7b6158bfb232964` | yes | 0.5000 | 7.6 | 2246 | 115 | — |
| 18 | `DOC-ede2172372d1f296` | yes | 0.1111 | 8.7 | 2282 | 140 | — |
| 19 | `DOC-8674660f9ccc8243` | yes | 0.5362 | 8.5 | 2377 | 142 | — |
| 20 | `DOC-4fa7aa63b169fea8` | yes | 0.3333 | 8.8 | 2523 | 147 | — |
| 21 | `DOC-4ea9a8cde42f450b` | yes | 0.4667 | 8.8 | 2309 | 152 | — |
| 22 | `DOC-ba3217c0524a9577` | yes | 0.3333 | 6.2 | 2368 | 124 | — |
| 23 | `DOC-5cdfee2b0ef0a218` | yes | 0.5362 | 10.0 | 2263 | 156 | — |
| 24 | `DOC-38a7cb4be93dbecd` | yes | 0.7778 | 11.0 | 2625 | 159 | — |
| 25 | `DOC-25958c023112a96e` | yes | 0.6667 | 11.4 | 2242 | 172 | — |
| 26 | `DOC-b78953fa896bdeb9` | yes | 0.6088 | 11.3 | 2441 | 174 | — |
| 27 | `DOC-5cef7d1205cc37d5` | yes | 0.1945 | 9.0 | 2581 | 156 | — |
| 28 | `DOC-3fd5fb2e4b505b04` | yes | 0.7647 | 10.2 | 2584 | 184 | — |
| 29 | `DOC-6bdc0c7c153547b6` | yes | 0.7451 | 14.1 | 2480 | 225 | — |
| 30 | `DOC-9417d989cb45b287` | yes | 0.0556 | 6.4 | 2212 | 89 | — |
| 31 | `DOC-8b2609c15d1d37af` | yes | 0.4286 | 10.7 | 2604 | 204 | — |
| 32 | `DOC-bdf1d75db5874068` | yes | 0.7778 | 17.2 | 2839 | 271 | — |
| 33 | `DOC-44dd971367dd458a` | yes | 0.6222 | 7.2 | 2298 | 113 | — |
| 34 | `DOC-315b7ca63910e311` | yes | 0.1939 | 12.5 | 2607 | 223 | — |
| 35 | `DOC-80c4ee15e95f8cc6` | yes | 0.0494 | 10.3 | 2631 | 155 | — |
| 36 | `DOC-65c30d7452215c4b` | yes | 0.1333 | 9.8 | 2272 | 131 | — |
| 37 | `DOC-fe0e62a4596a649b` | yes | 0.0606 | 8.3 | 2255 | 132 | — |
| 38 | `DOC-aff14c55ba2c4d16` | yes | 0.0769 | 10.1 | 3394 | 150 | — |
| 39 | `DOC-a7e5e24fade86aae` | yes | 0.4545 | 10.9 | 3230 | 158 | — |
| 40 | `DOC-537e1f953940c39c` | yes | 0.2333 | 11.3 | 2600 | 172 | — |
| 41 | `DOC-20dc95a39ec83250` | yes | 0.1911 | 9.3 | 2422 | 167 | — |
| 42 | `DOC-90326221a1667d50` | yes | 0.3333 | 8.5 | 3495 | 157 | — |
| 43 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 6.9 | 2255 | 132 | — |
| 44 | `DOC-5feb4a34e13ce77a` | yes | 0.1000 | 9.4 | 2415 | 180 | — |
| 45 | `DOC-f64e409a607594bb` | yes | 0.1768 | 6.2 | 2264 | 120 | — |
| 46 | `DOC-6823b2f649cf1d0a` | yes | 0.4074 | 6.6 | 4888 | 140 | — |
| 47 | `DOC-62d410af6bdd29f8` | yes | 0.2286 | 8.4 | 2520 | 182 | — |
| 48 | `DOC-851611e86c9e36d0` | yes | 0.5146 | 5.4 | 2806 | 141 | — |
| 49 | `DOC-f8fb6b01de0fc173` | yes | 0.5278 | 5.4 | 3169 | 142 | — |
| 50 | `DOC-e1e0cc74e784a403` | yes | 0.3212 | 6.2 | 2677 | 181 | — |

_Generated 2026-10-13T04:32:50+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-correspondence-specialist-awq-1l4-c16.card.json`._
