# Correspondence — 2× L4 · C32 · n=50

**Run:** `sand42-50-correspondence-specialist-awq-2l4-c32` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-correspondence-specialist-awq-2l4-c32` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | 6309643e… |
| **Time** |  |
| Wall (busy) | 39.05 s |
| GPU seconds | 37.74 s |
| Cold boot | 0.33 s |
| **Cost** |  |
| Busy-window GPU $ | $0.017357 |
| Billed GPU $ | $0.016775 |
| Billed seconds | 37.74 s |
| Idle $ | $0.009706 (21.84 s) |
| Cost per document | $0.000336 |
| Cost per ok document | $0.000336 |
| Cost per 1M tokens | $0.1223 |
| **Tokens** |  |
| Prompt tokens | 129,444 |
| Completion tokens | 7,767 (5.7%) |
| Total tokens | 137,211 |
| Tokens per document | 2,744 |
| Per document: instructions + template | 2,241 (81.7%) |
| Per document: document text | 348 (12.7%) |
| Per document: output | 155 (5.7%) |
| Instruction tokens per model call | 2,241 over 50 calls |
| Token split basis | fit across documents, 4.38 chars/token |
| Completion p95 / max (ok docs) | 214 / 287 |
| **Throughput** |  |
| Tokens / second | 3,513.5 |
| Tokens / second per L4 | 1,756.7 |
| Documents / minute | 76.82 |
| **Latency (per document, ok rows)** |  |
| Mean | 11.02 s |
| p50 | 10.69 s |
| p95 | 17.90 s |
| Max | 20.45 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 14.11× of 32 |
| Slot occupancy | 44.1% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 20 / 30 |
| Mean TTFT per replica | 1.391 s / 4.692 s |
| Prefix-cache hit per replica | 60.0% / 63.8% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 10 samples · serving-replica nvidia-smi |
| GPU utilization | 49.1 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 94.4 % |
| GPU power draw | 52.9 W (min 28.4 / max 72.8) of 72 W cap |
| GPU memory bandwidth | 42.0 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,716 MHz (min 1,155 / max 2,040) |
| GPU temperature | 60.3 C (min 44.0 / max 75.0) |
| GPU memory used | 20,976 MiB (min 20,790 / max 21,022) |
| **Quality** |  |
| Overall extraction score | 0.3733 (sd 0.237) |
| Score min / max | 0.0278 / 0.8246 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Correspondence run dashboard](sand42-50-correspondence-specialist-awq-2l4-c32.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-2a7acfac00e67bac` | yes | 0.0278 | 8.3 | 2256 | 120 | — |
| 2 | `DOC-3433644b29e318b3` | yes | 0.4967 | 8.3 | 2311 | 123 | — |
| 3 | `DOC-25958c023112a96e` | yes | 0.3333 | 8.1 | 2242 | 125 | — |
| 4 | `DOC-1de496e8c9350155` | yes | 0.3696 | 8.3 | 2314 | 131 | — |
| 5 | `DOC-a21b03af9a6afc21` | yes | 0.8246 | 8.3 | 2412 | 130 | — |
| 6 | `DOC-fcab49d5955c76c0` | yes | 0.0606 | 8.4 | 2332 | 136 | — |
| 7 | `DOC-ede2172372d1f296` | yes | 0.1111 | 8.2 | 2282 | 140 | — |
| 8 | `DOC-4fa7aa63b169fea8` | yes | 0.3333 | 8.3 | 2523 | 142 | — |
| 9 | `DOC-8ca6802d3a0f5d1a` | yes | 0.8148 | 9.3 | 3289 | 163 | — |
| 10 | `DOC-0dfd9710f2380220` | yes | 0.2050 | 9.5 | 2367 | 169 | — |
| 11 | `DOC-b7f699fd18d0f80c` | yes | 0.5185 | 9.8 | 2731 | 179 | — |
| 12 | `DOC-e7b6158bfb232964` | yes | 0.5000 | 10.2 | 2246 | 117 | — |
| 13 | `DOC-ba3217c0524a9577` | yes | 0.3333 | 10.6 | 2368 | 124 | — |
| 14 | `DOC-5cef7d1205cc37d5` | yes | 0.2341 | 11.2 | 2581 | 141 | — |
| 15 | `DOC-8674660f9ccc8243` | yes | 0.5362 | 11.3 | 2377 | 142 | — |
| 16 | `DOC-6bdc0c7c153547b6` | yes | 0.7451 | 11.5 | 2480 | 225 | — |
| 17 | `DOC-3c85eb56a4145e0c` | yes | 0.7143 | 11.8 | 2357 | 138 | — |
| 18 | `DOC-5cdfee2b0ef0a218` | yes | 0.5362 | 12.1 | 2263 | 146 | — |
| 19 | `DOC-275198e372250586` | yes | 0.1587 | 13.0 | 2880 | 150 | — |
| 20 | `DOC-4ea9a8cde42f450b` | yes | 0.4667 | 13.8 | 2309 | 160 | — |
| 21 | `DOC-b78953fa896bdeb9` | yes | 0.5754 | 14.1 | 2441 | 169 | — |
| 22 | `DOC-af2b2b54e31214cc` | yes | 0.3636 | 14.7 | 2822 | 177 | — |
| 23 | `DOC-65c30d7452215c4b` | yes | 0.1333 | 6.4 | 2272 | 132 | — |
| 24 | `DOC-fe0e62a4596a649b` | yes | 0.0606 | 6.2 | 2255 | 132 | — |
| 25 | `DOC-d9937f535b7c22f3` | yes | 0.3333 | 14.8 | 2447 | 173 | — |
| 26 | `DOC-bdf1d75db5874068` | yes | 0.7778 | 14.5 | 2839 | 287 | — |
| 27 | `DOC-38a7cb4be93dbecd` | yes | 0.7407 | 15.0 | 2625 | 178 | — |
| 28 | `DOC-3fd5fb2e4b505b04` | yes | 0.7647 | 15.5 | 2584 | 184 | — |
| 29 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 5.4 | 2255 | 132 | — |
| 30 | `DOC-90326221a1667d50` | yes | 0.3333 | 6.5 | 3495 | 153 | — |
| 31 | `DOC-3a21b2695c19d388` | yes | 0.0952 | 16.3 | 2766 | 199 | — |
| 32 | `DOC-20dc95a39ec83250` | yes | 0.1911 | 6.9 | 2422 | 168 | — |
| 33 | `DOC-fc6108235411ca8e` | yes | 0.0606 | 16.7 | 2465 | 198 | — |
| 34 | `DOC-6823b2f649cf1d0a` | yes | 0.4074 | 5.5 | 4888 | 143 | — |
| 35 | `DOC-f8fb6b01de0fc173` | yes | 0.5278 | 5.2 | 3169 | 142 | — |
| 36 | `DOC-315b7ca63910e311` | yes | 0.1939 | 17.0 | 2607 | 214 | — |
| 37 | `DOC-9417d989cb45b287` | yes | 0.0556 | 9.3 | 2212 | 89 | — |
| 38 | `DOC-bcc74152bde91996` | yes | 0.8095 | 17.9 | 2211 | 121 | — |
| 39 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 18.0 | 2310 | 128 | — |
| 40 | `DOC-f64e409a607594bb` | yes | 0.1768 | 7.8 | 2264 | 108 | — |
| 41 | `DOC-44dd971367dd458a` | yes | 0.6222 | 10.8 | 2298 | 113 | — |
| 42 | `DOC-aff14c55ba2c4d16` | yes | 0.0769 | 11.1 | 3394 | 150 | — |
| 43 | `DOC-80c4ee15e95f8cc6` | yes | 0.0494 | 11.3 | 2631 | 160 | — |
| 44 | `DOC-a7e5e24fade86aae` | yes | 0.4545 | 11.3 | 3230 | 152 | — |
| 45 | `DOC-851611e86c9e36d0` | yes | 0.5146 | 8.6 | 2806 | 141 | — |
| 46 | `DOC-537e1f953940c39c` | yes | 0.2333 | 12.3 | 2600 | 181 | — |
| 47 | `DOC-8b2609c15d1d37af` | yes | 0.4286 | 20.4 | 2604 | 204 | — |
| 48 | `DOC-5feb4a34e13ce77a` | yes | 0.1000 | 11.3 | 2415 | 176 | — |
| 49 | `DOC-62d410af6bdd29f8` | yes | 0.2286 | 10.5 | 2520 | 181 | — |
| 50 | `DOC-e1e0cc74e784a403` | yes | 0.3212 | 9.1 | 2677 | 181 | — |

_Generated 2026-10-13T04:33:09+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-correspondence-specialist-awq-2l4-c32.card.json`._
