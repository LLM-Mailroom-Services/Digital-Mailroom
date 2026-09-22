# Operator desk

> This file is mirrored at `wiki/Operator-Desk.md` — edit both together.

`operator_desk/` is a dedicated submodule on the visualizer process. It is
**not** a document-display source. Pixel console and Observatory stay the
default vanilla desks. An optional React package lives in `ui/` and mounts
at `/desk` only after `npm run build` (or when baked into the `operator`
Docker image target).

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

Default admin is `admin` / `changeme` until `MAILROOM_OPERATOR_ADMIN_PASSWORD`
is set. Use `MAILROOM_OPERATOR_JWT_SECRET` (or `JWT_SECRET`) — never reuse
`MAILROOM_PIPELINE_TOKEN`.

Compose — single front door, operator edition (visualizer + observer +
nginx; nginx `:80` is the only published port; the visualizer builds the
`operator` image target — `.[operator]` extras + the baked React `ui/dist`,
served at `/desk` — while the headless observer builds the lean
`operator-core` target with no Node stage):

```bash
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"
export MAILROOM_OPERATOR_ADMIN_PASSWORD='<strong-password>'
docker compose -f operator_desk/docker-compose.yml up --build
# → http://localhost/desk
```

Both secrets are fail-fast (`${VAR:?}` — compose refuses to start without
them). `MAILROOM_OPERATOR_INGEST_TOKEN` stays optional. The old `mailroom-ui`
sidecar service and the backend's `8001:8001` publish are gone.

See `operator_desk/README.md` and `.env.example` (`MAILROOM_OPERATOR_*`).

Optional React desk (Node 22+, never required for `mailroom-web`):

```bash
cd ui && npm install && npm run build
# then GET http://127.0.0.1:8001/desk   (local non-docker path)
```

Standalone container (dev only — production uses the baked operator image):

```bash
docker build -t mailroom-ui ./ui && docker run -p 5174:80 mailroom-ui
```

See `ui/README.md`. Extra `[ui]` is a marker only.
