# Archived Scripts

**Status: FROZEN / PROVENANCE-ONLY.** Everything under this tree is
preserved for lineage and reproducibility — none of it is part of the live
workflow.

| Bucket | Contents | Status |
|:---|:---|:---|
| `sync_edge_suites.py` | Langfuse dataset sync for generated edge suites (`edge-<agent>` datasets) | Superseded inline — the bench gate documents the manual Langfuse sync step; nothing in the live workflow references this script |

## Why archive instead of delete

- `sync_edge_suites.py` automated a one-off operation: pushing generated
  edge suites into The-Mailroom's Langfuse environment as datasets. The
  bench gate (`scripts/durability_gate.sh`) documents the same sync as an
  inline manual step, and no live pipeline, test, skill, or CI workflow
  invokes this script — the reference audit found only historical
  governance-board mentions.
- The generation side (`gen_edge_cases.py`) is LIVE and stays in
  `scripts/`; only the standalone Langfuse sync script is retired. The
  `--dataset <agent>` filtering contract is preserved here if the sync is
  ever needed again.

## Audit trail

Archived 2026-09-14 in the scripts organization pass (mailroom-issues #17
monorepo sweep). Reference audit: no live consumers.

## Running archived scripts

```bash
.venv/bin/python scripts/archive/sync_edge_suites.py \
    --env-file /path/to/The-Mailroom/.env
```