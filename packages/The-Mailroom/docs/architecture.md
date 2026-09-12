# Architecture

> This file is mirrored at `wiki/Architecture.md` — edit both together (see
> `wiki/sync-wiki.sh`). This page describes the architecture of The-Mailroom,
> the visual engine for the `llm-mailroom` pipeline. For the pipeline's own
> architecture see the sister repo's docs (`../llm-mailroom`).

## Overview

The-Mailroom renders every run of the `llm-mailroom` multi-agent
legal-document pipeline from its Langfuse traces (pixel-art console, hosted
Observatory, TUI REPL, and the GH Pages terminal site).
**Langfuse is the sole source of truth**: no display value is ever fabricated
or served from local canned data. The repo is read-only against Langfuse
(project-scoped API keys, backend proxies everything — the browser never holds
keys).

```
┌────────────────────────── Langfuse (US cloud, project llm-mailroom) ──────┐
│  traces · observations (spans/generations) · scores · sessions            │
└────────────▲──────────────────────────────────────────────▲────────────────┘
             │ project-scoped API keys (read-only)          │
┌────────────┴──────────────── The-Mailroom ────────────────┴────────────────┐
│ mailroom_ui/  langfuse_source.py ← adapter (trace/observations/scores/     │
│               trace_interpreter.py ← sessions via SDK)                    │
│               pipeline_schema.py ← topology mirror (taxonomy.yaml)        │
│               hf_corpus.py ← Hub datasets-server ladder (corpus reads)    │
│               metrics.py · models.py                                       │
│ server/  FastAPI → /api/* + /ws → serves web/ (console) and hosted/ (/live)│
│          + operator_desk mount (/v1/auth|/archive|/ops, /ws/pipeline)     │
│ web/     pixel-art SPA: Floor (conveyor, 7 stations incl. JUDGE) ·        │
│          Inspector · Sessions · History · Metrics · Review · Console      │
│ hosted/  Observatory — public modern accessible desk (live + replay)      │
│ tui/     mailroom-tui — typed-command REPL (floor desk, corpus browser,   │
│          constellation browser; commands.py/views.py/corpus.py/repos.py)  │
│ terminal/ owlcot-family terminal site (static; snapshot traces + LIVE Hub │
│          corpus via datasets-server; staged to gh-pages:/docs/terminal/)  │
│ operator_desk/  JWT, local archive, Langfuse-backed ops, bin observer     │
│ ui/      optional React desk (/desk when built; Node never required)      │
└────────────────────────────────────────────────────────────────────────────┘
```

**Corpus + constellation surfaces** (TUI and terminal site): the
`mailroom-dataset` Hub dataset is read through the canonical
`mailroom_ui/hf_corpus.py` ladder — slim windowed listing (2 requests per
page, instant), one-time slim catalog for search/stats, and per-row live
`doc_text`/ground-truth fetches (LRU-capped). `tui/repos.py` +
`terminal/js/data.js` carry the constellation manifest (every package the
monorepo mirrors upstream — contract-tested against `packages_sync.json` —
plus the hub copies `mailroom-dev`/`mailroom-hub`/`LLM-Postal` and the
derived graph sites). The static site bundles a slim catalog
(`scripts/export_corpus_catalog.py` → `site/data/corpus.json`, 2,000 rows)
so listing/search/stats work offline; `corpus show` fetches rows live
(datasets-server CORS is verified for the Pages origin).

## Data flow

1. `server/poller.py` `PollHub` polls `list_recent_runs()` every
   `MAILROOM_POLL_INTERVAL` seconds over a **7-day** window by default
   (`MAILROOM_RECENT_WINDOW=604800`, matching `/api/traces` / `/api/metrics`
   / the TUI). `list_recent_runs` uses **trace-list responses only**
   ("light" runs) — cheap enough to poll continuously. In-flight traces
   are then **re-enriched every poll** (`inflight_ttl=0`) so a node that
   just flushed moves the envelope on the next tick; archived/failed runs
   stay on the 60s detail cache until `updated_at` / stage change.
   List/obs TTLs follow `MAILROOM_POLL_INTERVAL`.
2. Each light run is interpreted by `trace_interpreter.interpret_trace` and
   compacted by `poller.floor_payload` (stage, doc type, confidences, verdict,
   cost, …). Optional `MAILROOM_PIPELINE_URL` is fetched the same tick
   (`GET /v1/health`) and attached as `pipeline` on the WS snapshot — watcher
   heartbeat and inbox pending, never fabricated envelopes.
3. Full drill-down (`/api/traces/{id}`) fetches observations + scores on
   demand via `LangfuseSource.get_run()`; pass `force_refresh` for in-flight.
4. Snapshots are broadcast over WebSocket `/ws`; the SPA renders the floor,
   sessions, metrics, and console from the same payloads. HTTP fallback
   (pixel console and Observatory) polls traces + `/api/pipeline` at the
   same interval as the hub when the WebSocket is down.

## Interpreting traces

A `document-pipeline` trace carries:

- **Trace fields**: `id` (deterministic, seeded from filename), `name`,
  `timestamp`, `latency`, `session_id` (= matter_id, or a run-scoped session
  for pilots), `environment`, optional `user_id` / `release`, `tags`
  (`[mailroom, <env>, run-<n>, ...]`), `metadata` (`{attempt, run_id,
  run_deadline}`), curated `input`/`output`.
- **Typed observations** (Langfuse data model; v2/v3 `type` or v4
  `observationType`): the root is a **CHAIN** named `document-pipeline`.
  Children use the most specific type — **AGENT** (classify / extract /
  arbiter / boss / report), **EVALUATOR** (`judge-verify`), **RETRIEVER**
  (PDF/image ingest), **SPAN** (intake, catalog, archive, review route),
  **GENERATION** (`pipeline-result`, LegalBench `answer-question`, and
  auto-traced LLM calls). Verb-first names map to stages by
  `pipeline_schema.SPAN_STAGE_MAP` (`intake-document`, `classify-document`,
  `judge-verify`, `arbitrate-verdict`, `extract-fields`, `route-for-review`,
  `adjudicate-conflict`, `compile-report`, `write-catalog`,
  `archive-document`, …). The root chain is shown in the inspector and
  omitted from the floor routing path. The KANBAN-063 quality gate:
  `judge-verify` runs on the ambiguous extraction band and a partial
  verdict detours through the arbiter before reporting.
- **Generations**: auto-traced LLM calls (model, usage, latency,
  `cost_details`) plus the typed `pipeline-result` / `answer-question`
  generations.
- **Scores**: confidences, run metrics, judge verdict
  (`mailroom-pipeline-judge` CORRECT/PARTIAL/MISS) and quality
  (`mailroom-pipeline-quality` 0–1).

The pipeline (not this viewer) batches events with the Langfuse SDK
(`LANGFUSE_FLUSH_AT` / `LANGFUSE_FLUSH_INTERVAL`, defaults 512 / 5s) and
calls `flush()` then `shutdown()` on process exit so short-lived jobs drain
the queue. The visualizer is read-only.

Because pilot/attempt re-runs reuse the deterministic trace id, a single
trace can carry several full runs. The interpreter clusters observations by
time gap (`RUN_GAP_S`) and keeps only the latest cluster — one envelope per
trace, showing the latest run.

## Pipeline topology mirror

`pipeline_schema.py` bundles a mirror of the pipeline's graph
(`src/graph/routing.py` + `src/config/taxonomy.yaml`) and its Langfuse
observation-type map (`src/observability/tracing.py`
`NODE_OBSERVATION_TYPES`): node/span names (including `normalize-intake` →
INGEST), typed observations (chain/agent/evaluator/retriever/generation/span),
stage→phase mapping, node order, agent roster (incl. `intake` and
`compliance_specialist`), live doc classes (5 extract classes —
`contract`, `corporate_record`, `correspondence`, `compliance_filing`,
`insurance_claim` — plus the HF/sorter alias `merger_agreement` and the
routing token `unknown`; retired `court_opinion` / `due_diligence` stay
off the roster), Hub subclass catalogs + CUAD `contract_subtype`,
Langfuse score-name aliases, specialist-suite extras (Enron/MAUD),
specialist dispatch, and confidence thresholds (incl. `judge_band_high`).
The `MAILROOM_TAXONOMY`
env var can point at the live
`taxonomy.yaml` so thresholds/doc classes come straight from the pipeline
config instead of the mirror (cached at process level — restart to reload).

When the pipeline changes (new span, doc class, score, tag, env), the mirror
must be updated in the same change — see the sync checklist in `AGENTS.md`.

## Web frontend

Vanilla HTML/CSS/JS served from `web/` (no build step). The floor is a
canvas-rendered conveyor (pixel-art envelopes tinted per doc class, stations,
rollers, review/failed sidings) — see `web/js/floor.js`. The station roster
and doc-class colors must stay aligned with `pipeline_schema.py` and the
pipeline's `taxonomy.yaml`.

## Hosted Observatory (`hosted/`)

A **separate** public UI at `/live` (`mailroom-hosted`, or `/` when
`MAILROOM_EDITION=hosted`). Editorial layout, semantic HTML, skip link,
keyboard view switching (`1`–`6`, including Debug), native `<dialog>`
inspector, paced replay of stored traces (controls stay pinned in a
sticky bar), and a Debug desk that records fetches, WebSocket frames, and
uncaught errors. Same `/api/*` + `/ws` as the pixel console. Deploy with
the root `Dockerfile` (binds `0.0.0.0:7860`) — this is not GitHub Pages.
Hugging Face Spaces: SDK **Docker**, empty root directory, port 7860,
Langfuse keys as Space secrets (`scripts/publish_space.py`).
Observatory cards show primary/secondary classification outcomes and a
headline strip; `GET /api/snapshot` + `MAILROOM_TRACE_CACHE_DIR` cache
Langfuse-derived JSON (never fabricated). See `hosted/README.md` and
`hosted/SPACE_README.md`.

## GH Pages edition (static site, no Actions)

GitHub Pages hosts a static build of the SPA via **deploy-from-branch**
(one-time UI toggle: Settings → Pages → `gh-pages` `/docs`) — deliberately
no GitHub Actions workflow. `scripts/publish_pages.sh` stages `web/`
(relative asset paths: `index.html` + `static/css|js`), writes `.nojekyll`,
runs `scripts/export_snapshot.py` to bundle `data/*.json` + per-run detail
files + `debug/build-info.json`, verifies with `--check`, and pushes the
`gh-pages` branch.

Data modes (resolved in `web/js/api.js`):

- **API base**: `?api=<url>` → `localStorage["mailroom.api"]` → same-origin.
  A Pages visitor can drive a locally running `mailroom-web` (CORS via
  `MAILROOM_CORS_ORIGINS`) including its WebSocket.
- **Snapshot fallback**: when no live API answers, the site serves bundled
  JSON (`SOURCE: SNAPSHOT`, gold lamp) — never the closed overlay unless
  even snapshots are missing.

Trace sources (server side): `MAILROOM_SOURCE=langfuse | phoenix | both`
selects between `LangfuseSource`, `PhoenixSource` (local Arize Phoenix via
`arize-phoenix-client`; OTel/OpenInference spans remapped into the
Langfuse-shaped dicts `interpret_trace` consumes; unmapped spans degrade to
unknown staging per the breakage map), and `MultiSource` (fan-out reads,
per-trace isolation, aggregated health).

Debug surfaces for agents: pixel-console ring at
`window.__MAILROOM_DEBUG__` (`dump()` / `export()`, enabled verbosely by
`?debug=1` or the CONSOLE tab's DEBUG toggle); Observatory ring at
`window.__OBSERVATORY_DEBUG__` (Debug desk `#debug`, same `?debug=1`);
server request ring at `/api/debug/logs?limit=`, source introspection at
`/api/debug/source`, combined pull at `/api/debug/bundle`, last browser
dumps at `GET|POST /api/debug/client`, verbose stdout via
`MAILROOM_DEBUG=1`, and a machine-readable endpoint index in `/api/meta`.
Snapshot builds add `debug/build-info.json`.

## Reconsideration (not self-reported confidence)

The pipeline can auto-continue on high `classification_confidence` /
`extraction_confidence`. Those numbers are the model's own. The visualizer
does **not** treat an archived envelope as done when objective Langfuse
scores or ground truth say otherwise:

- GT class / subclass mismatch (`expected_hf_class` vs `doc_type`, with
  `merger_agreement` ≡ `contract`)
- Judge verdict `MISS` / `PARTIAL`
- `extraction_overall_score` below the confidence-low floor
- `schema_valid=0`, `guardrail_triggered`, `parse_error`
- completeness LOW / incomplete reporting
- `extraction_needs_judge_review` on a run that still archived

Those runs keep their archived stage (the pipeline already wrote the
catalog) but `needs_human` becomes true, they join `/api/review-queue`,
and the floor parks them on the REVIEW siding as **RECONSIDER** so a
wrong archive cannot look like a finished case. Cause tokens live in
`mailroom_ui/reconsideration.py` (mirrored by llm-mailroom
`pipeline/reconsideration.py`, which also parks GT misses before extract
and withholds catalog writes when `compile_report` fails).

Operators resolve those items from the REVIEW desk (pixel cards, inspector,
Observatory, or `mailroom-tui --resolve`). The visualizer proxies
`POST /api/review/resolve` to llm-mailroom `/v1/review/{doc_id}/resolve`:
`disposition=resume` re-extracts a parked `stage=review` document (optional
`doc_type` is mapped to producer `override_doc_type`; `doc_subclass` /
`contract_subtype` pass through); `record` appends a hash-chained audit row
without moving the file; `requeue` copies the source file back to the inbox;
`complete` archives operator-supplied `extracted_data` without another LLM
pass after a specialist-schema check (llm-mailroom #53 — correspondence
fields on a contract 400). Aborted runs carry `failure_class` on the
Langfuse output or as `run aborted [<class>]: …` in `error_message`.
`GET /api/review/source` tries producer `GET /v1/documents/{doc_id}/source`
and, on 404, falls back to `GET /v1/lookup` catalog JSON (`original_filename`,
`extracted_data`). Binary `?download=1` 404s when that route is missing.
Requires `MAILROOM_PIPELINE_URL` + `MAILROOM_PIPELINE_TOKEN` on the visualizer
(local `http://127.0.0.1:8000`, or a public producer Space such as
`https://<user>-mailroom-producer.hf.space` — not `MAILROOM_API_URL`, which
is TUI → this process `:8001`). Inbox enqueue is `POST /api/inbox/enqueue`
→ producer `POST /v1/upload`. `MAILROOM_PIPELINE_API_PREFIX` defaults to
`/v1`. Display data stays Langfuse-only — the producer token never leaves
the visualizer server.

## Operator desk (`operator_desk/`)

A dedicated submodule mounted on the visualizer — **not** a second display
source. JWT auth (`/v1/auth`) gates archive file access (`/v1/archive`) and
ops snapshots (`/v1/ops`). Ops numbers come from the same Langfuse
`PipelineRun` window as METRICS. The bin observer (`MAILROOM_OBSERVER=1`
in-process, or `mailroom-observer` POSTing `/v1/ops/events`) publishes
filesystem bin moves on `/ws/pipeline`. SQLite tables live in
`MAILROOM_OPERATOR_DB`; the producer's `documents` table is never required.
Display `/api/*` and floor `/ws` stay open.

An optional React package (`ui/`, extra `[ui]` is a marker only) can be
built and served at `/desk` when `ui/dist` exists. Default `mailroom-web`
does not need Node. Pixel console and Observatory stay vanilla.

The producer **code** pin is optional extra `[pipeline]`
(`mailroom @ git+https://github.com/Exios66/llm-mailroom.git@3cf9fb9`,
package 0.6.0 / tag `v0.6.0`).
`mailroom_ui/producer.py` imports `pipeline.review_resolve` and
`schemas.manifest` when that extra or a sibling checkout is present; the
REVIEW proxy and `tests/fake_producer.py` use those contract helpers
(dispositions, `serialize_document`, tray actions). The adapter never
imports `api.main` or `llm_dojo_scoring`. `/api/meta` reports the pin.

## Demos & screenshots

A working REVIEW-tray round-trip (FakeClient traces + `tests/fake_producer.py`
`/v1` stub) is `PYTHONPATH=. python scripts/demo_review_tray.py --port 8006`.
`--check-api` hits lookup, source fallback, record, resume, and complete.

Stills of every pixel / Observatory / TUI desk live in `docs/screenshots/`.
The live Hugging Face Space walkthrough
(`docs/demos/hf-space-observatory-live-walkthrough.mp4`), the PR desk
walkthrough (`docs/demos/tui-server-observatory-desk-walkthrough.mp4`),
and the gallery notebook (`docs/demos/The-Mailroom-Demos.ipynb`) live next
to them. Index: `docs/demos.md` / wiki `Demos`. These are
documentation of the live surfaces — not a canned UI fallback.

