# Correspondence — 1× L4 · C8 · n=20

**Run:** `grid-20-correspondence-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 20 docs (fingerprint 0ec3314ab111) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-20-correspondence-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 20 |
| Spec hash | db94f6be… |
| **Time** |  |
| Wall (busy) | 10.05 s |
| GPU seconds | 10.38 s |
| Cold boot | 0.33 s |
| **Cost** |  |
| Busy-window GPU $ | $0.002234 |
| Billed GPU $ (incl. boot) | $0.002308 |
| Idle $ | not captured |
| Cost per document | $0.000112 |
| Cost per ok document | $0.000112 |
| Cost per 1M tokens | $0.0442 |
| **Tokens** |  |
| Prompt tokens | 47,832 |
| Completion tokens | 2,710 (5.4%) |
| Total tokens | 50,542 |
| Tokens per document | 2,527 |
| Per document: instructions + template | 2,199 (87.0%) |
| Per document: document text | 193 (7.6%) |
| Per document: output | 136 (5.4%) |
| Instruction tokens per model call | 2,199 over 20 calls |
| Token split basis | fit across documents, 4.17 chars/token |
| Completion p95 / max (ok docs) | 180 / 296 |
| **Throughput** |  |
| Tokens / second | 5,028.6 |
| Tokens / second per L4 | 5,028.6 |
| Documents / minute | 119.39 |
| **Latency (per document, ok rows)** |  |
| Mean | 5.63 s |
| p50 | 5.76 s |
| p95 | 7.95 s |
| Max | 12.24 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 11.21× of 8 |
| Slot occupancy | 140.1% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 20 |
| Mean TTFT per replica | 0.960 s |
| Prefix-cache hit per replica | 66.7% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **Quality** |  |
| Overall extraction score | 0.3268 (sd 0.241) |
| Score min / max | 0.0000 / 0.7843 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 20 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-1d5664e2c826ad07` | yes | 0.3889 | 5.8 | 2216 | 104 | — |
| 2 | `DOC-f36a37e1a9c1351e` | yes | 0.0833 | 5.8 | 2238 | 104 | — |
| 3 | `DOC-c2826f69ed293da4` | yes | 0.0494 | 5.8 | 2229 | 104 | — |
| 4 | `DOC-c71d3ca0b727a0d4` | yes | 0.3333 | 5.8 | 2310 | 128 | — |
| 5 | `DOC-38c54645bf0e601a` | yes | 0.3704 | 5.9 | 2556 | 132 | — |
| 6 | `DOC-44b1e5a60b363d3e` | yes | 0.3333 | 6.1 | 2527 | 141 | — |
| 7 | `DOC-a318b50872273528` | yes | 0.6818 | 7.9 | 2559 | 164 | — |
| 8 | `DOC-16dfd03aed14e557` | yes | 0.0000 | 3.6 | 2205 | 76 | — |
| 9 | `DOC-38265bcc6ecfecc3` | yes | 0.1212 | 4.9 | 2260 | 113 | — |
| 10 | `DOC-cb4f8fb4ccb52f44` | yes | 0.3333 | 5.0 | 2270 | 118 | — |
| 11 | `DOC-c4debd478f2c06e0` | yes | 0.5119 | 5.9 | 2467 | 137 | — |
| 12 | `DOC-690cb07fef21747b` | yes | 0.0833 | 5.9 | 2485 | 140 | — |
| 13 | `DOC-2431095adda97989` | yes | 0.1752 | 12.2 | 2606 | 296 | — |
| 14 | `DOC-2cde0c6d0c70b02b` | yes | 0.0784 | 7.0 | 2737 | 180 | — |
| 15 | `DOC-d3d85dc1b1514bec` | yes | 0.5384 | 5.7 | 2444 | 169 | — |
| 16 | `DOC-edd0a288e32f0d3b` | yes | 0.6667 | 4.5 | 2507 | 132 | — |
| 17 | `DOC-5adf644f3cb1d34e` | yes | 0.0000 | 2.6 | 2199 | 76 | — |
| 18 | `DOC-21460a9f6d7e6348` | yes | 0.7843 | 4.1 | 2337 | 123 | — |
| 19 | `DOC-c4074ed5b08f097e` | yes | 0.3827 | 4.1 | 2255 | 128 | — |
| 20 | `DOC-5b63f9fe205d564b` | yes | 0.6212 | 4.2 | 2425 | 145 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-20-correspondence-specialist-awq-1l4.card.json`._
