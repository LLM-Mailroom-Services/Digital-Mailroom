# Serving — `sand42-50-merger-specialist-awq-2l4-c32`

Stem `RUN-50-MERGER-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand42-50-merger-specialist-awq-2l4-c32` |
| task | `merger_agreement_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 50 |
| concurrency | 32 |
| wall_seconds | 1937.171 |
| cold_boot_seconds | 0.522 |
| gpu_seconds | 1937.693 |
| estimated_gpu_cost_usd | 0.861197 |
| **gpu_cost_per_document** | **0.017224** |
| token-proxy cost_usd | 0.188075 |
| latency mean / p50 / p95 / max (s) | 951.547533 / 935.459782 / 1491.484186 / 1630.016426 |
| latency_sum_seconds | 47577.377 |
| latency_sum_over_wall | 24.56 |
| prompt_tokens | 4867606 |
| completion_tokens | 323439 |
| total_tokens | 5191045 |
| tokens_per_second | 2679.70 |
| slot_utilization | 0.7675 |
| busy_slot_seconds | 1486.793 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
