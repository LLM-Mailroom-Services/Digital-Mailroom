# Serving — `sand40-100-insurance-claims-specialist-awq-2l4`

Stem `RUN-100-INSURANCE-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand40-100-insurance-claims-specialist-awq-2l4` |
| task | `insurance_claims_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 100 |
| concurrency | 32 |
| wall_seconds | 81.502 |
| cold_boot_seconds | 0.289 |
| gpu_seconds | 81.791 |
| estimated_gpu_cost_usd | 0.036352 |
| **gpu_cost_per_document** | **0.00036352** |
| token-proxy cost_usd | 0.015228 |
| latency mean / p50 / p95 / max (s) | 22.060185 / 20.420715 / 38.447552 / 58.460930 |
| latency_sum_seconds | 2206.018 |
| latency_sum_over_wall | 27.07 |
| prompt_tokens | 327213 |
| completion_tokens | 41631 |
| total_tokens | 368844 |
| tokens_per_second | 4525.58 |
| slot_utilization | 0.8458 |
| busy_slot_seconds | 68.938 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
