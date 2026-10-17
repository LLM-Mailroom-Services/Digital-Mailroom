# Serving — `sand42-50-insurance-claims-specialist-awq-1l4-c16`

Stem `RUN-50-INSURANCE-AWQ-1L4-C16`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand42-50-insurance-claims-specialist-awq-1l4-c16` |
| task | `insurance_claims_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×1 |
| n | 50 |
| concurrency | 16 |
| wall_seconds | 107.332 |
| cold_boot_seconds | 0.311 |
| gpu_seconds | 107.643 |
| estimated_gpu_cost_usd | 0.023921 |
| **gpu_cost_per_document** | **0.00047842** |
| token-proxy cost_usd | 0.007718 |
| latency mean / p50 / p95 / max (s) | 22.390650 / 21.412539 / 31.897680 / 48.613538 |
| latency_sum_seconds | 1119.533 |
| latency_sum_over_wall | 10.43 |
| prompt_tokens | 165315 |
| completion_tokens | 21216 |
| total_tokens | 186531 |
| tokens_per_second | 1737.89 |
| slot_utilization | 0.6519 |
| busy_slot_seconds | 69.971 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
