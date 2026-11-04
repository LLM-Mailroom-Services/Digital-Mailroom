# Serving — `grid-50-merger-specialist-awq-2l4`

Stem `RUN-50-MERGER-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `grid-50-merger-specialist-awq-2l4` |
| task | `merger_agreement_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 50 |
| concurrency | 32 |
| wall_seconds | 340.849 |
| cold_boot_seconds | 0.407 |
| gpu_seconds | 341.256 |
| estimated_gpu_cost_usd | 0.151669 |
| **gpu_cost_per_document** | **0.00329715** |
| token-proxy cost_usd | 0.018641 |
| latency mean / p50 / p95 / max (s) | 100.162625 / 92.491563 / 167.228292 / 211.573933 |
| latency_sum_seconds | 4607.481 |
| latency_sum_over_wall | 13.52 |
| prompt_tokens | 429708 |
| completion_tokens | 44229 |
| total_tokens | 473937 |
| tokens_per_second | 1390.46 |
| slot_utilization | 0.4224 |
| busy_slot_seconds | 143.984 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
