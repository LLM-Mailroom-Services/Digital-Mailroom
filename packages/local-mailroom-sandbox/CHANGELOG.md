# Changelog

## [Unreleased]

### Added — local-first job traces (pack → upload → prune)

- Endpoint-mode runs (`sandbox run start`, the Modal-vLLM grid and SAND runs) now build a tracer; before this
  they always passed `tracer=None`, so no job spans were ever emitted whatever the locked sink said.
- Each run gets a `job.run` span with its `job.item` children nested across worker threads, carrying
  item id, ok/error, attempts and token usage.
- Spans are mirrored to `data/traces/<run_id>.spans.jsonl.gz` even with `sink: none`
  (`SANDBOX_TRACE_LOCAL=0` disables); Phoenix/Langfuse/OTLP export is unchanged.
- `sandbox traces pack <run_id> [--dest DIR] [--prune]` zips the mirror as zstd Parquet + manifest, copies it
  to a synced upload folder (`SANDBOX_TRACE_UPLOAD_DIR`, e.g. the Drive LOGS folder) under a date
  subfolder, verifies the copy by SHA-256, and only then deletes the local copies. See `docs/tracing.md`.

### Changed — SAND-040 runs on one 32K deploy; † merger keeps the optimized settings

- `sandbox runbook show sand40` deploys the SAND-037 2×L4 engine once (native 32768 window, no 64K
  redeploy). Correspondence, insurance claims, corporate records and contracts run n=100 on the aligned spec
  unchanged. Merger runs the same 50 agreements as SAND-37 2×L4 with the optimized † settings: chunked
  whole-document extraction (47,000-char windows + 6,500 overlap, sized to the 32K window), the MAUD v1
  prompt, Qwen3 sampling (0.7 / top_p 0.8 / top_k 20 / presence 1.0), a 6,144 cap and one length re-sample.
- A 5-agreement gate cell (`sand40-check-5-merger-specialist-awq-2l4`) runs first on the same deploy;
  `sandbox run card --gate` fails unless every document is ok and vLLM accepted every chunk the documents need
  (`extract_chunked` skips a rejected chunk silently). On failure the script tears down and stops.
- Runbook catalog: optional `gate: {config: …}` renders the gate before the scored loop.
- Master card: new *Merger † settings* table (SAND-37 vs SAND-40, changed settings in bold, result and
  matched-agreement delta once measured); SAND-40 column reads 100 (merger 50†).
- Removed the unrun 64K long-phase cells and the `sand40-short` / `sand40-long` runbooks. The executed 64K
  probes stay as a matched-document appendix.

### Changed — SAND-040 master score & cost card validated and fully detailed

- Validated `reports/SAND-37/SAND-37-MASTER-SCORE-COST-CARD.md` three ways: a fresh `sandbox run card --master`
  render is identical to the committed card; every pooled and per-specialist figure recomputes from the
  per-document rows in the 15 cell cards (ok counts, tokens, busy-window cost, throughput, p50 latency, MAUD
  accuracy and coverage, CUAD F1); every finding's numbers match the cards. Card p95 latency is nearest-rank.
- Contracts is now labeled as what it measures: the per-document CUAD clause-presence F1 averaged over
  successful documents with CUAD labels (micro F1 in parentheses). The run reports count unlabeled documents
  as 0, which is why they read about 0.10 lower.
- New master sections: per-cell detail for each posture (errors by kind, schema-valid rate, score sd, p50/p95,
  tokens per document, completion p95/max, wall, busy GPU $, $ per 1M tokens, tokens/s/GPU); clause scoring
  detail (CUAD precision, recall, value accuracy; MAUD questions, answered, correct, precision); vLLM engine
  telemetry (requests, length-capped finishes, preemptions, prefix-cache hit rate, TTFT); run conditions by
  specialist; pooled wall, token split, length finishes and preemptions.
- SAND-40 validation probes appear in an appendix with a matched-document comparison against the SAND-37
  2×L4 cell, never in the pooled columns. On matched documents the 64K contracts probe is flat (−0.002,
  8 better / 7 worse); the merger probe gains +0.081 MAUD accuracy (14 / 3) while reading 11.5× the prompt
  tokens through chunked extraction.
- The SAND-40 header no longer commits the run to a 64K YaRN redeploy; each SAND-40 card records its window.

### Added — SAND-037 aligned specialist grid and runbooks

- All 20 Qwen3-8B-AWQ specialist grid cells (5 classes × n = 20/50 × 1×L4 C8 / 2×L4 C32) now share one spec:
  the SAND-032 frozen L5 engine (`awq_marlin`, fp8 KV, CUDA graphs, `max_num_seqs` 16 per replica, thinking off,
  `max_inputs` 32), `split: all` single-class draws at seed 42 (n = 20 nests in n = 50), the frozen v1
  `*_simplified` prompts, and `max_tokens` 8192. Only n, replicas and concurrency vary. Previously the 1×L4 cells
  ran plain `awq` eager at `max_num_seqs` 8, the 2×L4 cells plain `awq`, and the n = 20 insurance / corporate /
  merger draws were stratified on `split: test` / `train`.
- `docs/SPECIALIST-GRID-PLAN.md`: the aligned spec, the length-error analysis, all 20 cell run ids, and the
  existing records each cell supersedes.
- Runbooks `grid-1l4` and `grid-2l4` (new `grid` catalog family, serving variants that differ only in replica
  count): one warm deploy per fleet shape, ten cells each.
- Eight new run YAMLs (the n = 20 cells the grid lacked, plus `grid-20-merger-specialist-awq-1l4-rerun` and
  `grid-50-contracts-specialist-awq-2l4-rerun`, which leave the executed cells' reports intact); every grid YAML
  is generated from one template.

- SAND-37 score & cost cards (`mailroom_sandbox.job.grid_cards`): every grid run writes
  `reports/SAND-37/<1L4|2L4>/<specialist>/<run_id>.card.{md,json}` (conditions; run, time, cost, tokens,
  throughput, latency, per-replica vLLM telemetry, quality and CUAD/MAUD clause scoring; error ledger;
  per-document rows), and `sandbox run card --runbook grid-1l4|grid-2l4` writes the finalized
  `L4x1-` / `L4x2-SCORE-COST-CARD.{md,json}` from the committed card JSON. The runner writes the card at the end of
  each grid run; `sandbox run card --config` re-renders it after the `/metrics` after-scrape, reusing the runner's
  busy wall. The grid runbooks bracket each start with `scrape-metrics` before/after and end with the suite card
  (catalog flags `scrape_metrics`, `export_card`).

### Fixed — SAND-037 runaway decoding on contracts and merger

- Every LengthFinishReasonError on record is a contracts or merger document that used its whole cap (4096, 8192
  or 16384), while successful outputs top out at 4,055 tokens and the failing documents change between runs.
  Those two specialists decode under the JSON-schema grammar at a call-site `temperature=0.1`; near-greedy
  decoding loops and job retries replay the loop. Grid contracts and merger cells now run at temperature 0.7
  (Qwen3's documented non-thinking setting); the json_object classes keep 0.1.
- `mailroom_sandbox.sampling`: applies a run-scoped `temperature` knob to the vendored specialists, whose call
  sites pass `temperature=0.1` as a literal (previously a configured temperature never reached the request).
  Installed at `activate()`; agents without a knob are untouched.
- `sandbox runbook check` fails when a grid runbook's export block disagrees with `sandbox run deploy-env` for any
  of its configs; `sandbox run benchmark-check` applies its deploy-env drift gate to grid cells as well as
  SAND-032 runs. The `preflight_force` catalog flag renders `preflight --live --force` to re-lock a drifted run.

### Added — SAND-036 warm vs cold GPUs, cost per 1M tokens, Modal vs API break-even, mailroom-issues Pages site

- `reports/dashboard/gpu_report.py`: cost per 1M tokens on three bases (warm busy-window, one cold batch, program-loaded),
  warm-fleet cost per token at falling utilization with the break-even busy share, and a warm vs cold section (boot
  measurements, warm vs cold $/doc and $/1M per workload, the batch size that amortizes a cold start, keep warm vs
  scale to zero with the threshold = scale-down + L5 boot). Every setup value and date in the report is read from the
  serving exports and run reports; the hub `fleet` extract gains `scaledown` and each run's own score.
- `reports/dashboard/breakeven.py`: one per-document Modal-vs-API calculation (verdict per class, every measured Modal
  configuration against the cheapest hosted model, warm and cold break-even volumes, the optimal measured deployment)
  quoted by the cost comparison's §3, the GPU report and the site, so no two reports disagree.
- Dark, high-contrast figures: `scripts/sand032/viz.py` renders every chart as a dark card on the reference palette's
  dark steps (validated `--mode dark`: ALL PASS), with a fixed color per model (`ENTITY`) and a legend whenever
  bars carry more than one color; subtitles in sentence case. All 51 SAND-032 figures re-rendered
  (`rerender.py`, data unchanged). The Pages site and the hub dashboard are dark by default.
- `reports/dashboard/source_charts.py`: the eval-environment and mailroom-ml charts the reports used to copy are
  redrawn from hub data in the same kit, so every report figure shares one theme.
- `reports/dashboard/export_pngs.py`: 2× PNG of every report figure for slides (`mailroom-issues/reports/viz/`).
- The per-token comparison includes the Qwen3.7-Flash n = 50 legs (token counts now extracted and cross-checked
  against their reports); the sorter table lists every hosted model's largest run (Qwen3-8B: n = 20).
- Model per route made explicit: Qwen3-8B-AWQ is the only model self-hosted on Modal; Qwen3.7-Flash and every other
  hosted model ran through the API only. The cost comparison's §3.2 adds the same-model comparison (Qwen3-8B-AWQ on
  Modal vs Qwen3-8B via the API), isolating the route from the model.
- `reports/dashboard/pages_site.py` + `export_hub_reports.py --site`: the three reports as a static GitHub Pages site
  for `mailroom-issues/docs/` (inline SVG, no JavaScript, no external requests; covered by `--check`).
- Hub snapshot re-pinned to eval-environment `86b4e54` (main, including the qwen3.7-flash suite README); `markdown-it-py`
  joins `[dev]` (requirements regenerated with `scripts/sync_requirements.py`).
- `tests/test_gpu_report.py`: the $/1M identity, the keep-warm threshold, the amortizing batch, the break-evens and the
  optimal row, and site integrity (no scripts, every internal link and anchor resolves).

### Added — SAND-035 cross-repo report audit + Modal vs API cost comparison

- `scripts/sand032/viz.py` sizes label columns by measured text width (middle ellipsis, full label in
  `<title>`), gives reference-line labels their own lane, and spaces dumbbell legends by measured width;
  `dumbbell(val=...)` overrides the end-of-row label. `scripts/sand032/rerender.py` re-lays all 51
  committed SAND-032 figures from their embedded data and asserts the data is unchanged (`--check`).
- Reports hub: **Modal vs API** tab (cost vs quality per specialist and for the sorter); snapshot synced to
  eval-environment `f6bb510` / mailroom-ml `d3ad222` (the merged chart-layout fixes; source SHAs only, no
  values changed); Qwen3.7-Flash n = 50 legs cross-checked; the merger
  leg eval-environment files under Qwen3-8B is labelled by its logged model (Qwen3.7-Flash, frozen prompts).
- `reports/dashboard/export_hub_reports.py` writes `COST-COMPARISON-MODAL-VS-API.md`, `MASTER-REPORT.md` and
  figures for `mailroom-issues/reports/`; `report_audit.json` records the sweep (0 overflow / 0 collisions /
  0 broken links across the three repos).

- `reports/dashboard/gpu_report.py` writes `MODAL-VLLM-GPU-REPORT.md` for `mailroom-issues/reports/`: cost per token,
  GPU spend breakdown, client-slot occupancy, per-replica vLLM metrics and the second-L4 analysis. The hub gains a
  `fleet` section (`hub_extract.sand032_fleet`): all 24 SAND-032 serving exports cross-checked against their run
  reports (wall, tokens, throughput, busy and billed GPU $, slot occupancy, replica request split). `viz.hbar` gains
  `domain_max` so small multiples can share one scale.

### Fixed — SAND-036

- Hub stratum means and the legacy spend total use `math.fsum`, so `hub_data.json` is identical whether it is
  rebuilt on Python 3.11 or 3.12 (3.12's `sum()` compensates, 3.11's does not; the two differed in the last digit).

### Fixed — SAND-035

- `build_hub.py --check` crashed (`KeyError: 'run_id'`) on eval-environment log rows without a run id.
- Latency/subclass figure labels overflowed the left edge; p50/p95 labels collided with each other and
  the subtitle.
- Broken relative links in CHANGELOG, docs, RUN-20 serving reports and agent prompts.
- SAND-032 spend: the program summary's header gave the stage 1–5 ledger ($1.21) while its closing ledger read $2.80;
  the runs alone bill $2.18. The header is corrected, and the hub checks it against the closing ledger and the runs'
  billed GPU $.
- The S6 sorter's $/doc was the billed figure (with its 131 s cold boot); the hub now uses the busy-window basis like
  every other run and records the report's figure as a documented source issue.

### Changed — governance: DMR-068 hub tracker + SAND board reconciliation

- `docs/scale-matrix.md` status line cites the DMR-068 hub tracker
  (LLM-Mailroom-Services/mailroom-issues#205) for owner and spend decision.
- `governance/TASKS.md` gains rows for SAND-021..025, which existed only as
  GitHub issues (#27-#31), and states that the board is the SAND numbering
  authority (highest id in use: SAND-033). Closes mailroom-issues#194.

### Added — SAND-031 centralized operator runbooks

- **Single edit surface:** [`config/runbooks/catalog.yaml`](config/runbooks/catalog.yaml).
  Change pins / steps there, then `sandbox runbook check` (catalog vs
  `deploy/modal_vllm.py` + `config/models.yaml` + cited run YAMLs) and
  `sandbox runbook write` (regenerates `docs/runbooks/`).
- **Singular 1×L4 / 1-container Qwen3-8B:** `sandbox runbook show l4-qwen3-8b`
  (plus Operator A/B tracks and the SAND-018 N=20 probe).
- **Improved configs:** AWQ, AWQ-c8, correspondence AWQ/c8, FP16 isolation twin
  (blocked), Granite 4.2-8B FP8 swap-in, second-L4 data parallel, scale-matrix
  cells — `sandbox runbook list --family improved`.
- CLI: `sandbox runbook list|show|check|write`. Tests:
  `tests/test_runbooks.py`. `docs/modal/benchmark-l4.md` is now the pointer;
  operator scripts are generated.

### Changed — monorepo target Digital-Mailroom (2026-09-24)

- Subagent propagate/materialize docs and package ids use **`digital-mailroom`**
  ([LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom));
  `mailroom-dev` remains a legacy CLI alias only.

### Fixed — SAND-027-3 eval-environment prompt versions on Modal + vLLM specialist evals

- Family A specialists (`correspondence`, `corporate_records`, `insurance_claims`,
  `merger_agreement`) bind `get_managed_prompt` at import time. Preflight
  imports those modules via `prompt_templates()`, so patching only
  `llm.prompts.get_managed_prompt` left Modal runs on vendor/Langfuse
  production text. `apply_runtime_overrides` now rebinds every loaded module
  and writes LangChain `PROMPT_VERSIONS` role + `{role}_v*` keys (same
  injection as eval-environment `evals.prompts.registry.activate`).
- Isolated specialist evals default to the frozen v1 sandbox stems. Job locks
  that pin `prompt.agents.<task>` now pass that stem into `activate`.
- Experiment / serving records log `contracts_specialist_v1` (etc.) + sha256
  when the pin is a catalog stem.
- Hermetic lock: `config/prompts/eval_environment_lineage.json` (sha256 +
  opening line). `tests/test_eval_environment_lineage.py` fails on drift;
  sibling eval-environment checkout is compared when present.

### Changed — SAND-030 Modal L4 long-prompt vLLM posture

- Deploy defaults (`deploy/modal_vllm.py` + compose parity):
  `max_num_seqs=6` (was 256), explicit `--enable-prefix-caching`,
  `--enforce-eager` (faster cold boot). `gpu_memory_utilization=0.90` and
  HF/vLLM Volumes unchanged.
- Second L4 = **data parallel**: raise `MODAL_VLLM_MAX_CONTAINERS=2` (Modal
  `@web_server` round-robins). Do not use `GPU=L4:2`+TP for 8B-class.
- `VLLMSpec` gains `enable_prefix_caching` / `enforce_eager`; specialist and
  cost-eval run YAMLs pin the new posture. Scale-matrix cells keep
  `max_num_seqs: 256` and must export `MODAL_VLLM_MAX_NUM_SEQS=256` at deploy.
- Docs: `deploy/README.md`, `docs/modal/benchmark-l4.md`, `docs/scale-matrix.md`
  (container topology), `docs/modal/modal-serving-ops.md`, skill knobs.

### Added — SAND-020 correspondence extraction-quality diagnosis (issue #21)

- **`eval/schema_adherence.py`** — parse-failure / schema-adherence checks
  (`parse_error`, `schema_valid`, `schema_adherence`) separate from
  `overall_extraction_score` / `extraction_f1`. Wired into
  `score_extraction_row`, isolated / extract / pipeline summaries, and
  `sandbox metrics` quality extraction (additive keys only).
- **Empty-field + partial-credit tests** pinning dojo behavior: empty
  scalars are not events; empty-list inventions zero overall; F1 TP requires
  typed score ≥ 1.0; isolated `exact_match` is a runner alias of overall.
- **Offline diagnosis** of `run-20-correspondence-awq-c8` (fingerprint
  `285f423d3708`): [`docs/archive/extraction-quality-diagnosis.md`](docs/archive/extraction-quality-diagnosis.md)
  (best/worst docs, token evidence, owner-locked 0.25 / 0.50 gates).
- **FP16 twin YAML** [`config/runs/run-20-correspondence-fp16-c8.yaml`](config/runs/run-20-correspondence-fp16-c8.yaml)
  — same draw, `Qwen/Qwen3-8B`, **not run** (spend/auth blocked). Runbook:
  [`docs/jobs.md`](docs/jobs.md) §AWQ vs FP16 isolation.

### Changed — SAND-026 simplified specialist extraction prompts (issue #32) (2026-09-25)

- Parallel `*_simplified` stems under `config/prompts/` for the five live
  specialists. Each stem is **class-specific** (live schema, typical
  document shape, class-local empty rules, class traps) — not a shared
  generic extract template. Vendor mirrors (`contracts_specialist_v33`,
  `*_production`) stay byte-identical for sync.
- Correspondence no longer dual-lists retired `key_points` /
  `referenced_communications` as registered fields; contracts no longer
  trains `key_obligations` / `termination_clauses` then forbids them.
- Run-20 / run-30 specialist YAMLs + `specialist_posture.prompt_file` pin
  the simplified stems. `scripts/sync_specialist_prompts.py` default write
  cannot clobber experiment pins (`--overwrite-experiment` is the opt-in).
- **Empty / class-mismatched Hub GT is not a miss.**
  `eval.extraction_scope` drops empty placeholders and other-class keys
  (and aliases correspondence `claimed_amount` → `demand_amount`) before
  `score_extraction_row` calls the dojo suite, so empty insurance-claim
  fields on non-claim rows cannot pull down `overall_extraction_score` /
  F1. Vendor `score_extraction` still treats `[]` as an event — we do not
  edit `vendor/` (hub#62). Lock: `tests/test_extraction_scope.py`. Docs:
  [`docs/evals.md`](docs/evals.md) §Extraction scoring.
- Inventory + operator path: [`config/prompts/README.md`](config/prompts/README.md).
  Catalog promotion remains in `LLM-Mailroom-Services/eval-environment`
  issues 4–8 — not this package.

### Added — SAND-018 single-class 20-contract Modal run + full-corpus logged sample (2026-09-25)

- **`config/runs/run-20-contracts-specialist.yaml`** — the runbook's
  [`docs/modal/benchmark-l4.md`](docs/modal/benchmark-l4.md) L4 Qwen pins (`Qwen/Qwen3-8B`,
  L4, `v0.29.0`, `max_model_len=16384`, scaledown 120, `contracts_specialist_v33`
  local prompt) applied to a **20-contract** single-class run drawn as a seeded
  random sample (`sample_seed=42`) from the **full** corpus (`split: all`, 3,302
  rows). Preflight records the draw (seed, rows, sha256) in `spec.lock.json`
  and writes it to `dataset.jsonl` — the logged random sample.
- **`job/specialist_posture.py`** — `run-20-contracts-specialist` posture row
  (concurrency 4, `cost_cap_usd` 0.55, `max_wall_seconds` 3200) plus
  `SPECIALIST_LIMIT_BY_RUN` / `expected_limit()`, so the per-doc-type pins cover
  the 20-doc variant.
- **`job/benchmark_check.py`** — the specialist `limit` + local-prompt-pin
  enforcement now keys on the posture map (covers `run-20-*`), not only the
  `run-30-*` prefix; a 20-doc YAML that forgot `limit: 20` fails the loud gate
  instead of passing it silently.
- Tests: `tests/test_specialist_posture.py` (posture coverage + gate rejects a
  wrong limit).

### Added — SAND-017 central subagent roster (2026-09-24)

- **`config/subagents/family-roster.yaml`** — family-wide manifest (home package,
  package membership, harness metadata) shared across Digital-Mailroom /
  llm-mailroom / llm-entity-extraction / local-mailroom-sandbox.
- **`.opencode/agents/`** — family prompt-engineer / eval-judge /
  experiment-log-sync / trace-log-analyst / mailroom-arch-optimizer /
  legal-changelog-auditor prompts plus sandbox-native **`harness-doctor`** and
  **`adversarial-reviewer`**.
- **Harness adapters:** `sandbox subagents sync --harness opencode|cursor|all`
  (OpenCode frontmatter merge + Cursor stub generation);
  **`sandbox subagents materialize --package … --root …`** copies the manifest and
  missing prompts into sibling checkouts (`governance/subagents/` on digital-mailroom).
- **`sandbox subagents propagate`** + [`config/subagents/checkout-map.yaml`](config/subagents/checkout-map.yaml)
  — materialize + sync all mapped checkouts; monorepo hook
  [`scripts/monorepo/after_packages_sync.py`](scripts/monorepo/after_packages_sync.py)
  (wire via [`scripts/monorepo/INTEGRATION.md`](scripts/monorepo/INTEGRATION.md)).
- Docs: [`docs/subagents-family-sync.md`](docs/subagents-family-sync.md).
- Tests: `tests/test_subagents.py`.

## [0.2.0] - 2026-09-24

### Added — Modal/vLLM ↔ dojo cost-compare metrics parity (SAND-016)

- **`sandbox metrics compare --fixture`** scores the Grant-style local /
  Modal / API triple (`data/fixtures/serving/cost_compare.json`) through
  both sandbox `job.metrics.compare` and vendored
  `get_suite("local_vs_api")` / `compare_serving` (no GPU).
- Adapter `mailroom_sandbox.eval.serving_parity` converts `latency_ms` /
  `ttft_ms`, stamps champion token $ for `Qwen/Qwen3-8B`, and keeps
  `serving_kind=modal` out of the local bucket (`eval local_vs_api --from-log`
  now compares Modal↔API).
- Three-way `$/doc` aggregation uses 8 decimal places (4 dp previously
  rounded Grant token-proxy rates to 0).

### Added — full Hub corpus cache + per-class Modal samples (2026-09-24)

- **`sandbox datasets pull`** defaults to the full
  `Lucius-Morningstar/mailroom-dataset` `ground_truth` **train+test** pin
  (3,302 rows at `FAMILY_HF_REVISION`) under `data/cache/`. `--max-rows 50
  --split test` remains for tiny slices.
- **`sandbox datasets sample --per-class N`** draws 20/40/100+ per live
  class from that local JSONL (offline; merger_agreement ceiling is 152).
- Corpus loader accepts `split: all`. Class-bucket quotas above availability
  now hard-fail (same as nested sub_buckets). Template:
  `config/runs/example-per-class.yaml`.

### Added — SAND-001 local SAND board prefix (2026-09-24)

- **Sandbox-isolated governance** uses prefix **`SAND-NNN`** on
  `governance/TASKS.md` (rules in `governance/README.md` +
  `governance/PREFIX.md`). Family **`DMR-*`** cards stay on
  llm-entity-extraction's MESSAGE_BOARD — do not open DMR cards on the
  local board.
- Legacy `SANDBOX-050-*` mission archived → epic `SAND-010` (+ sub-cards).
- Docs: `AGENTS.md`, `docs/setting-up/sister-repos.md`, `docs/modal/modal-doc-jobs.md` gate
  rows (`SAND-014`). Drift guard: `tests/test_governance_sand.py`.

### Added — DMR-078b requirements completeness (2026-09-24)

- **`[pipeline]` extra** now declares `aiosqlite` + `greenlet` (required for
  the vendored graph's default `sqlite+aiosqlite://` URL — DMR-067 left
  sqlalchemy alone) and PDF/page deps (`pypdf`, `pdfplumber`, `pillow`).
- **`requirements/`** mirrors of every pyproject extra (`base`, `dev`,
  `pipeline`, `deploy`, `observability`, `hf`, `notebooks`, `modal-job`,
  `all`) plus root `requirements.txt` → `requirements/dev.txt`. Generated by
  `scripts/sync_requirements.py` (`--check` for drift).
- **`deploy/modal_job.py`** `uv_pip_install` expanded to the specialist worker
  surface (dojo scoring + pipeline + observability) so Modal jobs boot with
  numpy/sqlalchemy/langchain/aiosqlite present.

### Added — DMR-078 Qwen Modal specialist posture + merger specialist (2026-09-24)

- **Per-doc-type Modal L4 runbooks** for all five `run-30-*-specialist.yaml`:
  concurrency / `cost_cap_usd` / `max_wall_seconds` sized by typical token
  length (correspondence/insurance c=5; corporate/contracts c=4; merger c=3).
  Source of truth: `job/specialist_posture.py` (also drives estimate-suite
  tables + overlay generation budgets).
- **Qwen/Qwen3-8B context-fit budgets** in `config/taxonomy.overlay.yaml`:
  specialist `max_tokens` / `max_input_chars` no longer advertise windows
  larger than L4 `max_model_len=16384` (contracts was 100k chars).
- **Runner abort guards:** `JobSpec.cost_cap_usd` + `max_wall_seconds` fail
  the run loud when wall×L4 $/hr or wall seconds exceed the pin.
- **`merger_agreement_specialist` plumbing** (issue #9 Phase 2): vendored
  upstream draft agent + schema/registry from llm-mailroom PR #64; sandbox
  taxonomy / components / eval registry / prompt sync / run-30 merger YAML
  now use the dedicated specialist (not `contracts_specialist` on MAUD).
- **`sandbox run benchmark-check`** enforces posture concurrency, task 1:1
  map, cost_cap, and max_wall for every run-30 specialist YAML.

### Added — DMR-077 two-operator specialist tracks (2026-09-23)

- **Suite manifests** under `config/runs/suites/`: `track-a` (contracts →
  corporate_records → correspondence), `track-b` (merger → insurance_claims),
  and `full` (single-operator five-run alternative). Separate Modal accounts
  via `SANDBOX_MODAL_PROFILE_TRACK_A` / `_TRACK_B` (Hermes default on A only).
- **CLI:** `sandbox run suite --suite track-a|track-b|full` (runbook /
  `--print-loop` / `--check` / `--execute`); `sandbox metrics estimate-suite
  --suite …`; `sandbox run benchmark-check --suite …`.
- **Docs:** two-operator runbook in `docs/modal/benchmark-l4.md` + `.env.example`
  profile-name placeholders (no secrets). Spend posture unchanged: scaledown
  120, c=4, L4, max_containers=1, warm-once per track.

### Added — DMR-076 cut-spend specialist suite (2026-09-23)

- **Attended scaledown 120s** pinned in all five `run-30-*-specialist.yaml`
  (`engine.modal.scaledown_seconds`) + deploy default
  `MODAL_VLLM_SCALEDOWN_SECONDS=120`; restore **600** for unattended/overnight.
- **Loud warm-once headers** on every run-30 YAML + `docs/modal/benchmark-l4.md`
  (one `sandbox-vllm` app through all five runs; teardown only after the fifth).
- **`sandbox run benchmark-check`** enforces spend posture: scaledown=120,
  min_containers=0, max_containers=1, concurrency=4, limit=30, DMR-074 local
  prompt pins; AWQ accepted as optional path (warning), bf16 remains default.
- **`sandbox metrics estimate-suite`** / extrapolate defaults align to 120 so
  pre-flight $ matches the attended suite YAMLs.
- AWQ stays optional (`sandbox modal-matrix env Qwen/Qwen3-8B-AWQ`) — DMR-068
  accuracy gate not green for flipping the default bf16 suite.

### Added — DMR-061 live-or-loud sweep (2026-09-14)

- **Vendored pins (DMR-057, now reflected in this changelog):** llm-mailroom
  **v0.7.1** (`2a212e76`, `vendor/llm-mailroom/VENDOR.md`), llm-dojo-scoring
  **v0.15.0** (`9db1417b`, vendor snapshot refreshed with the emitter
  counters in the same commit so the hub#62 drift guard stays byte-identical);
  the corpus pin is **v9 `46a4d3c2`** (`FAMILY_HF_REVISION`).
- **Tracing loudness:** `eval/tracing.py` now warns on every silent-degrade
  path (dojo constants fallback, mailroom-setup/SDK unavailability,
  `propagate_attributes` failure) and COUNTS lost score emissions + failed
  flushes (`tracing_failure_counts()`).
- **Engine-base resolution:** a typo'd run-spec profile now raises with the
  available list; `modal-vllm` without `MODAL_WORKSPACE` raises instead of
  emitting a literal `<workspace>` URL.
- **hub#41 double-fire guard:** a malformed `fired_at` FAILS CLOSED (refuses
  the re-fire) instead of silently bypassing the cooldown.
- **Honest provenance:** a live intake failure falls back AND labels the row
  `offline_fallback=True`; `_live_intake` never re-labels a degraded output
  as a real prediction.
- **No unknown-as-ok:** a live pipeline returning no `doc_type` raises on
  the sorter + pipeline + job-runner paths (was scored `ok=True` "unknown").
- **Corrupt GT is loud:** malformed `expected_fields` JSON raises with row
  context in `datasets.py` + `corpus.py` (was silently scored as empty).
- **Methodology transparency:** `eval/scoring.py` stamps `scoring_method`
  and warns on every silent suite→generic fallback; the chained composite
  refuses a 0-sentinel when either half produced no scores.
- **Failure counters with test seams:** `job/otel.py` (OTLP flush errors),
  `job/metrics.py` (dojo cost fallback), `job/remote.py` (state-Dict/lock
  probes) all log instead of swallowing; `tracing_failure_counts()` and
  `llm_dojo_scoring.emitter.sink_failure_counts()` are test-pinned.
- **CLI/deploy:** `sandbox health` rc=1 on probe failure is pinned; the
  visualizer pull rc is honored; `tunnel down` raises on a failed kill;
  metrics compare refuses a run without a lock; compose vllm gained a
  bearer-aware healthcheck; HTCondor `.sub` files opt into
  `notification = Error`; `run_batch_eval.sh` writes the failing rc into
  `run.log` and fixes the elapsed-time off-by-one; `modal_job.py` re-raises
  when the terminal failure state cannot be published (the CLI watch would
  stall forever).
- **New tests:** `tests/test_live_or_loud_sweep.py` (13 pins) + the
  vendored-family counter pins in the dojo emitter suite.

### Planned (not yet shipped — hub#54)

- **DMR-059 — Modal doc-pipeline job queue plan**: `docs/modal/modal-doc-jobs.md`
  designs a `sandbox-doc-jobs` Modal app modeled on the Modal docs tutorial
  (`09_job_queues/doc_ocr_jobs.py`) — a CPU-side document job queue whose LLM
  is the already-deployed `sandbox-vllm` endpoint: bytes staged on a
  `sandbox-doc-inbox` Volume, `extract_text` (pdf/image → text via the
  vendored transcriber surface) + `process_document` (connected mailroom
  graph through `DEFAULT_PROVIDER=vllm`) stages, `sandbox-doc-state` Dict
  progress mirror, `modal run` local-entrypoint smoke, and
  `Function.from_name(...).spawn(...)` consumption. Three phases (mock
  smoke → live vLLM → CLI). **Not yet shipped** — the card is still
  `in_progress` on the board and neither `docs/modal/modal-doc-jobs.md` nor
  `.opencode/agents/` now ships the coding subagent roster (SAND-017); Modal
  doc-jobs code remains unshipped — this entry documents the queue plan only.

### Added

- **DMR-066 — subclass-stratified sorter evals + loud strata guards (SHIPPED
  2026-09-16)**: the DMR-063 50-run exposed a stratification no-op —
  `expected_doc_class` is constant `contract` in the joined `ground_truth`,
  so the legacy `strata.expected` FILTER silently truncated to contract×N.
  New `strata.field`/`values`/`counts` form draws per-stratum sub-seeded
  buckets over any row field (`expected_subclass` default) with
  class-aware normalized matching (raw CUAD surfaces like
  `License_Agreements` match catalog tokens like `license` — via the vendored
  dojo normalizer, both sides normalized per-row doc class, with an
  `other`-fallback guard that stopped cross-class candidate inflation).
  Preflight now hard-fails (exit 1) on: requested strata absent from the
  data, a constant stratum field with >1 requested value (the run-50 trap,
  named), and a draw/limit that drops a requested stratum; the lock records
  `strata_actual` (drawn distribution) so a lock proves what was drawn.
  Delivered: `config/runs/run-50-subclass.yaml` (13 strata · Service 8, …
  Manufacturing 2 · 50 rows; `preflight --force` locked with `strata_actual`
  matching exactly; old generation archived per DMR-049), spec validation
  (unknown keys / counts length / positive ints), 6 new corpus tests + 3
  spec tests. 271 passed / 3 skipped.

- **DMR-067 — sqlalchemy restored to the live pipeline surface (SHIPPED
  2026-09-16)**: added `sqlalchemy>=2.0` to the sandbox `[pipeline]` extra —
  the vendored graph's `storage.catalog` / `storage.audit_log` imports
  failed without it (every live doc logged `catalog_upsert_error` /
  `latest_audit_hash_fetch_failed`, loud but non-fatal, and the agent roster
  degraded to the static 18 via `vendored llm.prompts not importable`).
  Verified: `sqlalchemy 2.0.54` installed; `storage.catalog`,
  `storage.audit_log`, `llm.prompts` all importable from the vendored tree.
  One live sorter row with the full surface is the designated DMR-063
  300-run preflight step.

- **DMR-068 — L4 scale-matrix protocol + exemplar specs (READY, runs
  pending spend approval)**: `docs/scale-matrix.md` — run-50 analysis
  (8.7–13.9 tok/s/engine vs the ~18 tok/s fp16 HBM ceiling on L4; scheduler
  caps non-binding below ~2048 decodes; chunked prefill on by default at
  v0.29.0), the AWQ lever (v0.29.0 docs mark AWQ ✅ Ada; official Qwen3-8B
  benchmark 1.76× decode; `Qwen/Qwen3-8B-AWQ` drop-in; accuracy gate
  ≥98 %), fixed-doc-size fixture plan (2k/6k/12k char buckets from run-50
  rows), and a 7-cell matrix {1,2,4}×L4 × concurrency {8,16,32} + AWQ cell —
  est. **$13.08 ≤ $15** at $0.80/GPU-hr, teardown per cell via
  `deploy/teardown_vllm.sh`, measurement contract (items.jsonl primary,
  engine `/metrics` + log windows secondary, billing per cell). Exemplar
  specs `config/runs/scale-c1-4xl4-c16.yaml` (bf16 baseline) +
  `scale-d1-awq-4xl4-c16.yaml` (quant-only delta); fleet pinning via
  `MODAL_VLLM_MIN_CONTAINERS=4` (already supported by the deploy app).

- **DMR-063 — 50-doc Modal vLLM scale-out run + teardown safeguards (SHIPPED
  2026-09-16)**: `config/runs/run-50-modal-hf.yaml` — 50 contract-class rows
  (19 subclasses; Hub pinned revision), concurrency 16, `max_containers: 4`
  (2–3 warm L4s), `scaledown_seconds: 600`. Result: **49/50 = 98.0 %**,
  0 run errors, 0 timeouts; one out-of-set misclassification
  (contract → corporate_record). Per-item E2E mean 971 s (median 883, p90
  1520, max 2054 — queueing-dominated at 16-way); aggregate ≈ 0.65 docs/min;
  engine generation 8.7–13.9 tok/s per L4, prefix-cache hits 56–58 %, KV ≤ 30
  %; Modal metered **$7.98 → credited → billed $0.00** (≈ $0.16/doc metered).
  **Timeout fix**: vendored `llm_call_timeout_seconds` 120 → 300 s (the
  vendored taxonomy is the live source — the base file is shadowed; both kept
  in sync) — killed the `APITimeoutError` retry storms (attempt A cancelled at
  cursor 0). **Driver resilience proven**: orphaned runner loss at cursor 31 →
  `sandbox run resume` re-attached and drove 50/50 to `done` with all items
  intact (checkpoint/`items.jsonl` self-heal). **Teardown**: new
  `deploy/teardown_vllm.sh` (stop → verify zero deployments → volumes persist
  → billing best-effort; TTY-aware `--yes` for headless) + README guard
  matrix + `TestTeardownScript`. Full breakdown: `reports/RUN50-MODAL-HF-REPORT.md`.
  Findings spawned: strata no-op (expected_doc_class constant → 19-subclass
  coverage instead of 3-class strata), missing `sqlalchemy` in the pipeline
  extra (loud non-fatal catalog/audit degrade), scale-out flatness at 4×L4.
  262 passed / 3 skipped.

- **DMR-062 — Modal HF-secret wiring + v0.29.0 live parity pilot (SHIPPED
  2026-09-16)**: the deploy app now attaches the Modal named secret
  `huggingface-secret` (`Secret.from_name(..., required_keys=["HF_TOKEN"])`,
  override via `MODAL_HF_SECRET_NAME`) to BOTH `serve` and `download_model`;
  `HF_TOKEN` was dropped from the local-env knob secret (Modal applies
  function secrets in list order — last wins — so a local `HF_TOKEN` would
  have silently overridden the named secret). vLLM pinned to **v0.29.0**
  across Modal + local compose + HTCondor after the live parity pilot
  passed (Qwen/Qwen3-8B L4: 7/7 sorter rows, F1=1.0, `json_object` verified,
  `serving_kind=modal` records; vllm-specialist docs-verified the v0.29.0
  flag set). Preflight engine probe fixed: it appended `/v1/models` to a
  base that already carries the `/v1` seam (`.../v1/v1/models` → live 404);
  the probe now normalizes (pinned by `test_engine_probe_url_seam_normalizes_v1_suffix`).
  `test_vendor` stale-pin scan no longer trips on pip-installed venv wheels.
  First live pilot spec: `config/runs/pilot-sorter-modal-hf.yaml`.
  260 passed / 3 skipped.

- **DMR-058 — full CLI verification sweep + quickstart**: every `sandbox`
  command exercised against a fresh in-repo `.venv` (offline + live Hub
  paths); `docs/setting-up/QUICKSTART.md` is the verified full command reference
  (install, flag-placement rules, workflows, exit codes, troubleshooting).
  New extras: `[pipeline]` (vendored langchain stack for the legalbench
  suite / live mailroom paths), `[dev]` now carries the Hub client
  (`huggingface_hub`, `pyarrow`); the vendored dojo runtime surface
  (`numpy`, `pandas`, `matplotlib`, `openpyxl`) moved into BASE deps so a
  clean `pip install .` boots the CLI. Clean degradations (no tracebacks):
  compose/ollama/ssh failures (`up`/`down`/`pull-models`), `datasets pull`
  without the Hub client (points at `[hf]`/`[dev]`), `legalbench` loud
  guards (suite without `--n`, missing corpus, missing `[pipeline]`), and
  Modal job mode without the SDK (points at `[deploy]`). `sandbox fetch-deps`
  is now layout-aware and non-destructive (the llm-dojo-scoring clone ships
  the package at the repo root; the old `work/name` fallback half-wiped the
  tracked tree before crashing). `run status/resume/cancel --config`
  resolves the embedded `run_id` (previously demanded `--run-id` even with a
  config). `config/runs/example.yaml` fixture path is CWD-relative again.
  ~6 new network-free tests (230 passed / 1 skipped).

- **HUB-026 — remote-serving integration completeness**: `vllm-remote`
  profile with a `tunnel:` block + `mailroom_sandbox/tunnel.py`
  (network-free argv builders, pidfile lifecycle, double-forward guard) +
  `sandbox tunnel plan/up/status/down`; `deploy/conda/environment.yml`
  (CPU-first portable env, vLLM deliberately external);
  `deploy/htcondor/` CHTC job templates — batch eval (in-job vLLM, works
  on the shared GPU Lab where `condor_ssh_to_job` is unavailable) and an
  owned-GPU server variant tied to the tunnel profile
  (`docs/setting-up/remote-serving.md` is the overview).
- **Modal deploy hardening (SDK 1.5.5 / vLLM v0.28.0)**: `deploy/modal_vllm.py`
  now pins the Modal SDK (`modal==1.5.5` in the `[deploy]` extra), defaults to
  `vllm/vllm-openai:v0.28.0` (matching the local compose pin), caches vLLM
  JIT/CUDA-graph artifacts in a `sandbox-vllm-cache` Volume, pre-warms weights
  with `modal run deploy/modal_vllm.py::download_model` (HF cache Volume +
  explicit commit), tags the app for cost allocation, and bounds cost with
  `max_containers=1` / `min_containers=0` plus configurable scaledown and
  startup timeouts (`MODAL_VLLM_SCALEDOWN_SECONDS`,
  `MODAL_VLLM_MAX_CONTAINERS`, `MODAL_VLLM_MIN_CONTAINERS`,
  `MODAL_VLLM_STARTUP_TIMEOUT_SECONDS`) and an optional
  `MODAL_VLLM_REVISION` pin. New network-free contract tests
  (`tests/test_modal_vllm.py`) pin the argv builder, bearer env mapping,
  secret construction, cost guards, and the SDK/image pins. Docs:
  `deploy/README.md` (deploy → verify → cost → security → troubleshooting),
  `.cursor/skills/modal/SKILL.md`, `docs/setting-up/remote-serving.md`,
  `config/.env.example`.

- **DMR-027 — sandbox job CLI (`sandbox run`)**: a spec-driven, locked,
  resumable eval runner over vLLM + Modal + an OTEL trace sink. New
  `src/mailroom_sandbox/job/` (`spec`, `checkpoint`, `preflight`, `runner`,
  `otel`, `metrics`, `remote`), `src/mailroom_sandbox/corpus.py`
  (revision-pinned HF full-corpus/subset loader: default+ground_truth parquet
  join, `content_sha256` integrity, deterministic strata/limit selection,
  offline `file://` path), and `src/mailroom_sandbox/prompt_registry.py`
  (every pipeline agent's prompt: local variants + Langfuse integer-version
  pins + code default; `sorter`/`contracts_specialist` Family-B
  `PROMPT_VERSIONS` injection). Preflight resolves/validates all domains,
  prepares the subset, and writes an immutable `spec.lock.json` (drift
  refused on resume unless `--force`); the runner checkpoints per item
  (`items.jsonl` source of truth, atomic `checkpoint.json`, torn-tail
  self-healing) and resumes after pause/failure. `sandbox run
  preflight|start|status|resume|cancel|list`, `sandbox prompts list|show`,
  `sandbox metrics compare` (local/Modal/API buckets, deltas vs API, dojo
  pairwise comparisons). Modal mode: `deploy/modal_job.py` worker
  (`sandbox-runs` Volume + `sandbox-job-state` Dict polling, resume via
  FunctionCall re-attach/re-spawn lease). Deps: `observability` +
  `opentelemetry-sdk`/`opentelemetry-exporter-otlp-proto-http`; new `hf`
  extra (`huggingface_hub`, `pyarrow`). Docs: `docs/jobs.md`. ~52 new
  network-free tests.

## [0.1.0] - 2026-09-10

### Changed

- **HUB-015 — reduced agent profile + current-pipeline alignment**: the
  **reporter agent is retired** (moved to `retired_agents`; the compile stage
  is the computational procedural `compile_report` node — deterministic
  matter-record assembly, **zero LLM calls**, and the sandbox eval no longer
  acquires an LLM client for it). **Reviewers stay enabled.** Sandbox surfaces
  aligned to llm-mailroom **v0.6.0** (`fetch-deps`, docs) and dojo **v0.12.2**.
  HF fixtures (`data/fixtures/hf/docclass_mini.jsonl`) now carry full
  docclass-merged ground-truth targets: corpus-strata `expected_subclass` for
  all 5 doc types + `expected_fields` from the 27-key GT schema (correspondence
  intent + provenance; insurance claim entities), propagated into every eval
  row. Dockerfile gains a non-root user + HEALTHCHECK; all four `:latest`
  compose images pinned (ollama 0.33.2, vllm v0.28.0, phoenix version-20.4.0,
  minio RELEASE.2025-09-07…).

### Fixed

- **Modal SDK 1.5.5 removed `Secret.from_local`** — `deploy/modal_vllm.py`
  used it and would fail at import/deploy. Knobs are now built with
  `Secret.from_dict`, which skips absent keys, preserving the optional
  `HF_TOKEN` / `MODAL_VLLM_API_TOKEN` contract (`from_local_environ` raises
  on missing names). Regression-guarded by `tests/test_modal_vllm.py`.

### Added

- Local-first LLM-Mailroom experiment sandbox: provider profiles (Ollama, vLLM
  local, Modal vLLM, llama.cpp, LM Studio, opt-in OpenRouter), taxonomy overlay
  with OpenRouter→local model map, Docker Compose (Phoenix / Ollama / vLLM /
  llama.cpp / optional Langfuse), Modal deploy wrapper (`sandbox-vllm`),
  fixture catalog + tiny HF / LegalBench slices, eval runners (sorter /
  extract / chained / pipeline / legalbench), provider×model×prompt matrix,
  llm-dojo-scoring emission, Langfuse v4 `document-pipeline` tracing, append-only
  `reports/experiment_log.jsonl`, and a `sandbox` CLI.
- Isolated evals for every live agent/node (`sandbox eval judge`,
  `contracts_specialist`, `arbiter`, …) plus connected pipeline scoring
  (class / stage / extraction / routing).
- Per-agent overlay knobs and `sandbox cutover --agent-model NAME=tag`.
- Langfuse 3 compose (web + worker + postgres + clickhouse + redis + minio)
  with headless `LANGFUSE_INIT_*` keys matching The-Mailroom filters.
- Scoring + pipeline are **vendored snapshots** (DMR-057): `llm-dojo-scoring
  @ v0.12.2` (local vs API serving table + scorecard + cost from
  [#10](https://github.com/Exios66/llm-dojo-scoring/pull/10); aligned with
  llm-mailroom v0.6.0's own pin) and llm-mailroom **v0.6.0** ship under
  `vendor/` (tracked); `sandbox fetch-deps` refreshes them from the pinned
  tags — the `[pipeline]` extra is gone.
- `sandbox eval local_vs_api --mock` compares offline (Ollama/vLLM) vs API-key
  (OpenRouter) serving metrics via `get_suite("local_vs_api")` without needing
  `OPENROUTER_API_KEY`. The comparison returns a full T0/T1 **table** (missing
  stays `None`), a **scorecard** with identity tags, and token × price-table
  **cost**. Local and API values emit as separate scorecards (`run_id:local` /
  `run_id:api`). Sorter T0 stays `accuracy` + `f1_macro`; TTFT is never
  inferred from e2e / n_tokens. GPU/KV/VRAM stay `None` on API-key records.
- Offline Docker image (`deploy/Dockerfile` → `mailroom-sandbox:offline`) and
  Compose profile `jupyter` for Jupyter Lab on `:8888`, plus dedicated notebooks
  (`notebooks/01`–`03`) and `sandbox datasets prepare` to load/clean/write
  fixtures under `data/runtime/prepared/`.
- Project Agent Skills under `.cursor/skills/` for tool selection: router plus
  Langfuse, Braintrust, Apache Phoenix, Ollama, Modal, and Hugging Face
  (offline-first Hub usage).

### Fixed

- ClickHouse compose healthcheck no longer passes database credentials
  as CLI flags (GitGuardian generic CLI secret detector).
