---
name: operator-desk
description: Operator desk submodule (operator_desk/) — JWT auth, archive file access, Langfuse-backed ops snapshots, /ws/pipeline, and the bin observer. Use when changing /v1/auth, /v1/archive, /v1/ops, mailroom-observer, or MAILROOM_OPERATOR_* knobs — not the pixel CRT, Observatory, or a React/npm UI.
---

# Operator desk (`operator_desk/`)

**When:** `/v1/auth`, `/v1/archive`, `/v1/ops`, `/ws/pipeline`,
`mailroom-observer`, `MAILROOM_OPERATOR_*`, `MAILROOM_OBSERVER`, operator
SQLite (`ui_users` / `ui_audit` / `archive_index`).
**Not:** a second document-display source. The optional React SPA lives in
`ui/` — see [optional-ui](../optional-ui/SKILL.md). Do not replace `web/` or
`hosted/` with npm.

## Contract

| Piece | Rule |
| --- | --- |
| Display | Still Langfuse via `/api/*` + `/ws`. Ops numbers come from `PipelineRun`s. |
| Auth | Gates operator routes only. Do not require JWT on the floor or TUI. |
| Archive | Local `archive_index` + files under `MAILROOM_BASE_DIR`. No fabricated catalog. |
| Observer | Prefer in-process (`MAILROOM_OBSERVER=1`). Standalone POSTs `/v1/ops/events`. |
| Producer | Never `import api.main`. Review resolve stays `mailroom_ui/review_actions.py`. |

## Commands

```bash
pip install -e ".[operator]"
python -m operator_desk
mailroom-observer
docker compose -f operator_desk/docker-compose.yml up --build
```

## Related

- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
- Floor WS: [live-floor](../live-floor/SKILL.md)
- Code: `operator_desk/`, `server/main.py` (`mount_operator`)
