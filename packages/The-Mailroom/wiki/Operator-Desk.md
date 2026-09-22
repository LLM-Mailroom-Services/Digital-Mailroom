# Operator desk

> This file is mirrored at `docs/operator-desk.md` — edit both together.

`operator_desk/` is a dedicated submodule on the visualizer process. It is
**not** a document-display source. Pixel console and Observatory stay the
default vanilla desks. An optional React package lives in `ui/` and mounts
at `/desk` only after `npm run build`.

## What it adds

| Surface | Path | Source of truth |
| --- | --- | --- |
| JWT login / profile | `/v1/auth/*` | Local `ui_users` |
| Archive list / download / preview / verify | `/v1/archive/*` | Local `archive_index` + files under `MAILROOM_BASE_DIR` |
| Ops status / throughput / distribution | `/v1/ops/*` | Langfuse `PipelineRun`s (same window as METRICS) |
| Bin-move events | `/ws/pipeline` | Observer (in-process or POST `/v1/ops/events`) |

Display `/api/*` and the floor WebSocket `/ws` stay unauthenticated.

## Run

```bash
pip install -e ".[dev]"
pip install -e ".[operator]"     # bcrypt, PyJWT, watchdog, PyMuPDF
scripts/setup_operator.sh
mailroom-web                     # mounts the desk on :8001
MAILROOM_OBSERVER=1 mailroom-web # in-process bin watcher
mailroom-observer                # standalone → POST /v1/ops/events
```

Default admin is `admin`; set `MAILROOM_OPERATOR_ADMIN_PASSWORD` before any
shared exposure (a local-dev fallback exists). Use
`MAILROOM_OPERATOR_JWT_SECRET` (or `JWT_SECRET`) — never reuse
`MAILROOM_PIPELINE_TOKEN`.

Compose — the production path (visualizer + observer + nginx, no local
Langfuse). The `operator` image target installs `.[operator]` and bakes the
React `/desk` build; nginx `:80` is the single front door. Both
`MAILROOM_OPERATOR_JWT_SECRET` and `MAILROOM_OPERATOR_ADMIN_PASSWORD` are
required (compose fails fast):

```bash
cd packages/The-Mailroom/operator_desk
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"
export MAILROOM_OPERATOR_ADMIN_PASSWORD='<strong-password>'
docker compose up --build          # → http://localhost/ , /live , /desk
```

See `operator_desk/README.md` and `.env.example` (`MAILROOM_OPERATOR_*`).

Optional React desk, docker-free (Node 22+, never required for `mailroom-web`):

```bash
cd ui && npm install && npm run build
# then GET http://127.0.0.1:8001/desk
```

See `ui/README.md`. Extra `[ui]` is a marker only.
