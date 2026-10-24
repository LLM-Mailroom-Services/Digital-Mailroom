---
name: optional-ui
description: Optional React operator desk (ui/, the-mailroom-ui). Use when changing the Vite/React package, /desk mount, or MAILROOM_UI_DIST — never replace web/ or hosted/ with npm, and never make Node required for mailroom-web.
---

# Optional React desk (`ui/`)

**When:** `ui/` Vite/React package, `/desk`, `MAILROOM_UI_DIST`, extra `[ui]`.
**Not:** pixel CRT (`web/`), Observatory (`hosted/`), GH Pages, or a second
Langfuse adapter.

## Contract

| Rule | Detail |
| --- | --- |
| Optional | `pip install -e ".[dev]"` and `mailroom-web` work with zero Node |
| Mount | `/desk` only if `ui/dist/index.html` (or `MAILROOM_UI_DIST`) exists |
| APIs | Display via `/api/*`; operator via `/v1/*`; WS `/ws/pipeline` |
| Proxy | Vite targets **:8001**, never producer `:8000` |
| Ingest | No upload to this visualizer — producer inbox only |

```bash
cd ui && npm install && npm run build
mailroom-web   # GET /desk
npm run dev    # :5173 with proxy
```

## Related

- Operator APIs: [operator-desk](../operator-desk/SKILL.md)
- Pixel CRT: [pixel-console](../pixel-console/SKILL.md)
