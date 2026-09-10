<div align="center">

# 📊 Audit Reports

**Baseline audits and structural analysis for the Digital-Mailroom monorepo.**

</div>

---

## Reports

| Report | Description |
|:---|:---|
| [`docclass_merged_baseline.md`](docclass_merged_baseline.md) | Canonical baseline audit for docclass-merged corpus |
| [`docclass_merged_baseline.json`](docclass_merged_baseline.json) | Machine-readable baseline data |

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
