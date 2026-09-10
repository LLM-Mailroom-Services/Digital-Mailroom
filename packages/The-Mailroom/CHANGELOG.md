# Changelog

All notable changes to The-Mailroom are documented here, following
[Keep a Changelog](https://keepachangelog.com) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **DMR-016: vendored docclass mirror resynced 32→74 keys.**
  `mailroom_ui/docclass_prompts.py::DOCLASS_PROMPT_VERSIONS` regenerated
  verbatim (byte-identical, order-preserving) from llm-entity-extraction
  `src/prompts_docclass.py::DOCCLASS_PROMPT_VERSIONS` — the mirror had gone
  stale at the KANBAN-090 era (32 keys) while the source registry grew to 74
  (KANBAN-101/103 specialists, HUB-041 mailroom v8, DMR-015 reviewer v2 +
  the 14-key `mailroom_prompts` lineage). Count pin in
  `tests/test_prompts.py::test_docclass_registry_shape` bumped to match.
  Defaults unchanged; `scripts/sync_prompts.py --docclass` pushes the
  refreshed family to Langfuse when run.

## [0.4.0] - 2026-09-04

### Added

- **mailroom-tui is now a typed-command REPL** (M6). A persistent
  `mailroom@floor:~$` prompt over a rich live frame (status header +
  scrollback + prompt) with a raw-key line editor (Tab completion, arrows =
  history, Ctrl+L clear, Ctrl+C cancel), a background floor poller that
  pushes AgentLab banners into the scrollback, and a `floor` live desk
  (`q`/`quit` to leave). New commands: `help`/`man`, `clear`, `history`,
  `date`, `echo`, `uname`, `neofetch`, `whoami`, `filter stage=…`, plus
  the two new surfaces below. The codebase split into `tui/commands.py`
  (registry + man pages), `tui/views.py` (renderers), `tui/corpus.py`
  (Hub corpus client), `tui/repos.py` (constellation manifest);
  `mailroom_console.py` re-exports every legacy renderer so existing
  scripts keep working. Scripting flags unchanged (`--once --view`,
  `--resolve`, `--source`) with `--view corpus|repos` added.

- **Corpus browser (TUI + terminal site).** `corpus ls|show|search|stats`
  over `Lucius-Morningstar/mailroom-corpus` through the canonical
  `mailroom_ui/hf_corpus` ladder: slim listing (instant, windowed paging),
  per-file live `doc_text` + ground-truth fetch, filename/class/subclass
  search, and split/class stats. The Hub being unreachable is an explicit
  closed state — never canned data.

- **Constellation repo browser (TUI + terminal site).** `repos ls`,
  `repos <name>`, `open <name>` over the full manifest — every package the
  monorepo mirrors upstream (verified against `packages_sync.json` in the
  contract tests), the three hub copies (`mailroom-dev`, `mailroom-hub`,
  `LLM-Postal`), and the derived graph sites; live GitHub metadata
  (description/stars/language) fail-soft + cached.

- **Terminal GH Pages site** (`terminal/`, owlcot-family). A TTY-emulating
  static page at `/terminal/` on the Pages snapshot: `ls`/`cat`/`cd`/
  `whoami`/`mail` virtual filesystem (runs/, corpus/, repos/, topics/),
  `floor`/`inspect`/`review`/`metrics`/`sessions` from the exported
  snapshot, live Hub corpus commands, repos browsing, themes
  (amber/green/cyan), CRT scanline toggle, opt-in keypress sound,
  ghost-text Tab completion, 1.06s CRT-accurate blink cursor, animated
  man-page help, command history + prefs in localStorage. Staged to
  `docs/terminal/` by `publish_pages.sh` (pixel console stays the root);
  `scripts/export_corpus_catalog.py` writes the slim `site/data/corpus.json`
  (2,000 rows: filename/class/subclass/sha/split + row-index offsets for
  on-demand doc_text fetches).

- **`mailroom_ui/hf_corpus.py` robustness.** `fetch_rows` gains `offset`
  (single-row/windowed fetches) and `page_sleep` (pacing); 429 rate limits
  get a patient backoff ladder (5s→40s). The catalog export verified
  end-to-end against the live Hub: 2,000 rows (1,792 train / 208 test),
  classes 950/509/350/152/39, all shas + GT indices present.

### Changed

- **Railway now uses Infrastructure as Code.** `railway.json` (Config as
  Code) is retired by Railway — new projects stopped reading it on
  2026-08-28, hard cutoff 2026-12-01. `.railway/railway.py` (`railway_sdk`,
  authoring-only) declares the Observatory service: Dockerfile source,
  `start="python -m server.hosted"`, `/health` healthcheck, and the
  non-secret variables (`MAILROOM_EDITION` / `HOST` / `POLL_ENRICH` /
  `TRACE_CACHE_DIR`); secrets stay `preserve()`d on the service. Workflow:
  `railway config plan` / `railway config apply` (legacy services migrate
  with `railway config migrate --lang py --apply --delete-files`). Docs /
  wiki / `.env.example` / contract tests updated.

- **Deploys are verifiable at a glance.** The Dockerfile bakes
  `RAILWAY_GIT_COMMIT_SHA` → `MAILROOM_BUILD_SHA` (guarded default, other
  platforms unaffected); `GET /health` and `/api/meta` now carry `platform`
  (`railway` / `render` / `fly` / `huggingface`) and `build_sha`.

- **Eval / Langfuse dataset sync pin the corrected full Hub corpus.**
  `mailroom_ui/hf_corpus.py` defaults to
  `Lucius-Morningstar/docclass-merged` @
  `1d4753578d91aae09033b359bc32dc1b431e4c20` (`ground_truth` config)
  via the datasets-server REST API. `scripts/eval_pipeline.py` and
  `scripts/sync_pilot_dataset.py` (default `--corpus merged`) honor
  `MAILROOM_HF_DATASET` / `MAILROOM_HF_REVISION` / `MAILROOM_HF_CONFIG`.
  Railway checklist documents producer `HF_HOME` cache under `/data`.

- **Aligned with llm-mailroom v0.6.0** (`3cf9fb9`, package `mailroom`
  0.6.0). Topology mirror: `merger_agreement` is a live MAUD class (not a
  CUAD `contract` alias); pared extraction field keys (checklists /
  semantic trio — retired `key_obligations` / `termination_clauses` /
  `key_provisions` / `key_points`); severity-aware confidence defaults
  (`high=0.97`, `low=0.88`, `retry_max=2`, `judge_band_high=0.95`,
  `arbiter_retry_max=2`, `judge_max_passes=3`) plus optional
  `confidence.by_class` when `MAILROOM_TAXONOMY` is set. Optional
  `[pipeline]` pin bumped `0928de1` → `3cf9fb9`. Eval / reconsideration
  no longer treat MAUD↔CUAD as equivalent.

### Fixed

- **REVIEW tray no longer 404-storms or starves the server.** A producer
  catalog miss on a trace/filename probe now returns a 200 `lookup-miss`
  payload (`readable: false` + error copy) instead of a hard HTTP 404 per
  row — the tray shows per-item "no catalog record" instead of tripping
  the global error banner (explicit `doc_id` misses and downloads keep
  honest 404s). Review probes are concurrency-capped at 4 in both SPAs and
  backend tray probes timeout at 4s, so a long queue no longer saturates
  the threadpool.

- **`/api/health` no longer hangs for ~30s.** The Langfuse health probe is
  cached 5s (page + poller + extra tabs collapse into one read; failures
  cached too), and the REVIEW fan-out that was queuing health behind ~50
  producer probes is gone.

- **Railway `/health` no longer calls Langfuse.** Platform probes
  (`railway.json` healthcheckPath, Docker `HEALTHCHECK`) get a fast
  `{"ok": true, "status": "alive"}` response. Source reachability stays
  on `GET /api/health`. Avoids HEALTHCHECK timeouts when keys are
  missing or Langfuse is slow. Docs / `.env.example` Railway checklist
  and contract tests (`railway.json` DOCKERFILE builder) updated.

- **Full browser QA against live Langfuse (2026-08-29).** Pixel console
  (`/?debug=1`) and Observatory (`/live?debug=1`) desks, inspector,
  History replay, mobile FLOOR/REVIEW, and debug dump/push were exercised
  on `:8001` with Langfuse up and the producer unset. Review resolve
  returns an honest HTTP 503. No SPA regressions required a code change.

### Added

- **Railway deploy contract.** Root `railway.json` (Dockerfile builder +
  `/health` probe), `nixpacks.toml` fallback, multi-stage non-root
  Observatory `Dockerfile` with `HEALTHCHECK`, platform `PORT` preferred
  over image `MAILROOM_PORT=7860`, and
  [docs/deployment.md](docs/deployment.md) § Railway (required Langfuse
  keys; optional `MAILROOM_PIPELINE_*` pairing).

- **Live Hugging Face Space Observatory demo.** Full-desk recording
  (~102s) of
  https://lucius-morningstar-mailroom-observatory.hf.space/ after #30
  (classification cards, headline strip, inbox setup hint, Export
  snapshot, Review / History / Matters / Metrics / Debug). Filed at
  `docs/demos/hf-space-observatory-live-walkthrough.mp4` and indexed on
  `docs/demos.md` / wiki `Demos`.

- **Observatory cards show classification success.** Pipeline cards
  display primary / secondary class labels with hit · miss · pending
  (ground truth when present; otherwise “assigned a live roster class”).
  Headline strip: in flight · review · archived · failed · classified
  counts · judge CORRECT/MISS. Confidence percentages and extraction
  scores are off the card (still on the API and inspect Scores).
  Standardized `archive_name`
  (`{doc_type}/{yyyy-mm-dd}/{doc_type}__{subclass}__{slug}__{id8}{ext}`)
  is the archived card title. Inbox **Queue a document** proxies
  multipart files to llm-mailroom `POST /v1/upload` when
  `MAILROOM_PIPELINE_URL` + `MAILROOM_PIPELINE_TOKEN` are set
  (`MAILROOM_PIPELINE_API_PREFIX=/v1`); unconfigured stays HTTP 503.
  Langfuse snapshot cache (`MAILROOM_TRACE_CACHE_DIR`, `GET /api/snapshot`)
  serves traces/inspect when the live `get_run` is slow or down; empty
  cache + Langfuse down stays MAILROOM CLOSED. Poller default
  `MAILROOM_POLL_ENRICH=inflight` avoids a 200-trace N+1 on the Space.

- **Hugging Face Docker Space publisher.** `scripts/publish_space.py`
  ships the committed Observatory image (`Dockerfile`,
  `MAILROOM_EDITION=hosted`, port 7860) to a Hub Space, sets Langfuse
  keys as Space **secrets** (never the git tree), and accepts
  `LANGFUSE_BASE_URL` as an alias of `LANGFUSE_HOST`. Optional
  `MAILROOM_PIPELINE_URL` / `MAILROOM_PIPELINE_TOKEN` /
  `MAILROOM_PIPELINE_API_PREFIX` are copied from the environment when
  set. Dashboard checklist lives in `hosted/SPACE_README.md`. `--check`
  is offline.

- **Operator desk submodule (`operator_desk/`).** Dedicated FastAPI package
  for JWT auth (`/v1/auth`), local archive list/download/preview/verify
  (`/v1/archive`), Langfuse-backed ops snapshots (`/v1/ops`), and
  `/ws/pipeline` bin-move events. Mounted on the existing visualizer
  (`mount_operator` in `server.main`); display `/api/*` + floor `/ws` stay
  open and Langfuse-only. `mailroom-observer` watches
  `MAILROOM_BASE_DIR` bins in-process (`MAILROOM_OBSERVER=1`) or POSTs
  events to `/v1/ops/events`. SQLite tables (`ui_users`, `ui_audit`,
  `archive_index`) live in `MAILROOM_OPERATOR_DB` — the producer's
  `documents` table is never required. Extra `[operator]` adds bcrypt /
  PyJWT / watchdog / PyMuPDF; stdlib pbkdf2 + HMAC-JWT fallbacks keep
  `[dev]` tests green. Compose + nginx sit under `operator_desk/` (no
  React/npm UI as a required path — pixel + Observatory already cover
  the default desks).

- **Optional React operator desk (`ui/`, extra `[ui]`).** Vite/React
  package `the-mailroom-ui` is an optional dependency branch: default
  `pip install -e ".[dev]"` and `mailroom-web` never need Node. `cd ui &&
  npm install && npm run build` produces `ui/dist`; the visualizer mounts
  it at `/desk` when present (`MAILROOM_UI_DIST` override). The desk talks
  to this process (`:8001` `/api/*` + `/v1/*` + `/ws/pipeline`), not
  producer `:8000`. Ingest stays on llm-mailroom. Compose profile `ui`
  is opt-in.

- **llm-mailroom #53 abort class and REVIEW Complete schema.** Aborted
  traces now surface `failure_class` (`llm_timeout` / `llm_auth` /
  `llm_rate_limit` / `llm_transient` / `io_error` / `schema_error` /
  `run_budget` / `unexpected`) on `PipelineRun`, the floor payload, and
  the pixel / Observatory / TUI inspect desks. The token is read from
  Langfuse output or metadata, or parsed from `run aborted [<class>]: …`
  on `error_message` / `escalation_reason`. `disposition=complete` rejects
  operator `extracted_data` keys that belong to another specialist schema
  (HTTP 400) before the producer call.

- **Pinned llm-mailroom as an importable extra.** `pip install -e ".[pipeline]"`
  installs dist `mailroom` from
  `git+https://github.com/Exios66/llm-mailroom.git@0928de1` (package 0.5.0).
  `mailroom_ui/producer.py` imports `pipeline.review_resolve` /
  `schemas.manifest` (dispositions, `serialize_document`, tray actions) from
  that extra, a sibling checkout, or a git-archive of the pin SHA when the
  live sibling branch has moved on. Missing extra falls back to the same
  contract. The visualizer never imports `api.main` or `llm_dojo_scoring`.
  `/api/meta`, `/api/health`, and `/api/debug/source` surface the pin.

- **Working REVIEW-tray demo.** `scripts/demo_review_tray.py` boots a FakeClient
  floor plus an in-process llm-mailroom stub (`/v1` lookup, resolve, audit,
  health) so Approve / Reject / Record / Requeue / Complete, class correction,
  and the parked-text pane actually round-trip `POST /api/review/resolve` and
  `GET /api/review/source` (lookup fallback). `--check` / `--check-api` verify
  the cast without a browser. Pixel + Observatory REVIEW gained a Complete
  action and `extracted_data` JSON field. Snapshot / GH Pages stay read-only.

- **REVIEW tray class correction and document viewer.** Pixel REVIEW, inspector,
  and Observatory Review can correct `doc_type` / `doc_subclass` on a parked
  item and read parked text (extracted text pane + Open original) while
  deciding. `POST /api/review/resolve` forwards those fields; new
  `GET /api/review/source` proxies producer source when present, else the
  catalog lookup row. `mailroom-tui --resolve` gained `--doc-type` /
  `--doc-subclass`; `--source` prints parked text. `/api/health` and
  `/api/meta` now surface `pipeline_configured` (boolean only) plus
  `doc_subclasses`. Snapshot / GH Pages stay read-only. Requires
  `MAILROOM_PIPELINE_URL` + `MAILROOM_PIPELINE_TOKEN` pointing at
  llm-mailroom `:8000` — not `MAILROOM_API_URL` (TUI → this visualizer
  `:8001`).

### Changed

- **Producer pin `2c0bcac` → `0928de1`.** Optional extra `[pipeline]`
  tracks llm-mailroom #53 (abort classification, REVIEW Complete
  specialist-schema check, stale-claim requeue on the producer, API token
  rotation). The visualizer still sends a single
  `MAILROOM_PIPELINE_TOKEN`; bins requeue stays on the producer.

- **Aligned the producer proxy with llm-mailroom `main`.** Calls go through
  `/v1` (`MAILROOM_PIPELINE_API_PREFIX`, default `/v1`; empty/`/` uses the
  unversioned aliases). Class correction is posted as `override_doc_type`
  (the UI/TUI still send `doc_type`; the proxy maps it). `disposition=complete`
  and `extracted_data` are forwarded. `GET /api/review/source` tries
  `GET /v1/documents/{doc_id}/source` and, on 404 (the route is not on
  producer main), falls back to `GET /v1/lookup` (`original_filename`,
  `extracted_data`, `escalation_reason`). Binary download 404s honestly
  instead of synthesizing a file. Watcher/inbox liveness uses
  `GET /v1/health` and `GET /v1/queue`.

### Fixed

- **Debug dumps and REVIEW hints from a closed Langfuse.** Pixel
  `__MAILROOM_DEBUG__.dump()` now includes `href` / `eventCount` so
  `POST /api/debug/client` stores the page URL (the Observatory dump already
  did; the server also accepts `location` as a fallback). Observatory
  Debug **Clear ring** resets `lastError` instead of leaving a stale
  fetch-error after `errors: 0`. The `fetch-error` glossary covers HTTP
  `>= 400` as well as thrown fetches. Pixel and Observatory REVIEW still
  show the `MAILROOM_PIPELINE_URL` setup hint when the Langfuse review
  queue returns 503.

- **Parked non-catalog subclasses no longer 400 Complete.** Producer main does
  not catalog-gate `doc_subclass`; the proxy now passes parked tokens such as
  insurance `fnol` through so Complete / Resume still work.

- **50-doc reused-trace pilots group as one matter.** Deterministic Langfuse
  trace ids reused by a later HF session kept the first-write `session_id` on
  cached `get_run` rows, so SESSIONS/REVIEW split 50 documents across old and
  new session ids and the pixel desk sliced each matter to 20 rows.
  `list_traces` now merges into `list-harvest`, the poller overlays list
  identity (session / stage / `needs_human`) onto cached full runs, `/api/sessions`
  embeds every run in the window as compact floor payloads (no 20-row cap;
  list responses are `Cache-Control: no-store` so a stale 20-row fetch cannot
  linger). `GET /api/sessions/{id}` reads the poller
  desk instead of N+1 Langfuse (and falls back to the trace list, not
  `sessions.get`, when the desk is still empty). Empty-desk SESSIONS/REVIEW/METRICS
  fall back to the cheap trace list, not `enriched_recent_runs`. Pixel SESSIONS and
  Observatory Matters scroll the full list.

## [0.3.0] - 2026-08-28

> review resolve, live floor, skills, and reconsideration

### Added

- **v0.3.0 GitHub-release demos.** `scripts/demo_v030_cast.py` holds a
  FakeClient floor covering the INBOX hopper, parked REVIEW (with `doc_id`
  so Approve / Reject / Requeue render), archived judge-MISS RECONSIDER,
  and a failed bin. Recordings live in `docs/demos/`
  (`v030-pixel-desks-review-resolve.mp4` and
  `v030-observatory-review-resolve.mp4`; the pilot director now parks a
  scan in INBOX so the hopper is visible).
  `scripts/release.py` now *moves* `[Unreleased]` under the new version
  header instead of duplicating the bullets above it.

- **Human-review resolve on the REVIEW desk.** Pixel REVIEW cards, the
  inspector, Observatory Review, and `mailroom-tui --resolve` can approve,
  reject, record-only, or requeue a `needs_human` run. The visualizer proxies
  `POST /api/review/resolve` to llm-mailroom (`MAILROOM_PIPELINE_URL` +
  `MAILROOM_PIPELINE_TOKEN`); the browser never holds the producer token.
  `disposition=resume` re-extracts a parked review; `record` appends a
  hash-chained audit row without moving the file (archived/RECONSIDER);
  `requeue` copies the source file back to the inbox. `PipelineRun.doc_id`
  is lifted from Langfuse output/input/metadata. Snapshot mode stays
  read-only.

- **Project Agent Skills (companion to local-mailroom-sandbox #4).** Committed
  `.cursor/skills/` with `mailroom-tool-router` plus family stack skills
  (Langfuse, Apache Phoenix, Braintrust, Ollama, Modal, Hugging Face) and
  visualizer-surface skills (pixel console, Observatory, live floor, schema
  sync, GH Pages, TUI) so agents pick the right tool instead of inventing a
  second display source or a Node/LLM client here.

- **Live conveyor freshness + producer watcher lamp.** In-flight traces are
  re-enriched every poll (terminal runs stay on the 60s detail cache) so a
  just-flushed classify/extract/judge span moves the envelope on the next
  tick instead of sitting on the previous station for a minute. List/obs
  TTLs match `MAILROOM_POLL_INTERVAL` (3s). WS snapshots carry
  `poll_interval_s` and `pipeline` ops; the pixel fallback poll uses that
  interval (was a hard-coded 10s). `GET /api/pipeline` reports llm-mailroom
  watcher heartbeat + inbox pending when `MAILROOM_PIPELINE_URL` is set
  (operator liveness, not fabricated document data). Floor gained an INBOX
  hopper; Observatory/TUI show watcher/inbox; graph node ids
  (`retry_classify`, `judge_verify`, …) map onto stations.

- **Observatory Inbox tray.** Hosted live board parks `stage=inbox` in its
  own tray (matching the pixel hopper) instead of mixing those envelopes
  into Sorter.

- **Reconsideration beyond self-reported confidence.** Archived runs with
  objective misses (judge MISS/PARTIAL, GT class/subclass mismatch,
  extraction score below the low floor, schema/guardrail/parse failures,
  incomplete reporting, skipped-judge flag) join the REVIEW queue and park
  on the REVIEW siding as RECONSIDER even when the model stated 0.99
  confidence. Cause tokens are `PipelineRun.review_causes`; the inspector,
  Observatory, TUI, and metrics surface them. Self-reported classification
  / extraction confidence is never a trigger.

- **Dojo 0.9.0 / llm-mailroom #30 scoring sync.** Live taxonomy is five extract
  classes (`contract`, `corporate_record`, `correspondence`, `compliance_filing`,
  `insurance_claim`) plus the HF/sorter alias `merger_agreement` (still tints and
  labels, extracts via `contracts_specialist`) and the routing token `unknown`.
  Retired `court_opinion` / `due_diligence` stay off the roster.
  `compliance_specialist` is on the agent list. Hub subclass catalogs and CUAD
  `contract_subtype` keys are copied into `DOC_SUBCLASS_BY_CLASS`. The interpreter
  lifts `doc_subclass` / `contract_subtype`, HF ground truth
  (`expected_hf_class`, `expected_subclass`), and `normalize-intake` span stats
  onto `PipelineRun` and the compact floor payload. Langfuse's 35-char score
  alias `extraction_verified_precision` dual-writes the canonical
  `extraction_overall_verified_precision`. Metrics tiles Enron topic/sentiment
  and MAUD extras only when those scores exist (never fabricated zeros). Eval
  reports `subclass_accuracy` (exact token match; CUAD subtype counts as the
  contract subclass). Inspector, history/review, Observatory, and TUI show
  subclass + intake chips/rows and a grouped suite-extras score section.

- **Langfuse data-model + batching mirror (llm-mailroom #29).** The interpreter
  reads v4 `observationType` as well as `type` and treats `CHAIN` / `AGENT` /
  `EVALUATOR` / `RETRIEVER` (plus SPAN/EVENT) as node observations, so
  classify/extract/judge no longer depend on the generic-SPAN fallback.
  `pipeline_schema.NODE_OBSERVATION_TYPES` matches the pipeline map; the
  root `document-pipeline` chain is kept for the inspector (`is_root`) and
  omitted from the floor routing path. `pipeline-result` and LegalBench
  `answer-question` stay generations. Trace `user_id` / `release` (producer
  `MAILROOM_TRACE_USER_ID` / `LANGFUSE_RELEASE`) surface on the pixel
  inspector, Observatory inspect dialog, and TUI. Phoenix remaps known
  mailroom names to the same types. Flush/batch knobs stay on the pipeline
  (`LANGFUSE_FLUSH_AT` / `FLUSH_INTERVAL`); this viewer is read-only.

### Fixed

- Pixel console no longer logs `inbox pending: N` on every WebSocket tick;
  the console line fires only when the count changes. Fallback poll
  retunes if `poll_interval_s` changes after the timer started.
- Observatory HTTP fallback now polls traces + `/api/pipeline` at the
  hub interval when the socket is down (previously a one-shot
  `refreshTraces` at boot, then silence until reconnect).
- Langfuse/Phoenix list-cache TTL follows `MAILROOM_POLL_INTERVAL` instead
  of a hardcoded 3s/5s, so a 1s poll no longer waits on a longer list cache.
- `GET /api/pipeline` prefers the producer's `checks.watcher` lamp and
  accepts top-level heartbeat/inbox fields from older health payloads.

### Changed

- **Dojo scoring pin documented as `@v0.11.0`.** The constellation table and
  wiki Home now cite the [released tag](https://github.com/Exios66/llm-dojo-scoring/releases/tag/v0.11.0)
  (canonical scoring docs + importable prompt catalog; T0 names and formulas
  unchanged from v0.10.0). This visualizer still does not install
  `llm-dojo-scoring` at runtime; catalogs remain copied constants.

- **Dojo scoring pin documented as `@v0.10.0`.** The constellation table and
  wiki Home now cite the [released tag](https://github.com/Exios66/llm-dojo-scoring/releases/tag/v0.10.0)
  (field-micro P/R/F1/F2, doc-class macro-PRF, insurance `determination_consistency`).
  This visualizer still does not install `llm-dojo-scoring` at runtime; catalogs
  remain copied constants.

- **Dojo scoring pin documented as `@v0.9.0`.** The constellation table and
  wiki Home now cite the [released tag](https://github.com/Exios66/llm-dojo-scoring/releases/tag/v0.9.0)
  dependents should pin instead of `@v0.7.0`. This visualizer still does not
  install `llm-dojo-scoring` at runtime; catalogs remain copied constants.

### Fixed

- Pixel SESSIONS / REVIEW / METRICS no longer re-walk hundreds of Langfuse
  traces on every tab click. They reuse the poller's already-enriched window,
  so the inspector overlay can load a trace instead of stalling behind a
  ~2-minute sequential enrich. Those tabs also show a loading placeholder
  instead of a blank panel while the request is in flight.

### Added

- README screenshot gallery now covers the pixel console (FLOOR / REVIEW /
  SESSIONS / METRICS / CONSOLE), the hosted Observatory (pipeline / review /
  metrics / debug), and TUI desks, with collapsible `<details>` sections for
  the rest of the documentation.
- **Demos notebook + PR walkthrough video** — `docs/demos/The-Mailroom-Demos.ipynb`
  galleries every still; `docs/demos/tui-server-observatory-desk-walkthrough.mp4`
  is the ~56s desk recording (pixel then Observatory). Index:
  `docs/demos.md` / wiki `Demos`.
- **Pilot-run floor video** — `docs/demos/pilot-run-documents-through-pipeline.mp4`
  (~25s) shows five envelopes sliding the conveyor (REVIEW siding + a failed
  corporate record). Re-record with `scripts/demo_pilot_run.py`.
- **Production HF pipeline eval** — `scripts/eval_pipeline.py` scores Langfuse
  `document-pipeline` traces against `Lucius-Morningstar/docclass-merged`
  ground truth (exact + aligned accuracy; merger_agreement≡contract).
  `scripts/run_production_pilot.py` drives a Qwen 3.7-Flash subset through
  sibling `llm-mailroom` (`src/scripts/run_hf_pilot.py`). Intake clerk span
  `normalize-intake` maps to INGEST; agent `intake` added to the roster.
  Live Qwen 3.7-Flash subset of `docclass-merged` scored exact 0.80 /
  aligned 1.00; insurance claims with `adjuster: null` were the production
  schema miss that parked CMS-style rows in REVIEW. Evaluator latency now
  reads the explicit `run_duration_seconds` score instead of trace
  `updatedAt`, which can move when asynchronous evaluators attach scores.
- **Fully patched production rerun** — Langfuse session
  `pilot-hf-20260825T044207Z` ran five representative
  `docclass-merged` documents through Qwen 3.7-Flash: all five archived,
  exact accuracy 0.80 / aligned accuracy 1.00, 113,059 tokens, $0.0045,
  and 22.94s mean pipeline latency. The Langfuse v4 session-detail adapter
  and reused-trace newest-score selection were fixed during viewer
  verification; tracked report:
  `docs/reports/evaluations/hf-pilot-20260825T044407Z.{md,json}`.

### Fixed

- **TUI treated a dead API as an empty live floor** — `fetch_list` coerced
  HTTP failures to `[]`, so `mailroom-tui --once` printed
  `MAILROOM LIVE` with zero runs instead of `MAILROOM CLOSED`. Failures now
  propagate as `None`; the debug ring (`[d]ebug`, `--view debug`) records
  the urllib/WS error. `review_classify` maps to the Sorter station.
  Inspect no longer calls `input()` inside Rich Live (broken the display);
  `[` / `]` cycle runs. Metrics nulls render as `-`, not `None` / `$None`.
  Scores accept a dict or `{name,value}` list (same contract as the web
  inspector). Sessions desk (`s`) and `--view` / `--inspect` flags added.
- Pixel console `window.__MAILROOM_DEBUG__` can `pullServer()` /
  `pushClient()` against `/api/debug/bundle` and `/api/debug/client`,
  matching the Observatory and TUI debug pull. The `D` key no longer
  fabricates demo envelopes on a live floor (opt-in `?demo=1` only, and
  only when the source is down).
- **7-day live window mismatch** — the Observatory asked for `since=604800`
  while the TUI HTTP fallback used 6 hours, `/api/traces` defaulted to 30
  minutes, `/api/metrics` to 1 hour, and the WebSocket poller defaulted to
  6 hours. All four now default to 7 days (`MAILROOM_RECENT_WINDOW`,
  `MAILROOM_TRACE_LIMIT` 200) so FLOOR / HISTORY / TUI / Observatory show
  the same runs.
- **FakeClient discarded an empty traces list** — `traces or []` replaced a
  caller-owned `[]` with a new list, so `scripts/demo_pilot_run.py` appended
  envelopes the API never saw.
- **SPA: REVIEW tab TypeError (live + GH Pages)** — `Mailroom.api.reviewQueue`
  dispatched the string `"review-queue"` but both the live and snapshot
  clients are keyed `reviewQueue`, so every REVIEW refresh threw
  `… is not a function`, painted the error banner, and left the siding
  empty even when `/api/review-queue` / `data/review-queue.json` were fine.
- **GH Pages boot error flash** — `main.js` fetched `/api/meta` before the
  health probe, so every Pages visit showed `ERROR — HTTP 404 /api/meta`
  (and a red console line) even after snapshot mode engaged. Meta now loads
  only after a live health OK or a successful snapshot fallback; the
  expected missing live API is a dim console line, not a banner.
- **Snapshot fallback ignored a dead `?api=` / localStorage base** — bundled
  `data/*.json` was prefixed with the live API origin (`http://host:8001data/…`
  when the slash was missing). A stale localhost base blanked Pages.
  Snapshots are always same-origin; `?api=` (empty) now clears the persisted
  base.
- **Floor animation leak + dead ARCHIVE station** — `frame()` still called
  `requestAnimationFrame(frame)`, defeating the V-17 idle/visibility pause
  and running a second 60fps chain. `catalog`/`archive` stages parked on
  REPORT so the ARCHIVE desk never received an envelope. Same-station
  envelopes stacked on one pixel (only the top one was clickable).
- **TUI verdict truncation** — Rich 15 squeezed the floor table so
  `CORRECT` rendered as `COR…`. Verdict and cost columns are now no-wrap.
  error banner sat inside `.screen { overflow: hidden }`; verdict bars
  ignored per-entry colors (PARTIAL/MISS rendered green); `tile.wide`
  `span 2` overflowed single-column layouts; GitHub Pages 404'd `favicon.ico`
  into the debug log. Inspector scores now accept dict or `{name,value}`
  lists instead of `[object Object]`.
- `export_snapshot.py`: `sessions.json` top-level `count` was hardcoded to
  `0` regardless of content — now the real session count (matches
  `/api/sessions` shape; agents reading the static snapshot get honest
  numbers).
- **SECURITY: leaked `.env` purged from gh-pages history** — a Desktop
  branch-switch mishap had committed `.env` (Langfuse keys) plus stray dirs
  (`mailroom_ui/`, `server/`, `site/`, `.DS_Store`) to the branch root.
  `gh-pages` was force-pushed to a single fresh orphan commit containing
  only `docs/` (the deployed site never exposed the file — Pages serves
  `docs/` only — but clones could read it). Keys must still be rotated at
  the Langfuse UI: unreachable objects can persist on GitHub's side.
  Recurrence guards: `scripts/publish_pages.sh` now strips `.env`/
  `.DS_Store`/stray dirs from the publish clone and aborts if `.env` files
  or `sk-lf-`/`pk-lf-` key material appear anywhere in the staged tree;
  `hooks/pre-push` rejects direct `gh-pages` pushes whose tree contains any
  `.env`-like file.
- Observatory visual/UX: replay controls stay pinned while playback runs
  on Pipeline; health polls no longer clobber a live WebSocket status
  line; cards/metrics use valid HTML; trays wrap as a 2×4 grid; replay
  finishes on the run's real terminal stage (review/failed, not always
  archived); verdict bars use per-status color.

### Added

- API surface test (`tests/test_api_surface.py`) hits every `/api/meta`
  endpoint plus trace 404, session detail, review queue, and the debug
  bundle so a silent 404 cannot blank the TUI, pixel console, or Observatory.
- **Mailroom Observatory debug suite** — hosted UI gained a Debug desk
  (`#debug`, `?debug=1`, keyboard `6`), a client ring at
  `window.__OBSERVATORY_DEBUG__` (`dump` / `export` / `pullServer` /
  `pushClient` / `explain`), and server one-pull `GET /api/debug/bundle`
  plus `POST /api/debug/client` so the next agent can read the last
  browser dump.
- **Mailroom Observatory (hosted edition)** — a public, modern, accessible
  site at `/live` (`mailroom-hosted`, `MAILROOM_EDITION=hosted`), distinct
  from the local pixel console, the TUI, and the GitHub Pages snapshot.
  Same Langfuse-backed `/api/*` + `/ws` contract: live pipeline trays,
  review queue, matters, metrics, inspect dialog, and paced trace replay
  (respects `prefers-reduced-motion`). Container image (`Dockerfile`) binds
  `0.0.0.0:7860` for Hugging Face Spaces / any Docker host. Docs:
  `hosted/README.md`.
- **main ↔ gh-pages sync discipline (still no Actions):** committed
  `hooks/pre-push` republishes `gh-pages:/docs` automatically on every push
  of `main` once `git config core.hooksPath hooks` is set per clone; failures
  warn by default (`MAILROOM_STRICT_SYNC=1` blocks the push instead).
  New `scripts/publish_pages.sh --status` compares the deployed
  `docs/debug/build-info.json` git SHA against HEAD (exit 1 = stale), always
  fetching fresh since publishes ride a temp clone. The publisher now refuses
  to run from any branch other than `main` (clear error when e.g. GitHub
  Desktop left `gh-pages` checked out) and the snapshot exporter retries
  transient source fetches 3× with backoff so a cloud blip can't blank a
  populated site.
- **GitHub Pages edition (static site, NO GitHub Actions):** the pixel-art
  SPA now deploys to GitHub Pages via `scripts/publish_pages.sh` using Pages'
  native "Deploy from a branch" mode (one-time Settings toggle; Actions is
  deliberately not involved). The script stages `web/` with relative asset
  paths, exports a JSON snapshot of the configured trace source
  (`scripts/export_snapshot.py` → `data/*.json`, per-run detail files,
  `debug/build-info.json` provenance for agents), verifies it (`--check`),
  and pushes the site into `docs/` on the `gh-pages` branch (Pages source:
  Deploy from a branch → gh-pages /docs; legacy root-level site files are
  cleaned up on publish) (`--dry-run` builds + verifies only;
  `--skip-export` republishes the shell with existing data). Without a
  reachable source the site still ships and honestly shows its CLOSED state.
- **Static + live dual mode in the SPA** (`web/js/api.js`, `main.js`): the
  site resolves its API endpoint as `?api=<url>` → `localStorage`
  (`mailroom.api`) → same-origin; when no live API answers it falls back to
  bundled snapshots (`SOURCE: SNAPSHOT`, gold lamp) instead of the closed
  overlay. WS only starts after the first health probe succeeds.
- **Agent debug console:** every fetch/WS frame/error/console line is
  captured into a client ring buffer exposed at
  `window.__MAILROOM_DEBUG__` (`dump()`, `export()` downloads
  `mailroom-debug.json`, clipboard copy); `?debug=1` or the CONSOLE tab's
  DEBUG toggle enables verbose capture + reveals low-level lines. Server
  side: always-on request ring buffer at `GET /api/debug/logs?limit=`,
  source/knob introspection at `GET /api/debug/source`, verbose stdout with
  `MAILROOM_DEBUG=1`, and `/api/meta` now carries `mode`, `version`,
  active `source`, plus a machine-readable endpoint index.
- **Arize Phoenix trace source** (`mailroom_ui/phoenix_source.py`): reads a
  locally running Phoenix (`PHOENIX_ENDPOINT`, default
  `http://localhost:6006`) via `arize-phoenix-client` and maps
  OpenTelemetry/OpenInference spans into the Langfuse-shaped dicts
  `interpret_trace` already consumes — llm-mailroom span names route through
  `SPAN_STAGE_MAP`, unmapped spans degrade to unknown staging (same breakage
  map philosophy), LLM spans become generations (model/token counts/cost),
  span annotations and `mailroom.score.*` attributes become scores.
  Optional dependency; never fabricated data on unreachability.
- **Source selector + multi-source facade:** `MAILROOM_SOURCE=langfuse |
  phoenix | both` picks the backend (`mailroom_ui/multi_source.py` fans
  reads out with per-trace isolation and aggregates health);
  `TraceSourceUnavailable` base class shared by both adapters so the 503
  handler covers everything; `health()` payloads gain a source-agnostic
  `"ok"` key. CORS enabled via `MAILROOM_CORS_ORIGINS` (GET/OPTIONS) so the
  Pages site can drive a locally running server next to Phoenix.

### Changed

- **README overhaul — governed-constellation edition:** root README rebuilt from 102 to 177 lines around the family story while keeping every operational byte (quick start, screens, demo seeding, requirements, config, layout, tests, releases). Added: a factual static badge row (`version 0.2.0`, `python 3.11+`, `data source: Langfuse only` — deliberately NO release/license/CI badges: no v0.2.0 tag/release exists yet and the repo carries neither a LICENSE file nor workflows); a **"The governed constellation"** section with an ASCII YOU-ARE-HERE diagram and an at-a-glance table covering all seven family repos (llm-mailroom upstream · llm-entity-extraction prompt loop + shared board · llm-dojo-scoring engine · Enron-Evaluation-Environment + claims-data-eda corpus feeds · atticus-investigation eval sibling · both graphify sites) linking llm-mailroom's canonical `docs/sister-repos.md`; a new **"The trace contract & the mirror duty"** section documenting the #1 maintenance rule (mirror span names / roster / doc classes / thresholds / judge scores in the same change window) with the visible-by-design breakage map, deferring to `AGENTS.md` as authority; an `[!IMPORTANT]` alert on the schema-cache restart gotcha; dividers between major parts; honest "No license published yet" close. Docs-only; suite unchanged.

## [0.2.0] - 2026-08-23

## [0.2.0] - 2026-08-24

### Added
- Langfuse v4 SDK tolerance: camelCase observation fields (`startTime`,
  `endTime`, `modelId`, `totalTokens`, `inputTokens`, `outputTokens`,
  `totalCost`, trace `sessionId`/`updatedAt`/`createdAt`) accepted alongside
  v2/v3 snake_case shapes (`trace_interpreter.py` `_both`/`_pick` helpers).
- `tests/fake_langfuse.py:make_trace_v4` — v4-shaped (camelCase) trace
  fixture; interpreter tests cover both shapes.
- M2 web engine (complete): `web/css/theme.css` pixel-art theme (bezel,
  scanlines, titlebar, tabs, statusbar, overlay panels, metric tiles);
  `web/js/api.js` (fetch client + WebSocket with exponential-backoff
  reconnect + format helpers); `web/js/floor.js` canvas conveyor renderer
  (stations, rollers, bins, terminals, source lamp, envelopes animated
  to their stage target with per-doc-type tint + verdict/review/failed
  stamps, click/hover inspection); `web/js/inspector.js` (spans timeline,
  LLM generations, scores); `web/js/sessions.js`; `web/js/metrics.js`;
  `web/js/console.js` (AgentLab-style banners); `web/js/main.js` app shell
  (tabs, clock, source light, WS snapshot wiring with polling fallback,
  "MAILROOM CLOSED — no Langfuse connection" overlay).
- M3 review queue: `web/js/review.js` + REVIEW tab listing
  `/api/review-queue` runs (escalation reason, confidence, verdict) with
  30s auto-refresh while visible.
- M4 TUI console: `tui/mailroom_console.py` (entry point `mailroom-tui`) —
  AgentLab-style live console (`*** Entering/Moving to station: ... ***`
  banners, judge-verdict banners, per-run floor table, review siding,
  metrics dashboard, full inspect panels: spans/generations/scores). Reads
  the same Langfuse-derived display API; subscribes to the `/ws` floor
  snapshots (full payloads) with an HTTP fallback; `--once` one-shot mode
  for scripting/CI. Keybindings: f/r/m/i/c/q.
- `tests/test_tui.py` — TUI banner/table rendering tests (no live server).
- `scripts/seed_demo.py` — seeds demo scenarios INTO Langfuse
  (env `demo`, deterministic `demo-<slug>` trace ids, verb-first spans,
  generations with usage/cost, judge verdict/quality scores via a
  CATEGORICAL `mailroom-pipeline-judge` score config) — never served
  locally. Verification modes: `--check` (asserts the stored Langfuse
  records against what was seeded), `--check-api` (asserts the live server
  display payloads), `--check-logs` (asserts against run logs physically
  saved by llm-mailroom's `sync_langfuse_logs.py`). Explicit request
  timeouts on every API call; credential preflight; delete-then-reseed
  with settle (ingestion appends, so re-seeding must start clean).
- **Upstream sync (llm-mailroom KANBAN-062/063)**: `judge_verify`
  (`judge-verify` span) and `arbiter` (`arbitrate-verdict` span) stages in
  the Stage enum, `SPAN_STAGE_MAP`, `STAGE_PHASE`, and `NODE_ORDER`;
  `sorter_reviewer`, `arbiter`, and `insurance_claims_specialist` joined the
  agent roster; `insurance_claim` doc class + specialist mapping;
  `judge_band_high` (0.85) mirrored from `graph/routing.py:judge_gate`.
- Floor gains a seventh station — **JUDGE** (between EXTRACT and BOSS),
  shared by `judge_verify`/`arbiter`; replay animates runs through the gate;
  `insurance_claim` envelopes tint violet (plus a `merger_agreement` tint for
  docclass-merged corpus rows classified as contracts).
- seed_demo: `judge-verify`/`arbitrate-verdict` span emission, three new
  scenarios (`insurance-clean`, `insurance-judge-gate`, `merger-arbitrated`;
  13 total), and generation models/prices moved onto the pipeline's real
  registry (qwen/qwen3.7-flash everywhere, deepseek/deepseek-v4-flash judge)
  with taxonomy.yaml cost_models rates.
- Fake Langfuse client exposes the v3 scores endpoint (`scores_v3`) so the
  source adapter's primary score path is exercised by every test.

### Changed
- **Release furnishing (v0.2.0 official):** official GitHub release published
  for the pre-declared `[0.2.0]` milestone. README gains a **Screenshots**
  gallery — four real captures (`docs/screenshots/`: FLOOR conveyor, REVIEW
  siding, METRICS dashboard, TUI console) rendered from genuine pipeline
  traces through the production stack, fixture-seeded exactly like the test
  suite so Langfuse stays the sole display source — plus **collapsible
  sections** (`<details>`) for demo seeding commands, configuration
  reference, and project layout, and a linked `release v0.2.0` badge.
- **README overhaul — governed-constellation edition:** root README rebuilt from 102 to 177 lines around the family story while keeping every operational byte (quick start, screens, demo seeding, requirements, config, layout, tests, releases). Added: a factual static badge row (`version 0.2.0`, `python 3.11+`, `data source: Langfuse only`); a **"The governed constellation"** section with an ASCII YOU-ARE-HERE diagram and an at-a-glance table covering all seven family repos (llm-mailroom upstream · llm-entity-extraction prompt loop + shared board · llm-dojo-scoring engine · Enron-Evaluation-Environment + claims-data-eda corpus feeds · atticus-investigation eval sibling · both graphify sites) linking llm-mailroom's canonical `docs/sister-repos.md`; a new **"The trace contract & the mirror duty"** section documenting the #1 maintenance rule (mirror span names / roster / doc classes / thresholds / judge scores in the same change window) with the visible-by-design breakage map, deferring to `AGENTS.md` as authority; an `[!IMPORTANT]` alert on the schema-cache restart gotcha; dividers between major parts; honest "No license published yet" close. Docs-only; suite unchanged.
- Generation cost is read from `cost_details` (v2/v3) or top-level
  `totalCost`/`totalPrice` (v4), never from a single fixed field — v4 also
  stores the field camelCase as `costDetails`.
- Observation classification: explicit `type` (SPAN/EVENT/GENERATION)
  decides span-vs-generation; v4 spans carry a zeroed `usage` dict that
  previously misclassified every span as a generation. The
  model/usage heuristic now applies only to `OBSERVATION`-typed or
  type-less records (the pipeline's auto-traced generations).
- CATEGORICAL scores (judge verdicts) resolve their stored numeric index
  back to the config label (`score_configs` param of `interpret_trace`,
  fed by `LangfuseSource.get_score_configs`). Score `data_type` read via
  `_both(data_type, dataType)`.
- `LangfuseSource.get_scores` reads the v3 scores API first: on Langfuse
  v4 the v1 endpoint ignores `trace_id` (returns global pages, attributing
  scores to the wrong traces) and its values are label-resolved indexes;
  v3 filters correctly and returns labels.
- `LangfuseSource.get_observations` uses the trace record's embedded
  observation set as the primary source (complete records: usage, cost,
  model, io) with the v2 index as fallback — one API call instead of two.
- `LangfuseSource.health()` is a live, briefly-cached API check; the
  server's `/api/health` reports its result. A revoked key or outage now
  surfaces as `langfuse: false` instead of a stale startup flag.
- All `LangfuseSource` read methods raise `LangfuseUnavailable` on any
  API failure; the server maps it to a 503 `{"error": "langfuse
  unavailable"}` instead of a raw 500.
- Poller `detail_ttl` raised 15s → 60s so full-detail fetch load on
  Langfuse stays well under rate limits.
- In-flight display: the generic `processing` output marker no longer pins a
  run to INGEST — `derive_stage` refines it with the deepest node span, so
  extract/retry/judge/arbiter/boss progress is visible live.
- Retry clustering is idempotent: the KANBAN-062 reviewer pass emits a third
  consecutive `classify-document` span without stacking duplicate
  `retry_classify` entries into routing paths (Python + floor replay agree).

### Fixed
- **V-3**: metrics tiles were permanently `$0.00 / 0 tok / 0 calls` in live
  mode — `/api/metrics` aggregated list-level "light" runs with no
  observations. It (and `/api/review-queue`) now aggregate enriched runs via
  the new cached `LangfuseSource.get_run()`; sessions likewise serve enriched
  runs (V-19/V-20).
- **V-5**: N+1 fetch storm — `list_recent_runs` issued one score fetch per
  trace per poll and cache TTLs (1-2 s) were shorter than the 3 s poll
  (~102-302 Langfuse calls per poll). Per-trace score fetches removed from
  the list path; run-level cache (60 s) shared by poller/metrics/review/
  sessions; cache TTL defaults raised to ≥ poll interval; HTTP 429 now backs
  off exponentially.
- **V-9**: archived/failed envelopes respawned on every 3 s snapshot after
  sliding off — tombstones keyed by trace id + updated_at now suppress
  re-creation (cleared by re-runs and manual replays).
- **V-16**: replay ignored real span durations (fixed 600/700 ms pacing) and
  dropped retry stages whenever timings existed — steps now follow the actual
  span order incl. `retry_classify`/`retry_extract`, paced by each span's
  real latency (clamped 250 ms-4 s).
- **V-18**: silent catch blocks across the SPA — global error banner +
  `window.onerror`/`unhandledrejection` hooks, non-JSON WS frames logged,
  server 503/500 `detail` bodies propagated into error messages, generic
  server errors return JSON with `detail` (were plain text 500s).
- Cost extraction regressed during v4 tolerance work — observations were
  searched for cost at the wrong level, zeroing all run costs.
- `server/main.py:_serialize` imported `floor_payload` only in the
  `full=False` branch — `/api/traces/{id}` crashed with `UnboundLocalError`.
- `web/js/sprites.js` was missing the `const SORTER = [` declaration —
  the floor's first sprite referenced an undefined matrix.
- `web/js/sprites.js:drawSprite` treated `x`/`y` as sprite-grid units
  (`(x + c) * px`) while `floor.js` passes canvas pixels — every sprite
  drawn off-origin landed 4× away (most off-canvas; envelopes rendered at
  `e.x * 4` while the hover outline drew at `e.x`, so envelopes were
  invisible until hovered). `drawSprite` now uses pixel semantics.
- The `SPRITES` map never registered the three stamps
  (`stamp_approved`/`stamp_review`/`stamp_failed`) — `floor.js` stamping
  silently referenced `undefined` and no envelope ever showed its verdict
  stamp.
- `tests/test_metrics.py::test_p95_generation_latency` expected 9.4 but
  the fixture (two generations per trace) yields a nearest-rank p95 of 9.1.
- Date bomb in `TestTzNormalization.test_compute_metrics_mixed_tz_no_crash`:
  fixed 2026-08-10 run timestamps silently fell out of the `now - 1d` window
  on Aug 11, zeroing `total_docs`. Timestamps are now relative to the clock.
- Mirror drift: `"image-extractor"` agent key corrected to `image_extractor`
  (upstream module name); `.env.example` `MAILROOM_TAXONOMY` example path
  updated to the post-restructure `src/config/taxonomy.yaml`.

### Removed
- **V-21**: `web/js/sprites.js` — 766 lines of dead sprite code, never
  loaded by `index.html` nor referenced by `floor.js` (the floor renders
  envelopes procedurally). AGENTS.md/docs/wiki references updated.

## [0.1.0] - 2026-08-10

### Added
- M1 data core: `mailroom_ui` package — `langfuse_source.py` (Langfuse SDK
  adapter + `TTLCache`), `trace_interpreter.py` (trace → `PipelineRun`),
  `pipeline_schema.py` (topology mirror, `MAILROOM_TAXONOMY` override),
  `models.py` (pydantic), `metrics.py` (aggregations).
- M1 server: FastAPI read-only API (`/api/health`, `/api/traces`,
  `/api/traces/{id}`, `/api/metrics`, `/api/sessions[/{id}]`,
  `/api/review-queue`, `/api/meta`, WebSocket `/ws`) with background
  `PollHub` snapshot broadcaster (`server/poller.py`).
- M1 tests: fake Langfuse client (`tests/fake_langfuse.py`) — the suite never
  touches the real API.
- Re-run clustering: deterministic trace ids are reused by pilot/attempt
  re-runs, so observations are clustered by time gap (`RUN_GAP_S`) and only
  the latest run's spans/generations are displayed.
- Retry detection via explicit retry stages (`RETRY_CLASSIFY` /
  `RETRY_EXTRACT`) instead of duplicate-based heuristics.
- Trace listing filter by trace `name` (`document-pipeline`) to keep the
  floor/poller focused on pipeline runs.
- Project scaffolding: `pyproject.toml`, `.env.example`, `.gitignore`,
  `mailroom-web` console entrypoint.
