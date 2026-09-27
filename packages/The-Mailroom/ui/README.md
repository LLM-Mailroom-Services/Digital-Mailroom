# Optional React operator desk (`the-mailroom-ui`)

This package is an **optional dependency branch**. Default `pip install -e ".[dev]"`
and `mailroom-web` never need Node. Pixel console (`web/`) and Observatory
(`hosted/`) stay vanilla HTML/CSS/JS.

When built, the visualizer serves the desk at **`/desk`**.

## Install (Node 22+)

```bash
cd ui
npm install
npm run dev      # http://127.0.0.1:5173  (proxies /api /v1 /ws → :8001)
npm run build    # ui/dist  →  mailroom-web mounts /desk
```

Python extra is a marker only (`pip install -e ".[ui]"` does not install npm):

```bash
pip install -e ".[ui]"
```

## What it talks to

| Desk | Source |
| --- | --- |
| Pipeline / review queue | Langfuse via `/api/traces`, `/api/review-queue` |
| Review resolve / parked text | `/api/review/resolve`, `/api/review/source` |
| Archive / ops / login | `/v1/archive`, `/v1/ops`, `/v1/auth` |
| Bin events | `/ws/pipeline?token=` |

Ingest still happens on llm-mailroom `:8000`. This desk does not accept uploads
and does not fabricate envelopes.

## Docker

Production does **not** ship a second UI container. The operator compose
builds the `operator` target of the root `Dockerfile`, whose `ui-builder`
stage runs `npm ci && npm run build` and bakes the result into the backend
image at `/app/ui/dist`; the backend serves `/desk` and the front-door nginx
plain-proxies it. See [`../operator_desk/README.md`](../operator_desk/README.md):

```bash
cd ../operator_desk
export MAILROOM_OPERATOR_JWT_SECRET="$(openssl rand -hex 32)"
export MAILROOM_OPERATOR_ADMIN_PASSWORD='<strong-password>'
docker compose -f operator_desk/docker-compose.yml up --build          # → http://localhost/desk
```

`ui/Dockerfile` remains as an **optional standalone** UI image (serves the
build at `/` and proxies `/api` `/v1` `/ws` to a backend reachable as
`mailroom:8001` on a shared network). It is not part of the production
compose. To build/run the standalone image for development/evaluation:

```bash
docker build -t mailroom-ui ./ui        # VITE_BASE=/ → serves SPA at /
# run on a network shared with the backend, then open :5174
docker run --network mailroom-net -p 5174:80 mailroom-ui
```
