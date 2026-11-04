# Serving — `grid-50-correspondence-specialist-awq-2l4`

Stem `RUN-50-CORRESPONDENCE-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `grid-50-correspondence-specialist-awq-2l4` |
| task | `correspondence_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 50 |
| concurrency | 32 |
| wall_seconds | 13.956 |
| cold_boot_seconds | 0.297 |
| gpu_seconds | 14.253 |
| estimated_gpu_cost_usd | 0.006335 |
| **gpu_cost_per_document** | **0.0001267** |
| token-proxy cost_usd | 0.005098 |
| latency mean / p50 / p95 / max (s) | 11.134810 / 10.732824 / 18.455351 / 22.278216 |
| latency_sum_seconds | 556.740 |
| latency_sum_over_wall | 39.89 |
| prompt_tokens | 134797 |
| completion_tokens | 8106 |
| total_tokens | 142903 |
| tokens_per_second | 10239.54 |
| slot_utilization | 1.2466 |
| busy_slot_seconds | 17.398 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
