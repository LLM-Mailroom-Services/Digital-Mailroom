# DMR-068 — L4 scale matrix: fixed-doc-size throughput probe (protocol)

Status: **protocol ready; GPU cells pending spend approval** (est. **$13.08** capped
at $15, credit-covered today). Research: vLLM v0.29.0 docs + Qwen official
benchmarks + NVIDIA L4 + Modal pricing (all cited inline, fetched 2026-09-16).

## Why (from run-50)

`run-50-modal-hf` on 2–3 warm L4s (client concurrency 16) delivered ≈0.65
docs/min aggregate, per-engine generation 8.7–13.9 tok/s, prefix-cache 56–58 %,
KV ≤ 30 % idle. Per-doc ≈5 serial generations (up to 2048 out-tokens) at ~15
tok/s → 2.5–3.5 min/call. Pilot (1×L4, short fixture docs) ≈4.1 docs/min —
confounded by document size. Qwen3-8B on L4 is **HBM-bandwidth-bound**: 8.19B ×
2 B ≈ 16.4 GB weight read/token ÷ 300 GB/s (NVIDIA L4 spec) ≈ **18 tok/s fp16
single-sequence ceiling**; the empirical 8.7–13.9 tok/s sits below it at partial
fill. vLLM v0.29.0 scheduler caps (`max_num_batched_tokens` 2048,
`max_num_seqs` 128 defaults; repo sets 256) are **non-binding** below ~2048
in-flight decodes (engine args + scheduler source, v0.29.0) — and chunked
prefill is ON by default; `max_num_seqs`/`max-num-batched-tokens` stay put.

## The lever with measured backing: AWQ

- v0.29.0 quantization table: AWQ ✅ Ada (L4 is Ada-Lovelace; the brief's
  "Ampere" read was wrong), Marlin (AWQ) ✅ Ada (quantization docs).
- Official Qwen3-8B benchmark (SGLang, H20): decode BF16 81.73 tok/s vs
  AWQ-INT4 144.11 = **1.76×** (speed benchmark, GitHub QwenLM/Qwen3).
- Memory-bound arithmetic on L4 predicts ~1.8–2× (weights ÷2 → ~24 tok/s/engine
  fp16-equivalent); `Qwen/Qwen3-8B-AWQ` is a drop-in Hub model id
  (vLLM auto-detects the checkpoint quant config; `--quantization awq` is
  belt-and-braces). Gate: **accuracy must stay ≥ 98 %** (AWQ cell).

## Fixed-doc-size fixture (removes the pilot confound)

Run-50 docs are median 21.6k chars — buckets of 2k/6k/12k chars are built by
deterministic head-truncation of run-50 rows (same pinned revision; a fixture
tokenizer check so prompts ≈ 1.5k/4.5k/9k tokens). One `sandbox datasets
prepare` step produces `data/fixtures/scale/` (byte-identical guarantee per
spec); specs below reference it via `dataset.provider: file`.

## The matrix (7 cells)

Fleet pinned per cell: `MODAL_VLLM_MIN_CONTAINERS = MODAL_VLLM_MAX_CONTAINERS = R`
(run-50's 2-of-4-warm drift is not allowed in a measurement). Cost:
`R × T_h × $0.80` (Modal L4 $0.000222/s ≈ $0.80/GPU-hr, region multiplier
1.15–1.75 unless overridden) + $0.20·R startup/scale taper; teardown via
`deploy/teardown_vllm.sh` after every cell. Wall model (worst case 2048
out-tokens/call, 5 calls/doc): `T = D×5×2048 / (R×g)` with g = 12 tok/s bf16
(×0.85 @c8, ×1.15 @c32 fill factors; AWQ 24).

| cell | replicas | client conc. | docs (2k/6k/12k) | g (tok/s/eng) | est. wall | est. cost |
| --- | --- | --- | --- | --- | --- | --- |
| A1 baseline | 1 | 16 | 6 (2/2/2) | 12 bf16 | 1.4 h | $1.34 |
| B1 | 2 | 8 | 6 | 10.2 bf16 | 0.8 h | $1.74 |
| B2 | 2 | 16 | 6 | 12 bf16 | 0.7 h | $1.54 |
| B3 | 2 | 32 | 12 (4/4/4) | 13.8 bf16 | 1.2 h | $2.38 |
| C1 | 4 | 16 | 6 | 12 bf16 | 0.4 h | $1.94 |
| C2 | 4 | 32 | 12 | 13.8 bf16 | 0.6 h | $2.78 |
| **D1 AWQ** | 4 | 16 | 6 | 24 awq | 0.2 h | $1.37 |
| Σ | | | | | | | **$13.08** (≤ $15; ~$3.3 if avg out ≈ 512 tok) |

Exemplar specs shipped: `scale-c1-4xl4-c16.yaml` (bf16 baseline cell) and
`scale-d1-awq-4xl4-c16.yaml` (the A/B delta — quant is the ONLY change).

## Measurement contract (which number, where)

- **docs/min, per-item E2E latency, retries, correctness** → `items.jsonl` per
  run (primary truth; runner wall-clock).
- **gen tok/s, prompt tok/s, prefix-cache hit %, KV util** → engine log
  throughput windows (`modal app logs sandbox-vllm`) + `/metrics`
  (`vllm:generation_tokens_total`, `vllm:time_to_first_token_seconds`,
  `vllm:requests_running`) during each cell.
- **out-tokens/call, calls/doc** → runner usage fields / Langfuse trace
  (replaces the 2048 worst case with the real O).
- **cost** → `modal billing summary` per cell window.
- Fixed-noise guards: pinned fleet, same seed, warm-up ping before timing,
  per-cell g reported alongside docs/min (separable fill vs engine effects).

## Decision rule (pass criteria)

1. A/B **D1 vs C1** (same fleet, quant the only delta): AWQ is the default
   engine config **iff** ≥ 1.5× docs/min AND doc-class accuracy ≥ 98 %.
2. Replica scaling at fixed concurrency is linear-until-plateau: doubling
   replicas must give ≥ 1.5× docs/min to justify marginal cost; else concurrency
   (B3/C2) is the bottleneck, not the engine — stop adding GPUs.
3. Beyond the matrix: promote the winning config into `run-300` (DMR-063).

## Pending

- Fixture build step (`sandbox datasets prepare` for `data/fixtures/scale/`).
- GPU cell runs (→ spend approval; teardown + guard matrix already shipping
  with DMR-063).