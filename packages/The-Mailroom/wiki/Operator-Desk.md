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
mailroom-observer                # standalone → POST /v1/ops/events (not with MAILROOM_OBSERVER=1)
```

Default admin is `admin` / `changeme` until `MAILROOM_OPERATOR_ADMIN_PASSWORD`
is set — **loopback only**. On a public bind (hosted edition or a non-loopback
`MAILROOM_HOST`) login is refused until `MAILROOM_OPERATOR_JWT_SECRET` (or
`JWT_SECRET`) is set and the admin password is rotated; review resolve and
inbox upload then require a reviewer (or admin) token. Never reuse
`MAILROOM_PIPELINE_TOKEN`. Roles: `viewer` < `reviewer` < `admin`; archive
download / preview / verify and `POST /v1/ops/events` need reviewer+ (the
ingest token counts as admin).

Compose — the production operator stack (one front door, one watcher):

```bash
cd operator_desk
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"
export MAILROOM_OPERATOR_ADMIN_PASSWORD='<strong-password>'
docker compose up --build        # → http://localhost/desk
```

- `mailroom` builds `operator_desk/Dockerfile`: the visualizer with the
  `[operator]` extra and the React desk baked in at `ui/dist` (Node is a
  build stage only). It publishes no host port.
- `nginx` is the only published port (`${MAILROOM_HTTP_PORT:-80}`) and
  proxies `/`, `/live`, `/desk`, `/api`, `/v1`, `/ws`, `/ws/pipeline`.
- The in-process bin watcher runs in `mailroom` (`MAILROOM_OBSERVER=1`); there
  is no observer sidecar (mailroom-issues#118). Run the standalone
  `mailroom-observer` CLI only where the bins live on another host, and set
  `MAILROOM_OBSERVER=0` on the visualizer if you do.
- Compose refuses to start without the JWT secret and admin password. No
  local Langfuse is started.
- The hosted Observatory image (root `Dockerfile`) is unchanged.

See `operator_desk/README.md` and `.env.example` (`MAILROOM_OPERATOR_*`).

Optional React desk (Node 22+, never required for `mailroom-web`):

```bash
cd ui && npm install && npm run build
# then GET http://127.0.0.1:8001/desk
```

See `ui/README.md`. Extra `[ui]` is a marker only.
