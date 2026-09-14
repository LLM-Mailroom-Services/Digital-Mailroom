---
name: pipeline-schema-sync
description: Keep The-Mailroom topology mirror in sync with llm-mailroom (pipeline_schema.py, trace_interpreter.py, fake_langfuse fixtures, SPAN_STAGE_MAP, DOC_CLASSES, scores). Use when upstream graph, taxonomy, span names, observation types, or judge scores change — the #1 maintenance duty.
---

# Pipeline schema sync

**When:** `llm-mailroom` changes nodes, `taxonomy.yaml`, span names, observation
types, agent roster, doc classes, subclasses, or score names.  
**Always update in one change:** schema + interpreter + tests + CHANGELOG.

## Mirror set

| File | Upstream |
| --- | --- |
| `mailroom_ui/pipeline_schema.py` | `src/graph/routing.py`, `src/config/taxonomy.yaml`, `src/observability/tracing.py` |
| `mailroom_ui/trace_interpreter.py` | span names, metadata/input/output, `type` / v4 `observationType`, score names |
| `tests/fake_langfuse.py` | v2/v3 `make_trace` **and** v4 `make_trace_v4` |

Live override: `MAILROOM_TAXONOMY` → absolute path to the pipeline taxonomy.
Cached at process level — **restart** after edits.

## Breakage map

| Upstream change | Symptom here |
| --- | --- |
| New span / graph id | Envelope sits in `unknown` / INBOX |
| New doc class | Gray default stamp |
| Renamed judge scores | Verdict/quality vanish |
| New env/tag | Filters in `.env` miss runs |
| New observation type | Node hidden or filed as generation |

Do **not** import `llm-dojo-scoring` at runtime; catalogs stay copied constants
(pin documented `@v0.11.0`).

Producer **code** pin (separate from the topology mirror): extra `[pipeline]`
installs dist `mailroom` `@2a212e76a62b` (v0.7.1). Import only through
`mailroom_ui/producer.py` (`pipeline.review_resolve`, `schemas.manifest`).
Never import `api.main`. Bump `MAILROOM_GIT_SHA` and `pyproject.toml` together.

## Related

- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
- Process: `AGENTS.md` (“Sister repo” + “What we mirror”)
- HF catalogs: [huggingface](../huggingface/SKILL.md)
