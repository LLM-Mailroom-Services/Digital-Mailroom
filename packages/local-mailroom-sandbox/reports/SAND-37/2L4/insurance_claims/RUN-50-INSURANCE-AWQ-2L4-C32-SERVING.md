# Serving — `grid-50-insurance-claims-specialist-awq-2l4`

Stem `RUN-50-INSURANCE-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `grid-50-insurance-claims-specialist-awq-2l4` |
| task | `insurance_claims_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 50 |
| concurrency | 32 |
| wall_seconds | 35.600 |
| cold_boot_seconds | 0.326 |
| gpu_seconds | 35.926 |
| estimated_gpu_cost_usd | 0.015967 |
| **gpu_cost_per_document** | **0.00031934** |
| token-proxy cost_usd | 0.007478 |
| latency mean / p50 / p95 / max (s) | 20.931632 / 19.635036 / 32.625674 / 33.369161 |
| latency_sum_seconds | 1046.582 |
| latency_sum_over_wall | 29.40 |
| prompt_tokens | 162525 |
| completion_tokens | 20014 |
| total_tokens | 182539 |
| tokens_per_second | 5127.50 |
| slot_utilization | 0.9187 |
| busy_slot_seconds | 32.706 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
