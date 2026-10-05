# Serving — `grid-50-correspondence-specialist-awq-1l4`

Stem `RUN-50-CORRESPONDENCE-AWQ-1L4-C8`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `grid-50-correspondence-specialist-awq-1l4` |
| task | `correspondence_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×1 |
| n | 50 |
| concurrency | 8 |
| wall_seconds | 40.559 |
| cold_boot_seconds | 0.333 |
| gpu_seconds | 40.892 |
| estimated_gpu_cost_usd | 0.009087 |
| **gpu_cost_per_document** | **0.00018174** |
| token-proxy cost_usd | 0.005095 |
| latency mean / p50 / p95 / max (s) | 7.284221 / 6.601969 / 11.707445 / 19.762077 |
| latency_sum_seconds | 364.211 |
| latency_sum_over_wall | 8.98 |
| prompt_tokens | 134797 |
| completion_tokens | 8084 |
| total_tokens | 142881 |
| tokens_per_second | 3522.79 |
| slot_utilization | 1.1225 |
| busy_slot_seconds | 45.526 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
