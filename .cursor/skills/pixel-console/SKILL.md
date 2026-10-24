---
name: pixel-console
description: Pixel-art The-Mailroom SPA (web/ vanilla HTML/CSS/JS, no npm). Use when changing the conveyor floor, envelopes, tabs, inspector, theme, cache-bust query strings, or MAILROOM CLOSED — never introduce a Node toolchain or JS test harness.
---

# Pixel console (`web/`)

**When:** FLOOR animation, envelope stations, REVIEW/SESSIONS/HISTORY/METRICS/
CONSOLE tabs, `web/js/*.js`, `theme.css`, `index.html` cache-bust `?v=`.  
**Stack:** vanilla HTML/CSS/JS, no build step, **no npm**.

## Surfaces

| File | Job |
| --- | --- |
| `web/js/floor.js` | Canvas conveyor (INBOX hopper, 7 stations, sidings, tombstones) |
| `web/js/main.js` | Boot, WS + HTTP fallback, watcher/inbox strip |
| `web/js/api.js` | Fetch + WS; `?api=` + snapshot fallback for Pages |
| `web/js/inspector.js` | Run drill-down (observations, scores, subclass) |
| `web/js/review.js` / `sessions.js` / `history.js` / `metrics.js` / `console.js` | Desks |

REVIEW is not display-only: `Mailroom.reviewPanel` / `bindReviewForms` in
`api.js` post `POST /api/review/resolve` (resume / record / requeue / complete)
with optional `doc_type` / `doc_subclass` (proxy maps `doc_type` → producer
`override_doc_type`) and `extracted_data`, and fetch `GET /api/review/source` for
the parked-file text pane (lookup fallback on producer main). Snapshot mode must stay
read-only. Producer URL/token live on the server
(`MAILROOM_PIPELINE_URL` = `:8000`, `/v1`). Working demo:
`PYTHONPATH=. python scripts/demo_review_tray.py --port 8006`.

Entry: `mailroom-web` / `python -m server.main` → `http://127.0.0.1:8001/`.

## Rules

1. Bump `?v=` on `web/index.html` (and `hosted/index.html` if that SPA changed)
   whenever JS/CSS changes.
2. Frontend has **no test harness** — lock contracts in
   `tests/test_spa_contracts.py` (source-string asserts). Verify UI in the
   browser when tools exist; otherwise curl + those contracts.
3. Live path: Langfuse via backend. `?demo=1` only when the source is down
   (opt-in). GH Pages may serve bundled `data/*.json` snapshot mode — that is
   the static edition, not a live canned floor.
4. Station map must include `inbox`, intake/classify/retry, extract, judge,
   arbiter, boss, report, catalog/archive, review, archived/failed.
5. Do not invent a linter/formatter/typechecker.

## Related

- Live poll: [live-floor](../live-floor/SKILL.md)
- Public desk: [observatory](../observatory/SKILL.md)
- Pages snapshot: [gh-pages](../gh-pages/SKILL.md)
