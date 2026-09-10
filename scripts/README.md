<div align="center">

# ⚙️ Monorepo Scripts

**Shared governance, sync, and build scripts for the Digital-Mailroom monorepo.**

</div>

---

## Available Scripts

| Script | Purpose | Usage |
|:---|:---|:---|
| [`board_state.py`](board_state.py) | Parse and validate the governance board | `python scripts/board_state.py status` |
| [`github_labels.py`](github_labels.py) | Label taxonomy audit (CI gate) | `python scripts/github_labels.py audit` |
| [`taxonomy_parity.py`](taxonomy_parity.py) | Doc-class taxonomy drift (CI gate) | `python scripts/taxonomy_parity.py` |
| [`release_chain.py`](release_chain.py) | Hub release chain: changelog ↔ semver tags ↔ hub version (CI gate) | `python scripts/release_chain.py check` |
| [`sync_packages.py`](sync_packages.py) | Reconcile package mirrors (status/pull/push/snapshot) | `python scripts/sync_packages.py status` |

## Package Sync

```bash
python scripts/sync_packages.py status     # show sync status
python scripts/sync_packages.py pull       # pull from all mirrors
python scripts/sync_packages.py push       # push to all mirrors
python scripts/sync_packages.py snapshot   # create snapshot
```

Cursor state is stored in `scripts/packages_sync.json`.

## Related Scripts

| Package | Scripts Location |
|:---|:---|
| `llm-mailroom` | `packages/llm-mailroom/src/scripts/` — pipeline, deployment, evaluation |
| `llm-entity-extraction` | `packages/llm-entity-extraction/scripts/` — eval, reporting, site build |
| `llm-dojo-scoring` | `packages/llm-dojo-scoring/scripts/` — scoring utilities |
| `mailroom-corpus-eda` | `packages/mailroom-corpus-eda/scripts/` — EDA, HF upload, chart generation |
| `claims-data-eda` | `packages/claims-data-eda/scripts/` — CMS DE-SynPUF EDA |
| `Enron-Evaluation-Environment` | `packages/Enron-Evaluation-Environment/scripts/` — Enron EDA |
| `local-mailroom-sandbox` | `packages/local-mailroom-sandbox/scripts/` — sandbox utilities |

## Notes

- Scripts here are governance/sync tools — package-specific scripts live in their respective `scripts/` directories.
- All scripts require the monorepo virtualenv (`uv sync`).
- CI gates run on changes to `governance/`, `scripts/`, or `.github/`.
