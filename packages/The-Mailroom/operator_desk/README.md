# 🖥️ Operator Desk

**Docker Compose configuration for the Mailroom Operator Desk — single front door.**

## Structure

| Path | Contents |
| :--- | :--- |
| [`docker-compose.yml`](docker-compose.yml) | Docker Compose configuration |
| [`nginx/`](nginx/) | Nginx reverse proxy configuration |

## Running

Required env (fail fast — compose exits if unset):

| Var | Purpose |
| :--- | :--- |
| `MAILROOM_OPERATOR_JWT_SECRET` | JWT signing secret (or `JWT_SECRET` alias) |
| `MAILROOM_OPERATOR_ADMIN_PASSWORD` | Admin login password |

```bash
cd packages/The-Mailroom/operator_desk
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"
export MAILROOM_OPERATOR_ADMIN_PASSWORD='<strong-password>'
docker compose up --build
```

Front door: **http://localhost** — nginx `:80` is the only published port;
the desk is at **`/desk`**. The backend port `8001` is NOT published. Both
app services build the root Dockerfile's `operator` target (installs
`.[operator]` via the `MAILROOM_EXTRAS` build arg and bakes `ui/dist`).

## Services

| Service | Image | Purpose |
| :--- | :--- | :--- |
| `mailroom` | root `Dockerfile` → `target: operator` | Visualizer + `/v1/auth` `/v1/archive` `/v1/ops` `/ws/pipeline`, serves `/desk` |
| `mailroom-observer` | root `Dockerfile` → `target: operator` | Standalone bin watcher → POST `/v1/ops/events` |
| `nginx` | `nginx:alpine` | Reverse proxy — the only published front door (`:80`) |

## Related Files

- `ui/` — optional React operator desk source (standalone container only;
  production bakes it into the `operator` image target)
- `hosted/` — Observatory (hosted edition)
- `server/` — Backend server
