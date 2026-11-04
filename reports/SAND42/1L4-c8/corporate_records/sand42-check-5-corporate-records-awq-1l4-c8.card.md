# Corporate Records — 1× L4 · C8 · n=5

**Run:** `sand42-check-5-corporate-records-awq-1l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | corporate_records_specialist |
| Prompt | corporate_records_specialist_simplified |
| Temperature | 0.1 (vendored call site) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 15,000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 5 docs (fingerprint 34c1303db918) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand42-check-5-corporate-records-awq-1l4-c8` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 5 |
| Spec hash | 53132be4… |
| **Time** |  |
| Wall (busy) | 24.94 s |
| GPU seconds | 24.30 s |
| Cold boot | 0.33 s |
| **Cost** |  |
| Busy-window GPU $ | $0.005543 |
| Billed GPU $ | $0.005400 |
| Billed seconds | 24.30 s |
| Idle $ | $0.004211 (18.95 s) |
| Cost per document | $0.001080 |
| Cost per ok document | $0.001080 |
| Cost per 1M tokens | $0.2582 |
| **Tokens** |  |
| Prompt tokens | 20,069 |
| Completion tokens | 841 (4.0%) |
| Total tokens | 20,910 |
| Tokens per document | 4,182 |
| Per document: instructions + template | 2,214 (52.9%) |
| Per document: document text | 1,799 (43.0%) |
| Per document: output | 168 (4.0%) |
| Instruction tokens per model call | 2,214 over 5 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 210 / 210 |
| **Throughput** |  |
| Tokens / second | 838.3 |
| Tokens / second per L4 | 838.3 |
| Documents / minute | 12.03 |
| **Latency (per document, ok rows)** |  |
| Mean | 9.59 s |
| p50 | 9.34 s |
| p95 | 10.54 s |
| Max | 10.54 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 1.92× of 8 |
| Slot occupancy | 24.0% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 5 |
| Mean TTFT per replica | 2.103 s |
| Prefix-cache hit per replica | 31.8% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **GPU hardware (nvidia-smi)** | 3 samples · serving-replica nvidia-smi |
| GPU utilization | 32.0 % mean (p95 96.0 / peak 96.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 43.2 W (min 28.4 / max 72.0) of 72 W cap |
| GPU memory bandwidth | 33.3 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,865 MHz (min 1,515 / max 2,040) |
| GPU temperature | 42.3 C (min 39.0 / max 45.0) |
| GPU memory used | 20,945 MiB (min 20,790 / max 21,022) |
| **Quality** |  |
| Overall extraction score | 0.6292 (sd 0.177) |
| Score min / max | 0.4103 / 0.8205 |
| Scoring method | `suite` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 5 |

## Figure

![Corporate Records run dashboard](sand42-check-5-corporate-records-awq-1l4-c8.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-37152a33cfb70d37` | yes | 0.4103 | 9.3 | 2902 | 161 | — |
| 2 | `DOC-f134b9491efc5c57` | yes | 0.7949 | 9.3 | 2865 | 153 | — |
| 3 | `DOC-e478fa89043a29e3` | yes | 0.8205 | 9.3 | 2910 | 151 | — |
| 4 | `DOC-0a8eb16fff7e67ca` | yes | 0.6923 | 9.4 | 5246 | 166 | — |
| 5 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 10.5 | 6146 | 210 | — |

_Generated 2026-10-12T18:00:34+00:00 by `sandbox run card`. Machine-readable twin: `sand42-check-5-corporate-records-awq-1l4-c8.card.json`._
