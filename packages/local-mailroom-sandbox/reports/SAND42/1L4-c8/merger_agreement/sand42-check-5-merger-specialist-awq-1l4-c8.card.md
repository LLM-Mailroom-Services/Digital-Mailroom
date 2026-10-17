# Merger Agreements — 1× L4 · C8 · n=5

**Run:** `sand42-check-5-merger-specialist-awq-1l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 5 docs (fingerprint a8953394973e) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand42-check-5-merger-specialist-awq-1l4-c8` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 5 |
| Spec hash | d90678b7… |
| **Time** |  |
| Wall (busy) | 100.26 s |
| GPU seconds | 100.56 s |
| Cold boot | 0.30 s |
| **Cost** |  |
| Busy-window GPU $ | $0.022279 |
| Billed GPU $ (incl. boot) | $0.022346 |
| Idle $ | not captured |
| Cost per document | $0.004456 |
| Cost per ok document | $0.004456 |
| Cost per 1M tokens | $0.0449 |
| **Tokens** |  |
| Prompt tokens | 464,217 |
| Completion tokens | 31,545 (6.4%) |
| Total tokens | 495,762 |
| Tokens per document | 99,152 |
| Per document: instructions + template | 7,347 (7.4%) |
| Per document: document text | 85,496 (86.2%) |
| Per document: output | 6,309 (6.4%) |
| Instruction tokens per model call | 942 over 39 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 8,179 / 8,179 |
| **Throughput** |  |
| Tokens / second | 4,945.0 |
| Tokens / second per L4 | 4,945.0 |
| Documents / minute | 2.99 |
| **Latency (per document, ok rows)** |  |
| Mean | 374.84 s |
| p50 | 357.27 s |
| p95 | 434.48 s |
| Max | 434.48 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 18.69× of 8 |
| Slot occupancy | 233.7% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 39 |
| Mean TTFT per replica | 5.142 s |
| Prefix-cache hit per replica | 11.0% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **GPU hardware (nvidia-smi)** | 73 samples · serving-replica nvidia-smi |
| GPU utilization | 94.2 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 70.7 W (min 30.3 / max 73.8) |
| GPU temperature | 75.9 C (min 60.0 / max 80.0) |
| GPU memory used | 20,992 MiB (min 20,763 / max 20,995) |
| **Quality** |  |
| Overall extraction score | 0.0154 (sd 0.031) |
| Score min / max | 0.0000 / 0.0769 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 5 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 53 / 75 (70.7%) |
| Micro accuracy | 1.3% |
| Precision on answered | 1.9% |
| Clean subset | 1 / 28 |
| Suite field score (mean) | not captured |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-45f801408be08af6` | yes | 0.0000 | 334.2 | 109920 | 5153 | — |
| 2 | `DOC-eb2b56fe30dc35f4` | yes | 0.0000 | 337.5 | 85298 | 5274 | — |
| 3 | `DOC-ff3ceb691481f1bd` | yes | 0.0000 | 357.3 | 91432 | 5651 | — |
| 4 | `DOC-23f224263f6974c5` | yes | 0.0000 | 410.8 | 83736 | 7288 | — |
| 5 | `DOC-386ac6d669b7731c` | yes | 0.0769 | 434.5 | 93831 | 8179 | — |

_Generated 2026-10-12T02:17:08+00:00 by `sandbox run card`. Machine-readable twin: `sand42-check-5-merger-specialist-awq-1l4-c8.card.json`._
