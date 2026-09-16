# Changelog

## [Unreleased]

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

- **DMR-059 — Modal doc-pipeline job queue plan**: `docs/modal-doc-jobs.md`
  designs a `sandbox-doc-jobs` Modal app modeled on the Modal docs tutorial
  (`09_job_queues/doc_ocr_jobs.py`) — a CPU-side document job queue whose LLM
  is the already-deployed `sandbox-vllm` endpoint: bytes staged on a
  `sandbox-doc-inbox` Volume, `extract_text` (pdf/image → text via the
  vendored transcriber surface) + `process_document` (connected mailroom
  graph through `DEFAULT_PROVIDER=vllm`) stages, `sandbox-doc-state` Dict
  progress mirror, `modal run` local-entrypoint smoke, and
  `Function.from_name(...).spawn(...)` consumption. Three phases (mock
  smoke → live vLLM → CLI). **Not yet shipped** — the card is still
  `in_progress` on the board and neither `docs/modal-doc-jobs.md` nor
  `.opencode/agents/` exist in the tree yet; this entry documents the plan
  only.

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
  paths); `docs/QUICKSTART.md` is the verified full command reference
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
  (`docs/remote-serving.md` is the overview).
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
  `.cursor/skills/modal/SKILL.md`, `docs/remote-serving.md`,
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
