# AGENTS.md — Agent Operational Guide

**Repository:** claims-data-eda
**Purpose:** Full-corpus EDA of the CMS 2008-2010 DE-SynPUF (Sample 1) and production of a pipeline-ready `insurance_claim` dataset for the llm-mailroom ecosystem.
**Last updated:** 2026-08-23

---

## 🏛️ Governed Repositories (Ecosystem)

This repo is the **insurance-claims data-production node** of a governed
evaluation family under [Exios66](https://github.com/Exios66). Artifacts flow
downstream; nothing flows back without a versioned handoff.

| Repo | Role | Coupling |
| --- | --- | --- |
| [`llm-mailroom`](https://github.com/Exios66/llm-mailroom) | Multi-agent legal-document intake pipeline; owns the doc-class taxonomy incl. **`insurance_claim`** (`InsuranceClaimExtraction` schema + `insurance_claims_specialist`) this repo renders GT against | Upstream taxonomy governor |
| **claims-data-eda** (this repo) | Full-corpus EDA + rendered-EOB dataset production for CMS DE-SynPUF Sample 1 | — |
| [`llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction) | Training/eval environment consuming streamer-dump JSONLs via `build_docclass_merged.py`; Enron feeds it as `correspondence`, this repo as `insurance_claim` | Direct downstream consumer |
| [`Enron-Evaluation-Environment`](https://github.com/Exios66/Enron-Evaluation-Environment) | Sibling correspondence data-production node; structural template for this repo | Sibling node |
| [`atticus-investigation`](https://github.com/Exios66/atticus-investigation) | LegalBench prompt-engineering eval pipeline (OpenRouter × Braintrust) | Adjacent eval environment |

**Sync obligation:** if the GT mapping in `scripts/render_eob.py` drifts from
llm-mailroom's `InsuranceClaimExtraction` schema (see its
`src/agents/insurance_claims_specialist.py`), update both and note it here.

---

## 🚀 First-Time Setup (One Shot)

```bash
git clone https://github.com/Exios66/claims-data-eda.git
cd claims-data-eda

# 1. Acquire the corpus (8 ZIPs ~356 MB; 5 live from CMS, 3 recovered from
#    Wayback Machine -- all sha256-manifested into data/raw/MANIFEST.json)
python scripts/acquire_synpuf.py

# 2. Build the unified index (~11.2M claim events -> gzipped JSONL)
python scripts/build_corpus_index.py

# 3. Run the full EDA -> reports/eda/{report.md,findings.md,figures/,corpus_stats.json}
python scripts/eda/explore_cms.py

# 4. Build the pipeline-ready stratified sample
python scripts/build_pipeline_dump.py --n 400

# 5. Human review artifact + validation
python scripts/spot_check.py
pytest tests/ -v          # 30 tests, no corpus data needed
```

All data lives under gitignored `data/`. Disk budget: raw CSVs ~4.7 GB,
index.gz ~0.7 GB. The extracted CSVs are regenerable from the kept ZIPs at any
time (`extract()` re-materializes missing files).

## ⚠️ Provenance & Environment Notes (agents, read before rerunning)

* **Three archives are Wayback-recovered**: DE-SynPUF Sample-1's
  `2010_Beneficiary_Summary`, `Carrier_Claims_1A/1B` and `Prescription_Drug_Events`
  are no longer hosted by CMS. `acquire_synpuf.py` pins exact capture timestamps;
  do not "fix" those URLs back to cms.gov.
* **Disk-constrained machine**: keep an eye on `df -h /`; delete
  `data/raw/*.csv` (not the ZIPs) when space is tight.
* `.env` holds HF_TOKEN (gitignored). Never commit tokens.

## Repo Structure (Quick Reference)

```
scripts/
├── acquire_synpuf.py        ← download + verify + extract (idempotent, resumable)
├── build_corpus_index.py    ← normalize 8 CSVs → data/cms/{beneficiaries,index}.jsonl.gz
│                              (shared helpers: jopen, compact, bene_snapshot)
├── render_eob.py            ← deterministic EOB renderer + GT builder (verbatim contract)
├── build_pipeline_dump.py   ← stratified reservoir sample → data/cms/pipeline.jsonl
│                              (coverage contract: every non-empty stratum ≥1 row)
├── spot_check.py            ← human review CSV w/ verbatim audit
├── publish_hf_dataset.py    ← HF Hub publisher (schema guard + VERIFY: GREEN)
└── eda/
    └── explore_cms.py       ← full-corpus EDA → reports/eda/
reports/
├── eda/                     ← committed EDA output (report/findings/stats/figures)
└── pipeline/README.md       ← wiring into llm-mailroom / llm-entity-extraction
docs/examples/               ← real insurance_claim corpus documents as PDF samples
                              (manifest + README; regenerate via render_samples.py --input <hub jsonl>)
scripts/render_samples.py    ← deterministic zero-dep text→PDF sampler feeding docs/examples
tests/test_pipeline.py       ← 30 unit tests (normalizers, renderer, GT schema, dump shape)
tests/test_examples.py       ← sample-artifact + PDF-writer tests (no network)
```

## Key Design Decisions

* **Carrier rows are claim-level** with up to 13 embedded line slots
  (wide format); payments exist only per line, so `payment_amt` is the line sum
  and lines ride along as structured sub-records.
* **Null-dropped compact index + gzip level 1**: 11.2M events stay under ~700 MB;
  beneficiary demographics join at render time, not per-row.
* **Verbatim GT contract**: every scalar ground-truth value appears literally in
  the rendered document text — asserted by `render()`, audited by
  `spot_check.csv`, tested in pytest.
* **Honest caveats baked in**: no denial ground truth exists (SynPUF = paid FFS
  claims only); `adjuster` always null; single line of business (`health`);
  fully synthetic data = pipeline substrate, not epidemiology.
