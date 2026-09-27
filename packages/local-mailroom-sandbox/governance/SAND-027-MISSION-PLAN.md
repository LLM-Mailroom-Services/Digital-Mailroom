# SAND-027 MISSION PLAN — Granite-4.2-8b: Modal vLLM ↔ OpenRouter apples-to-apples

**Status: PLAN COMPLETE — NO LIVE SPEND YET. Awaiting human gates H1/H2.**
**Claimed:** 2026-09-25 (UTC) · **Owner:** orchestrator-governor · **Board:** `governance/TASKS.md`
**Repos this mission touches:** `~/Downloads/local-mailroom-sandbox` (Modal/vLLM leg, tracking) ·
`~/Downloads/eval-environment` (OpenRouter leg, execution home).

---

## 0 · RESUME PROTOCOL (read this first after compaction)

If context was compacted, resume exactly here:

1. `git -C ~/Downloads/local-mailroom-sandbox status` — expect: `M src/mailroom_sandbox/job/spec.py`
   (openrouter engine-kind, keep) + `?? api-evals/` (untracked Qwen-OpenRouter harness, keep) +
   `M governance/TASKS.md` (SAND-027 tree) + `?? governance/SAND-027-MISSION-PLAN.md` (this file).
2. Read `governance/TASKS.md` (SAND-027 rows) and this file. Nothing is funded past this point.
3. Read `~/Downloads/eval-environment/AGENTS.md` before touching that repo (its own governance; it is a
   **different org repo, own rules, own board/issue tracker**).
4. Next action when gates H1/H2 are green: execute **U3** (N=20 probe wave, both legs) per §5/§6.
5. Specialist verification (U1, SAND-027-1) is **DONE** — verdicts summarized in §2.4; do not re-dispatch
   unless a gate re-opens (e.g. vLLM image bump changes the deploy-smoke outcome).
6. Compaction notes: keep §2 (verified facts), §3 (architecture), §4 (locked decisions), §5 (units),
   §6 (spend), §7 (gates), §8 (risks) — the rest is navigational.

---

## 1 · Mission statement

Run an as-close-to-apples-to-apples evaluation of the **same IBM Granite model** on two serving legs:

- **Leg A — Modal vLLM** (sandbox infra; 1× NVIDIA L4 24GB, 2× optional) using **open weights**.
- **Leg B — OpenRouter** (eval-environment infra; API twin of the same weights).

Across **all 5 primary document-type specialists** (contracts, merger agreement, corporate records,
correspondence, insurance claims) at **20 / 50 / 100 documents per class**, where:

- the **prompts** are byte-aligned between legs (same stems, sha256-verified);
- the **model** is the same (HF open-weights id == OpenRouter id);
- **each specialist sees the SAME subset of documents** per class (nested 20⊂50⊂100, seed 42);
- every live run is **traced to Braintrust** and logged to the durable experiment logs in BOTH repos;
- results are analyzed with **paired statistics** (bootstrap Δ-CI over documents), and
- **full cost reports** are written for (a) the earlier QWEN-flash OpenRouter runs, (b) the
  archived Qwen Modal baseline, (c) the new Granite legs.

**Non-goals:** no new Qwen live spend (baseline = archived records unless gate H4 says otherwise);
no changes to eval-environment's prompt lineage (frozen v1) outside the sanctioned
`promote_sandbox_specialist.py` flow; no 2×L4 unless the N=20 probe shows >32k context is needed.

**Venue decision (2026-09-25):** the OpenRouter comparison runs execute in **eval-environment**
(issues **#18–#21** there carry the work: #18 program, #19 prompt alignment, #20 same-subset,
#21 Braintrust/log). The sandbox's role is **the Modal vLLM leg + request plumbing only**:
`api-evals/` (OpenRouter-request harness + spec.py `openrouter` engine kind) is preserved as
plumbing parity + the QWEN-flash cost-report tooling and does **NOT** host the Granite-OpenRouter
live runs. Sandbox unit SAND-027-2 tracks the eval-env issues; it does not re-implement them here.

---

## 2 · Verified facts (all checked 2026-09-25, sources cited)

### 2.1 Model twin (the decisive fact)
- OpenRouter serves **`ibm-granite/granite-4.2-8b`** — live `/api/v1/models` payload:
  prompt $0.00000006/tok ($0.06/1M), completion $0.00000025/tok ($0.25/1M), ctx 131072.
- HF hosts the **identical id** `ibm-granite/granite-4.2-8b` (public, Apache-2.0, 110k downloads) —
  first-party weight lineage, NOT a champion-map pairing (stronger than the Qwen
  `qwen/qwen3.7-flash`↔`Qwen/Qwen3-8B` map).
- No other 8B Granite is on OpenRouter (4.0-h-micro is a 3.2B MoE hybrid — rejected).

### 2.2 HF hub facts (verified by `lucius`)
- License **Apache-2.0**, **not gated**, no `trust_remote_code` needed (no `auto_map`).
- 8B dense `GraniteForCausalLM`: 40 layers, GQA 32/8 KV heads, RoPE θ=1e7, ctx **131072** native.
- Chat template: custom ChatML (`chat_template.jinja`), Qwen-style thinking
  (`<thinking>`/`response`), kwargs `enable_thinking`, `low_effort`/`reasoning_effort`.
- Native tool calling (OpenAI schema, `qwen3_coder` parser per IBM card); structured-output RL training.
- **Model card mandates `temperature=1.0`, `top_p=0.95`** for all backends.
- Quantized siblings (all public/Apache-2.0):
  - `granite-4.2-8b-fp8` — compressed-tensors **W8A8 FP8**, ~9.5 GiB → **the L4 pick** (native on Ada SM≥8.9).
  - `-nvfp4` / `-mxfp4` — Blackwell/Hopper FP4 classes → **NOT L4-viable**.
  - `-GGUF` — llama.cpp path only.
  - **No AWQ/GPTQ exists** for granite-4.2 (AWQ slot from the Qwen setup is void; FP8 replaces it).

### 2.3 vLLM + Modal viability (verified by `docker-deployment-specialist` — current docs)
- vLLM supports `GraniteForCausalLM`; native `--reasoning-parser granite_thinking_parser` on vLLM
  `main`/0.30.0. **On the sandbox's pinned v0.29.0-era image: MUST-VERIFY in deploy smoke**; IBM's
  fallback is `--reasoning-parser-plugin <hf>/granite_thinking_parser.py` (vLLM ≥ 0.20).
- Tool calling: `--tool-call-parser qwen3_coder --enable-auto-tool-choice`. Structured JSON: supported;
  **with thinking ON, vLLM needs `--structured-outputs-config.enable_in_reasoning=True`**.
- Boot admission (current vLLM): KV pool must hold ONE request at `max_model_len` or boot raises.
  - 1×L4 FP8 @ **32768 → boot-validates** (~6 GB headroom). bf16 base @ 32768 FAILS; bf16 @ 16384 borderline.
  - 1×L4 FP8 @ ~64k possible with `--kv-cache-dtype fp8` (smoke-first); 2×L4 TP2 FP8 @ 131072 validates.
- Modal: `gpu="L4"` / `gpu="L4:2"` (≤8 same-machine), SDK pin `modal==1.5.5` **matches the repo**;
  current vLLM stable 0.30.0. L4 ≈ **$0.80/hr**; 2×L4 ≈ $1.60/hr.
- Recommended Leg A env (locked, from the specialist):
  `MODAL_VLLM_MODEL=ibm-granite/granite-4.2-8b-fp8`, `GPU=L4`, `QUANTIZATION=compressed-tensors`
  (auto-detected), `MAX_MODEL_LEN=32768`, `KV_CACHE_DTYPE=fp8` (optional stretch), `TP_SIZE=1`,
  `MAX_CONTAINERS=1`, `SCALEDOWN=120-600`, flags as §4.3.

### 2.4 Selection & design verdict (verified by `ml-systems-oracle`)
- **Winner: `ibm-granite/granite-4.2-8b`** — only candidate satisfying the cross-host twin constraint
  at 8B quality; 4.1-8b superseded, 3.3-8b-instruct / 4.0-h-micro fail twin/quality/L4 criteria.
- **Posture: 1× L4 FP8 TP1 — NOT 2×L4.** Inputs cap ~36k chars ≈ 9-10k tokens + ≤8k output ≪ 32k ctx;
  2×L4 doubles cost for zero quality gain at n≤100 (concurrency-8 AWQ-c8 precedent on 1×L4 already proven).
- **Sampling: nested 20 ⊂ 50 ⊂ 100** drawn ONCE per class (seed 42, canonical order) per leg →
  **one-shot 100-doc inference per class per leg (500 calls/leg)**, all buckets scored from the same
  stored outputs by prefix slicing. Paired bootstrap Δ-CI (over documents) is the honest leg-difference
  statistic; n=20 CIs are wide (±0.08-0.12 abs; Δ ±0.03-0.06) — say so in reports; never
  significance-test "20 vs 100" as independent.
- **Thinking mode: ON both legs** (OpenRouter cannot pass `chat_template_kwargs`; Granite 4.2 default is
  think-on → the twin-safe choice). **Strip `<thinking>…</thinking>`/`response` spans pre-scoring.**
  Probe first at N=20; if OpenRouter unexpectedly serves non-thinking, flip Leg A to `enable_thinking=False`.
  This is the single biggest twin-breaking risk (§8).
- **OpenRouter leg MUST pass explicit `max_tokens` per request** (OR default ≈117k would silently
  destroy the comparison + $). Per-class thinking-ON budgets: correspondence 4096; insurance 6144;
  corporate/contracts/merger 8192.
- Decode: `temp=1.0`, `top_p=0.95` both legs; seed pinned (Leg A), best-effort passthrough (Leg B);
  optional temp-0 ablation at N=20.
- Concurrency (mirror DMR-078): correspondence 5 · insurance 5 · corporate_records 4 · contracts 4 ·
  merger 3.

### 2.5 Cost model — MEASURED re-derivation (supersedes the ~$7 oracle estimate)

Re-derived 2026-09-25 from the three real serving records in `reports/RUN-*-REPORT.md` plus
`docs/RUN-COST-DERIVATION.md` (full per-doc derivation, exact formulas, sensitivity).

| Leg | Basis | **Total ≈** |
|---|---|---|
| A · Modal 1×L4 FP8 | 2 classes measured @100 = $2.15; 3 classes extrapolated = $3.90 | **~$6.05** |
| B · OpenRouter | real token volumes × $0.06/$0.25 | **~$0.25–0.45** |
| **Program** | | **≈ $6.30–6.50 unoptimized** |

- **Cap: $6 soft / $8 hard** (was $8/$12 — the old figure was 1.7× padded headroom over an
  unverified ~$7 estimate, not a forecast). The program cap is an outer *safety ceiling*, **not an
  authorization**: no wave is funded until its own gate is passed.
- **Per-wave caps govern, not the program cap:**
  - **W1 probe (N=20, both legs, 5 classes): hard cap $1.50** — the only pre-authorized spend.
  - **Per-class escalation cap = 3× that class's measured N=20 both-leg cost.** Because escalation
    is 5× the documents, a 3× spend ceiling only passes if the F1–F4 optimizations actually land.
    If the projected 100-doc cost breaches it, fix first — do not raise the cap.
  - 3 of 5 classes (merger/corporate/insurance ≈ $3.90 of $6.05) are still **extrapolated**;
    re-derive from the probe before any escalation is priced.
- Per-doc contract-class cost: **API $0.001063 mean / $0.001403 p95** vs **Modal $0.0188**
  (a 1:18 ratio) — see `docs/RUN-COST-DERIVATION.md`.

### 2.6 Repo state (working tree, as of 2026-09-25)
- **local-mailroom-sandbox** @ HEAD `97c0f94` (dirty): `M src/mailroom_sandbox/job/spec.py`
  (adds `"openrouter"` to `EngineSpec.kind` — keep, mission depends on it); `?? api-evals/`
  (untracked Qwen-OpenRouter harness: 6 tasks, real-cost accounting, report writer — becomes the
  Qwen-flash cost-report tooling); this plan + TASKS.md edits (uncommitted).
- **eval-environment** @ HEAD `4ba63b2`, clean. Own AGENTS.md (10 non-negotiables — cited in §5 units),
  31 tasks incl. the 5 specialist extraction nodes, frozen prompt lineage (sha256 per stem),
  OpenRouter-primary + Braintrust/Phoenix sinks, Vercel viewer snapshot duty. **No Modal/vLLM
  machinery** — that leg lives in the sandbox by design.

### 2.7 Earlier QWEN flash runs (the cost-report subject; data verified)
3 records in `reports/experiment_log.jsonl` (all `qwen/qwen3.7-flash`, profile openrouter, backend none):
| record | n | prompt_tokens | completion_tokens | **real API $ (tokens × live price $0.03/$0.13)** | logged L4-proxy $ |
|---|---|---|---|---|---|
| api-smoke-1 | 1 | 12,158 | 997 | **$0.000494** | 0.001854 |
| contracts-20 #1 (22:04Z) | 20 | 123,829 | 16,629 | **$0.005877** | 0.008428 |
| contracts-20 #2 (22:08Z) | 20 | 123,829 | 15,310 | **$0.005705** | 0.008276 |
| **Totals** | 41 | | | **≈ $0.0121** | ≈ $0.0186 |
Caveats that MUST appear in the report: all three logged `prompt_version: mailroom-default` (pinned
simplified stems NOT recorded → not prompt-fixed quality claims); score 0.0 with 0 errors on
contracts-20 = measurement-status UNPROVEN (diagnostic open, see §8.3); fingerprint `9c87afb3c10c` =
the same contracts-20 draw as Modal `run-20-contracts-*` (draw parity confirmed).

---

## 3 · Architecture (two legs, one comparison)

```
                        ┌─────────────────────────── Leg A (Modal vLLM) ───────────────────────────┐
corpus (pinned          │ sandbox: deploy/modal_vllm.py  →  ibm-granite/granite-4.2-8b-fp8 (1×L4)    │
 rev 46a4d3c2, seed 42) │ sandbox run <spec> (config/runs/granite-*.yaml)  · Braintrust via vendored  │
        │              │ observability.braintrust_setup (wrap_openai + task spans) · experiment_log  │
        │              └──────────────────────────────────────────────────────────────────────────────┘
        │ SAME subset per doc class (nested 20/50/100, same filenames both legs)
        │ SAME prompt stems (sha256-verified sandbox ↔ eval-environment)
        ▼
                        ┌─────────────────────────── Leg B (OpenRouter) ───────────────────────────┐
                        │ eval-environment: scripts/run_evals.py --task eval:<specialist>           │
                        │   --invoke agent --model ibm-granite/granite-4.2-8b --subset class:X       │
                        │   --sample 100 --seed 42 · explicit max_tokens · EVALS_TRACE_BACKEND=      │
                        │   braintrust · experiment_log + Vercel snapshot                            │
                        └────────────────────────────────────────────────────────────────────────────┘
        ▼
paired analysis: bootstrap Δ-CI over docs · score tables (both legs ≡ same model, else model swap)
cost reports: Granite legs + Qwen-flash earlier runs + archived Qwen Modal baseline
```

---

## 4 · Locked decisions (do not re-litigate without a gate)

1. **Model:** `ibm-granite/granite-4.2-8b` on both legs; Leg A serves the **`-fp8`** checkpoint.
2. **Leg A posture:** 1×L4, FP8, TP1, `max_model_len=32768`, `--kv-cache-dtype fp8` optional stretch,
   reasoning + tool parsers per §2.3; image tag **v0.29.0 unchanged UNLESS deploy smoke demands a bump**
   (gate H5; the native `granite_thinking_parser` needs ≥0.30.0 — plugin fallback otherwise).
3. **Leg B posture:** explicit `max_tokens` per class (§2.4), `temp=1.0/top_p=0.95`, `seed=42` best-effort.
4. **Thinking:** ON both legs; strip `<thinking>`/`response` spans before scoring; N=20 probe arbitrates.
5. **Sampling:** one bucket draw per class at n=100; the 20/50 buckets are **prefix slices of the
   locked 100-row set — NEVER re-drawn**. (Verified 2026-09-25: `corpus._draw_buckets` seeds per
   CLASS, not per count, so nesting is coincidental — 50⊂100 holds only ~26% of seeds, 20⊂100 ~82%.
   Re-drawing per size would break the same-subset guarantee. This corrects the naive nested-draw
   assumption in §2.4; mirrored in `docs/modal-serving-ops.md` §5 and eval-env issue #20.)
6. **Prompts:** eval-environment frozen lineage + promoted catalog stems are the single source of truth;
   sandbox `config/prompts/*` locked to identical bytes (sha256 drift test).
7. **Scoring:** pipeline's own suite/field scorers (nested `extraction.overall_score`); report raw AND
   normalized exact-match; per-doc error distribution + per-field coverage.
8. **Sink:** Braintrust (both repos) — spans carry `run_id`, model, cost; experiment logs stay the
   durable local record; graceful no-op without keys.
9. **Baseline:** Qwen comparisons = ARCHIVED records only (no new Qwen spend) unless H4 expands.
10. **Sequencing gate:** N=20 wave (both legs) must pass JSON-parse-rate, token-budget, thinking-probe,
    and Δ-CI sanity before N=50 → N=100. All spend is capped (§6).

---

## 5 · Units of work (dispatch order; evidence contract each)

| # | Unit (card) | Owner | Scope | Evidence contract / gate | Depends |
|---|---|---|---|---|---|
| **U1** | SAND-027-1 · Granite claims verification | **DONE 2026-09-25** (lucius + docker-deployment-specialist + ml-systems-oracle) | §2 of this file | Verdicts folded into §2; no re-dispatch unless gates re-open | — |
| **U2** | SAND-027-2 · Leg B prep in eval-environment (execution tracked in eval-env issues) | eval-env subagents (eval-runner, corpus-curator) under its AGENTS.md | **Issues filed 2026-09-25: #18 program, #19 prompt alignment, #20 same-subset, #21 Braintrust/log.** Execute per those issues: parametrize `eval:<specialist>` × 5 for `--model ibm-granite/granite-4.2-8b` + explicit max_tokens + seed; confirm `--invoke agent` + subset grammar give identical per-class draws; Braintrust `--trace-backend braintrust` | `--task eval:<s> --mock --n 2` green; per-class 20/50/100 case lists recorded (filenames) | U1 |
| **U3** | SAND-027-3 · Prompt alignment (sandbox ↔ eval-env) | atom (sandbox) + eval-env prompt lineage gate | stem table {doc_type: sandbox file → eval-env file → sha256 → status}; fix drift via `promote_sandbox_specialist.py` (eval-env, Refs issue) or copy-and-lock; sha256 cross-repo drift test (skip-if-sibling-absent, hermetic) | table + drift test green; every stem byte-identical | U1 |
| **U4** | SAND-027-4 · Same-subset guarantee | corpus-curator (eval-env) + harness-doctor (sandbox) | nested per-class locks BOTH sides; compare filename-sets sandbox preflight `dataset.jsonl` vs eval-env case list per class; pin in tests | equality report (5 classes × 3 sizes); degenerate-draw check (dup/near-dup docs) | U3 |
| **U5** | SAND-027-5 · Braintrust sink (both repos) | langfuse-trace-sink-specialist | sandbox: `braintrust` dep (+dev lock), env (provider/key/project), vendored wrap_openai + task span + flush in the run path; eval-env: `EVALS_TRACE_BACKEND=braintrust` + metadata (run_id/model/cost) | 1-doc mock-safe smoke on each side; spans visible in Braintrust project `mailroom-sandbox`; no-key path unchanged; both suites green | U2/U3 |
| **U6** | SAND-027-6 · Leg A deploy + swap-in runbook | docker-deployment-specialist (config) → general (deploy) | sandbox: `models.yaml` local_catalog/modal_models row for granite-4.2-8b(-fp8); posture YAMLs; deploy 1×L4 FP8 on hermes (or declared host); health + preflight + **deploy-smoke: parsers/structured-output/maxlen boot**; docs (extend `docs/benchmark-l4.md` → Granite runbook) | endpoint healthy; smoke verdict recorded (H5 decides tag bump); teardown AFTER all runs (DMR-076 posture) | U5 |
| **U7** | SAND-027-7 · N=20 probe wave (FIRST SPEND) | eval-runner (B) + general (A) | both legs × 5 classes × 20 docs; thinking-probe, token-count check (vs budgets), JSON parse rate w/ thinking-strip, Δ-CI sanity | probe report; spending inside cap; if thinking mismatch or parse-rate <~95% → stop, file needs_attention | U2-U6 |
| **U8** | SAND-027-8 · N=50 + N=100 waves | as U7 | one-shot 100-doc runs per class per leg (500 calls/leg); prefix-slice 20/50/100 | all 30 run records in experiment logs; Braintrust traces; real cost blocks; no cap breach | U7 |
| **U9** | SAND-027-9 · QWEN-flash cost reports (parallel-safe) | atom + lucius | `reports/QWEN-FLASH-COST-REPORT.md` per §2.7 data + api-evals `run_api_evals.py report --from-log` + archived Modal Qwen serving JSONs/MODAL-RUNS-REPORT.md | every number reconciles to logs/registry pin/live prices; TTFT never inferred; caveats stated | U1 |
| **U10** | SAND-027-10 · Paired analysis + final comparison report | lucius + eval-judge | bootstrap Δ-CI (paired, over docs): Granite/MODAL vs Granite/OR per class per size; vs archived Qwen baseline; score tables + cost tables + convergence curves | report.md + data files in `reports/`; claims match experiment logs | U8, U9 |
| **U11** | SAND-027-11 · Adversarial review | adversarial-reviewer | every report number vs source; comparability claims vs specs; Braintrust evidence; no hallucinated rows | verdict naming file:line per claim; close all gaps | U8-U10 |
| **U12** | SAND-027-12 · Board close + commits + snapshots | orchestrator + atom | SAND-027 rows → done w/ evidence (commit SHAs, run_ids, report paths); eval-env: render log + `export_site_snapshot.py` + commit; sandbox: SAND-prefixed commits (api-evals, spec.py, configs, reports, tests, this plan) | both repos clean-for-scope; viewer snapshot fresh | U11 |

---

## 6 · Sequencing & spend posture (cap enforced, no exceptions)

- **Free work (now →):** U2-U6, U9 (all config/tests/docs — zero API/GPU spend).
- **First funded step: U7 N=20 probe** (5 classes × 20 docs × 2 legs ≈ **$1.29**, of which
  contracts + correspondence are **measured** and the other 3 classes extrapolated).
  **Hard cap $1.50.** Gate: probe report green → per-class escalation (each under its own 3×
  measured-cost cap) → U8 → U10 analysis.
- **Caps:** the **per-wave** caps above govern. Outer program ceiling **$6 soft / $8 hard** across
  both legs, enforced via `job.cost_cap_usd`/`max_wall_seconds` (+ wallet-side confirmation at each
  wave start). Track: `reports/` experiment logs are the ledger. **No expansion is pre-authorized
  by the program ceiling** — each wave needs its own approval.
- **Deploy discipline (DMR-076/078):** ONE warm sandbox-vllm app; teardown `./deploy/teardown_vllm.sh`
  only after the last Leg A run; scaledown 120s attended.

---

## 7 · Human gates (needs_attention until answered)

- **H1 · Braintrust:** provision `BRAINTRUST_API_KEY` + confirm/create project **`mailroom-sandbox`**
  (used by BOTH repos). Blocks U5+.
- **H2 · OpenRouter + spend:** confirm `OPENROUTER_API_KEY` (eval-env `.env`) and **approve the
  W1 probe only — $1.50 hard cap for N=20 across both legs**. The $6 soft / $8 hard program ceiling
  is a safety bound, not a spend authorization; every later wave is re-priced from the probe's
  measured per-class costs and re-approved. Blocks U7+.
- **H3 · Twin acceptance:** approve the "same model" basis = identical HF/OpenRouter id
  (`ibm-granite/granite-4.2-8b`), GPU-host decode differs kernel-level — claim is over the **score
  distribution**, not bit-identical outputs. (ml-systems-oracle + this file; no action = accepted.)
- **H4 · Qwen baseline scope:** (a) archived-only (recommended) vs (b) new matched Qwen legs
  (5×{20,50,100}×2 legs — adds ≈$7+. Not in the current budget).
- **H5 · vLLM image tag:** keep v0.29.0 + IBM plugin parser (default) vs bump to 0.30.0 for native
  `granite_thinking_parser` (must-verify side effects on the sandbox's v0.29.0-pinned machinery).
  Decided AT the U6 deploy smoke, not before.
- **H6 · eval-environment tracking: RESOLVED 2026-09-25** — tracker = GitHub issues on
  `LLM-Mailroom-Services/eval-environment`; program issues **#18–#21** filed; eval-env-side units
  reference them and the SAND epic cross-cites each issue.

---

## 8 · Risks & open questions (must-verify list)

1. **Thinking-mode mismatch between legs** (biggest twin-breaker) → U7 probe arbitrates; flip Leg A if OR
   serves non-thinking. (§2.4, §4.4)
2. **OpenRouter unprompted max_tokens** — MUST be explicit per class or the comparison + $ blow up. (§2.4)
3. **Earlier flash score-0.0 status (sandbox)** — measurement gap vs genuine? Diagnostic in U9/U11; the
   Qwen-flash report marks it UNPROVEN, does not paper over it. (§2.7)
4. **v0.29.0 parser availability** for `granite_thinking_parser` → plugin fallback; covered by U6 smoke + H5.
5. **Structured JSON with thinking ON** needs `enable_in_reasoning=True` (vLLM) — validate in U6 smoke.
6. **Seed-42 draw degeneracy** (duplicate/near-dup docs within a class) — U4 check before inference.
7. **n=20 CI width + exact-match brittleness** — report normalized matches + per-doc error distribution;
   paired Δ is the only honest small-n claim. (§2.4)
8. **api-evals + spec.py are uncommitted open work** — preserve as-is; incorporate into U12 commits only
   after adversarial review. Do NOT `git add .` — targeted staging.
9. **BNumbers discipline:** all cost numbers in reports MUST trace to experiment-log records / serving
   JSONs / live or pinned prices; never $0 fabrications; honest gaps required where data missing.

---

## 9 · Deliverable inventory

| Artifact | Where | Owner | Due |
|---|---|---|---|
| Laid-open board + this plan | sandbox `governance/TASKS.md` + `governance/SAND-027-MISSION-PLAN.md` | orchestrator | now |
| Prompt-alignment table + drift test | sandbox `config/prompts/` + `tests/` | atom | U3 |
| Granite modal row + runbook | sandbox `config/models.yaml`, `config/runs/granite-*.yaml`, `docs/` | docker-deployment-specialist/general | U6 |
| eval-env task/config deltas | eval-env `src/evals/` + its tracker | eval-env subagents | U2 |
| N=20 probe report | both repos `reports/` | eval-runner/general | U7 |
| Full run records (30) | both `reports/experiment_log.jsonl` + Braintrust | — | U8 |
| QWEN-flash cost report | sandbox `reports/QWEN-FLASH-COST-REPORT.md` + `api-evals/reports/<stamp>/` | atom/lucius | U9 |
| Final paired comparison report | sandbox `reports/GRANITE-APPLES-TO-APPLES.md` (+ eval-env comparison) | lucius/eval-judge | U10 |
| Adversarial verdict | chat + linked into U12 commit | adversarial-reviewer | U11 |

---

## 11 · Cross-repo issues filed (2026-09-25, `gh` as Exios66 → LLM-Mailroom-Services/eval-environment)

| Issue | Title | Maps to |
|---|---|---|
| [#18](https://github.com/LLM-Mailroom-Services/eval-environment/issues/18) | Granite-4.2-8b OpenRouter comparison runs — 5 specialists × nested 20/50/100 | SAND-027-2 U7/U8/U10 |
| [#19](https://github.com/LLM-Mailroom-Services/eval-environment/issues/19) | Prompt alignment: EXACT stems the Modal leg uses (sha256-locked) | SAND-027-3 (refs #4–#8) |
| [#20](https://github.com/LLM-Mailroom-Services/eval-environment/issues/20) | Same-subset guarantee: identical doc sets per class/count | SAND-027-4 |
| [#21](https://github.com/LLM-Mailroom-Services/eval-environment/issues/21) | Braintrust tracing + experiment-log coverage | SAND-027-5 |

Existing related issues (do not duplicate): **#4–#8** catalog prompt promotions, **#9** empty-GT scoring.

---

## 10 · Board actions (card lifecycle)

- `SAND-027` epic: **in_progress** (owner orchestrator) — opened with this plan.
- `SAND-027-1` (verification): **done** — evidence = this file §2 + specialist transcripts (2026-09-25).
- `SAND-027-2..12`: created **todo**; claim→in_progress as each unit starts (owner + UTC date in Notes).
- Human gates land as rows in `needs_attention` with the exact question (H1-H6).
- Every `done` cites commit SHAs + run_ids + report paths. Next ID after this epic: `SAND-028`.