# Correspondence — 2× L4 · C32 · n=100

**Run:** `sand40-100-correspondence-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 100 docs (fingerprint 046a2c9bfc4e) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand40-100-correspondence-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 100 |
| Spec hash | 9aabe1bc… |
| **Time** |  |
| Wall (busy) | 27.52 s |
| GPU seconds | 28.15 s |
| Cold boot | 0.63 s |
| **Cost** |  |
| Busy-window GPU $ | $0.012231 |
| Billed GPU $ (incl. boot) | $0.012511 |
| Idle $ | not captured |
| Cost per document | $0.000122 |
| Cost per ok document | $0.000122 |
| Cost per 1M tokens | $0.0416 |
| **Tokens** |  |
| Prompt tokens | 277,062 |
| Completion tokens | 17,014 (5.8%) |
| Total tokens | 294,076 |
| Tokens per document | 2,941 |
| Per document: instructions + template | 2,193 (74.6%) |
| Per document: document text | 578 (19.7%) |
| Per document: output | 170 (5.8%) |
| Instruction tokens per model call | 2,193 over 100 calls |
| Token split basis | fit across documents, 3.89 chars/token |
| Completion p95 / max (ok docs) | 269 / 621 |
| **Throughput** |  |
| Tokens / second | 10,686.3 |
| Tokens / second per L4 | 5,343.1 |
| Documents / minute | 218.03 |
| **Latency (per document, ok rows)** |  |
| Mean | 11.52 s |
| p50 | 10.30 s |
| p95 | 20.29 s |
| Max | 37.86 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 41.88× of 32 |
| Slot occupancy | 130.9% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 52 / 48 |
| Mean TTFT per replica | 2.797 s / 2.487 s |
| Prefix-cache hit per replica | 34.5% / 35.1% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **Quality** |  |
| Overall extraction score | 0.3413 (sd 0.188) |
| Score min / max | 0.0000 / 0.8148 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 100 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-b5d016f4b2abaa39` | yes | 0.3333 | 10.7 | 2234 | 104 | — |
| 2 | `DOC-1d5664e2c826ad07` | yes | 0.3889 | 10.8 | 2216 | 104 | — |
| 3 | `DOC-c2826f69ed293da4` | yes | 0.0494 | 10.8 | 2229 | 105 | — |
| 4 | `DOC-f36a37e1a9c1351e` | yes | 0.0833 | 10.8 | 2238 | 104 | — |
| 5 | `DOC-f49b5cc25d9cb557` | yes | 0.1535 | 10.8 | 2527 | 125 | — |
| 6 | `DOC-9ec94a2619e46dfb` | yes | 0.4000 | 11.7 | 2273 | 143 | — |
| 7 | `DOC-553256644e7b4547` | yes | 0.3333 | 11.9 | 2304 | 118 | — |
| 8 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 12.2 | 2310 | 129 | — |
| 9 | `DOC-44b1e5a60b363d3e` | yes | 0.3333 | 12.3 | 2527 | 127 | — |
| 10 | `DOC-02dc4ab50ea271a4` | yes | 0.3333 | 12.7 | 2569 | 145 | — |
| 11 | `DOC-38c54645bf0e601a` | yes | 0.3704 | 13.0 | 2556 | 132 | — |
| 12 | `DOC-c45ecc852b2cb0f4` | yes | 0.6667 | 13.2 | 2354 | 157 | — |
| 13 | `DOC-0ab974301d63024f` | yes | 0.5000 | 13.9 | 2283 | 132 | — |
| 14 | `DOC-228e51bba45b5c7d` | yes | 0.2582 | 14.4 | 3037 | 175 | — |
| 15 | `DOC-ab94c5d183e5f7ca` | yes | 0.1067 | 15.0 | 5331 | 157 | — |
| 16 | `DOC-fc6108235411ca8e` | yes | 0.3939 | 15.2 | 2465 | 197 | — |
| 17 | `DOC-a318b50872273528` | yes | 0.2152 | 15.2 | 2559 | 157 | — |
| 18 | `DOC-2aea82e94dba6438` | yes | 0.2045 | 15.7 | 2442 | 165 | — |
| 19 | `DOC-383b9badb01a1a00` | yes | 0.3333 | 16.2 | 4778 | 181 | — |
| 20 | `DOC-ba72bbffee783647` | yes | 0.5185 | 16.2 | 2410 | 175 | — |
| 21 | `DOC-a763315b8f7cb96e` | yes | 0.5000 | 16.7 | 2668 | 189 | — |
| 22 | `DOC-8754555168547e16` | yes | 0.2641 | 16.8 | 3162 | 221 | — |
| 23 | `DOC-e72ff16f78525d0f` | yes | 0.4444 | 17.0 | 2774 | 232 | — |
| 24 | `DOC-32b1660fb702fd84` | yes | 0.1111 | 17.2 | 2689 | 239 | — |
| 25 | `DOC-31c068618dba65f3` | yes | 0.3333 | 6.2 | 2344 | 108 | — |
| 26 | `DOC-2431095adda97989` | yes | 0.1752 | 18.4 | 2606 | 269 | — |
| 27 | `DOC-e624b1b9823e53f5` | yes | 0.5425 | 18.6 | 2917 | 217 | — |
| 28 | `DOC-9be315cbfa0fbd19` | yes | 0.8148 | 19.0 | 4365 | 269 | — |
| 29 | `DOC-cb4f8fb4ccb52f44` | yes | 0.3333 | 8.6 | 2270 | 118 | — |
| 30 | `DOC-eaeffa14c92e7cd8` | yes | 0.3810 | 20.3 | 3043 | 160 | — |
| 31 | `DOC-314aa51db90c8c92` | yes | 0.4167 | 9.8 | 3072 | 156 | — |
| 32 | `DOC-8eed243667c985bd` | yes | 0.3333 | 8.3 | 2680 | 159 | — |
| 33 | `DOC-b0055813bc08a29c` | yes | 0.0556 | 9.2 | 2593 | 143 | — |
| 34 | `DOC-9d0aa39a8ac68936` | yes | 0.3333 | 4.8 | 2202 | 97 | — |
| 35 | `DOC-2bdbf0be591edea6` | yes | 0.0513 | 6.9 | 2260 | 116 | — |
| 36 | `DOC-25958c023112a96e` | yes | 0.6667 | 10.7 | 2242 | 155 | — |
| 37 | `DOC-4eb0e9385b81cc4b` | yes | 0.2281 | 7.3 | 2315 | 138 | — |
| 38 | `DOC-99c7dacadccd6e78` | yes | 0.5088 | 9.1 | 2327 | 138 | — |
| 39 | `DOC-c4debd478f2c06e0` | yes | 0.5119 | 7.3 | 2467 | 137 | — |
| 40 | `DOC-bc3f4676ac0c2e16` | yes | 0.3333 | 10.3 | 3889 | 169 | — |
| 41 | `DOC-522399c5514f180a` | yes | 0.5000 | 10.1 | 2974 | 171 | — |
| 42 | `DOC-690cb07fef21747b` | yes | 0.0833 | 8.2 | 2485 | 140 | — |
| 43 | `DOC-d3e421962da61b35` | yes | 0.7917 | 7.2 | 2660 | 135 | — |
| 44 | `DOC-36b9a080db747f3d` | yes | 0.0667 | 8.0 | 3389 | 147 | — |
| 45 | `DOC-91f5631a20c62dc5` | yes | 0.3544 | 9.1 | 2453 | 168 | — |
| 46 | `DOC-379b182c302a6821` | yes | 0.3333 | 8.0 | 2278 | 119 | — |
| 47 | `DOC-16dfd03aed14e557` | yes | 0.0000 | 4.7 | 2205 | 76 | — |
| 48 | `DOC-38265bcc6ecfecc3` | yes | 0.1212 | 6.9 | 2260 | 109 | — |
| 49 | `DOC-556e41697352e63d` | yes | 0.0800 | 12.1 | 2407 | 189 | — |
| 50 | `DOC-19d9fd70a08d306b` | yes | 0.3333 | 15.7 | 2970 | 230 | — |
| 51 | `DOC-47647a5fdcd45666` | yes | 0.3333 | 10.1 | 2447 | 143 | — |
| 52 | `DOC-84a9981be2435b55` | yes | 0.4286 | 8.5 | 2378 | 120 | — |
| 53 | `DOC-cc6e6dece6a787c2` | yes | 0.4452 | 10.3 | 2321 | 163 | — |
| 54 | `DOC-20b4e31d9a4bf994` | yes | 0.2844 | 9.8 | 2386 | 123 | — |
| 55 | `DOC-cfe8e8e7b9b3f38d` | yes | 0.3333 | 15.3 | 3159 | 234 | — |
| 56 | `DOC-4321eefceb0f4289` | yes | 0.3333 | 8.3 | 2451 | 131 | — |
| 57 | `DOC-4ab559dfb4d79b6d` | yes | 0.3333 | 9.8 | 2288 | 128 | — |
| 58 | `DOC-cd6877aeb3f2f7e4` | yes | 0.1569 | 11.2 | 2794 | 147 | — |
| 59 | `DOC-8c312283e2533866` | yes | 0.5088 | 29.7 | 2599 | 423 | — |
| 60 | `DOC-21460a9f6d7e6348` | yes | 0.8039 | 7.7 | 2337 | 123 | — |
| 61 | `DOC-d0c241ea24439be2` | yes | 0.5101 | 10.1 | 2324 | 111 | — |
| 62 | `DOC-f4b4c8c623ccb915` | yes | 0.1067 | 31.3 | 4894 | 443 | — |
| 63 | `DOC-a7d76cec54e46f1f` | yes | 0.1633 | 31.5 | 3364 | 454 | — |
| 64 | `DOC-9d65887887fe53d2` | yes | 0.3750 | 10.4 | 2343 | 167 | — |
| 65 | `DOC-d3d85dc1b1514bec` | yes | 0.5384 | 10.8 | 2444 | 169 | — |
| 66 | `DOC-6f05af738f455d50` | yes | 0.1323 | 8.3 | 3319 | 135 | — |
| 67 | `DOC-9501118a02fe39b9` | yes | 0.4002 | 9.8 | 2420 | 165 | — |
| 68 | `DOC-752a5e85c01ca6f0` | yes | 0.3939 | 8.8 | 2397 | 144 | — |
| 69 | `DOC-edd0a288e32f0d3b` | yes | 0.6667 | 10.6 | 2507 | 134 | — |
| 70 | `DOC-f6a9a00e53cc7973` | yes | 0.3333 | 11.0 | 6379 | 144 | — |
| 71 | `DOC-341d347babb3a19f` | yes | 0.2229 | 9.9 | 2427 | 143 | — |
| 72 | `DOC-2cde0c6d0c70b02b` | yes | 0.0784 | 13.2 | 2737 | 180 | — |
| 73 | `DOC-8c7847bfbb91d578` | yes | 0.3333 | 8.8 | 3255 | 134 | — |
| 74 | `DOC-5a424efe5df6ba6f` | yes | 0.5471 | 10.4 | 4634 | 148 | — |
| 75 | `DOC-5adf644f3cb1d34e` | yes | 0.0000 | 5.1 | 2199 | 76 | — |
| 76 | `DOC-a8efd6e4c4d49aaf` | yes | 0.2190 | 13.4 | 2471 | 176 | — |
| 77 | `DOC-9b2bc061621a56be` | yes | 0.5278 | 12.0 | 2574 | 192 | — |
| 78 | `DOC-d6e2bbd8c5e394a4` | yes | 0.8095 | 8.2 | 2263 | 126 | — |
| 79 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 7.0 | 2255 | 128 | — |
| 80 | `DOC-1dcf4dfd5ec6defb` | yes | 0.2457 | 25.0 | 3533 | 417 | — |
| 81 | `DOC-6aa30fb5a4e67d76` | yes | 0.3362 | 10.6 | 3212 | 179 | — |
| 82 | `DOC-95a872ee4ff237d5` | yes | 0.2034 | 5.9 | 2710 | 131 | — |
| 83 | `DOC-a6fff0ef0e406461` | yes | 0.3810 | 8.6 | 2374 | 167 | — |
| 84 | `DOC-595ab9fc19465909` | yes | 0.3333 | 8.7 | 2371 | 172 | — |
| 85 | `DOC-c00ffce3272be5fd` | yes | 0.3458 | 9.2 | 2915 | 182 | — |
| 86 | `DOC-ff15276697cdfbb2` | yes | 0.1162 | 8.1 | 2853 | 165 | — |
| 87 | `DOC-e25814bd08d418aa` | yes | 0.2467 | 11.7 | 2553 | 211 | — |
| 88 | `DOC-f0e1241d461dd523` | yes | 0.4167 | 6.9 | 2589 | 166 | — |
| 89 | `DOC-96438076efc6cc7b` | yes | 0.3333 | 5.6 | 2309 | 144 | — |
| 90 | `DOC-c01ab1c1c673f355` | yes | 0.5069 | 5.2 | 2394 | 124 | — |
| 91 | `DOC-17ac4251c7d94cea` | yes | 0.1212 | 4.5 | 2261 | 112 | — |
| 92 | `DOC-76375ebb4cd91de9` | yes | 0.1111 | 9.3 | 3047 | 196 | — |
| 93 | `DOC-1f3f868558fc4a6e` | yes | 0.3810 | 4.6 | 2376 | 113 | — |
| 94 | `DOC-9422c8775b387935` | yes | 0.8000 | 6.7 | 3119 | 157 | — |
| 95 | `DOC-8ce704cea54b1469` | yes | 0.3333 | 7.7 | 3196 | 174 | — |
| 96 | `DOC-162babf552426b57` | yes | 0.0800 | 6.1 | 2344 | 157 | — |
| 97 | `DOC-caaba1c5a3f9a41e` | yes | 0.5333 | 37.9 | 3648 | 621 | — |
| 98 | `DOC-ee6bae4d269c1911` | yes | 0.3333 | 12.0 | 3361 | 265 | — |
| 99 | `DOC-f7af031d61f7d7f5` | yes | 0.3333 | 6.1 | 4498 | 158 | — |
| 100 | `DOC-5b63f9fe205d564b` | yes | 0.6212 | 5.5 | 2425 | 153 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `sand40-100-correspondence-specialist-awq-2l4.card.json`._
