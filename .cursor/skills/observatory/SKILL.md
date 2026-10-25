---
name: observatory
description: Mailroom Observatory hosted desk (hosted/ vanilla SPA at /live, mailroom-hosted). Use when changing the public pipeline board, inspect dialog, debug bundle, replay, Inbox tray, or MAILROOM_EDITION=hosted — not the GitHub Pages snapshot and not the pixel CRT.
---

# Observatory (`hosted/`)

**When:** `/live`, `mailroom-hosted`, `MAILROOM_EDITION=hosted`, Debug desk,
`GET /api/debug/bundle`, replay bar, hosted Inbox tray.  
**Not:** GH Pages (`scripts/publish_pages.sh`) and not the pixel CRT at `/`.

## Layout

- `hosted/index.html` + `hosted/js/app.js` + `client.js` + `debug.js`
- Vanilla HTML/CSS/JS, no npm. Cache-bust `?v=` on the three script tags + CSS.
- Debug: `window.__OBSERVATORY_DEBUG__` — fetch/WS/error ring; Export / Pull /
  Push against `/api/debug/*`.
- Inbox tray is its own station (`stage=inbox`); sorter is intake/classify.

## Live vs snapshot

| Mode | Command | Data |
| --- | --- | --- |
| Hosted live | `mailroom-hosted` (binds `0.0.0.0`) | Langfuse via `/api` + `/ws` |
| Pixel + /live | `mailroom-web` | Same API; Observatory still at `/live` |
| GH Pages | `publish_pages.sh` | Static snapshot — **not** this UI |
| Hugging Face Space | `scripts/publish_space.py` | Same live Langfuse desk; Docker, port 7860 |

When the WebSocket drops, HTTP fallback must poll traces + `/api/pipeline` at
`poll_interval_s` (see [live-floor](../live-floor/SKILL.md)).

The Review desk can **resolve** items (`Obs.api.reviewResolve`) the same way
as the pixel console, including class/subtype correction (`doc_type` mapped
to producer `override_doc_type`), Complete + `extracted_data`, and
`Obs.api.reviewSource` for parked text (lookup fallback on producer main).
Unconfigured producer → setup hint, not a fabricated catalog write.
Working demo: `scripts/demo_review_tray.py`.

## Hugging Face Space

SDK **Docker**, root directory empty, `app_port` 7860. Secrets:
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (US cloud
`https://us.cloud.langfuse.com`; `LANGFUSE_BASE_URL` is an alias).
`python scripts/publish_space.py --check` is offline. Do not configure
the Space as FastAPI/Vercel and do not bake keys into the image.
Cards show primary/secondary hit·miss·pending (not cls/ext %). Inbox
queue proxies `POST /v1/upload` when `MAILROOM_PIPELINE_URL` + token
are set (loopback `:8000` locally, or a public producer Space URL).
Trace inspect uses `MAILROOM_TRACE_CACHE_DIR` (`GET /api/snapshot`)
when Langfuse is slow.

## Related

- Pixel CRT: [pixel-console](../pixel-console/SKILL.md)
- Source: [langfuse](../langfuse/SKILL.md)
- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
