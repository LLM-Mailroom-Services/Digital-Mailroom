# 🖥️ Operator Desk

**Docker Compose configuration for the Mailroom Operator Desk — single front door.**

**JWT-gated operator surface: the optional React desk (`/desk`) and its
auth / archive / ops / pipeline-WS backend.**

Auth is minted **against this visualizer, not the producer.**

## Structure

| Path | Contents |
| :--- | :--- |
| `auth.py` | HS256 JWT — `POST /v1/auth/login`, `GET /v1/auth/me`, `POST /v1/auth/logout` |
| `db.py` | SQLite (`ui_users`, `ui_audit`, `archive_index`); seeds the admin on `migrate()` |
| `mount.py` | `mount_operator()` — mounts the routers and gates `/desk` on `ui/dist/index.html` |
| `ops.py` / `archive.py` / `websocket.py` / `observer.py` | Langfuse-backed ops, archive, `/ws/pipeline`, bin watcher |
| `docker-compose.yml` / `nginx/` | Production Docker path (single nginx front door) |
| `../ui/` | React desk source (**optional** — Node is never needed for a default install) |
| `../Dockerfile` | Shared image. Default target = hosted edition; `--target operator` = this desk (adds `[operator]` + bakes `/desk`) |

`/desk` is served **only when `ui/dist/index.html` exists**. Without a build
the route is simply absent; the pixel console (`/`) and Observatory (`/live`)
are unaffected. The local run below builds it on the host; the Docker path
bakes the same build into the `operator` image target.

---

## Docker-free local run (testers)

The desk is a static Vite build; the backend serves it. Node 22+ and Python
3.11+ are the only requirements — **Docker is not needed.**

```bash
cd packages/The-Mailroom

# 1) Build the optional React desk (emits ui/dist with base=/desk/)
cd ui && npm ci && NODE_ENV=production npm run build && cd ..

# 2) Install the operator extra (bcrypt / PyJWT / watchdog; stdlib fallbacks exist)
pip install -e ".[operator]"

# 3) Set the tester credentials + a FRESH signing secret, then boot
export MAILROOM_OPERATOR_ADMIN_USER=admin
export MAILROOM_OPERATOR_ADMIN_PASSWORD=<your-local-tester-password>   # see caveat
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"          # never the dev default
python -m server.main                                                  # http://127.0.0.1:8001
```

`MAILROOM_PORT` (default **8001**) picks the port — a platform `PORT` env wins.
`server.main:run()` calls `load_dotenv()`, so a local `.env` (gitignored) also
supplies these. `ui/dist` is gitignored: build output is never committed.

### Log in

| Field | Value |
| :--- | :--- |
| URL | `http://127.0.0.1:8001/desk` (redirects to `/desk/login`) |
| Username | `admin` (from `MAILROOM_OPERATOR_ADMIN_USER`) |
| Password | the value of `MAILROOM_OPERATOR_ADMIN_PASSWORD` |

The seeded admin is created by `migrate()` on first boot **only when
`ui_users` is empty**; changing the env afterwards does not rewrite an
existing row. To reseed, point `MAILROOM_OPERATOR_DB` at a fresh file (or
delete the local `data/operator.db`).

> ⚠️ **Local/trusted testers only.** The dev fallback password (`changeme`)
> and any shared `MAILROOM_OPERATOR_JWT_SECRET` are for a loopback /
> trusted-LAN trial — **rotate both before any public or shared exposure.**

---

## Docker Compose (production)

This is the **production** path: a single nginx front door on `:80`. The image
builds the `operator` target of `../Dockerfile`, which installs
`.[operator]` (bcrypt / PyJWT / watchdog / PyMuPDF) and bakes the React
`/desk` build — no Node at runtime, no second UI container. The backend is
**not** published on the host; only nginx is.

Two secrets are **required** and the compose file fails fast without them:

Required env (fail fast — compose exits if unset; the operator process
also refuses missing / known-unsafe values outside explicit DEV mode):

| Var | Purpose |
| :--- | :--- |
| `MAILROOM_OPERATOR_JWT_SECRET` | JWT signing secret (or `JWT_SECRET` alias) |
| `MAILROOM_OPERATOR_ADMIN_PASSWORD` | Admin login password |

Local DX without those secrets: `MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS=1`
or `MAILROOM_ENV=development`. Compose `${VAR:?}` is unchanged.

```bash
cd packages/The-Mailroom/operator_desk
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"
export MAILROOM_OPERATOR_ADMIN_PASSWORD='<strong-password>'
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"
export MAILROOM_OPERATOR_ADMIN_PASSWORD='<strong-password>'

docker compose -f operator_desk/docker-compose.yml up --build

Front door: **http://localhost** — nginx `:80` is the only published port;
the desk is at **`/desk`**. The backend port `8001` is NOT published. The
visualizer builds the root Dockerfile's `operator` target (installs
`.[operator]` via the `MAILROOM_EXTRAS` build arg and bakes `ui/dist`) and
runs the in-process bin watcher (`MAILROOM_OBSERVER=1`). Do not add a
`mailroom-observer` sidecar on the same volume (issue #78).

## Services

| Service | Image | Purpose |
| :--- | :--- | :--- |
| `mailroom` | root `Dockerfile` → `target: operator` | Visualizer + `/v1/auth` `/v1/archive` `/v1/ops` `/ws/pipeline`, serves `/desk`, in-process bin watcher |
| `nginx` | `nginx:alpine` | Reverse proxy — the only published front door (`:80`) |

The standalone `mailroom-observer` CLI (`python -m operator_desk.observer`,
POST `/v1/ops/events`) is optional and **not** part of this compose file.
If you run it, set `MAILROOM_OBSERVER=0` on `mailroom` first so the two
watchers do not double-emit.
- `hosted/` — Observatory (hosted edition)
- `server/` — Backend server (`mount_operator` is wired at `server/main.py`)
