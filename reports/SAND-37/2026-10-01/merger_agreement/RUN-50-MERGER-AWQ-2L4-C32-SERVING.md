# Serving — `sand40-50-merger-specialist-awq-2l4`

Stem `RUN-50-MERGER-AWQ-2L4-C32`. Model `Qwen/Qwen3-8B-AWQ`. TTFT is never inferred.

| metric | value |
| --- | --- |
| run_id | `sand40-50-merger-specialist-awq-2l4` |
| task | `merger_agreement_specialist` |
| model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` ×2 |
| n | 50 |
| concurrency | 32 |
| wall_seconds | 1658.838 |
| cold_boot_seconds | 0.345 |
| gpu_seconds | 1659.183 |
| estimated_gpu_cost_usd | 0.737415 |
| **gpu_cost_per_document** | **0.014748** |
| token-proxy cost_usd | 0.196244 |
| latency mean / p50 / p95 / max (s) | 1120.395534 / 1044.398393 / 2067.440566 / 2264.440750 |
| latency_sum_seconds | 56019.777 |
| latency_sum_over_wall | 33.77 |
| prompt_tokens | 5334445 |
| completion_tokens | 278545 |
| total_tokens | 5612990 |
| tokens_per_second | 3383.69 |
| slot_utilization | 1.0553 |
| busy_slot_seconds | 1750.618 |
| ttft_seconds | — |
| ttft_note | TTFT never inferred (served locally; do not infer from e2e) |

Machine-readable sibling: same stem with `.serving.json`.
