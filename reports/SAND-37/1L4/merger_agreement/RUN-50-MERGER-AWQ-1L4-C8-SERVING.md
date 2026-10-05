# Serving — `grid-50-merger-specialist-awq-1l4`

Stem `RUN-50-MERGER-AWQ-1L4-C8`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `grid-50-merger-specialist-awq-1l4` |
| task | `merger_agreement_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×1 |
| n | 50 |
| concurrency | 8 |
| wall_seconds | 588.411 |
| cold_boot_seconds | 0.994 |
| gpu_seconds | 589.405 |
| estimated_gpu_cost_usd | 0.130979 |
| **gpu_cost_per_document** | **0.00284737** |
| token-proxy cost_usd | 0.018582 |
| latency mean / p50 / p95 / max (s) | 57.872950 / 51.255857 / 109.716175 / 146.059443 |
| latency_sum_seconds | 2662.156 |
| latency_sum_over_wall | 4.52 |
| prompt_tokens | 428281 |
| completion_tokens | 44106 |
| total_tokens | 472387 |
| tokens_per_second | 802.82 |
| slot_utilization | 0.5655 |
| busy_slot_seconds | 332.769 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
