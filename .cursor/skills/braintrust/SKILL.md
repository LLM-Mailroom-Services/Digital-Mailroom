---
name: braintrust
description: Braintrust is not a The-Mailroom display source. Use this skill when the user mentions Braintrust, BRAINTRUST_API_KEY, or hosted experiments — redirect to Langfuse (and optional Phoenix); never add a Braintrust adapter or default offline sink here.
---

# Braintrust (not a display source)

**When:** Someone asks to “log to Braintrust”, set `BRAINTRUST_API_KEY`, or
mirror sandbox `OBSERVABILITY_PROVIDER=braintrust` inside this visualizer.  
**Prefer Langfuse.** The-Mailroom has no Braintrust client and must not grow one
unless the user explicitly requests a new `MAILROOM_SOURCE` value **and** a
read-only adapter with tests.

## Why it stays out

- Document display is Langfuse-only (optional Phoenix union).
- Braintrust is a **cloud** experiment sink used by
  [local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox)
  as an opt-in escape hatch — never the sandbox default, and never this UI.
- Adding it here would invent a second truth for envelopes.

## If the user opts in later

1. Do not replace Langfuse.
2. New source must implement the same `get_run` / `list_recent_runs` surface
   (`mailroom_ui/sources.py`) with fakes in `tests/` — no live API in pytest.
3. Document `MAILROOM_SOURCE` and keep browser keys off the client.

Until then: point hosted-eval work at the sandbox Braintrust skill / `reports/`.

## Related

- Default source: [langfuse](../langfuse/SKILL.md)
- Sandbox companion: that repo’s `.cursor/skills/braintrust/SKILL.md`
- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
