<div align="center">

# 📁 Monorepo Data Directory

**Shared data assets for the Digital-Mailroom monorepo — manifests, pipelines, and runtime data.**

</div>

---

## What This Directory Contains

This directory holds shared data that spans multiple packages in the monorepo. Package-specific data lives in `packages/<name>/data/`.

### Structure

| Path | Contents | Git |
|:---|:---|:---|
| [`manifests/`](manifests/) | Pipeline manifests, document catalogs, and classification outputs | Tracked (`manifests/extraction_langfuse.jsonl` + READMEs) |
| `pipeline/` | Bin lanes (`inbox/`, `processing/`, `review/`, `classified/`, `failed/`) | Regenerated locally (gitignored) |
| `archive/` | Archived pipeline documents | Regenerated locally (gitignored) |
| `runtime/` | Runtime taxonomy (`taxonomy.yaml`) and similar operator state | Regenerated locally (gitignored) |
| `operator.db` (+ `-shm`/`-wal`) | Local operator SQLite store | Regenerated locally (gitignored via `*.db`) |
| `watcher_heartbeat` | Pipeline watcher liveness file | Regenerated locally (gitignored) |

## Related Data Locations

| Package | Data Directory |
| :--- | :--- |
| `llm-entity-extraction` | `packages/llm-entity-extraction/data/` — CUAD/MAUD/S-1 corpora, ground truth, manifests |
| `llm-mailroom` | `packages/llm-mailroom/data/` — HF pilot outputs |
| `local-mailroom-sandbox` | `packages/local-mailroom-sandbox/data/` — fixtures, runtime data |
| `mailroom-corpus-eda` | `packages/mailroom-corpus-eda/data/` — parquet exports, staging |

## Notes

- Heavy assets (large PDFs, demo screenshots) are pruned per `.gitignore`.
- EDA deliverables in `packages/mailroom-corpus-eda/reports/` are the exception — tracked in full per HUB-008.
- Never commit secrets or API keys to this directory.
