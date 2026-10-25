<div align="center">

# ⚙️ The-Mailroom Scripts

**Utility scripts for the The-Mailroom visualizer package.**

</div>

---

## Functional index

| Group | Script | Purpose |
| :--- | :--- | :--- |
| **Demo / seed** | `demo_pilot_run.py` | Stagger a fake Langfuse pilot so envelopes travel the conveyor |
| | `demo_review_tray.py` | Working REVIEW-tray demo (FakeClient Langfuse + in-process producer) |
| | `demo_v030_cast.py` | Static FakeClient floor for the v0.3.0 release stills + desk recordings |
| | `seed_demo.py` | Seed demo traces INTO Langfuse (`env=demo`) for UI/UX play-testing |
| **Live pipeline** | `eval_pipeline.py` | Score Langfuse `document-pipeline` traces against HF docclass ground truth |
| | `run_production_pilot.py` | Orchestrate a production Langfuse-traced HF subset pilot |
| **Export / publish** | `export_corpus_catalog.py` | Slim catalog of `mailroom-dataset` for the terminal site (`site/data/corpus.json`) |
| | `export_snapshot.py` | Static JSON snapshot of trace sources for GitHub Pages |
| | `publish_pages.sh` | Build `site/` + push the static SPA to `gh-pages:/docs` (also `--status`) |
| | `publish_space.py` | Publish the live Observatory to a Hugging Face Docker Space |
| **Sync** | `sync_pilot_dataset.py` | Mirror `mailroom-dataset` INTO a Langfuse dataset |
| | `sync_prompts.py` | Push the vendored agent prompts into Langfuse Prompt Management |
| **Release / ops** | `release.py` | Semver release workflow |
| | `setup_operator.sh` | One-time operator-desk setup (bins + migrate, no npm) |
| | `render_tui_shots.py` | Render TUI frames against a running Mailroom API for README screenshots |

## Usage notes

```bash
cd packages/The-Mailroom

# Publish the Observatory to HF Spaces (offline check first)
python scripts/publish_space.py --check
python scripts/publish_space.py --repo <user>/mailroom-observatory

# Snapshot + deploy the static site
scripts/publish_pages.sh             # build site/ + push gh-pages:/docs
scripts/publish_pages.sh --status    # exit 1 = stale vs main
```

## Related Files

- `hosted/` — Observatory (hosted edition)
- `web/` — Pixel console
- `server/` — Backend server
