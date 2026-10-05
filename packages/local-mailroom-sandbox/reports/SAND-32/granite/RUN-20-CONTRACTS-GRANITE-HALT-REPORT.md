# HALT report — Granite vs Qwen 20-per-specialist sweep (stopped 2026-09-27 ~03:31 CDT)

The Granite sweep was **HALTED** during its first run (`run-20-contracts-granite`:
8/20 docs, **0 ok / 8 errors**) before it could burn further credits. No further
Granite runs (2–5) were dispatched. The Modal app is stopped; no GPU billing accrues.

## What was failing

| | |
| --- | --- |
| run | `run-20-contracts-granite` (sweep 1/5) |
| engine | `ibm-granite/granite-4.2-8b-fp8`, vLLM `v0.29.0`, 1×L4, `compressed-tensors`, 32768 |
| posture at halt | concurrency 8, MIN=MAX=1 pinned, scaledown 120 |
| outcome | **killed by operator at 8/20: 0 ok, 8 errors** (~03:13–03:31 CDT) |
| per-doc pattern | docs 1–5: ~195 s each, strictly serial, then error; docs 6–8: ~5 s fast errors |
| engine logs | **zero** errors/exceptions/500s (per-request lines suppressed by `--no-enable-log-requests`) |
| harness logs | **zero** `llm_retry` warnings, **zero** `structured_output_parse_error` errors |

## Root cause (prime hypothesis, evidence-backed)

**Granite-4.2 thinking-mode × harness guided-JSON pipeline mismatch.**
The harness calls `with_structured_output(..., method="json_schema")` (guided
decoding). Smoke probes the same morning proved Granite-4.2-FP8 on this image
thinks out loud: plain chat returned thinking chatter as content
(`reasoning_content: None` — the native `granite` parser did not separate it),
and `response_format: json_object` was silently ignored (chatter returned, not JSON).

- 195 s × ~42 tok/s ≈ **8,190 tokens ≈ the full 8192-token decode budget**: the
  model burns the window on unconstrained reasoning, leaving no room for the
  answer → non-retryable completion failure → doc error with no retry and no
  parse-error log. Fits all five slow docs exactly.
- Concurrency 8 produced **1.0× serialization** (completions strictly ~195 s
  apart; Qwen AWQ c8 measured 5–7× speedup on the same shape) — guided decode
  plus 12k-token contract prompts do not batch on 1×L4 here.

**Honest gap:** docs 6–8 failed in ~5 s by an undetermined fast path. The
isolated specialist runner keeps rows in-memory and writes `items.jsonl` only
at completion, so killing the run destroyed the per-item error strings. This
detail is unresolved and must be captured from a passing/failing probe with
full stdout before any full-run resume.

## Deploy incidents fixed before the run (no longer blockers)

1. `granite_thinking_parser` does **not** exist on vLLM 0.29.0 — engine
   crash-looped (`KeyError`, available: `..., granite, ...`). Redeployed once
   with the native `--reasoning-parser granite` and no tool parser. Catalog,
   `models.yaml`, and `deploy/modal_vllm.py` comments corrected.
2. `/metrics` (and `/version`) return **404** on the pinned serve path — engine
   observations come from deploy/engine logs + run serving records instead.
   Measured at boot: **KV 10.4 GiB / 68,128 tokens → max ~2.08 concurrent full-32k
   requests**; engine init 14.4 s; prefix caching on; eager on.
3. Cold boot: deploy metadata 2 s; container start → `/v1/models` 200 in
   **153 s**; preflight `cold_boot=0.32 s` (already warm). `/v1/models` serves
   `ibm-granite/granite-4.2-8b-fp8` at 32768 with no admission-raise.

## Concurrency decision: 8 → 3 (applied, all five configs READY)

- **KV math (measured):** 68,128-token pool ÷ ~20k tokens per full-length
  contracts request (12k prompt + 8k decode) ≈ **3 concurrent**.
- **DMR-072:** c=8 piled on 1×L4 even for Qwen sorter graphs; Granite's longer
  thinking decodes pile harder.
- **Measured:** c=8 serialized to 1.0× on Granite (vs 6–7× on Qwen AWQ c8).
- Raise only with `/metrics` headroom — currently unmeasurable on this image
  (404 gap above); treat 3 as a ceiling until a probe shows utilization slack.

Pre-flight at c=3: suite likely ≈ 45 min wall / ≈ $0.60 GPU (100 docs + one
warm app). Resume spends nothing until the probe passes.

## Spend stopped / accounting

- **Halt actions:** local `run start` killed at 8/20 (no new dispatches);
  `modal app stop --yes sandbox-vllm` (app stopped, GPU billing halted).
- **Granite-window estimate:** ~40 min 1×L4 (R1 crash-loop ~20 min + R2 warm
  ~22 min incl. 18 min run overlap) ≈ **$0.40–0.55** + CPU-only pre-warm.
- **Account cumulative** (`modal billing summary`, includes today's Qwen 2×L4
  correspondence runs): metered $18.34, credits −$18.15, **billed $0.00**.
- Exact per-app attribution needs the Modal dashboard; figures above are
  wall-time × $0.80/hr estimates, not metered reads.

## Revised plan (probe-gated; no spend until operator confirms)

1. Redeploy identical R2 env (`eval "$(sandbox modal-matrix env
   ibm-granite/granite-4.2-8b-fp8)"` + `MODAL_VLLM_REASONING_PARSER=granite`,
   MIN=MAX=1, scaledown 120) — cold boot ≈ 153 s expected.
2. **1-doc live probe** (single contracts doc, full stdout capture). Pass =
   ok + schema-valid + wall < 300 s + thinking/answer separation visible.
3. If the thinking-budget failure repeats: fix = raise run decode budget
   (run-scoped, Qwen rows untouched) and/or disable thinking via
   `chat_template_kwargs`, then re-probe. Do **not** resume 20-doc runs.
4. Only after a clean probe: preflight `--live` run 1 (cold boot record),
   chain runs 1–5 on the warm app at c=3, teardown after the fifth, then
   per-specialist reports under `reports/granite/`.

## Artifacts

| path | role |
| --- | --- |
| `config/runs/run-20-*-granite.yaml` (5) | sweep specs, now c=3 (HALT revision) |
| `data/runtime/runs/run-20-contracts-granite/stdout.log` | 8-error timeline (full capture) |
| `data/runtime/runs/run-20-contracts-granite/{checkpoint,cold_boot}.json` | halt state (cursor 8, cold_boot 0.321 s) |
| `data/runtime/logs/granite-deploy{,-r2}.log` | deploy evidence (R1 KeyError → R2 warm) |
| `src/mailroom_sandbox/job/{specialist_posture,benchmark_check,metrics}.py` | granite posture (c=3) + check allowlist + prices |
| `config/{models.yaml,runbooks/catalog.yaml}`, `deploy/modal_vllm.py` | parser-pin corrections |
