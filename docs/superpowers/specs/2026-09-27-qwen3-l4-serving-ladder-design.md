# SAND-032 — Qwen3-8B-AWQ on L4: serving-knob ladder → 2-replica scale-out → 5-specialist sweep

- **Date:** 2026-09-27
- **Status:** design — awaiting spec review
- **Card:** SAND-032 (Related: SAND-028, SAND-030, SAND-031, SAND-027-4 / issue #38)
- **Budget:** **$5.00 hard cap**, total Modal spend, fresh Modal account

## 1. Intent

**Why:** this self-funded pilot produces the evidence for a **funding request to our industry partner
(AmFam)**, the capstone partner for a master's capstone project, to continue the research.

**Data provenance:** every run uses only the **public** Hugging Face dataset
`Lucius-Morningstar/mailroom-dataset`. We have **no access to proprietary AmFam data and no
data-sharing agreement**. Nothing in this program, including the proposal, may imply otherwise. The
proposal frames the funded work as research on public/synthetic data, whose findings AmFam can
apply internally. The forward ask is at least **$200**, and plausibly several hundred
dollars more. Every cost figure must therefore be *billed-reconciled and defensible*, not estimated.
The funded phase would cover full-corpus runs, model comparisons and prompt/quality optimization
(§5a).

Serve Qwen3-8B on Modal + vLLM v0.29.0 on L4 GPUs as cheaply as possible, without losing quality.

- **Objective:** minimize GPU **$/doc**. Quality is a non-regression guardrail, not the thing being optimized.
- **Topology:** 1×L4 per container; production uses **2 containers × 1 L4** (replicas) at c16 total
  (8 per replica). A 1-replica c8 arm is the scale-out baseline.
- **Deliverables:**
  1. A measured, frozen serving config (every controllable knob decided by evidence).
  2. A scale-out demonstration: correspondence n=100 on 1 replica vs 2 replicas.
  3. A 5-specialist scorecard: all five classes at n=50, plus correspondence at n=100, under one runbook.
  4. An AWQ-vs-bf16 quality delta from one isolated arm.
- **Constants:** AWQ weights (`Qwen/Qwen3-8B-AWQ`), vLLM image v0.29.0, `max_model_len` 32768,
  `gpu_memory_utilization` 0.90, prefix caching on, prompts pinned by SHA, dataset revision
  = the current `FAMILY_HF_REVISION` pin (v9.1, `ed7576b676343e0b402ec5412cded301e629bdee`), seed 42.
  Earlier runs used `46a4d3c2`, so comparisons with them are indicative only, not paired.
- **Fixed by decision:** **`kv_cache_dtype=fp8` on every 2×L4 run** and on the 1-replica
  scale-out baseline.

## 2. Findings this design responds to

1. **Qwen3 thinking is never explicitly disabled.**
   - No `enable_thinking` or `chat_template_kwargs` appears in `src/`, `deploy/`, `config/` or `vendor/`.
   - The only control sent is `extra_body.reasoning.effort` (`vendor/llm-mailroom/src/agents/base.py:157`),
     which the Qwen3 chat template does not read.
   - JSON mode plausibly suppresses thinking today (~184 completion tokens/doc on correspondence),
     but nothing guarantees it.
   - Contracts `LengthFinishReasonError` at 8192 and the 140–190 s stragglers are consistent with
     uncontrolled thinking.
2. **`--quantization awq` forces the slow AWQ kernel** (`deploy/modal_vllm.py:100, :248`). vLLM
   upgrades AWQ checkpoints to `awq_marlin` on Ada only when the method is not forced.
3. **At c8, `max_num_seqs=6` binds, not KV memory.**
   - Correspondence needs ~20k KV tokens at c8.
   - Contracts and merger need ~160k (≈12k prompt + up to 8k decode × 8), which exceeds the
     ~90k-token bf16 KV pool. fp8 KV roughly doubles the pool.
4. **`enforce_eager=1` skips CUDA graphs**, trading steady-state decode speed for boot time. The
   `sandbox-vllm-cache` volume is already mounted, so compiled artifacts persist across boots.
5. **Plumbing gaps:**
   - Run YAML never reaches the deployment; only hand-exported `MODAL_VLLM_*` env vars do.
   - The live cost cap ignores replicas (`src/mailroom_sandbox/job/runner.py:457-466`), so it is about
     2× too loose on 2×L4.
   - `benchmark-check` does not verify `max_model_len`, `max_num_seqs` or quantization.
   - The isolated specialist path writes no `items.jsonl`.
   - Latency records have mean/p50/max only: no p95, no TTFT.
6. **Data:**
   - Correspondence test split has only 62 rows, so the draws use `split: all` (every class has ≥152 rows).
   - The sampler is not nested (issue #38), so draw 100 per class once and slice 20/50 from it.
   - Contracts has no extraction ground truth, so contracts results are serving-only.
8. **Latest 1×L4 c8 AWQ runs (origin/main 08f43e3):**
   - **corporate_records n=20:** 20/20 ok, score 0.4231, schema_valid 0.95, ~$0.0076/doc busy.
   - **merger n=20:** 15/20 ok, run through `contracts_specialist`. That agent confound gives a score of
     0.0 against MAUD ground truth.
     - It had **5 `OpenAIConnectionError` drops at c8** on the longest docs (proxy saturation).
     - It had a **~102-min command span vs a 740 s busy wall**, from client timeout/backoff inflation.
   - Implications:
     - Busy-wall cost can badly understate billed cost.
     - Proxy/connection behavior must be fixed before c16.
     - Stage 3 must use `merger_agreement_specialist` (AGENTS.md 1:1 mapping).
7. **Vendor trees are byte-locked** by `tests/test_vendor_drift.py`. No vendor edits; all changes live
   in `src/mailroom_sandbox/`, `deploy/`, `config/`.

## 3. Approach: staged, gated ladder

**Rejected alternatives:**
- Tuning directly on the 2-replica fleet: every variant pays 2× boot cost.
- Freezing knobs from reasoning alone: cheapest, but leaves the optimization unmeasured.

### Stage 0 — Plumbing (code only, $0, TDD, network-free tests)

| Unit | Change | Location |
| --- | --- | --- |
| Deploy knobs | New env knobs rendered into `vllm serve` argv: `kv_cache_dtype`, `default_chat_template_kwargs` (thinking off), CUDA-graph capture sizes via `--compilation-config`, `max_num_batched_tokens` | `deploy/modal_vllm.py` `build_vllm_command`, `CONFIG_ENV_KEYS` |
| Spec fields | Same knobs as validated `VLLMSpec` fields | `src/mailroom_sandbox/job/spec.py:230-281` |
| Thinking fallback | If `--default-chat-template-kwargs` is absent on v0.29.0: `--chat-template` pointing at a repo copy of the Qwen3 template with `enable_thinking` defaulting false (prompt SHA unchanged) | `deploy/` |
| YAML → env | `sandbox run deploy-env --config <yaml>` prints the exports derived from the spec; deploy-side check refuses when env ≠ spec | reuse `job/runbooks.py` `ENV_FIELDS` |
| Live verification | `preflight --live` checks `/v1/models` `max_model_len`; serving record stores the full vLLM argv and the boot-log KV pool size | `job/preflight.py` |
| Cost cap | Live GPU estimate × replica count | `job/runner.py:457-466`, `eval/runners.py:263-275` |
| Metrics | Per-doc `items.jsonl` on the isolated specialist path; p95 latency; per-replica vLLM `/metrics` scrape before/after each run (TTFT histogram, KV usage peak, preemptions, prefix-cache hits, request counts) | `eval/runners.py`, `metrics.py` |
| Nested sampling | One seed-42, 100-row manifest per class under `data/runtime/`; run configs reference a slice (`first 20`, `first 50`) | dataset/sampling module |
| Offline BT experiments | `data/runtime/bt_experiments/<run_id>/experiment.json` + `rows.jsonl` in Braintrust Experiment row shape (`id`, `input`, `output`, `expected`, `scores`, `metrics`, `metadata`), with every serving knob + git commit in metadata. Gitignored. No upload. `sandbox run dispose <run_id>` deletes it after the report is committed | new module under `src/mailroom_sandbox/` |
| Run configs | Ladder L0–L5, `run-100-correspondence-1rep`, `run-100-correspondence-2rep`, `run-50-{correspondence,insurance,corporate-records,merger,contracts}-2rep`, `run-20-correspondence-bf16`; Stage-3 suite YAML; allow-listed in `benchmark_check.py`, which also asserts `kv_cache_dtype=fp8` for Stage 2–3 | `config/runs/`, `job/benchmark_check.py` |
| Proxy robustness | Diagnose the c8 connection drops before any c16 run. Check whether `serve()` needs `@modal.concurrent(max_inputs=…)` (currently absent), and align client timeouts and retries so backoff cannot inflate the billed span. Record the *billed span* (first request → container idle/stop) next to busy wall on every run | `deploy/modal_vllm.py`, client/retry config |
| Governance | Open SAND-032 on the local board | `governance/TASKS.md` |

**Pre-spend check:** a CPU-only `modal run` of `vllm serve --help` on the v0.29.0 image confirms the
thinking, kv-cache and compilation flags exist before any GPU boot.

### Stage 1 — 1×L4 knob ladder (correspondence n=20 slice, c8, ~$0.35)

Rungs are cumulative, with one knob per rung. Each rung is a fresh boot, and boot time is recorded.

| Rung | Change | Rationale |
| --- | --- | --- |
| L0 | Current AWQ baseline, new slice | Paired reference |
| L1 | + thinking off | Removes decode waste and stragglers |
| L2 | + `awq_marlin` | Kernel speed |
| L3 | + `kv_cache_dtype=fp8` | **Pinned for all 2×L4 runs**; measured for quality and KV-pool impact only |
| L4 | + `max_num_seqs=16` | Admission ≥ concurrency |
| L5 | + CUDA graphs (`enforce_eager=0`, capture sizes 1,2,4,8,16) | Decode speed vs boot delta |

**Per-rung gate** (paired on the same 20 docs):
- ok 20/20
- mean score ≥ L0 − 0.02
- schema_valid ≥ L0 − 0.05
- $/doc not worse than the previous kept rung

**Gate outcomes:**
- A rung that fails is reverted, **except L3**: a quality regression under fp8 KV is reported, not reverted.
- The frozen config is the best passing stack, always with fp8 KV.
- **Stop rule:** if Stage 1 spend exceeds $0.50, freeze the best config so far.

### Stage 2 — Scale-out demonstration (correspondence n=100, frozen config)

- **2a:** 1 container, c8. This boot is the single measured production cold boot.
- **2b:** 2 containers (min = max = 2), c16.
- **Reported:** wall time, $/doc (billed for all GPUs), tok/s, per-replica request split, p50/p95, KV peak.
- **Scale-out benefit:** wall ratio and $/doc delta between 2a and 2b.

### Stage 3 — 5-specialist sweep (2 replicas kept warm, c16, one suite, cheapest first)

Order:
1. correspondence n=50 (a slice of the 100; consistency check against 2b)
2. insurance_claims n=50
3. corporate_records n=50
4. merger_agreement n=50 (**`merger_agreement_specialist`**, not the contracts agent)
5. contracts n=50 (serving metrics only)
6. **correspondence n=50 repeat** (same slice, same warm fleet, ~$0.12). Gives the run-to-run variance
   that the funding projections' error bars need.

**Budget gate before each class:** spent + (measured $/doc × remaining docs) must be ≤ $4.50;
otherwise merger and contracts drop to n=20. Per-run `cost_cap_usd` is 1.5× the projection.
The app is stopped at suite end.

### Stage 4 — bf16 quality arm (1×L4, 16k window, correspondence n=20 slice, ~$0.10)

- Uses the same 20 docs as the ladder, giving a paired AWQ-vs-bf16 quality delta.
- Runs last and is dropped if the budget is tight.

## 4. Budget

The estimates use measured $/doc from prior runs, before any optimization.

| Stage | Estimate |
| --- | --- |
| 1 — ladder (6 boots) | ~$0.35 |
| 2 — scale-out n=100 ×2 | ~$0.55 |
| 3 — sweep n=50 ×5 + repeat | ~$2.7 |
| 4 — bf16 arm | ~$0.10 |
| Idle / extra boots | ~$0.25 |
| **Total** | **~$3.95** (≈$1.05 margin under $5) |

The running total is reconciled against Modal usage after every stage. The **billed** figure from Modal's
usage/billing view is the one that feeds §5a, not the wall-clock estimate. The user supplies it; Claude
does not access the account.

## 5a. Funding-evidence deliverable (AmFam budget request)

`reports/funding/AMFAM-BUDGET-PROPOSAL.md`, built only from this pilot's committed measurements.

1. **Unit-cost table:** per class, $/doc and $/1,000 docs on the frozen config, for 1 replica and
   2 replicas. Billed and wall-estimated figures are shown side by side, with the ratio stated.
2. **Fixed overheads:** measured cold boot ($ and s per boot) and idle-warm $/min, stated separately
   from per-doc cost.
3. **Variance:** run-to-run spread from the correspondence repeat, and from the paired 20/50/100 slices,
   applied as ± bands on every projection.
4. **Line-item projections, each shown as a formula with its inputs:**
   - **Full-corpus pass:** Σ class_rows × class $/doc, plus boots and idle, × seeds (1 and 3).
   - **Prompt/quality optimization:** cost per eval iteration (a warm n=20 / n=50 run for each class,
     measured in Stage 3), × iterations per specialist.
   - **Model comparisons:** the Qwen3-8B-AWQ measured cost scaled by an explicit, labeled assumption
     (throughput ratio from a model's size and quantization). This is flagged as *projected, not
     measured*, with the pilot's Granite halt cited as the known risk.
5. **Funding tiers:** what **$200 / $500 / $800** each buy in concrete runs, with a stated contingency
   (e.g. 20%) for failed runs and re-boots, drawing on the historical failure rate in `reports/`.
6. **Evidence appendix:** what the pilot established (ladder gains, scale-out benefit, 5-class
   scorecard, AWQ-vs-bf16 delta), with links to the committed reports.
7. **Data statement:** all measurements come from the public HF `mailroom-dataset`; no AmFam or other
   proprietary data was used or is required. Any future use of partner data would need a separate
   data-sharing agreement and is outside this budget.
8. **Prior investment (optional):** one summary line, "researchers have self-funded ~$X to date".
   The user supplies the figure or the line is omitted. There is no itemization.

The proposal's claims go through the `adversarial-reviewer` pass along with the other reports.

## 5. Reporting and disposal

- **Per-run reports** go in `reports/serving/` and the per-class directories.
- **Program summary** at `reports/serving/QWEN3-L4-LADDER-SUMMARY.md`, containing:
  - the ladder table
  - the scale-out table
  - the 5-class scorecard
  - the bf16 delta
- **Adversarial review:** the `adversarial-reviewer` subagent checks every claim against the serving records
  and `items.jsonl` before commit.
- **Disposal:** after the reports are committed, `sandbox run dispose` removes the offline BT rows.

## 6. Operator prerequisites (performed by the user)

- Rotate any credentials that were shared in chat. Hosted Braintrust is not used.
- On the new Modal account:
  - `modal token new`
  - `modal secret create huggingface-secret HF_TOKEN=…`
  - `modal run deploy/modal_vllm.py::download_model` (CPU-only weight pre-warm)
- Provide the Modal profile name.

## 7. Verification

- **Stage 0:**
  - `pytest -v` passes, with new unit tests covering:
    - argv per knob
    - YAML→env round-trip
    - replica-scaled cost cap
    - nested-slice determinism
    - BT row schema
    - dispose
  - `sandbox runbook check` passes.
  - `sandbox run preflight` and `benchmark-check` pass on every new config.
- **Each live run:**
  - `preflight --live` confirms the served model and `max_model_len`.
  - The served argv matches the YAML (including fp8 KV for Stages 2–3).
  - `/metrics` shows both replicas taking traffic in 2b and Stage 3.
