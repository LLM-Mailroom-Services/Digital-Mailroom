# Serving — `sand40-probe-20-contracts-specialist-awq-2l4-64k`

Stem `RUN-20-CONTRACTS-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand40-probe-20-contracts-specialist-awq-2l4-64k` |
| task | `contracts_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 20 |
| concurrency | 32 |
| wall_seconds | 105.569 |
| cold_boot_seconds | 0.159 |
| gpu_seconds | 105.728 |
| estimated_gpu_cost_usd | 0.046990 |
| **gpu_cost_per_document** | **0.0023495** |
| token-proxy cost_usd | 0.008661 |
| latency mean / p50 / p95 / max (s) | 91.704538 / 94.926445 / 128.941250 / 135.374952 |
| latency_sum_seconds | 1834.091 |
| latency_sum_over_wall | 17.37 |
| prompt_tokens | 142889 |
| completion_tokens | 33650 |
| total_tokens | 176539 |
| tokens_per_second | 1672.26 |
| slot_utilization | 0.5429 |
| busy_slot_seconds | 57.315 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
