# Correspondence — 1× L4 · C8 · n=50

**Run:** `grid-50-correspondence-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 50 docs (fingerprint 8e4572ae7fba) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-50-correspondence-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | c20ff843… |
| **Time** |  |
| Wall (busy) | 40.56 s |
| GPU seconds | 40.89 s |
| Cold boot | 0.33 s |
| **Cost** |  |
| Busy-window GPU $ | $0.009013 |
| Billed GPU $ (incl. boot) | $0.009087 |
| Idle $ | not captured |
| Cost per document | $0.000180 |
| Cost per ok document | $0.000180 |
| Cost per 1M tokens | $0.0631 |
| **Tokens** |  |
| Prompt tokens | 134,797 |
| Completion tokens | 8,084 (5.7%) |
| Total tokens | 142,881 |
| Tokens per document | 2,858 |
| Per document: instructions + template | 2,181 (76.3%) |
| Per document: document text | 515 (18.0%) |
| Per document: output | 162 (5.7%) |
| Instruction tokens per model call | 2,181 over 50 calls |
| Token split basis | fit across documents, 3.75 chars/token |
| Completion p95 / max (ok docs) | 298 / 463 |
| **Throughput** |  |
| Tokens / second | 3,522.8 |
| Tokens / second per L4 | 3,522.8 |
| Documents / minute | 73.97 |
| **Latency (per document, ok rows)** |  |
| Mean | 7.28 s |
| p50 | 6.60 s |
| p95 | 11.71 s |
| Max | 19.76 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 8.98× of 8 |
| Slot occupancy | 112.2% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 0.813 s |
| Prefix-cache hit per replica | 61.1% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **Quality** |  |
| Overall extraction score | 0.3446 (sd 0.218) |
| Score min / max | 0.0000 / 0.8205 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-1d5664e2c826ad07` | yes | 0.3889 | 6.9 | 2216 | 101 | — |
| 2 | `DOC-f36a37e1a9c1351e` | yes | 0.0833 | 6.9 | 2238 | 105 | — |
| 3 | `DOC-c2826f69ed293da4` | yes | 0.0494 | 6.9 | 2229 | 105 | — |
| 4 | `DOC-38c54645bf0e601a` | yes | 0.1813 | 9.0 | 2556 | 139 | — |
| 5 | `DOC-a318b50872273528` | yes | 0.3485 | 9.7 | 2559 | 164 | — |
| 6 | `DOC-383b9badb01a1a00` | yes | 0.3333 | 10.5 | 4778 | 181 | — |
| 7 | `DOC-e624b1b9823e53f5` | yes | 0.5425 | 11.6 | 2917 | 218 | — |
| 8 | `DOC-8754555168547e16` | yes | 0.2641 | 11.7 | 3162 | 221 | — |
| 9 | `DOC-553256644e7b4547` | yes | 0.3333 | 6.3 | 2304 | 118 | — |
| 10 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 5.0 | 2310 | 128 | — |
| 11 | `DOC-c45ecc852b2cb0f4` | yes | 0.5362 | 8.5 | 2354 | 165 | — |
| 12 | `DOC-9ec94a2619e46dfb` | yes | 0.4000 | 6.7 | 2273 | 154 | — |
| 13 | `DOC-44b1e5a60b363d3e` | yes | 0.3333 | 5.9 | 2527 | 127 | — |
| 14 | `DOC-cb4f8fb4ccb52f44` | yes | 0.3333 | 5.0 | 2270 | 118 | — |
| 15 | `DOC-228e51bba45b5c7d` | yes | 0.2582 | 7.4 | 3037 | 175 | — |
| 16 | `DOC-314aa51db90c8c92` | yes | 0.4167 | 6.0 | 3072 | 163 | — |
| 17 | `DOC-2431095adda97989` | yes | 0.1752 | 11.2 | 2606 | 298 | — |
| 18 | `DOC-2bdbf0be591edea6` | yes | 0.0800 | 4.1 | 2260 | 117 | — |
| 19 | `DOC-8eed243667c985bd` | yes | 0.7917 | 7.1 | 2680 | 192 | — |
| 20 | `DOC-4eb0e9385b81cc4b` | yes | 0.2281 | 5.5 | 2315 | 139 | — |
| 21 | `DOC-f4b4c8c623ccb915` | yes | 0.1067 | 17.6 | 4894 | 433 | — |
| 22 | `DOC-91f5631a20c62dc5` | yes | 0.3847 | 6.8 | 2453 | 176 | — |
| 23 | `DOC-47647a5fdcd45666` | yes | 0.3333 | 5.0 | 2447 | 126 | — |
| 24 | `DOC-c4debd478f2c06e0` | yes | 0.5119 | 5.4 | 2467 | 137 | — |
| 25 | `DOC-690cb07fef21747b` | yes | 0.0833 | 5.3 | 2485 | 139 | — |
| 26 | `DOC-20b4e31d9a4bf994` | yes | 0.2844 | 5.0 | 2386 | 117 | — |
| 27 | `DOC-d0c241ea24439be2` | yes | 0.5101 | 4.7 | 2324 | 102 | — |
| 28 | `DOC-16dfd03aed14e557` | yes | 0.0000 | 3.6 | 2205 | 76 | — |
| 29 | `DOC-38265bcc6ecfecc3` | yes | 0.1212 | 5.1 | 2260 | 112 | — |
| 30 | `DOC-1dcf4dfd5ec6defb` | yes | 0.2457 | 19.8 | 3533 | 463 | — |
| 31 | `DOC-edd0a288e32f0d3b` | yes | 0.6667 | 6.8 | 2507 | 134 | — |
| 32 | `DOC-21460a9f6d7e6348` | yes | 0.7451 | 6.0 | 2337 | 115 | — |
| 33 | `DOC-a8efd6e4c4d49aaf` | yes | 0.2190 | 8.8 | 2471 | 176 | — |
| 34 | `DOC-d3d85dc1b1514bec` | yes | 0.8205 | 8.5 | 2444 | 175 | — |
| 35 | `DOC-2cde0c6d0c70b02b` | yes | 0.0784 | 9.3 | 2737 | 185 | — |
| 36 | `DOC-f6a9a00e53cc7973` | yes | 0.3333 | 8.1 | 6379 | 143 | — |
| 37 | `DOC-9b2bc061621a56be` | yes | 0.5278 | 9.6 | 2574 | 191 | — |
| 38 | `DOC-d6e2bbd8c5e394a4` | yes | 0.8095 | 5.5 | 2263 | 124 | — |
| 39 | `DOC-595ab9fc19465909` | yes | 0.3333 | 6.5 | 2371 | 150 | — |
| 40 | `DOC-5adf644f3cb1d34e` | yes | 0.0000 | 3.0 | 2199 | 76 | — |
| 41 | `DOC-a6fff0ef0e406461` | yes | 0.3810 | 7.1 | 2374 | 162 | — |
| 42 | `DOC-ff15276697cdfbb2` | yes | 0.1162 | 6.3 | 2853 | 165 | — |
| 43 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 4.9 | 2255 | 132 | — |
| 44 | `DOC-ee6bae4d269c1911` | yes | 0.3333 | 10.6 | 3361 | 265 | — |
| 45 | `DOC-76375ebb4cd91de9` | yes | 0.1111 | 8.2 | 3047 | 199 | — |
| 46 | `DOC-17ac4251c7d94cea` | yes | 0.1212 | 4.0 | 2261 | 112 | — |
| 47 | `DOC-9422c8775b387935` | yes | 0.8000 | 5.7 | 3119 | 156 | — |
| 48 | `DOC-96438076efc6cc7b` | yes | 0.3333 | 5.2 | 2309 | 144 | — |
| 49 | `DOC-5b63f9fe205d564b` | yes | 0.6212 | 4.6 | 2425 | 146 | — |
| 50 | `DOC-c01ab1c1c673f355` | yes | 0.5069 | 5.6 | 2394 | 125 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-correspondence-specialist-awq-1l4.card.json`._
