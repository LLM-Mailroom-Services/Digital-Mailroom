# Serving — `sand42-50-insurance-claims-specialist-awq-2l4-c32`

Stem `RUN-50-INSURANCE-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand42-50-insurance-claims-specialist-awq-2l4-c32` |
| task | `insurance_claims_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 50 |
| concurrency | 32 |
| wall_seconds | 75.887 |
| cold_boot_seconds | 0.348 |
| gpu_seconds | 76.235 |
| estimated_gpu_cost_usd | 0.033882 |
| **gpu_cost_per_document** | **0.00067764** |
| token-proxy cost_usd | 0.007637 |
| latency mean / p50 / p95 / max (s) | 25.573472 / 23.959121 / 40.077063 / 46.453676 |
| latency_sum_seconds | 1278.674 |
| latency_sum_over_wall | 16.85 |
| prompt_tokens | 165315 |
| completion_tokens | 20600 |
| total_tokens | 185915 |
| tokens_per_second | 2449.89 |
| slot_utilization | 0.5266 |
| busy_slot_seconds | 39.959 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
