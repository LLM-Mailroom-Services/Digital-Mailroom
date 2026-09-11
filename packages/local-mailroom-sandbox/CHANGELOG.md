# Changelog

## [Unreleased]

### Added

- **DMR-059 — Modal doc-pipeline job queue plan**: `docs/modal-doc-jobs.md`
  designs a `sandbox-doc-jobs` Modal app modeled on the Modal docs tutorial
  (`09_job_queues/doc_ocr_jobs.py`) — a CPU-side document job queue whose LLM
  is the already-deployed `sandbox-vllm` endpoint: bytes staged on a
  `sandbox-doc-inbox` Volume, `extract_text` (pdf/image → text via the
  vendored transcriber surface) + `process_document` (connected mailroom
  graph through `DEFAULT_PROVIDER=vllm`) stages, `sandbox-doc-state` Dict
  progress mirror, `modal run` local-entrypoint smoke, and
  `Function.from_name(...).spawn(...)` consumption. Three phases (mock
  smoke → live vLLM → CLI). The standalone repo also gains the monorepo's
  `vllm-specialist` + `modal-specialist` opencode agents (`.opencode/agents/`,
  sandbox-adapted wiring).

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
