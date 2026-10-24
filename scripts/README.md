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
| [`sync_packages.py`](sync_packages.py) | Import committed standalone sources (status/pull/snapshot; `push` is legacy and forbidden for package delivery) | `python scripts/sync_packages.py status` |
| [`sync_vendor.py`](sync_vendor.py) | Refresh sandbox vendor snapshots (byte-identical workspace packages) | `python scripts/sync_vendor.py` (`--check` for CI drift gate) |
| [`release_notes.py`](release_notes.py) | Render the GitHub Release body from the changelog section | `python scripts/release_notes.py X.Y.Z` |
| [`audit_references.py`](audit_references.py) | Org-migration reference audit (CI gate) | `python scripts/audit_references.py` |
| [`deploy_gh_pages.py`](deploy_gh_pages.py) | Deploy core corpus EDA reports to its standalone Pages site | `python scripts/deploy_gh_pages.py --package mailroom-corpus-eda` |
| [`apply_hub064_board.py`](archive/apply_hub064_board.py) | **Archived (historical)** — HUB-era one-shot, do not run on the DMR board | see `docs/reports/audits/APPLY-HUB-064.md` |

## Package Sync

```bash
python scripts/sync_packages.py status     # show sync status
python scripts/sync_packages.py pull --package <name> --squash   # import committed standalone source
python scripts/sync_packages.py snapshot   # content-verified cursor re-baseline
```

Cursor state for the five active core packages is stored in `scripts/packages_sync.json`. Implement package changes in the standalone source first, then import committed changes; outbound commands are historical and forbidden for package delivery.

## Tests

Hermetic unit tests for the governance/sync scripts:

```bash
python3 -m unittest discover scripts/tests
```

## Related Scripts

| Package | Scripts Location |
|:---|:---|
| `llm-mailroom` | `packages/llm-mailroom/src/scripts/` — pipeline, deployment, evaluation |
| `llm-dojo-scoring` | `packages/llm-dojo-scoring/scripts/` — scoring utilities |
| `mailroom-corpus-eda` | `packages/mailroom-corpus-eda/scripts/` — EDA, HF upload, chart generation |
| `claims-data-eda` (external/preserved) | [Preserved scripts](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/claims-data-eda/packages/claims-data-eda/scripts) — standalone feed |
| `Enron-Evaluation-Environment` (external/preserved) | [Preserved scripts](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/enron-evaluation-environment/packages/Enron-Evaluation-Environment/scripts) — standalone feed |
| `local-mailroom-sandbox` | `packages/local-mailroom-sandbox/scripts/` — sandbox utilities |

## Notes

- Scripts here are governance/sync tools — package-specific scripts live in their respective `scripts/` directories.
- All scripts require the monorepo virtualenv (`uv sync`).
- CI gates run on changes to `governance/`, `scripts/`, or `.github/`.

DMR-093 retires the feeder-only hub chart generator from main. Its original
implementation remains in the [complete preserved checkout](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/59c879d9fb4480084e53137e2e9fb25650933944/scripts/gen_interactive_charts.py).
The shared Pages helper selects only core `mailroom-corpus-eda`; unsupported
targets fail before writes. This does not unpublish either external feeder site.
Use a separate preservation-branch checkout for the historical workflow.
