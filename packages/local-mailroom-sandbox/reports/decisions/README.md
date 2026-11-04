# Decisions: reports, visualizations and insights

Reports on the **decision-reviewer experiments** (SAND-085, issue #208, run 2026-11-01): the Decisions-API model
`openai/gpt-6-luna-decisions` used as a reviewer of the sorter's class and subclass, and as a gate over specialist
extraction. Cost is priced against one **Qwen 3.7 Flash call on OpenRouter as 1x**.

Open [`decisions-dashboard.html`](decisions-dashboard.html) for every chart with tooltips and table views (light and dark
follow the system setting). Read the reports in order, or start with the summary.

## Reports

| # | Report | Answers |
| --- | --- | --- |
| 1 | [Executive summary](01-executive-summary.md) | The six findings, where the Decisions model wins and loses, decisions the data supports, and **what is established and what is not** |
| 2 | [Cost and effectiveness against a 1x Qwen call](02-cost-and-effectiveness.md) | What a Decisions review costs next to a **measured** Qwen reviewer; what it buys; when the saving disappears |
| 3 | [Classification reviewer experiments](03-classification-reviewer.md) | Accuracy, confidence, cutoffs, the v1 to v3.0.0 question-set loop, routing to people |
| 4 | [Extraction gate experiments](04-extraction-gate.md) | Whether the Decisions model can judge a specialist's extraction (it cannot yet) |
| 5 | [Method, data quality and next measurements](05-method-and-data-quality.md) | How numbers were made, source inconsistencies, limits, what to run next |

## Figures

Each figure is a standalone SVG (theme-aware, hover text on every mark) with a CSV table twin of the same name in `data/`.

| Figure | Shows | Report |
| --- | --- | --- |
| [f01](figures/f01-cost-stack.svg) | Pipelines in multiples of one Qwen agent call | 2 |
| [f02](figures/f02-sensitivity.svg) | The same, under tiered and flat Qwen prices | 2 |
| [f03](figures/f03-qwen-by-class.svg) | Where the Qwen agent bill comes from, by class | 2 |
| [f04](figures/f04-person-load.svg) | Documents needing a person per 1,000, by arm | 2 |
| [f05](figures/f05-latency.svg) | Latency, p50 and p95 | 2 |
| [f06](figures/f06-accuracy.svg) | Class accuracy by run, held-out against train | 3 |
| [f07](figures/f07-wrong-conf.svg) | Share of wrong answers at high confidence | 2, 3 |
| [f08](figures/f08-cutoffs.svg) | Per-class cutoffs across five calibrations | 3 |
| [f09](figures/f09-dumbbell.svg) | Subclass accuracy, question set v1 to v2 | 3 |
| [f10](figures/f10-verdict.svg) | v3.0.0 verdict against what the handoff needed | 3 |
| [f11](figures/f11-human-by-class.svg) | Documents parked for a person, v2 against v3.0.0 | 3 |
| [f12](figures/f12-sorter-errors.svg) | The Qwen sorter's class errors by pattern | 3 |
| [f13](figures/f13-gate-accept.svg) | Extraction gate accept rate against real quality | 4 |
| [f14](figures/f14-gate-auroc.svg) | Gate AUROC per class, pooled and per round | 4 |
| [f15](figures/f15-silent-errors.svg) | Wrong documents routed with no person, per 1,000 | 2 |
| [f16](figures/f16-routing-outcomes.svg) | Routing outcomes of the 3.1.0 reviewer on 1,488 train documents | 1, 3 |
| [f17](figures/f17-sorter-vs-reviewer.svg) | Sorter against reviewer accuracy, primary type and subclass | 3 |

## Layout

```
reports/decisions/
├── README.md                       this index
├── 01-executive-summary.md … 05-method-and-data-quality.md
├── decisions-dashboard.html        all figures, tooltips, table views (no network, no dependencies)
├── figures/f01-… f17-*.svg
├── data/
│   ├── f01-… f17-*.csv             the table view of each figure
│   ├── summary.json                every derived number the reports quote
│   └── palette-validation.txt      dataviz palette validator output (light and dark)
└── build_decisions_report.py       builds figures, CSVs, summary and dashboard from tracked files
```

## Rebuild

```bash
python reports/decisions/build_decisions_report.py           # write figures, data and dashboard
python reports/decisions/build_decisions_report.py --check   # exit 1 if any output is stale
```

The script is stdlib-only and reads: `reports/reviewer-calibration/*.json`, `reports/extraction-gate/*.calibration.json`,
`reports/reviewer-calibration/reviewer-validation-qwen-flash-test.*` (the measured Qwen reviewer), `reports/reviewer-calibration/reviewer-calibration-luna-decisions-v3.1.0-train-half.*` (the 3.1.0 half-train run), `data/handoff/sorter-qwen3.7-flash/*` (per-document Qwen agent tokens, latency, confidence) and the price sheet figures from
`config/api_prices.yaml`. A few numbers exist only in prose reports; the script lists each with its source file. The report text
quotes `data/summary.json`; if the inputs change, rebuild and re-read the prose.

## Sources

`reports/reviewer-calibration/` · `reports/extraction-gate/` · `reports/sorter-handoff/sorter-qwen3.7-flash-audit.md` ·
`config/decisions/LINEAGE.yaml` · `config/api_prices.yaml` · `config/experiments/decision-pilot/README.md` ·
`reports/run-ledger.md` · `CHANGELOG.md`.
