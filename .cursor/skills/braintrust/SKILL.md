---
name: braintrust
description: Opt-in Braintrust observability/eval logging for local-mailroom-sandbox. Use only when BRAINTRUST_API_KEY is set, OBSERVABILITY_PROVIDER=braintrust|auto selects it, or the user explicitly asks for Braintrust experiments — never as the default offline sink.
---

# Braintrust (opt-in hosted)

**When:** Explicit Braintrust request, or `auto` with `BRAINTRUST_API_KEY` and no Langfuse secret.  
**Prefer Langfuse** for local compose + The-Mailroom. Braintrust is a **cloud** escape hatch, not the sandbox default.

## Enable

```bash
# config/.env (never commit secrets)
OBSERVABILITY_PROVIDER=braintrust   # or auto
BRAINTRUST_API_KEY=...
BRAINTRUST_PROJECT=mailroom-sandbox
```

`auto` order: Langfuse → **Braintrust** → Phoenix → none (`mailroom_sandbox.eval.tracing.tracing_backend`).

## Boundaries

| Do | Don't |
| --- | --- |
| Use for hosted experiment comparison when the user opts in | Start Braintrust in default `sandbox up` |
| Keep `reports/experiment_log.jsonl` as the durable local log | Assume The-Mailroom reads Braintrust |
| Disable in pytest (`OBSERVABILITY_PROVIDER=none`) | Put API keys in fixtures or compose YAML |

Sandbox tracing code treats `braintrust` like a non-Langfuse backend: family Langfuse span helpers no-op / skip SDK path when backend ∉ langfuse. Durable scores still go to `reports/` via dojo/experiment log.

## Related

- Default sink: [langfuse](../langfuse/SKILL.md)  
- Router: [sandbox-tool-router](../sandbox-tool-router/SKILL.md)  
- Env template: `config/.env.example`
