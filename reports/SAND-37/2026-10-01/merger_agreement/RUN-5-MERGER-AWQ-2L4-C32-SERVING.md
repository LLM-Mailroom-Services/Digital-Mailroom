# Serving — `sand40-check-5-merger-specialist-awq-2l4`

Stem `RUN-5-MERGER-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand40-check-5-merger-specialist-awq-2l4` |
| task | `merger_agreement_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 5 |
| concurrency | 32 |
| wall_seconds | 284.493 |
| cold_boot_seconds | 0.359 |
| gpu_seconds | 284.852 |
| estimated_gpu_cost_usd | 0.126601 |
| **gpu_cost_per_document** | **0.025320** |
| token-proxy cost_usd | 0.019938 |
| latency mean / p50 / p95 / max (s) | 324.267980 / 268.796788 / 465.657994 / 465.657994 |
| latency_sum_seconds | 1621.340 |
| latency_sum_over_wall | 5.70 |
| prompt_tokens | 556273 |
| completion_tokens | 24996 |
| total_tokens | 581269 |
| tokens_per_second | 2043.18 |
| slot_utilization | 0.1781 |
| busy_slot_seconds | 50.667 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
