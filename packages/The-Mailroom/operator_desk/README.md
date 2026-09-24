# 🖥️ Operator Desk

**Docker Compose configuration for the Mailroom Operator Desk — single front door.**

## Structure

| Path | Contents |
| :--- | :--- |
| [`docker-compose.yml`](docker-compose.yml) | Docker Compose configuration |
| [`nginx/`](nginx/) | Nginx reverse proxy configuration |

## Running

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
docker compose up --build
```

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

## Related Files

- `ui/` — optional React operator desk source (standalone container only;
  production bakes it into the `operator` image target)
- `hosted/` — Observatory (hosted edition)
- `server/` — Backend server
