---
name: tui
description: The-Mailroom terminal console (mailroom-tui, tui/mailroom_console.py). Use when changing AgentLab-style banners, floor tables, MAILROOM_API_URL, MAILROOM_TUI_POLL, or --once scripting — point the TUI at this visualizer (:8001), not the producer API.
---

# TUI (`mailroom-tui`)

**When:** Terminal floor/review/sessions/metrics/inspect/debug,
`tui/mailroom_console.py`, `MAILROOM_TUI_POLL`, `--once`.  
**API base:** `MAILROOM_API_URL` default `http://127.0.0.1:8001` — **this
visualizer**, not llm-mailroom `:8000`. Producer liveness is
`MAILROOM_PIPELINE_URL` on the server, surfaced as `pipeline` on snapshots /
`GET /api/pipeline`.

## Commands

```bash
mailroom-tui
mailroom-tui --once          # scripting
# MAILROOM_TUI_POLL=3        # default matches hub
# MAILROOM_API_URL=http://127.0.0.1:8001
```

Same 7-day window as the pixel/Observatory HTTP clients
(`MAILROOM_RECENT_WINDOW=604800`). Status header shows watcher + inbox when
`/api/pipeline` is configured.

## Boundaries

- Do not invent a second data path; fetch `/api/traces` + `/api/pipeline`.
- Do not point `MAILROOM_API_URL` at the producer “to resolve review-queue”
  (that was the old docs mix-up). Resolve with
  `mailroom-tui --resolve TRACE --decision approved|rejected --disposition resume|record|requeue|complete [--doc-type X --doc-subclass Y]`
  against **this visualizer** (`POST /api/review/resolve`). `--source TRACE`
  prints parked text (`GET /api/review/source`). `--doc-type` is mapped to
  producer `override_doc_type` by the visualizer proxy.
- Closed state when the visualizer/Langfuse is down — no canned tables.

## Related

- Live poll: [live-floor](../live-floor/SKILL.md)
- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
