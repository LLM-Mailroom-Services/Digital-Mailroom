<div align="center">

# 🖥️ Operator Desk

**Production Docker stack for the Mailroom Operator Desk.**

</div>

---

## Structure

| Path | Contents |
| :--- | :--- |
| [`Dockerfile`](Dockerfile) | Visualizer + `[operator]` extra + baked React `/desk` (build context: repo root) |
| [`docker-compose.yml`](docker-compose.yml) | `mailroom` (visualizer, in-process bin watcher) + `nginx` (the only published port) |
| [`nginx/nginx.conf`](nginx/nginx.conf) | Reverse proxy for `/`, `/live`, `/desk`, `/api`, `/v1`, `/ws`, `/ws/pipeline` |

## Running

```bash
cd operator_desk
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"
export MAILROOM_OPERATOR_ADMIN_PASSWORD='<strong-password>'
docker compose up --build          # → http://localhost/desk
```

Compose refuses to start without both secrets (the stack binds `0.0.0.0`,
so the desk fails closed on local-dev defaults). `MAILROOM_HTTP_PORT` moves
nginx off port 80. Langfuse keys and `MAILROOM_PIPELINE_URL` / `_TOKEN` come
from the environment or `.env`.

## One watcher

The visualizer runs the in-process bin observer (`MAILROOM_OBSERVER=1`) and
broadcasts moves on `/ws/pipeline`. There is no observer sidecar — running
both double-emitted every event (mailroom-issues#118). The standalone
`mailroom-observer` CLI (POST `/v1/ops/events`, needs
`MAILROOM_OPERATOR_INGEST_TOKEN`) is for bins on another host; set
`MAILROOM_OBSERVER=0` on the visualizer if you use it.

## Not covered here

- TLS: see the commented `listen 443` block in `nginx/nginx.conf`, or put a
  TLS proxy in front (forward `X-Forwarded-Proto`).
- The hosted Observatory image is the root `Dockerfile` (HF Spaces /
  Railway / Fly) and is unaffected by this stack.

## Related

- `ui/` — React operator desk source (`ui/Dockerfile` is a dev-only image)
- `docs/operator-desk.md` — auth, roles, endpoints
