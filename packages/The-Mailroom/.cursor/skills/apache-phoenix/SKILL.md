---
name: apache-phoenix
description: Optional Arize Phoenix trace source for The-Mailroom (MAILROOM_SOURCE=phoenix|both, PHOENIX_ENDPOINT). Use when wiring local Phoenix, arize-phoenix-client, or comparing OTEL spans — not as the default document-display sink (prefer Langfuse).
---

# Apache Phoenix (optional source)

**When:** User asks for Phoenix/Arize, `MAILROOM_SOURCE=phoenix` or `both`, or
`PHOENIX_ENDPOINT`.  
**Prefer Langfuse** for the family conveyor and US-cloud `llm-mailroom` project.
Phoenix is an **additional** local reader, not a replacement.

## Enable

```bash
pip install arize-phoenix-client
# .env
MAILROOM_SOURCE=phoenix          # or both
PHOENIX_ENDPOINT=http://localhost:6006
# PHOENIX_API_KEY=
# MAILROOM_PHOENIX_PROJECT=default
```

Adapter: `mailroom_ui/phoenix_source.py` reshapes OpenInference spans into the
Langfuse-shaped dicts `interpret_trace` already consumes. `MultiSource` unions
Langfuse + Phoenix when `MAILROOM_SOURCE=both`.

GH Pages can point `?api=` at a local server with CORS
(`MAILROOM_CORS_ORIGINS`).

**mailroom-reloaded:** its `mailroom.document` / `mailroom.node.*` spans are
mapped by `RELOADED_NODE_STAGES` (`pipeline_schema.py`) and the root's
`mailroom.*` attributes (`PhoenixSource._reloaded_io`). New node or status in
that pipeline -> update both maps and `tests/fake_phoenix.make_reloaded_trace`.

## Boundaries

| Do | Don't |
| --- | --- |
| Use for local OTEL debugging next to Langfuse | Claim Phoenix feeds production The-Mailroom by default |
| Keep `MAILROOM_SOURCE=langfuse` for family demos | Fabricate Phoenix rows in tests — use fakes or skip |
| Install `arize-phoenix-client` only when this source is on | Require Phoenix in default pytest |

Sandbox compose profile `phoenix` (`:6006`) is started from
**local-mailroom-sandbox**, not from this repo.

## Related

- Default source: [langfuse](../langfuse/SKILL.md)
- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
- Env: `.env.example` (GH Pages edition knobs)
