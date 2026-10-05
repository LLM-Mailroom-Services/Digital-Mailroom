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

Compose profile (after `npm run build` or the UI image):

```bash
docker compose -f operator_desk/docker-compose.yml --profile ui up --build
```
