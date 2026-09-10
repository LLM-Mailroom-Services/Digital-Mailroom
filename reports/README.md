<div align="center">

# 📊 Monorepo Reports

**Top-level reports, audits, and analysis documents for the Digital-Mailroom monorepo.**

</div>

---

## Structure

| Path | Contents |
|:---|:---|
| [`audits/`](audits/) | Baseline audits and structural analysis |
| [`audits/mailroom_corpus_baseline.md`](audits/mailroom_corpus_baseline.md) | Canonical baseline audit for mailroom-corpus |
| [`audits/mailroom_corpus_baseline.json`](audits/mailroom_corpus_baseline.json) | Machine-readable baseline data |

## Related Reports

| Package | Reports Location |
|:---|:---|
| `llm-entity-extraction` | `packages/llm-entity-extraction/reports/` — experiment logs, evaluations |
| `llm-mailroom` | `packages/llm-mailroom/data/` — HF pilot outputs |
| `claims-data-eda` | `packages/claims-data-eda/reports/` — CMS DE-SynPUF EDA |
| `Enron-Evaluation-Environment` | `packages/Enron-Evaluation-Environment/reports/` — Enron EDA |
| `mailroom-corpus-eda` | `packages/mailroom-corpus-eda/reports/` — corpus EDA, figures, tables |

## Notes

- Heavy assets (screenshots, large PDFs) are pruned per `.gitignore`.
- EDA deliverables in `packages/mailroom-corpus-eda/reports/` are the exception — tracked in full per HUB-008.
- For package-specific reports, see the package's own `reports/` directory.
