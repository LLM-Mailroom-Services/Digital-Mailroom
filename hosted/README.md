# Mailroom Observatory (hosted edition)

A **public, modern, accessible** operations desk for the `llm-mailroom`
pipeline. It is a different product surface from:

| Surface | Who it is for | How it looks |
|---|---|---|
| **This site** (`/live`, `mailroom-hosted`) | Anyone with the URL | Editorial desk, semantic HTML, keyboard-first |
| Local pixel console (`mailroom-web`, `/`) | Operators on localhost | CRT / conveyor canvas |
| `mailroom-tui` | Terminal users | AgentLab banners + tables |
| GitHub Pages | Offline snapshot | Static export of the pixel SPA |

Langfuse (or the configured Phoenix / multi source) is still the **only**
display source. This edition talks to the same `/api/*` + `/ws` contract.

## Run locally (preview the public UI)

```bash
pip install -e ".[dev]"
cp .env.example .env          # LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
mailroom-hosted               # 0.0.0.0 — http://127.0.0.1:8001/live
# or keep the pixel console on / and open the Observatory beside it:
mailroom-web                  # http://127.0.0.1:8001/live
```

`MAILROOM_EDITION=hosted` also puts the Observatory on `/` (what the
container image does).

## Deploy to a public URL

The image listens on `0.0.0.0:$MAILROOM_PORT` (default **7860**, Hugging
Face Spaces convention). Inject the same secrets you use locally — never
bake keys into the image.

### Hugging Face Spaces (Docker)

The committed root `Dockerfile` **is** the Space image
(`MAILROOM_EDITION=hosted`, `0.0.0.0:7860`, `python -m server.hosted`).
Do not pick FastAPI / Gradio / a subdirectory as the Space SDK.

**Dashboard (one-time):**

| Field | Set to |
|---|---|
| SDK | **Docker** |
| Root directory | *(leave empty — Dockerfile is at the repo/Space root)* |
| App port | **7860** (also `app_port` in [`SPACE_README.md`](SPACE_README.md)) |
| Hardware | CPU basic (no GPU) |
| Secrets | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` |
| Variables | `MAILROOM_SOURCE=langfuse` (optional) |

This repo's knob is **`LANGFUSE_HOST`**. Langfuse's UI label
`LANGFUSE_BASE_URL` is accepted as an alias. Production US cloud:

```
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

**Publish** (never bake keys into git; `HF_TOKEN` stays on your machine):

```bash
pip install huggingface_hub
python scripts/publish_space.py --check
HF_TOKEN=hf_... \
  LANGFUSE_PUBLIC_KEY=pk-lf-... \
  LANGFUSE_SECRET_KEY=sk-lf-... \
  LANGFUSE_HOST=https://us.cloud.langfuse.com \
  MAILROOM_PIPELINE_URL=https://<user>-mailroom-producer.hf.space \
  MAILROOM_PIPELINE_TOKEN=$MAILROOM_API_TOKEN \
  MAILROOM_PIPELINE_API_PREFIX=/v1 \
  python scripts/publish_space.py --repo <user>/mailroom-observatory
```

The Space URL is the Observatory (`/` inside the container). Pixel assets
remain at `/static`. REVIEW resolve and Inbox enqueue (`POST /v1/upload`)
need `MAILROOM_PIPELINE_URL` on a **reachable** producer — `127.0.0.1:8000`
only works when the visualizer and producer share a host. A Space
Observatory must use the public producer Space URL. Without those knobs
the desk still shows the live Langfuse floor, with a disk snapshot cache
(`MAILROOM_TRACE_CACHE_DIR`) so inspect does not stall on `get_run`.

### Any Docker host (Fly, Render, Cloud Run, a VPS)

```bash
docker build -t mailroom-observatory .
docker run --rm -p 7860:7860 --env-file .env mailroom-observatory
```

Then `https://your-host/` (or `http://localhost:7860/live` if you also
expose the pixel console paths — assets stay under `/live/static`).

## What you can do here

- **Pipeline** — live trays for Sorter · Extract · Judge · Boss · Report ·
  Archive · Review · Completed. Cards update from the WebSocket snapshot.
- **Review** — human-review queue (`/api/review-queue`).
- **History + replay** — walk a stored trace through its real span sequence
  (paces by span latency; respects `prefers-reduced-motion`).
- **Matters** — Langfuse sessions.
- **Metrics** — window aggregates from the live source.
- **Inspect** — native `<dialog>` with spans, generations, scores.

Keyboard: `1`–`6` switch views (`6` = Debug). Tab order follows the page. Skip link jumps
to main content. Status is announced in an `aria-live` region.

## Debug suite (agents and humans)

Silent UI failures (a blank tray, a swallowed health error, a bad
WebSocket frame) are recorded in a ring buffer. Pull them without a
browser console:

| Who | How |
|---|---|
| Browser | Open **Debug** (`#debug` or `?debug=1`) — Refresh / Pull / Push / Export / Copy |
| Console | `window.__OBSERVATORY_DEBUG__.dump()` · `.export()` · `.explain(event)` · `.setVerbose(true)` |
| curl / next agent | `GET /api/debug/bundle` — health + source knobs + server request log + last posted client dumps |
| Leave a dump for the next agent | Debug desk **Push client dump**, or `POST /api/debug/client` with the dump JSON |

`GET /api/debug/logs` and `GET /api/debug/source` still exist; the bundle
is the one-pull wrapper. Event kinds have a glossary in `hosted/js/debug.js`
(`KINDS`) so a raw `window-error` or `review-error` row is readable.

## Accessibility notes

- Landmarks: header, nav, main, footer; skip link; `aria-current` on the
  active view.
- Color is never the only signal (badges include the verdict word).
- Focus rings are 3px and use a dedicated `--focus` token.
- `prefers-reduced-motion: reduce` disables replay autoplay and smooth
  scrolling.
- Contrast is sized for text on cream / ink (and the dark `color-scheme`
  pair).
