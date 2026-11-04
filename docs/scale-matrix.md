# DMR-068 — L4 scale matrix: fixed-doc-size throughput probe (protocol)

Status: **protocol ready; GPU cells pending spend approval** (est. **$13.08** capped
at $15, credit-covered today). Tracked in hub issue
[LLM-Mailroom-Services/mailroom-issues#205](https://github.com/LLM-Mailroom-Services/mailroom-issues/issues/205)
(owner, spend decision, status). Research: vLLM v0.29.0 docs + Qwen official
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
`max_num_seqs` 128 defaults; **specialist / long-prompt deploy default is
6** — see SAND-030; short-doc scale cells keep YAML `max_num_seqs: 256` and
must export `MODAL_VLLM_MAX_NUM_SEQS=256` at deploy) are **non-binding** below
~2048 in-flight decodes for short fixtures (engine args + scheduler source,
v0.29.0) — and chunked prefill is ON by default. For ~8–10k-token specialist
prompts, `max_num_seqs=6` **is** binding: 8 concurrent long-decode sequences
exhaust L4 KV and cliff latency.

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

## The matrix (7 baseline cells + 3 SAND-022 extensions)

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
| Σ (baseline) | | | | | | | **$13.08** (≤ $15; ~$3.3 if avg out ≈ 512 tok) |

### SAND-022 incremental cells (execution pending spend)

Adds three runnable specs on top of the baseline matrix. Original **$13.08**
unchanged; incremental estimates below assume the same wall model and L4
$0.80/GPU-hr (+ region multiplier unless pinned).

| cell | replicas / fleet | client conc. | docs (2k/6k/12k) | g (tok/s/eng) | est. wall | est. cost |
| --- | --- | --- | --- | --- | --- | --- |
| **E1 FP8-L4** | 4×1×L4 | 16 | 6 | 22 fp8 (native Ada) | 0.2 h | $1.37 |
| **F1 Qwen3.5-9B FP8** | 4×1×L4 | 16 | 6 | TBD (hybrid arch) | 0.2 h | $1.37 |
| **G1 Qwen3.5-35B TP2** | 1×L4:2 (`tp_size=2`) | 16 | 6 | TBD (PCIe TP) | 0.4 h | $0.69 |
| Σ (incremental) | | | | | | | **~$3.43** (deferred) |

Exemplar specs shipped (baseline): `scale-c1-4xl4-c16.yaml` (bf16 baseline
cell) and `scale-d1-awq-4xl4-c16.yaml` (the A/B delta — quant is the ONLY
change).

SAND-022 specs (YAML only until spend reopens):

- `scale-e1-fp8-l4-4xl4-c16.yaml` — `Qwen/Qwen3-8B-FP8` on **L4** (not H100)
- `scale-f1-qwen35-9b-fp8-4xl4-c16.yaml` — `Qwen/Qwen3.5-9B` online FP8,
  `tp_size: 1` (catalog row from SAND-021 / #43)
- `scale-g1-qwen35-35b-tp2-1xl4x2-c16.yaml` — `Qwen/Qwen3.5-35B-A3B` FP8 on
  `L4:2`, tensor parallel over PCIe

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

## Container topology (SAND-023 / SAND-030)

Default for models that fit one L4 (weights ≤ ~20 GB, including Qwen3-8B
bf16/AWQ/FP8 and Qwen3.5-9B FP8): **1 GPU per container, scale containers**.

| Goal | Deploy | Why |
| --- | --- | --- |
| Singular L4 | `MAX_CONTAINERS=1`, `GPU=L4`, `TP=1` | Independent KV, scale-to-zero, no PCIe all-reduce |
| Second L4 (8B) | `MAX_CONTAINERS=2`, still `GPU=L4` / `TP=1` | Data parallel — two vLLM replicas; Modal `@web_server` distributes (round-robin style). Each replica keeps `max_num_seqs=6`, APC, eager |
| Model won't fit ~20 GB | `GPU=L4:2` + `TP_SIZE=2` **or** prefer **L40S** (48 GB unified, Ada FP8, ~$1.95/hr vs 2×L4 ~$1.60/hr) | TP over PCIe (no NVLink) is a last resort — G1 cell measures it vs two independent 1×L4 replicas at equal spend |

Do **not** use tensor parallelism for 8B on two L4s: communication overhead
without a meaningful latency win. APC is per-replica (shared prefixes cached
twice); concurrency gain outweighs duplicate cache for specialist prompts.

Hub epic: LLM-Mailroom-Services/mailroom-issues#193 (program tracker #205). G1 (`scale-g1-…`) is
the measured decision cell once spend reopens.

## Pending

- Fixture build step (`sandbox datasets prepare` for `data/fixtures/scale/` —
  includes `e1.jsonl`, `f1.jsonl`, `g1.jsonl` for SAND-022 cells).
- GPU cell runs (→ spend approval; teardown + guard matrix already shipping
  with DMR-063). **SAND-022 E1/F1/G1 specs are runnable but not executed** while
  Modal spend is on hold; each YAML carries `cost_cap_usd` + `max_wall_seconds`
  abort guards.