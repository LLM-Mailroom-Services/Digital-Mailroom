---
name: ollama
description: Local Ollama inference is not part of The-Mailroom. Use this skill when the user asks to run qwen3/llama locally, SANDBOX_PROFILE=ollama, or OLLAMA_BASE_URL from this visualizer checkout — redirect to local-mailroom-sandbox / llm-mailroom; do not add an Ollama client here.
---

# Ollama (not served here)

**When:** Local LLM, `ollama pull`, `qwen3:8b`, or “run the pipeline offline
from The-Mailroom”.  
**Prefer** [local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox)
`.cursor/skills/ollama` (default sandbox provider) or `llm-mailroom` for the
graph. This repo is a **read-only visualizer** on `:8001`.

## What to do instead

```bash
# in local-mailroom-sandbox
sandbox up                 # langfuse + ollama
sandbox pull-models
sandbox health
# then point The-Mailroom at that Langfuse:
# LANGFUSE_HOST=http://localhost:3000
# LANGFUSE_PUBLIC_KEY=pk-lf-sandbox
# LANGFUSE_SECRET_KEY=sk-lf-sandbox
mailroom-web               # still this repo — display only
```

OpenRouter (`OPENROUTER_API_KEY` in `.env.example`) is only for
`scripts/run_production_pilot.py --real` against the **sibling pipeline**, not
for the pixel floor.

## Boundaries

- Do not add `ollama` / `httpx` chat clients under `mailroom_ui/` or `server/`.
- Do not default pytest to a live model.
- Do not confuse `MAILROOM_API_URL` (this visualizer, `:8001`) with Ollama
  `:11434`.

## Related

- Remote GPU: [modal](../modal/SKILL.md)
- Tracing still: [langfuse](../langfuse/SKILL.md)
- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
