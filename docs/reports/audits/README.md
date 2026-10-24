<div align="center">

# 📊 Audit Reports

**Baseline audits and structural analysis for the Digital-Mailroom monorepo.**

</div>

---

## Reports

### Corpus baselines (mailroom-corpus lineage)

| Report | Description |
|:---|:---|
| [`docclass_merged_baseline.md`](docclass_merged_baseline.md) / [`.json`](docclass_merged_baseline.json) | Canonical baseline audit for the docclass-merged corpus |
| [`docclass_coverage_matrix.md`](docclass_coverage_matrix.md) / [`.json`](docclass_coverage_matrix.json) | Class × subclass coverage matrix (plan §40–§41) |
| [`docclass_expansion_priorities.md`](docclass_expansion_priorities.md) / [`.json`](docclass_expansion_priorities.json) | Expansion priorities (P4, plan §89) |
| [`docclass_p5_surfaces.md`](docclass_p5_surfaces.md) | P5 advanced-evaluation surfaces status |
| [`org_migration_audit.md`](org_migration_audit.md) / [`.json`](org_migration_audit.json) | Org-migration reference audit |

### Hub integration, release and branch audits (2026-10-23, dated snapshots)

| Report | Description |
|:---|:---|
| [`DMR-009-branch-audit.md`](DMR-009-branch-audit.md) / [`manifest`](DMR-009-branch-manifest.json) | Complete remote/local branch and superseded-PR audit |
| [`DMR-091-feeder-reconciliation.md`](DMR-091-feeder-reconciliation.md) / [`manifest`](DMR-091-feeder-manifest.json) | Upstream-first feeder reconciliation (historical snapshot) |
| [`DMR-091-source-main-imports.md`](DMR-091-source-main-imports.md) | Intermediate source-main import evidence |
| [`DMR-091-open-pr-overlap.md`](DMR-091-open-pr-overlap.md) | Open hub PR overlap disposition |
| [`DMR-091-pre-pr162-rollback.md`](DMR-091-pre-pr162-rollback.md) | Pre-#162 recovery snapshot |
| [`DMR-091-nightly-drift-task.md`](DMR-091-nightly-drift-task.md) | Daily source/vendor drift audit task |
| [`DMR-092-v091-rollback.md`](DMR-092-v091-rollback.md) | v0.9.1 pre-#162 rollback release |
| [`DMR-093-feature-preservation.md`](DMR-093-feature-preservation.md) | Enron/claims feeder preservation branches |
| [`APPLY-HUB-064.md`](APPLY-HUB-064.md) | **Historical** HUB-era board update note |

The DMR-091/092/093 reports are point-in-time records written while #162 and
#167 were in flight (both merged 2026-10-23); read them as evidence of that
moment, not as current state.

## Purpose

These audits establish the ground truth baseline for the mailroom-corpus dataset:
- Row counts per doc_type
- Schema validation
- License compliance
- Provenance tracking
- Split distribution

## Usage

```bash
# View the audit
cat docs/reports/audits/docclass_merged_baseline.md

# Machine-readable format
python -c "import json; print(json.load(open('docs/reports/audits/docclass_merged_baseline.json')))"
```

## Related Files

- [`docs/DOCCLASS_CONTRACT.md`](../../DOCCLASS_CONTRACT.md) — Dataset contract
- [`docs/docclass-merged-plan.md`](../../docclass-merged-plan.md) — Strategic plan
- `packages/mailroom-corpus-eda/` — EDA pipeline that generates these audits
