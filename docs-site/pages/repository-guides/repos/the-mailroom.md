---
icon: film
title: The-Mailroom
---

# The-Mailroom

**A pixel-art visual engine that draws every pipeline run as envelopes on a conveyor, driven only by Langfuse traces.**

|               |                                                                           |
| ------------- | ------------------------------------------------------------------------- |
| Repository    | [Exios66/The-Mailroom](https://github.com/Exios66/The-Mailroom)           |
| Monorepo path | `packages/The-Mailroom` (Python package `the-mailroom`)                   |
| Release       | v0.5.0                                                                    |
| Site          | [exios66.github.io/The-Mailroom](https://exios66.github.io/The-Mailroom/) |

## What it does

The-Mailroom renders the pipeline as a mailroom floor: sorter, specialist bays, judge gate, boss's desk, reporter and archive, grouped into three rooms, with a human-review siding. Click an envelope to inspect its full run.

| Surface            | How to open it                                                         |
| ------------------ | ---------------------------------------------------------------------- |
| Pixel-art console  | `mailroom-web` → `http://127.0.0.1:8001/`                              |
| Hosted Observatory | `mailroom-hosted`, or `/live` on the same server                       |
| TUI                | `mailroom-tui`                                                         |
| Terminal site      | `/terminal/` on GitHub Pages, with a dataset viewer and a repo browser |

Console tabs: FLOOR, REVIEW (approve, reject, requeue, correct the class), INSPECTOR (span timeline, model, tokens, cost), SESSIONS, HISTORY with REPLAY, METRICS (including first-pass rate) and CONSOLE.

## How it connects to the pipeline

* **Langfuse is the only data source.** Every envelope, badge, verdict and metric comes from the pipeline's Langfuse project. Demo mode seeds synthetic runs into Langfuse rather than bypassing it.
* **It calls back into the pipeline API** for operator actions. Set `MAILROOM_PIPELINE_URL`, `MAILROOM_PIPELINE_TOKEN` and `MAILROOM_PIPELINE_API_PREFIX=/v1`. Queue a document posts to `/v1/upload`; REVIEW buttons call the pipeline's review-resolve endpoints. Producer keys never reach the browser.
* **Schema mirror duty.** When the pipeline changes spans, node order, agents, classes, thresholds or judge score names, update `mailroom_ui/pipeline_schema.py` and `mailroom_ui/trace_interpreter.py` in the same change window. `MAILROOM_TAXONOMY` can point at the pipeline's `taxonomy.yaml` directly.

## Security on public deployments (since v0.5.0)

Read this before you expose the server. Since v0.5.0 a public bind fails closed. A bind is public when the edition is `hosted` or `MAILROOM_HOST` is not a loopback address.

* **Operator login is refused** (HTTP 503) while `MAILROOM_OPERATOR_JWT_SECRET` is unset or default, or while the admin still has the default password. Set both `MAILROOM_OPERATOR_JWT_SECRET` and `MAILROOM_OPERATOR_ADMIN_PASSWORD`.
* **Producer writes need a reviewer token.** `POST /api/review/resolve` and `/api/inbox/enqueue` refuse cross-site browser origins. On a public bind they also require a reviewer JWT. Wildcard CORS (`MAILROOM_CORS_ORIGINS`) is read-only. The TUI reads `MAILROOM_OPERATOR_TOKEN`.
* **Roles are enforced.** Archive download, preview and verify, and ops events, need the reviewer role or higher. Tokens must carry `exp`.
* The operator compose file requires real secrets and the ingest token.

Pages: [operator-desk.md](https://github.com/Exios66/The-Mailroom/blob/main/docs/operator-desk.md) and [deployment.md](https://github.com/Exios66/The-Mailroom/blob/main/docs/deployment.md) list every setting.

## Settings you will meet

| Variable | Purpose |
| -------- | ------- |
| `MAILROOM_EDITION` | `console` (default) or `hosted` |
| `MAILROOM_HOST`, `MAILROOM_PORT` | Bind address and port |
| `MAILROOM_OBSERVER` | `1` runs the bin watcher inside `mailroom-web` |
| `MAILROOM_OPERATOR_DB` | Operator SQLite store |
| `MAILROOM_OPERATOR_JWT_SECRET`, `MAILROOM_OPERATOR_ADMIN_USER`, `MAILROOM_OPERATOR_ADMIN_PASSWORD` | Operator login (see above) |
| `MAILROOM_OPERATOR_INGEST_URL`, `MAILROOM_OPERATOR_INGEST_TOKEN` | Observer-to-desk ingest |
| `MAILROOM_CORS_ORIGINS` | Allowed browser origins |
| `MAILROOM_POLL_ENRICH`, `MAILROOM_POLL_ENRICH_BUDGET`, `MAILROOM_TRACE_CACHE_DIR` | Visualizer-side Langfuse polling. The pipeline never sets them |
| `MAILROOM_DEBUG` | `1` turns on verbose logging |

## Pipeline pin

v0.5.0 was resynced to llm-mailroom `959bb0b` (package 0.7.1), llm-dojo-scoring v0.16.0 and mailroom-dataset `v9.1` (as of 2026-09-28). The pipeline has moved on since: llm-mailroom v0.9.3 pins dojo v0.28.1. Check [`mailroom_ui/pipeline_schema.py`](https://github.com/Exios66/The-Mailroom/blob/main/mailroom_ui/pipeline_schema.py) against the pipeline's `taxonomy.yaml` before you trust a new span or score name. The `main` branch has one unreleased fix: `publish_pages.sh --skip-export` no longer wipes `build-info.json` on `gh-pages`.

## Quick start

```bash
pip install -e ".[dev]"
cp .env.example .env      # LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
mailroom-web              # pixel console on :8001
mailroom-tui              # typed-command console
```

Optional extras: `[pipeline]` (imports llm-mailroom for review resolve), `[operator]` (operator desk with auth, archive and observer), and a React desk under `ui/` that needs Node.

## Its documentation

* [README](https://github.com/Exios66/The-Mailroom/blob/main/README.md)
* [docs/architecture.md](https://github.com/Exios66/The-Mailroom/blob/main/docs/architecture.md)
* [docs/deployment.md](https://github.com/Exios66/The-Mailroom/blob/main/docs/deployment.md)
* [docs/operator-desk.md](https://github.com/Exios66/The-Mailroom/blob/main/docs/operator-desk.md)
* [docs/demos.md](https://github.com/Exios66/The-Mailroom/blob/main/docs/demos.md)
* [docs/releases.md](https://github.com/Exios66/The-Mailroom/blob/main/docs/releases.md)
* [Agent skills index](https://github.com/Exios66/The-Mailroom/blob/main/.cursor/skills/README.md)
* Pairing checklist on the pipeline side: [deploy/space/PAIRING.md](https://github.com/Exios66/llm-mailroom/blob/main/deploy/space/PAIRING.md)
