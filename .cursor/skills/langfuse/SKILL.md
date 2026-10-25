---
name: langfuse
description: Configure and read Langfuse as The-Mailroom's default document-display source (SDK 2.50–4.x, v4 camelCase). Use when setting LANGFUSE_HOST/keys, MAILROOM_SOURCE=langfuse, document-pipeline traces, scores, sessions, seed_demo, or debugging the floor against US-cloud project llm-mailroom.
---

# Langfuse (default document display)

**When:** Any live floor, Observatory, TUI, `/api/traces`, seed-into-Langfuse, or
`MAILROOM_SOURCE=langfuse` (default).  
**Prefer over:** Phoenix (optional extra source) and Braintrust (not a display
source). This viewer **reads**; it never constructs a write client or flushes.

## Contract

| Knob | Value |
| --- | --- |
| Project | US cloud `llm-mailroom` (producer writes; we read) |
| Host env | **`LANGFUSE_HOST`** (`LANGFUSE_BASE_URL` accepted as an alias) |
| Default host | `https://us.cloud.langfuse.com` |
| Keys | `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` |
| Root trace | `document-pipeline` (**CHAIN**) |
| Tags | `mailroom`, `<env>`, `run-<n>`, optional `source-<corpus>` |
| Scores | `mailroom-pipeline-judge`, `mailroom-pipeline-quality`, confidences |

`.env`:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
MAILROOM_SOURCE=langfuse
```

Sandbox compose uses `http://localhost:3000` + `pk-lf-sandbox` /
`sk-lf-sandbox` — same contract, local host.

## Family rules (do not break)

1. One document → one root `document-pipeline` chain; deterministic id from filename.
2. Child names stay verb-first (`classify-document`, …) **and** graph ids
   (`retry_classify`, `judge_verify`, …) both map in `SPAN_STAGE_MAP`.
3. Observation types: v2/v3 `type` **and** v4 `observationType`. New fields go
   through `_both` / `_pick` in `trace_interpreter.py`.
4. Tests use `tests/fake_langfuse.py` (`make_trace` + `make_trace_v4`). Never
   hit real Langfuse in pytest.
5. Unreachable Langfuse → **MAILROOM CLOSED**, not a JSON fixture floor.
6. `scripts/seed_demo.py` writes demo traces **into** Langfuse (`env=demo`).
   Demo envelopes in the pixel `?demo=1` path are opt-in when the source is down.

## Adapter

- `mailroom_ui/langfuse_source.py` — `list`/`get` traces, observations, scores, sessions; `TTLCache`; `force_refresh` for in-flight.
- List/obs TTL follows `MAILROOM_POLL_INTERVAL`.
- This process does **not** set `LANGFUSE_FLUSH_*` (producer knobs).

## Related

- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
- Optional extra source: [apache-phoenix](../apache-phoenix/SKILL.md)
- Live poll: [live-floor](../live-floor/SKILL.md)
- Process: `AGENTS.md` (“Langfuse is ALWAYS the source of visualization”)
