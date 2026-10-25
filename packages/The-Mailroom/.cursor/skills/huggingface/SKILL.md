---
name: huggingface
description: Hugging Face usage for The-Mailroom eval/pilot scripts (mailroom-dataset GT, HF_TOKEN, run_production_pilot, eval_pipeline). Use for Hub datasets and copied dojo catalogs; prefer offline pytest fixtures; offline scoring uses the canonical Dojo eval extra; keep display imports light and start a live Qwen/Hub pilot only when explicitly requested.
---

# Hugging Face (eval + catalogs, not serving)

**When:** `scripts/eval_pipeline.py`, `scripts/run_production_pilot.py`,
`scripts/sync_pilot_dataset.py`, `HF_TOKEN`,
`Lucius-Morningstar/mailroom-dataset`, or Hub subclass catalogs.  
**This visualizer does not download weights or serve models.** Serving is
[ollama](../ollama/SKILL.md) / [modal](../modal/SKILL.md) in sister repos.

## Authoritative corpus

Pin **`Lucius-Morningstar/mailroom-dataset`** (corrected GT tip —
`MAILROOM_HF_REVISION`, default in `mailroom_ui/hf_corpus.py`) for labels
and pilot intake. Prefer that over the smaller `docclass-pilot` examples
pack. Hub rows go through the datasets-server REST API (revision query)
so eval / sync stay light — no full `load_dataset` on the visualizer path.

| Env | Role |
| --- | --- |
| `HF_TOKEN` | Hub auth |
| `MAILROOM_HF_DATASET` | default `Lucius-Morningstar/mailroom-dataset` |
| `MAILROOM_HF_REVISION` | corrected GT commit pin |
| `MAILROOM_HF_CONFIG` | `ground_truth` |
| `HF_HOME` / `HF_HUB_CACHE` | producer volume cache (Railway) |

## Offline first

| Asset | Where | Network? |
| --- | --- | --- |
| Pytest traces | `tests/fake_langfuse.py` | No |
| Copied Hub subclass / CUAD keys | `mailroom_ui/pipeline_schema.py` | No |
| Dojo scoring pin | optional `[eval]` (`@4740d768`, Dojo v0.24.2) | Offline engine; live display stays light |
| Live `mailroom-dataset` eval | `scripts/eval_pipeline.py` | **Yes** (explicit) |
| Sync merged → Langfuse dataset | `scripts/sync_pilot_dataset.py` | **Yes** (explicit) |
| Live Qwen 3.7-Flash pilot | `scripts/run_production_pilot.py --real` | **Yes** (explicit) |

```bash
# needs sibling llm-mailroom
python scripts/run_production_pilot.py --check
python scripts/eval_pipeline.py --session pilot-hf-...
python scripts/sync_pilot_dataset.py --dry-run   # corrected merged by default
# --real only when the user asked for a live Hub/Qwen run
```

`.env`: `HF_TOKEN`, `MAILROOM_HF_*`, and `MAILROOM_PIPELINE_ROOT` are for
those scripts / the producer, not the Langfuse display path.

**Live Observatory on a Space** is a different job — Docker
`mailroom-hosted` via `scripts/publish_space.py` (see
[observatory](../observatory/SKILL.md)). Do not add a Gradio/FastAPI
Space SDK or a Hub model server here.

## Boundaries

- Offline evaluation delegates scoring to Dojo through `[eval]`; do not implement competing local scorers. Keep live display imports light and topology catalogs copied.
- **Do not** start a live Langfuse/HF/Qwen pilot unless explicitly requested.
- Default pytest: no Hub calls.
- For Hub CLI depth, follow the Cursor **hf-cli** plugin skill; this skill stays
  visualizer-scoped.

## Related

- Schema mirror: [pipeline-schema-sync](../pipeline-schema-sync/SKILL.md)
- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
- Pin: README constellation table (`llm-dojo-scoring` `@4740d768` (Dojo v0.24.2);
  llm-mailroom dist `mailroom` `@60cd5fad0c7a616ec575857841bb9897b9e8c3ed` / 0.8.1 (reviewed source adoption) via extra `[pipeline]`)
