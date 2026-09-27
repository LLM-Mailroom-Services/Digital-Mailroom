# Serving headline metrics — `run-20-contracts-awq-c8`

Cost + token capture for local/Modal vs API (OpenRouter) comparison. Machine-
readable twin:
[`serving/run-20-contracts-awq-c8.serving.json`](serving/run-20-contracts-awq-c8.serving.json)
produced by `sandbox metrics serving-record --run run-20-contracts-awq-c8`
(`job.metrics.serving_record_from_store`: `record_from_run` base + wall/concurrency/
latency_sum + SAND-028-1 idle block), so the shapes are directly comparable with the
API bucket base fields from `record_from_run`.

Engine: `Qwen/Qwen3-8B-AWQ` (AWQ, 1x L4, `max_model_len=32768`) | task
`contracts_specialist` | n=20 | dataset fingerprint `9c87afb3c10c` |
concurrency 8.

## Headline cost & token metrics

| metric | Modal (this run) | API (fill on OpenRouter run) |
|---|---|---|
| prompt_tokens | 194388 | |
| completion_tokens | 25614 | |
| total_tokens | 220002 | |
| prompt_tokens/doc | 9719.4 | |
| completion_tokens/doc | 1280.7 | |
| total_tokens/doc | 11000.1 | |
| e2e latency mean (s) | 532.049 | |
| e2e latency p50 (s) | 619.629 | |
| e2e latency max (s) | 817.619 | |
| TTFT (s) | not measured (never inferred) | |
| throughput total (tok/s) | 143.98 | |
| **token-proxy cost (USD)** | **0.009161** | |
| token-proxy cost/doc | 4.5807e-04 | |
| token-proxy cost / 1M tok | 0.041643 | |
| **GPU cost (USD)** | **0.375376** | n/a (API is per-token) |
| GPU cost/doc | 0.0187688 | n/a |
| GPU cost / 1M tok | 1.706239 | n/a |
| gpu_seconds (wall+cold boot) | 1689.19 | n/a |
| wall_seconds / concurrency | 1528.047 / 8 | n/a |
| cold_boot_seconds | 161.144 | n/a |

## Derived economics (Modal)

- GPU rate: $0.80/hr (L4); billed window 1689.19s.
- Effective throughput: 42.6 docs/hr (billed), 47.1 docs/hr (busy only).
- Token-proxy (OpenRouter list 0.03 in / 0.13 out per 1M) is 2.44% of the GPU
  cost — the L4, not the tokens, dominates the price of a long-contract run.

## Interpretation

- **Concurrency is effective:** sum(per-doc latency) 10641s / wall 1528s =
  **6.96x** at concurrency 8 — batched, not serialized.
- **Long-contract decode is the cost driver.** p50 619.6s vs correspondence's
  35.0s at the same concurrency: 8 concurrent ~8k-prompt + long-decode
  sequences share one L4, so per-doc latency is far higher and the wall is
  dominated by decode, not prefill.
- **Accuracy is not comparable here:** all rows score 0.0 because the Hub
  `ground_truth` config does not carry the contract extraction schema (see
  [`RUN-20-CONTRACTS-AWQ-C8-REPORT.md`](RUN-20-CONTRACTS-AWQ-C8-REPORT.md)).
  Treat this file as a *serving/cost* comparison, not an accuracy one.
- 17/20 ok; the 3 residual errors are `LengthFinishReasonError` at the 8192
  budget (the 16384-window `400` is fixed by the 32768 deploy).