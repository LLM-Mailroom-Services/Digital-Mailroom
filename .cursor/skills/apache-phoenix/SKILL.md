---
name: apache-phoenix
description: Optional Apache Phoenix / Arize Phoenix OTEL sidecar for local-mailroom-sandbox. Use when enabling compose profile phoenix, PHOENIX_ENDPOINT, or Arize UI debugging — not as the default The-Mailroom sink (prefer Langfuse).
---

# Apache Phoenix (optional sidecar)

**When:** User asks for Phoenix/Arize, OTEL trace UI on `:6006`, or `OBSERVABILITY_PROVIDER=phoenix`.  
**Prefer Langfuse** whenever The-Mailroom or the family `document-pipeline` contract is required — Phoenix spans are **not** plottable there.

## Enable

```bash
sandbox up --compose-profile phoenix
# UI http://localhost:6006
```

Env:

```bash
OBSERVABILITY_PROVIDER=phoenix   # or auto without Langfuse/Braintrust keys
PHOENIX_TRACING=enabled
PHOENIX_ENDPOINT=http://localhost:6006/v1/traces
PHOENIX_PROJECT=mailroom-sandbox
```

Compose service: `arizephoenix/phoenix:latest`, profile `phoenix`, port `6006`, volume `phoenix_data`.

`sandbox health` probes Phoenix `/healthz` alongside the LLM provider and Langfuse.

## Boundaries

| Do | Don't |
| --- | --- |
| Run as an **extra** compose profile next to Langfuse when comparing UIs | Replace Langfuse for mailroom family demos |
| Point Jupyter at `http://phoenix:6006/v1/traces` on the compose network | Claim Phoenix feeds The-Mailroom |
| Set `PHOENIX_TRACING=disabled` in unit tests | Require GPU |

## Related

- Default sink: [langfuse](../langfuse/SKILL.md)  
- Router: [sandbox-tool-router](../sandbox-tool-router/SKILL.md)  
- Docs: `docs/tracing.md`
