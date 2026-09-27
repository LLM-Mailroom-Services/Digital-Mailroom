# Serving headline metrics — `run-20-correspondence-awq-c8`

Cost + token capture for local/Modal vs API (OpenRouter) comparison. Machine-
readable twin:
[`serving/run-20-correspondence-awq-c8.serving.json`](serving/run-20-correspondence-awq-c8.serving.json)
produced by `sandbox metrics serving-record --run run-20-correspondence-awq-c8`
(`job.metrics.serving_record_from_store`), so the shapes are directly comparable with
the API bucket base fields from `record_from_run`.

Engine: `Qwen/Qwen3-8B-AWQ` (AWQ, 1x L4, `max_model_len=32768`) | task
`correspondence_specialist` | n=20 | dataset fingerprint `285f423d3708`
(identical draw to `run-20-correspondence-awq`, re-run at concurrency 8).

## Headline cost & token metrics

| metric | Modal (this run) | API (fill on OpenRouter run) |
|---|---|---|
| prompt_tokens | 39058 | |
| completion_tokens | 3619 | |
| total_tokens | 42677 | |
| prompt_tokens/doc | 1952.9 | |
| completion_tokens/doc | 180.95 | |
| total_tokens/doc | 2133.85 | |
| e2e latency mean (s) | 30.23227085 | |
| e2e latency p50 (s) | 34.993895 | |
| e2e latency max (s) | 38.517704 | |
| TTFT (s) | not measured (never inferred) | |
| throughput total (tok/s) | 472.09 | |
| **token-proxy cost (USD)** | **0.001642** | |
| token-proxy cost/doc | 8.211e-05 | |
| token-proxy cost / 1M tok | 0.0385 | |
| **GPU cost (USD)** | **0.055620** | n/a (API is per-token) |
| GPU cost/doc | 0.002781 | n/a |
| GPU cost / 1M tok | 1.3033 | n/a |
| gpu_seconds (wall+cold boot) | 250.29 | n/a |
| wall_seconds / concurrency | 90.401 / 8 | n/a |
| cold_boot_seconds | 159.887 | n/a |

## Derived economics (Modal)

- GPU rate: $0.80/hr (L4); billed window 250.29s.
- Effective throughput: 287.6 docs/hr (billed), 796.4 docs/hr (busy only).
- Token-proxy (OpenRouter list 0.03 in / 0.13 out per 1M) is 2.95% of the GPU
  cost.
- Concurrency 8 vs 5 (same draw): wall 90.401s vs 253.692s, GPU cost $0.055620
  vs $0.114231 — roughly half the cost at the same work.