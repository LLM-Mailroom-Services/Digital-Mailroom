# Serving — `sand40-100-correspondence-specialist-awq-2l4`

Stem `RUN-100-CORRESPONDENCE-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand40-100-correspondence-specialist-awq-2l4` |
| task | `correspondence_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 100 |
| concurrency | 32 |
| wall_seconds | 27.519 |
| cold_boot_seconds | 0.631 |
| gpu_seconds | 28.150 |
| estimated_gpu_cost_usd | 0.012511 |
| **gpu_cost_per_document** | **0.00012511** |
| token-proxy cost_usd | 0.010524 |
| latency mean / p50 / p95 / max (s) | 11.523961 / 10.299583 / 20.294228 / 37.861527 |
| latency_sum_seconds | 1152.396 |
| latency_sum_over_wall | 41.88 |
| prompt_tokens | 277062 |
| completion_tokens | 17014 |
| total_tokens | 294076 |
| tokens_per_second | 10686.29 |
| slot_utilization | 1.3086 |
| busy_slot_seconds | 36.012 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
