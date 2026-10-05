# Reports

Run reports, serving exports and the offline experiment log (JSONL + markdown written by `sandbox eval` / `sandbox matrix`).

## Reports hub

`dashboard/mailroom-reports.html` presents specialist, serving, hosted-API and ModernBERT results from this repo,
[eval-environment](https://github.com/LLM-Mailroom-Services/eval-environment) and
[mailroom-ml](https://github.com/LLM-Mailroom-Services/mailroom-ml). Every figure is read from a tracked file and
cross-checked; documented source defects are listed on its Data quality tab.

```bash
python reports/dashboard/build_hub.py sync      # re-pin eval-environment + mailroom-ml (sibling checkouts)
python reports/dashboard/build_hub.py           # rebuild the page
python reports/dashboard/build_hub.py --check   # fail if the page, data or snapshot is stale
```

| file | role |
| --- | --- |
| `dashboard/build_hub.py` | CLI: sync, build, check |
| `dashboard/hub_extract.py` | SAND-032, eval-environment and mailroom-ml extractors + cross-checks |
| `dashboard/legacy_runs.py` | 16–27 Sep specialist runs (pre-SAND-032) |
| `dashboard/external_snapshot.json` | pinned figures + provenance from the two sibling repos |
| `dashboard/hub.template.html` → `mailroom-reports.html` | page template → built page (`hub_data.json` is its data) |

Tabs: Overview · Specialists · Serving (Modal L4) · API models · **Modal vs API** (cost vs quality per
specialist task and for the sorter, both routes on one axis) · Classifier (ModernBERT) · ML diagnostics · Data quality.

## Cross-repo reports (mailroom-issues)

`dashboard/export_hub_reports.py` turns the hub data into the cost comparison, the master status report and the
Modal + vLLM GPU economics report (`dashboard/gpu_report.py`) published in
`LLM-Mailroom-Services/mailroom-issues` under `reports/` (markdown + SVG only; that repo holds no code). The GPU
report reads the hub's `fleet` section: every `serving/SAND-32/sand032-*.serving.json` cross-checked against its run report.
`dashboard/report_audit.json` records the figure/link audit the master report cites.
`dashboard/breakeven.py` is the single Modal-vs-API break-even calculation (per document: warm-fleet and cold-batch
break-evens, the optimal measured deployment) that the cost comparison, the GPU report and the site all quote.

The same run also renders the reports as a static GitHub Pages site, `dashboard/pages_site.py` → `--site`
(default `<out>/../docs`, i.e. `mailroom-issues/docs/`): `index.html` plus `reports/*.html`, with every figure inlined as
SVG, no JavaScript and no external requests. mailroom-issues serves it by deploying from branch `main` `/docs`
(https://llm-mailroom-services.github.io/mailroom-issues/). `--check` covers the site too.

`dashboard/export_pngs.py` renders every figure to a 2× PNG under `mailroom-issues/reports/viz/` for slides; its
`MANIFEST.json` records each source SVG's SHA-256, so `--check` detects stale PNGs without a browser
(`CHROMIUM_PATH` selects a pre-installed Chromium when writing).

```bash
python reports/dashboard/export_hub_reports.py --out ../mailroom-issues/reports           # write reports + docs/ site
python reports/dashboard/export_pngs.py --reports ../mailroom-issues/reports               # write reports/viz/*.png
python reports/dashboard/export_hub_reports.py --out ../mailroom-issues/reports --check   # exit 1 if either is stale
```

## SAND-032 figures

`SAND-32/<class>/figures/*.svg` and `serving/figures/*.svg` are written by `scripts/sand032/report.py`
(needs the machine-local `data/runtime/` run artifacts). To apply a chart-kit (`scripts/sand032/viz.py`)
layout change to the committed figures without re-running GPU jobs:

```bash
python scripts/sand032/rerender.py           # re-lay every figure from the data embedded in it
python scripts/sand032/rerender.py --check   # exit 1 if any figure is stale
```

`rerender.py` refuses to write if a figure's data (every mark's hover title) would change.
