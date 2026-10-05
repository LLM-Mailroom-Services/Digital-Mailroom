# Correspondence — 2× L4 · C32 · n=50

**Run:** `grid-50-correspondence-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `grid-50-correspondence-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | a6e93f63… |
| **Time** |  |
| Wall (busy) | 13.96 s |
| GPU seconds | 14.25 s |
| Cold boot | 0.30 s |
| **Cost** |  |
| Busy-window GPU $ | $0.006203 |
| Billed GPU $ (incl. boot) | $0.006335 |
| Idle $ | not captured |
| Cost per document | $0.000124 |
| Cost per ok document | $0.000124 |
| Cost per 1M tokens | $0.0434 |
| **Tokens** |  |
| Prompt tokens | 134,797 |
| Completion tokens | 8,106 (5.7%) |
| Total tokens | 142,903 |
| Tokens per document | 2,858 |
| Per document: instructions + template | 2,181 (76.3%) |
| Per document: document text | 515 (18.0%) |
| Per document: output | 162 (5.7%) |
| Instruction tokens per model call | 2,181 over 50 calls |
| Token split basis | fit across documents, 3.75 chars/token |
| Completion p95 / max (ok docs) | 296 / 443 |
| **Throughput** |  |
| Tokens / second | 10,239.5 |
| Tokens / second per L4 | 5,119.8 |
| Documents / minute | 214.96 |
| **Latency (per document, ok rows)** |  |
| Mean | 11.13 s |
| p50 | 10.73 s |
| p95 | 18.46 s |
| Max | 22.28 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 39.89× of 32 |
| Slot occupancy | 124.7% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 24 / 26 |
| Mean TTFT per replica | 2.325 s / 2.957 s |
| Prefix-cache hit per replica | 57.0% / 62.6% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **Quality** |  |
| Overall extraction score | 0.3340 (sd 0.203) |
| Score min / max | 0.0000 / 0.8627 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-16dfd03aed14e557` | yes | 0.0000 | 8.2 | 2205 | 76 | — |
| 2 | `DOC-1d5664e2c826ad07` | yes | 0.3889 | 9.7 | 2216 | 104 | — |
| 3 | `DOC-f36a37e1a9c1351e` | yes | 0.0833 | 9.7 | 2238 | 105 | — |
| 4 | `DOC-d0c241ea24439be2` | yes | 0.5101 | 9.6 | 2324 | 111 | — |
| 5 | `DOC-cb4f8fb4ccb52f44` | yes | 0.3333 | 9.8 | 2270 | 118 | — |
| 6 | `DOC-20b4e31d9a4bf994` | yes | 0.2844 | 9.9 | 2386 | 123 | — |
| 7 | `DOC-c2826f69ed293da4` | yes | 0.0494 | 10.3 | 2229 | 105 | — |
| 8 | `DOC-2bdbf0be591edea6` | yes | 0.0513 | 10.7 | 2260 | 116 | — |
| 9 | `DOC-38265bcc6ecfecc3` | yes | 0.1212 | 10.7 | 2260 | 114 | — |
| 10 | `DOC-44b1e5a60b363d3e` | yes | 0.3333 | 11.9 | 2527 | 127 | — |
| 11 | `DOC-553256644e7b4547` | yes | 0.3333 | 11.9 | 2304 | 127 | — |
| 12 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 12.6 | 2310 | 128 | — |
| 13 | `DOC-38c54645bf0e601a` | yes | 0.3704 | 12.6 | 2556 | 128 | — |
| 14 | `DOC-9ec94a2619e46dfb` | yes | 0.4000 | 12.7 | 2273 | 133 | — |
| 15 | `DOC-4eb0e9385b81cc4b` | yes | 0.2281 | 12.6 | 2315 | 138 | — |
| 16 | `DOC-c4debd478f2c06e0` | yes | 0.5119 | 13.5 | 2467 | 137 | — |
| 17 | `DOC-690cb07fef21747b` | yes | 0.0833 | 13.7 | 2485 | 140 | — |
| 18 | `DOC-314aa51db90c8c92` | yes | 0.4167 | 13.8 | 3072 | 156 | — |
| 19 | `DOC-8eed243667c985bd` | yes | 0.3333 | 14.0 | 2680 | 159 | — |
| 20 | `DOC-a318b50872273528` | yes | 0.3485 | 14.3 | 2559 | 157 | — |
| 21 | `DOC-c45ecc852b2cb0f4` | yes | 0.5362 | 14.5 | 2354 | 166 | — |
| 22 | `DOC-91f5631a20c62dc5` | yes | 0.3544 | 14.5 | 2453 | 168 | — |
| 23 | `DOC-228e51bba45b5c7d` | yes | 0.2582 | 15.0 | 3037 | 175 | — |
| 24 | `DOC-a8efd6e4c4d49aaf` | yes | 0.2190 | 14.9 | 2471 | 176 | — |
| 25 | `DOC-2cde0c6d0c70b02b` | yes | 0.0784 | 15.0 | 2737 | 180 | — |
| 26 | `DOC-383b9badb01a1a00` | yes | 0.3333 | 15.2 | 4778 | 181 | — |
| 27 | `DOC-47647a5fdcd45666` | yes | 0.3333 | 16.0 | 2447 | 130 | — |
| 28 | `DOC-5adf644f3cb1d34e` | yes | 0.0000 | 3.6 | 2199 | 76 | — |
| 29 | `DOC-8754555168547e16` | yes | 0.2641 | 16.9 | 3162 | 232 | — |
| 30 | `DOC-21460a9f6d7e6348` | yes | 0.8627 | 7.4 | 2337 | 137 | — |
| 31 | `DOC-d6e2bbd8c5e394a4` | yes | 0.8095 | 6.7 | 2263 | 123 | — |
| 32 | `DOC-edd0a288e32f0d3b` | yes | 0.6667 | 7.5 | 2507 | 134 | — |
| 33 | `DOC-f6a9a00e53cc7973` | yes | 0.3333 | 7.7 | 6379 | 144 | — |
| 34 | `DOC-d3d85dc1b1514bec` | yes | 0.5384 | 9.3 | 2444 | 169 | — |
| 35 | `DOC-595ab9fc19465909` | yes | 0.3333 | 6.9 | 2371 | 152 | — |
| 36 | `DOC-96438076efc6cc7b` | yes | 0.3333 | 5.2 | 2309 | 144 | — |
| 37 | `DOC-a6fff0ef0e406461` | yes | 0.3810 | 7.2 | 2374 | 163 | — |
| 38 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 5.5 | 2255 | 128 | — |
| 39 | `DOC-e624b1b9823e53f5` | yes | 0.5425 | 18.1 | 2917 | 280 | — |
| 40 | `DOC-ff15276697cdfbb2` | yes | 0.1162 | 6.3 | 2853 | 165 | — |
| 41 | `DOC-17ac4251c7d94cea` | yes | 0.1212 | 4.7 | 2261 | 112 | — |
| 42 | `DOC-c01ab1c1c673f355` | yes | 0.5069 | 4.9 | 2394 | 126 | — |
| 43 | `DOC-2431095adda97989` | yes | 0.1752 | 18.5 | 2606 | 296 | — |
| 44 | `DOC-5b63f9fe205d564b` | yes | 0.5800 | 4.7 | 2425 | 146 | — |
| 45 | `DOC-9b2bc061621a56be` | yes | 0.5278 | 8.9 | 2574 | 191 | — |
| 46 | `DOC-76375ebb4cd91de9` | yes | 0.1111 | 7.5 | 3047 | 190 | — |
| 47 | `DOC-9422c8775b387935` | yes | 0.8000 | 6.7 | 3119 | 158 | — |
| 48 | `DOC-ee6bae4d269c1911` | yes | 0.3333 | 11.0 | 3361 | 281 | — |
| 49 | `DOC-1dcf4dfd5ec6defb` | yes | 0.2457 | 22.1 | 3533 | 438 | — |
| 50 | `DOC-f4b4c8c623ccb915` | yes | 0.1067 | 22.3 | 4894 | 443 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-correspondence-specialist-awq-2l4.card.json`._
