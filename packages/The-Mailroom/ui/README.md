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

Compose: the `mailroom-ui` sidecar service was removed (DMR-076) — the
production compose bakes this desk into the root image's `operator` target
and serves it at `/desk` through nginx (`:80`, single front door). This
package is now standalone-only:

```bash
docker build -t mailroom-ui ./ui        # VITE_BASE=/ → serves SPA at /
# run on a network shared with the backend, then open :5174
docker run --network mailroom-net -p 5174:80 mailroom-ui
```

The standalone container proxies `/api` `/v1` `/ws` to a `mailroom` upstream
(see `nginx.conf`) — it is dev/evaluation use only, not the production path.
