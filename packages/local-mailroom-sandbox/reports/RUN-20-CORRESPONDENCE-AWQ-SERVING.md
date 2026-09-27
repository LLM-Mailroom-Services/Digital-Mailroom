# Serving headline metrics — `run-20-correspondence-awq`

Cost + token capture for local/Modal vs API (OpenRouter) comparison. Machine-
readable twin: [`serving/run-20-correspondence-awq.serving.json`](serving/run-20-correspondence-awq.serving.json)
produced by `sandbox metrics serving-record --run run-20-correspondence-awq`
(`job.metrics.serving_record_from_store`), so the shapes are directly comparable with
the API bucket base fields from `record_from_run`.

Engine: `Qwen/Qwen3-8B-AWQ` (AWQ, 1x L4, `max_model_len=32768`) | task
`correspondence_specialist` | n=20 | dataset fingerprint `285f423d3708`.

## Headline cost & token metrics

| metric | Modal (this run) | API (fill on OpenRouter run) |
|---|---|---|
| prompt_tokens | 39058 | |
| completion_tokens | 3424 | |
| total_tokens | 42482 | |
| prompt_tokens/doc | 1952.9 | |
| completion_tokens/doc | 171.2 | |
| total_tokens/doc | 2124.1 | |
| e2e latency mean (s) | 61.40090715 | |
| e2e latency p50 (s) | 23.29779 | |
| e2e latency max (s) | 187.642898 | |
| TTFT (s) | not measured (never inferred) | |
| throughput total (tok/s) | 167.46 | |
| **token-proxy cost (USD)** | **0.001617** | |
| token-proxy cost/doc | 8.085e-05 | |
| token-proxy cost / 1M tok | 0.0381 | |
| **GPU cost (USD)** | **0.114231** | n/a (API is per-token) |
| GPU cost/doc | 0.00571155 | n/a |
| GPU cost / 1M tok | 2.6889 | n/a |
| gpu_seconds (wall+cold boot) | 514.04 | n/a |
| wall_seconds / concurrency | 253.692 / 5 | n/a |
| cold_boot_seconds | 260.348 | n/a |

## Derived economics (Modal)

- GPU rate: $0.80/hr (L4); billed window 514.04s.
- Effective throughput: 140.1 docs/hr (billed), 283.8 docs/hr (busy only).
- Token-proxy (OpenRouter list 0.03 in / 0.13 out per 1M) is 1.42% of the GPU cost.
- Break-even: token-proxy would need to reach $0.1142 to match GPU spend, i.e. 70.6x the list price.

## Headline score (same row)

- overall_extraction_score = **0.08934** | exact_match = 0.08934 | error_count = 0 | n = 20

## Comparison procedure (API leg)

1. Run the same 20-doc draw on the API provider (OpenRouter opt-in) so the dataset fingerprint matches (`285f423d3708`).
2. The API run emits the same serving-record shape; compare with `sandbox metrics compare --runs local,modal,api` or `get_suite('local_vs_api')` (offline; no API key needed to compare).
3. TTFT is never inferred for the local bucket; if the API returns usage-based TTFT it appears only there, and the compare table marks local n/a rather than fabricating it.
