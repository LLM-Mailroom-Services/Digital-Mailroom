# SAND-028 — Modal + vLLM serving: critical review & spend-reduction plan

**Status: REVIEW COMPLETE — this is the analysis + optimization backlog. No live spend.**
**Claimed:** 2026-09-25 (UTC) · **Owner:** orchestrator-governor · **Board:** `governance/TASKS.md`
**Scope:** the sandbox's Modal+vLLM serving path (`deploy/modal_vllm.py`, posture, cost math,
runbook) — how to reduce $/doc and $/run without weakening the apples-to-apples evidence.
**Evidence base:** measured `reports/serving/*.serving.json` (3 Modal runs), the AWQ-C8 report,
`job/metrics.py` cost math, `job/specialist_posture.py`, `docs/benchmark-l4.md` doctrine.

## 0 · Resume protocol

This file is the durable plan. After compaction: read this + `governance/TASKS.md` + `git status`.
Everything below is measured or code-verified on 2026-09-25; do not re-litigate without new
serving runs. The Granite matrix (SAND-027) is the spend this review is meant to de-risk — apply
the wins in §4 BEFORE the 15-run matrix fires.

---

## 1 · The economics in one line

**Token-proxy cost is ~2.4% of GPU cost. The L4 wall-clock is ~97.6% of the price.** Every second
of container occupancy removed is ~near a dollar removed; token-level optimizations are rounding
errors by comparison. This reframes the whole optimization problem: optimize *GPU seconds*, not
*tokens*.

---

## 2 · Measured spend autopsy (the 3 measured Modal runs)

| run | n | conc | wall s | cold-boot s | gpu-s | $ GPU | $/doc | tok/s | p50 s | err | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| run-20-contracts-awq-c8 | 20 | 8 | 1528.0 | 161.1 | 1689.2 | 0.3754 | 0.01877 | 144.0 | 619.6 | 3 | 0.0* |
| run-20-correspondence-awq-c8 | 20 | 8 | 90.4 | 159.9 | 250.3 | 0.0556 | 0.00278 | 472.1 | 35.0 | 0 | 0.0871 |
| run-20-correspondence-awq | 20 | 5 | 253.7 | 260.3 | 514.0 | 0.1142 | 0.00571 | 167.5 | 23.3 | 0 | 0.0893 |
| **total** | 60 | | 1872.1 | 581.4 | 2453.4 | **0.5452** | | | | 3 | |

\* contracts score is a GT-schema gap, not a model verdict (AWQ-C8 report §Accuracy).

**Where the money actually went (measured):**
1. **Decode wall-time dominates.** Contracts-20 held the GPU 1528s (p50 619s, max 818s) for 20
   docs; correspondence-20 held it 90s for the same 20. The 17× wall difference is decode length +
   the 8192 max_tokens budget, not prefill. **Long generation IS the cost.**
2. **Cold boots = 24% of spend.** 581s of boots across 3 runs = $0.129 of the $0.545. One boot per
   run; warm reuse eliminates nearly all of it. For a 15-run matrix this is the difference between
   ~$0.53 burned on boots and ~$0.
3. **Tail stragglers = idle billing.** Contracts-20: 17 docs finished early; 3 LengthFinish
   stragglers ran to 800s+ each, keeping the $0.80/hr container alive for minutes of 1-of-8
   occupancy. Cost of waiting on stragglers ≫ cost of failing them fast.
4. **Token cost is negligible.** contracts-20: token-proxy $0.0092 vs GPU $0.3754 (2.4%). Even
   perfect token efficiency would not move the bill.

---

## 3 · Critical findings (ranked by $ impact on the Granite matrix)

### F1 — Decode length is the cost. Guided JSON decode + tighter contract is the top lever. (~$2-3 of the ~$6.4 matrix)
- Evidence: raising contracts `max_tokens` 4096→8192 "moved the cap rather than cleared it" and
  "costs ~2x decode" (AWQ-C8 report). 3/20 failures = `LengthFinishReasonError` — the model burned
  the full 8192 budget without a parseable object. Failed-and-long decodes are the worst $/token.
- Granite adds a *new* waste: thinking tokens. Granite-4.2 thinks by default; the thinking span
  burns decode on both legs (SAND-027 §2.4). On Modal that is L4 wall-clock dollars.
- Fixes, in order: (a) **vLLM guided/JSON structured decoding** so the object terminates on its
  own schema (xgrammar) instead of running to a token cap; (b) **fail-fast on LengthFinish** — a
  doc that hits the cap is a scored error, stop paying for it; (c) per-class `max_tokens` derived
  from *observed* completion p95, not the "cap moved" heuristic; (d) for Granite, cap/measure the
  thinking span and consider `--default-chat-template-kwargs '{"enable_thinking": ...}'` to match
  the OpenRouter leg (which cannot be steered) — this is a twin-vs-cost tension; measure it in the
  N=20 probe and decide with data.

### F2 — Cold-boot and redeploy tax. One warm app, enforced. (~$0.5 on the matrix; already doctrine, not yet enforced)
- Evidence: 24% of measured spend; boots 160-260s each. The doctrine says "one warm app, teardown
  after the last run" (DMR-076, `suite.py warm_once`) — but it is **operator discipline, not
  code-enforced** across separate `sandbox run` invocations.
- Fixes: (a) drive the 15-run matrix through `sandbox run suite` (which chains configs against one
  warm app, `suite_shell_loop`) rather than 15 manual `run start` calls; (b) keep
  `scaledown_seconds=120` (attended) / 600 (unattended) so the container does not die between
  batches; (c) pre-warm the Granite weights once (`modal run ...::download_model` into the HF-cache
  volume) so the first serve is a cache hit; (d) never `--strategy recreate` mid-matrix.

### F3 — Concurrency is the cheapest throughput. Raise the per-type floor. (large wall reduction, no quality cost)
- Evidence: correspondence tok/s **167 (c5) → 472 (c8) = 2.8×** on the *same* L4. Contracts c8 hit
  6.96× sum/wall. Current posture floors at c3 (merger) / c4 (contracts, corporate). FP8 Granite
  (SAND-027) frees KV headroom the bf16/AWQ rows did not have.
- Fixes: (a) raise concurrency toward 8 where the post-FP8 KV budget allows (re-derive per class in
  the N=20 probe, do not assume); (b) keep client concurrency ≤
  `replicas × max_num_seqs` — L4 long-prompt deploy default is
  `max_num_seqs=6` (SAND-030; cliff at ~8 × ~8k); raise containers for a
  second L4 rather than climbing past 6 on one GPU; (c) merger stays lowest
  (longest docs, KV-heavy) — re-measure, don't blanket-raise.

### F4 — Straggler handling: cap the tail, not the average. (direct $ on long-doc classes)
- Evidence: contracts-20 p50 619s but 3 docs at 800s+; the container bills for the tail at ~1/8
  occupancy.
- Fixes: (a) fail-fast on LengthFinish (F1b) so a runaway terminates; (b) consider a per-doc wall
  budget via the call timeout (`job/llm_timeout.py` exists) so one doc cannot hold the run; (c)
  report p95/max latency so regressions in the tail are visible.

### F5 — Cost-cap math must reflect real occupancy. (prevents both overspend and self-aborts)
- Evidence: `metrics.py` bills `gpu_seconds = wall + cold_boot` (or explicit `MODAL_BILLED_GPU_SECONDS`).
  Caps (`cost_cap_usd` 0.35-1.00) were set against `sec_per_doc` heuristics, and the c8 contracts run
  used 8192 tokens against a 4096-derived cap assumption. A cap that aborts a *correct* run wastes
  the whole warm window; a cap that never trips overspends.
- Fixes: (a) after the N=20 probe, re-derive `sec_per_doc` / caps from *measured* per-class
  wall + decode, per model; (b) prefer `MODAL_BILLED_GPU_SECONDS` (the Modal warm interval) over
  the `wall + cold_boot` estimate when available so caps match billing; (c) keep `max_wall_seconds`
  as the hard backstop.

### F6 — Instrumentation gaps that hide waste. (meta — makes the rest verifiable)
- TTFT is never inferred (correct), but nothing measures **container-occupancy vs productive-token
  time** — the idle-vs-busy split that F1-F4 target. The serving JSONs carry wall, gpu-s, p50, max,
  tok/s but no "busy seconds." Add a `busy_gpu_seconds` (sum of per-item in-flight time / conc) vs
  `billed_gpu_seconds` so each run reports its own idle fraction. This turns the next optimization
  round from guesswork into arithmetic.

### F7 — Hardware class: stay on L4 for the matrix; H100 only if measured to pay.
- L4 = $0.80/hr; H100 = $3.95/hr (~4.9×). A hardware swap only wins if it cuts *billed seconds*
  >4.9×. FP8-native H100 (per SAND-027 §2.3) may decode faster, but at these batch sizes (n≤100,
  concurrency ≤8) the L4 is not GPU-bound in a way 5× hardware can repay — the win would come from
  `--max-num-batched-tokens`/CUDA-graph tuning, not raw FLOPs. **Recommendation: L4 for the matrix;
  revisit H100 only if the probe shows decode-bound saturation.**

---

## 4 · Optimization backlog (apply BEFORE the Granite matrix)

**Shipped 2026-09-25 (free ops wins, zero spend, 438-test suite green):**
- `docs/modal-serving-ops.md` — the ops runbook (warm-once, teardown-once, L4, pre-warm is
  CPU-free, caps-from-measurement, anti-pattern table, **slice-don't-redraw** rule).
- `config/models.yaml` — Granite `modal_models` rows: `ibm-granite/granite-4.2-8b-fp8`
  (L4 / compressed-tensors / 32768) + `ibm-granite/granite-4.2-8b` (bf16 reference, 16384).
- `deploy/modal_vllm.py` — env-gated `--reasoning-parser` / `--reasoning-parser-plugin` /
  `--tool-call-parser` / `--enable-auto-tool-choice`; Qwen default serve command verified
  byte-identical (no parser leakage).

**Verified sampler fact (corrects §F-nesting assumptions):** `corpus._draw_buckets` derives the
sub-seed from `(sample_seed, class)` — NOT from the count. Measured: sample(k=20) ⊂ sample(k=100)
holds ~82% of seeds and sample(k=50) ⊂ sample(k=100) only ~26%. **Therefore the matrix MUST draw one
bucket per class (n=100) and score 20/50 as prefix slices of the locked set; re-drawing per size
breaks the same-subset guarantee** (this is why `docs/modal-serving-ops.md` §5 and eval-env issue
#20 exist).

| # | Optimization | Lever | Est. $ saved on ~$6.4 matrix | Risk | Owner |
|---|---|---|---|---|---|
| O1 | Guided/JSON structured decode (terminate on schema) | F1 | ~$2-3 | med (decode-shape change → re-score) | harness-doctor + prompt-engineer |
| O2 | Fail-fast on LengthFinish + per-doc wall budget | F1/F4 | ~$0.5-1 | low | harness-doctor |
| O3 | Drive matrix via `sandbox run suite` (one warm app) | F2 | ~$0.5 | low (ops change) | general (ops) |
| O4 | Pre-warm Granite weights once; no mid-matrix recreate | F2 | ~$0.1-0.3 | low | general (ops) |
| O5 | Re-derive per-class concurrency toward 8 on FP8 | F3 | ~$0.5-1 | low-med (re-measure in probe) | harness-doctor |
| O6 | Re-derive `sec_per_doc` / caps from measured probe | F5 | avoids abort-waste + overspend | low | general (post-probe) |
| O7 | Add `busy_gpu_seconds` vs `billed_gpu_seconds` (idle fraction) | F6 | enables next round | low | harness-doctor |
| O8 | Cap/measure Granite thinking span; twin-vs-cost decision | F1 (Granite) | ~$0.3-0.8 | med (twin) | prompt-engineer + harness-doctor |
| O9 | Keep L4 (H100 only if probe shows decode-bound) | F7 | avoids ~4.9× hardware overspend | low | general (ops) |

**Sequencing:** O3/O4/O9 (ops, no code) → O7 (instrument) → run N=20 probe → O1/O2/O5/O6/O8
tuned on probe data → full matrix. O1/O5/O8 must be **validated on the probe before the 50/100
waves** or they risk the apples-to-apples claim.

---

## 5 · What this does NOT change

- Sampling design, model twin, prompt alignment, same-subset guarantee (SAND-027 §4) — untouched.
- The apples-to-apples claim is about score distribution under matched decode; guided decode /
  fail-fast must be applied **identically on both legs** (OpenRouter guided-json via
  `response_format`, or the same terminate-on-schema contract) or the twin breaks. This is a real
  seam: **O1/O2 are only apples-safe if mirrored in eval-environment (issues #18/#19).**

---

## 6 · Board actions

- `SAND-028` epic: Modal+vLLM serving review & spend reduction (this file).
- Subcards to open with the matrix: instrumentation (F6), decode-length fix (F1), concurrency
  re-derivation (F3), caps re-derivation (F5), ops posture (F2/F7). Each claimed in
  `governance/TASKS.md` as the work starts; `done` cites measured before/after.
- This review **gates SAND-027 U6/U7** (deploy + N=20 probe): apply O3/O4/O7 and the F1/F3 fixes
  before the 15-run matrix so we spend less *and* get cleaner evidence.

## 7 · Evidence log (2026-09-25)

- `reports/serving/run-20-contracts-awq-c8.serving.json`, `-correspondence-awq-c8`, `-correspondence-awq` (measured).
- `reports/RUN-20-CONTRACTS-AWQ-C8-REPORT.md` + `-SERVING.md` (LengthFinish analysis, throughput, token-vs-GPU ratio).
- `reports/archive/MODAL-RUNS-REPORT.md` (6 Modal rows, cold-boot series, bf16 49:50 postmortem).
- `src/mailroom_sandbox/job/metrics.py` (gpu_seconds = wall + cold_boot; MODAL_BILLED_GPU_SECONDS; token-proxy rates).
- `src/mailroom_sandbox/job/specialist_posture.py` (per-type concurrency/max_tokens/caps; concurrency band [2,8]).
- `src/mailroom_sandbox/job/suite.py` (warm_once, suite_shell_loop).
- `deploy/modal_vllm.py` (env knobs, scaledown, min/max containers, HF/vLLM cache volumes, pre-warm).
- `docs/benchmark-l4.md` (DMR-076/077/078 posture doctrine).