# Serving — `grid-50-insurance-claims-specialist-awq-1l4`

Stem `RUN-50-INSURANCE-AWQ-1L4-C8`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `grid-50-insurance-claims-specialist-awq-1l4` |
| task | `insurance_claims_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×1 |
| n | 50 |
| concurrency | 8 |
| wall_seconds | 87.417 |
| cold_boot_seconds | 0.322 |
| gpu_seconds | 87.739 |
| estimated_gpu_cost_usd | 0.019498 |
| **gpu_cost_per_document** | **0.00038996** |
| token-proxy cost_usd | 0.00746 |
| latency mean / p50 / p95 / max (s) | 15.117111 / 13.958155 / 26.707036 / 36.729685 |
| latency_sum_seconds | 755.856 |
| latency_sum_over_wall | 8.65 |
| prompt_tokens | 162525 |
| completion_tokens | 19876 |
| total_tokens | 182401 |
| tokens_per_second | 2086.56 |
| slot_utilization | 1.0808 |
| busy_slot_seconds | 94.482 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
