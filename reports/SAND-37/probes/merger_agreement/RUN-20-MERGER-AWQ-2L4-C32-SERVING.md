# Serving — `sand40-probe-20-merger-specialist-awq-2l4-64k`

Stem `RUN-20-MERGER-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand40-probe-20-merger-specialist-awq-2l4-64k` |
| task | `merger_agreement_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 20 |
| concurrency | 32 |
| wall_seconds | 1472.968 |
| cold_boot_seconds | 0.136 |
| gpu_seconds | 1473.104 |
| estimated_gpu_cost_usd | 0.654713 |
| **gpu_cost_per_document** | **0.032736** |
| token-proxy cost_usd | 0.068945 |
| latency mean / p50 / p95 / max (s) | 819.281511 / 760.858609 / 1133.906225 / 1820.544089 |
| latency_sum_seconds | 16385.630 |
| latency_sum_over_wall | 11.12 |
| prompt_tokens | 1929564 |
| completion_tokens | 85063 |
| total_tokens | 2014627 |
| tokens_per_second | 1367.73 |
| slot_utilization | 0.3476 |
| busy_slot_seconds | 512.051 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
