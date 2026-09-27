# SAND task list — local-mailroom-sandbox

**Prefix: `SAND`** · Board rules: [`README.md`](README.md) · Cheat-sheet:
[`PREFIX.md`](PREFIX.md)

Cross-family work stays on llm-entity-extraction's MESSAGE_BOARD as
**`DMR-*`**. This file is the **only** sandbox-local task board — do not
open `DMR-*` cards here.

**Next ID: `SAND-032`**

Lanes: `todo` → `in_progress` → `needs_attention` → `done`.

---

## Open / in progress

| ID | Title | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| SAND-031 | Centralize operator runbooks (singular 1×L4 Qwen3-8B + improved configs) | cursor | **done** | Catalog `config/runbooks/catalog.yaml`; CLI `sandbox runbook list\|show\|check\|write`; generated `docs/runbooks/`. Pins tested against deploy + models.yaml + run YAMLs. Related: SAND-027-6 Granite live deploy still todo. |
| SAND-030 | Modal L4 long-prompt vLLM posture (max_num_seqs 4–6, APC, eager, DP second L4) | cursor | **done** | Deploy defaults + run YAMLs + docs. Data parallel via `MAX_CONTAINERS=2`, not TP. Related: SAND-023 topology / SAND-028 spend. |
| SAND-020 | Correspondence extraction floor diagnosis + parse/schema metric (issue #21) | cursor | **in_progress** | Offline: schema-adherence rates, empty-field/partial-credit docs, FP16 twin YAML (not run). Related: GitHub issue #21 |
| SAND-028-7 | Repo layout audit — document the two run-spec trees (no moves) | archivist-file-organizer | **done** | 2026-09-26. `docs/LAYOUT.md` + README/config README amendments; api-evals stays a separate tree (spend + distribution boundary, verified); junk swept; pytest 438/4 baseline unchanged. Commit `d01e754`. |
| SAND-029 | Repo layout follow-ups (from the SAND-028-7 audit) | orchestrator | todo | Epic for the audit's deferred items. |
| SAND-029-1 | Delete dead `DATA_DIR` / `BLANK_DIR` constants in `api-evals/api_evals/registry.py` | harness-doctor | todo | Point at `api-evals/data` + `api-evals/blank` which do not exist and are never referenced (verified dead). Needs SAND-027 owner go (card in progress). |
| SAND-029-2 | Docs gaps from the layout audit: `reports/README.md` table, AGENTS.md → `docs/LAYOUT.md` link, `data/memory/` convention decision | atom | todo | `reports/{archive,serving,scores}` + gitignored `experiment_log.*` are undocumented; `data/memory/` is gitignore-reserved but nothing creates it. |
| SAND-029-3 | Optional: `vendor/**/__pycache__` cache sweep as a leg SEPARATE from any vendor refresh | jarvis | todo | 11 inert dirs (drift test + .gitignore exclude them from byte-identity). Never conflate a cache sweep with a byte-identity refresh. |
| SAND-028 | Modal + vLLM serving: critical review & spend-reduction plan | orchestrator | **in_progress** | Review: `governance/SAND-028-SERVING-SPEND-REVIEW.md`. **No spend.** Measured anatomy: GPU wall-clock = ~98% of price (token-proxy only 2.4%); cold boots = 24% of the 3 measured runs; contracts $0.0188/doc vs correspondence $0.0028 (6.7×, decode-driven). Backlog O1-O9 gates SAND-027 U6/U7 — apply before the 15-run Granite matrix. |
| SAND-028-1 | Instrument `busy_gpu_seconds` vs `billed_gpu_seconds` (idle fraction per run) | harness-doctor | **in_progress** | F6 — makes F1-F4 arithmetic instead of guesswork. **BLOCKED:** the serving.json writer that emits wall/concurrency/latency_sum is NOT in tracked code (`record_from_run` metrics.py:224 omits them) → **issue #36**; billed-window definition defect → **#37**. Plan: build the committed serving-report generator first, then the idle block. |
| SAND-028-1a | Commit the open working tree (mission artifacts + harness changes) | orchestrator | **done** | 2026-09-25. Committed + pushed: `dfff460` (plan + api-evals + spec openrouter), `8ae4930` (serving review/ops, models.yaml, parser knobs, docs, board), `d01e754` (layout docs), `bf8e65e` (board follow-ups). Issue #35 closed; pytest 438 passed / 4 skipped at `bf8e65e`. |
| SAND-028-2 | Decode-length fix: guided/JSON structured decode + fail-fast on LengthFinish + per-doc wall budget | harness-doctor / prompt-engineer | todo | F1/F4 — top lever (~$2-3 on matrix). **Twin constraint: must be mirrored on OpenRouter leg (eval-env #18/#19) or the apples-to-apples claim breaks.** |
| SAND-028-3 | Re-derive per-class concurrency toward 8 on FP8 Granite (probe-driven) | harness-doctor | todo | F3 — measured 167→472 tok/s (c5→c8) on same L4. Re-measure per class; merger stays lowest. |
| SAND-028-4 | Re-derive `sec_per_doc` / cost caps from measured probe; prefer `MODAL_BILLED_GPU_SECONDS` | general (post-probe) | todo | F5 — caps set from heuristics; a cap that aborts a correct run burns the whole warm window. |
| SAND-028-5 | Ops posture: one warm app via `sandbox run suite`, pre-warm weights once, no mid-matrix recreate, stay on L4 | general (ops) | **done** | 2026-09-25. **Free ops wins shipped (zero spend):** `docs/modal-serving-ops.md` runbook (warm-once, teardown-once, L4, caps-from-measurement, anti-patterns); Granite `modal_models` rows in `config/models.yaml` (fp8 L4/32768 + bf16 ref); env-gated reasoning/tool parser knobs in `deploy/modal_vllm.py` (Qwen default byte-identical, verified); `sandbox modal-matrix env` granite resolves; full suite 438 passed / 4 skipped. |
| SAND-028-6 | Granite thinking-span cap/measure (twin-vs-cost decision) | prompt-engineer / harness-doctor | todo | F1 (Granite) — OpenRouter can't steer thinking; decide from N=20 probe with data. |
| SAND-027 | Granite-4.2-8b Modal vLLM ↔ OpenRouter apples-to-apples (5 types × 20/50/100) + QWEN-flash cost report | orchestrator | **in_progress** | Full plan: `governance/SAND-027-MISSION-PLAN.md`. **No spend yet.** Gates H1 (Braintrust key/project) + H2 (OpenRouter keys; **W1 probe only, $1.50 hard cap**) pending. Twin verified: `ibm-granite/granite-4.2-8b` (HF id == OpenRouter id, Apache-2.0, $0.06/$0.25 per 1M). **OpenRouter runs execute in eval-environment** (issues #18–#21 filed); sandbox = Modal vLLM leg + request plumbing only (api-evals/spec.py). U6/U7 gated by SAND-028 backlog. **Spend posture:** per-wave caps govern — probe $1.50, per-class escalation cap = 3× that class's measured N=20 both-leg cost; program ceiling $6 soft/$8 hard is a safety bound, NOT an authorization. Re-derived from measurement (`docs/RUN-COST-DERIVATION.md`). |
| SAND-027-1 | Granite claims verification (lucius + docker-deployment-specialist + ml-systems-oracle) | orchestrator | **done** | 2026-09-25. Verdicts in plan §2. Winner granite-4.2-8b; Leg A = `-fp8` 1×L4 @ 32768 (FP8 native Ada; no AWQ published); thinking ON both legs, strip spans; sampling nested 20⊂50⊂100 seed 42. |
| SAND-027-2 | eval-environment: Leg B prep — **execution tracks in eval-env issues #18–#21** (program / prompts / same-subset / braintrust+log) | eval-runner | todo | Issues filed 2026-09-25 (gh as Exios66). eval-env AGENTS.md non-negotiables apply; mock before real; H6 resolved → tracker = `LLM-Mailroom-Services/eval-environment` issues. |
| SAND-027-3 | Prompt alignment sandbox ↔ eval-environment (stem sha256 drift test) | atom | **in_progress** | Source of truth = eval-env frozen v1 catalog. Sandbox `*_simplified` stems sha256-locked in `config/prompts/eval_environment_lineage.json`. Runtime injection now rebinds Family A `get_managed_prompt` so Modal + vLLM specialist evals actually send those bytes (not vendor production). Records log `*_v1` keys. Eval-env side: issue #19. |
| SAND-027-4 | Same-subset guarantee (nested 20/50/100 per class; filename-set equality both legs; degenerate-draw check) | corpus-curator / harness-doctor | todo | **Sampler verified NOT nested (50⊂100 ≈26% of seeds) → issue #38**: must slice the locked 100-draw, never re-draw per size. Sandbox preflight `dataset.jsonl` vs eval-env case lists. |
| SAND-027-5 | Braintrust sink in BOTH repos | langfuse-trace-sink-specialist | todo | sandbox: SDK dep + vendored wrap_openai + task span + flush; eval-env: `EVALS_TRACE_BACKEND=braintrust`. 1-doc smoke + no-key no-op. |
| SAND-027-6 | Leg A deploy + Granite swap-in runbook (1×L4 FP8; deploy smoke: parsers, structured output, maxlen boot; H5 tag decision after smoke) | docker-deployment-specialist / general | todo | Operator runbook shipped under SAND-031 (`sandbox runbook show improved-granite-fp8`). Remaining = live deploy + smoke + H5. Draw ONE bucket/class (100) and slice 20/50 — do NOT re-draw. |
| SAND-027-7 | N=20 probe wave — **FIRST SPEND** (both legs × 5 classes × 20 docs) | eval-runner / general | todo | Gate: JSON parse rate, token budgets, thinking probe, Δ-CI sanity. **≈$1.29** (contracts + correspondence measured; 3 classes extrapolated) · **hard cap $1.50**. Contracts and correspondence are the priority classes. **Per-doc basis → `docs/RUN-COST-DERIVATION.md`.** |
| SAND-027-8 | N=50 + N=100 waves (one-shot 100/class/leg → prefix-slice buckets) | eval-runner / general | todo | **NOT pre-authorized.** Each class escalates only under its own cap = **3× that class's measured N=20 both-leg cost** (5× docs must cost ≤3×, or land F1–F4 first). Program ceiling $6 soft/$8 hard. Full 5×100 unoptimized ≈ $6.30–6.50 total — re-price from the probe before committing. 500 calls/leg; all 30 run records + Braintrust traces. |
| SAND-027-9 | QWEN-flash cost reports (earlier 3 records + api-evals `report --from-log` + archived Modal Qwen baseline) | atom / lucius | todo | Real API $ ≈ $0.012 total vs logged L4-proxy ≈ $0.0186; caveats per plan §2.7. **Reproducibility gap → issue #40** (log gitignored, no real API cost recorded); 0.0-score diagnosis open → **issue #41**. |
| SAND-027-10 | Paired analysis + final apples-to-apples report (bootstrap Δ-CI vs Qwen baseline) | lucius / eval-judge | todo | `reports/GRANITE-APPLES-TO-APPLES.md`. |
| SAND-027-11 | Adversarial review of reports + comparability claims | adversarial-reviewer | todo | Verdict names file:line per claim. |
| SAND-027-12 | Board close + commits (SAND-prefixed, targeted staging) + eval-env snapshot refresh | orchestrator / atom | todo | Evidence = commit SHAs + run_ids + report paths. |
| SAND-026 | Simplify sandbox extraction prompts + document field-level instructions | cursor | **in_progress** | GitHub #32 / draft PR #33. Class-specific `*_simplified` stems + empty-GT scoring scope. Catalog promotion tracked in eval-environment #4–#8. Do not close #21 or #32. |
| SAND-018-1 | Gate: `huggingface-secret` missing in `hermes-agent-jjb` (provision it, or deploy under `exios66`) | human | **done** | **Decision: Option A** — human provisioned `huggingface-secret` in `hermes-agent-jjb`; connect resumes on the runbook Track A default wallet. |
| SAND-018 | 20-contract Modal+vLLM readiness run (full-corpus logged sample) | orchestrator | **in_progress** | Runbook `sandbox runbook show l4-qwen3-8b-n20`; `run-20-contracts-specialist.yaml` + posture/gate coverage (DMR-078); preflight green — `spec_hash=423c7684cb6c…`, 20 contract rows, `seed=42`, `sha256=fad06e44f54f…`. Connect: deploying `sandbox-vllm` on `hermes-agent-jjb` (secret now present) |
| SAND-010 | Finish 50-subclass Modal sorter mission (teardown + interpret + monorepo sync) | jarvis / athena | **in_progress** | Epic for archived `SANDBOX-050` mission — see sub-cards below + [`archive/SANDBOX-050.md`](archive/SANDBOX-050.md) |
| SAND-010-3 | Preflight + guards loud (1-row live smoke pending) | test-suite-auditor | **in_progress** | was `SANDBOX-050-3`; DMR-072 silent-fallback fixed |
| SAND-010-5 | Run start → watch → completion | test-suite-auditor | **in_progress** | was `SANDBOX-050-5`; attempt 1 invalidated |
| SAND-010-6 | Teardown: app stop, zero containers, volumes persist | jarvis | todo | was `SANDBOX-050-6` |
| SAND-010-7 | Interpret: per-stratum accuracy, confusion, readiness | athena/lucius | todo | was `SANDBOX-050-7` |
| SAND-010-8 | Monorepo sync + close SAND-010 epic | atom | todo | was `SANDBOX-050-8` |
| SAND-014 | Modal doc-jobs Phase A human gates (3 decisions) | human | todo | Close rows in this board when decided — see `docs/modal-doc-jobs.md` §6 |
| SAND-014-1 | Gate: Stage A extraction depth (CPU OCR vs GPU vision) | human | todo | Plan default: pypdf/pdfplumber + pytesseract |
| SAND-014-2 | Gate: `process_document` graph scope (full vs reduced) | human | todo | Plan default: full 13-node |
| SAND-014-3 | Gate: CLI surface (`doc-jobs` vs `sandbox run` mode) | human | todo | Plan default: own `sandbox doc-jobs` family |

---

## Done (recent)

| ID | Title | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| SAND-017 | Central subagent roster + Cursor/OpenCode adapters | cursor | **done** | `config/subagents/roster.yaml`, `.opencode/agents/`, `sandbox subagents *`, harness-doctor + adversarial-reviewer |
| SAND-016 | Modal/vLLM ↔ dojo cost-compare metrics parity | cursor | **done** | Adapter + `--fixture`; *Related: DMR-049 / DMR-027* |
| SAND-001 | Establish SAND local board + prefix (isolated from DMR) | orchestrator | **done** | `governance/` README + PREFIX + TASKS; AGENTS.md / sister-repos wording |
| SAND-015 | Confirm SAND prefix adopted in AGENTS.md / sister-repos docs | orchestrator | **done** | Governance cutover shipped with SAND-001 |
| SAND-010-1 | Verify stratified 50-subclass sample | athena | **done** | was `SANDBOX-050-1`; strata QA green |
| SAND-010-2 | Amend run spec to GPU cap + lock | orchestrator | **done** | was `SANDBOX-050-2`; `run-50-five-types.yaml` |
| SAND-010-4 | Deploy sandbox-vllm v0.29.0 + verify endpoint | jarvis | **done** | was `SANDBOX-050-4`; health ok |
| SAND-011 | Qwen Modal specialist posture (per-doc-type runbooks) | orchestrator | **done** | Sandbox-local; *Related: DMR-078* on family board for merger vendor story |
| SAND-012 | `merger_agreement_specialist` sandbox plumbing | orchestrator | **done** | Taxonomy / components / eval / run-30 merger YAML; *Related: llm-mailroom #64 / DMR-078* |
| SAND-013 | Requirements surface completeness (`requirements/` + pipeline extras) | orchestrator | **done** | aiosqlite/greenlet/PDF stack; `scripts/sync_requirements.py`; *Related: DMR-078b* |

---

## How to add a card

1. Take **Next ID**, bump the counter in this file.
2. ID must match `SAND-<digits>` or `SAND-<digits>-<digits>` (see
   `tests/test_governance_sand.py`).
3. If the work is cross-family, file **`DMR-*`** on MESSAGE_BOARD instead
   (or in addition, with `Related: DMR-NNN` in notes).
4. Keep evidence links short (PR URL, run_id, commit SHA).
