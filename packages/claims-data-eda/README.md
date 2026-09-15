<div align="center">

# 🏥 claims-data-eda

**Full-corpus EDA of the CMS 2008–2010 DE-SynPUF (Sample 1) and production of a
pipeline-ready `insurance_claim` dataset for the llm-mailroom ecosystem.**

Every Medicare claim event rendered as a plain-text **EOB document** with
ground-truth extraction fields aligned to the mailroom's
`InsuranceClaimExtraction` schema.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/pytest-30%2F30_passing-brightgreen?logo=githubactions&logoColor=white)](tests/test_pipeline.py)
[![Status](https://img.shields.io/badge/status-production-success)](reports/eda/final_report.md)
[![Last Commit](https://img.shields.io/github/last-commit/Exios66/claims-data-eda?logo=github&label=updated)](https://github.com/Exios66/claims-data-eda/commits/main)
[![Repo Size](https://img.shields.io/github/repo-size/Exios66/claims-data-eda?logo=github)](https://github.com/Exios66/claims-data-eda)

[![Corpus](https://img.shields.io/badge/corpus-11.15M_claim_events-2563eb)](reports/eda/report.md)
[![Beneficiaries](https://img.shields.io/badge/beneficiaries-116%2C352-059669)](reports/eda/report.md)
[![🤗 Dataset](https://img.shields.io/badge/%F0%9F%A4%97_Dataset-cms--desynpuf--insurance--claims-fbe425?logo=huggingface&logoColor=black)](https://huggingface.co/datasets/Lucius-Morningstar/cms-desynpuf-insurance-claims)
[![License](https://img.shields.io/badge/license-CMS_Public_Use-lightgrey)](#-provenance--license)
[![Sibling Node](https://img.shields.io/badge/sibling-Enron--Evaluation--Environment-8b5cf6)](https://github.com/Exios66/Enron-Evaluation-Environment)

<img src="reports/eda/figures/01_corpus_overview.png" alt="Corpus overview — 11.15M claim events across inpatient, outpatient, carrier and PDE" width="720"/>

</div>

---

## 📊 Corpus at a Glance

| File type | Events | Unique IDs | Σ paid | p50 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 🏨 Inpatient | 66,773 | 66,705 | $639M | $7.0K | $57.0K |
| 🏥 Outpatient | 790,790 | 779,815 | $225M | $80 | $3.3K |
| 🩺 Carrier (physician) | 4,741,335 | 4,741,335 | $415M | $60 | $660 |
| 💊 PDE (drug fills) | 5,552,421 | 5,552,421 | $341M | $20 | $570 |
| **Total** | **11,151,319** | 11,140,276 | **~$1.62B** | — | — |

plus **116,352 beneficiaries** merged across three yearly Beneficiary Summary
files — with **perfect linkage** (zero orphan events across all 11.15M rows).

> **Provenance note.** Five archives download live from CMS; **three are no
> longer hosted by cms.gov** (2010 Beneficiary Summary, Carrier Claims A/B,
> Prescription Drug Events) and were recovered from Internet Archive Wayback
> Machine captures — every ZIP is sha256-manifested in
> `data/raw/MANIFEST.json`.

## 🌐 Governed Repository Ecosystem

This repo is the **insurance-claims data-production node** of a governed
evaluation family under [@Exios66](https://github.com/Exios66). Artifacts flow
downstream; nothing flows back without a versioned handoff.

| Repository | Role | Coupling |
| --- | --- | --- |
| [`llm-mailroom`](https://github.com/Exios66/llm-mailroom) | Multi-agent legal-document intake pipeline; owns the doc-class taxonomy incl. **`insurance_claim`** (`InsuranceClaimExtraction` + `insurance_claims_specialist`) this repo renders GT against | ⬆️ Upstream taxonomy governor |
| **claims-data-eda** (this repo) | Full-corpus EDA + rendered-EOB dataset production for CMS DE-SynPUF Sample 1 | — |
| [`llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction) | Training/eval environment consuming streamer-dump JSONLs via `build_docclass_merged.py` — Enron feeds `correspondence`, this repo feeds `insurance_claim` | ⬇️ Direct downstream consumer |
| [`Enron-Evaluation-Environment`](https://github.com/Exios66/Enron-Evaluation-Environment) | Sibling **correspondence** data-production node (CMU Enron corpus); structural template for this repo | ↔️ Sibling node |
| [`atticus-investigation`](https://github.com/Exios66/atticus-investigation) | LegalBench prompt-engineering eval pipeline (OpenRouter × Braintrust) | ↔️ Adjacent eval environment |

Handoff contract & wiring commands: [`reports/pipeline/README.md`](reports/pipeline/README.md).

## 🔍 Headline Findings

<table>
<tr><td width="50%">

### Heavy-tailed costs

Inpatient payments span **$3K (p10) → $57K (p99)**. Sampling must bucket on
**log-cost** or the tail vanishes from eval sets — the stratified sampler
enforces a **≥15% high-cost floor** per claim type.

</td><td width="50%">

### Concentration everywhere

Top 1% of carrier providers bill **23.9%** of physician lines; top 20% of
patients generate **42.4%** of all events. Provider NPIs are strong,
skewed entity-extraction targets.

</td></tr>
<tr><td width="50%">

### Stationary synthetics

Demographics, chronic-condition prevalence (ischemic heart disease **36%**,
diabetes **28%**, heart failure **25%**) and monthly volumes barely move across
2008–2010 — the fingerprint of template-driven generation.

</td><td width="50%">

### Clean GT anchors — with caveats

Empty-diagnosis rates **≤0.7%**; every event joins its beneficiary record.
But SynPUF contains only **adjudicated-paid** claims → no denial ground truth
exists, and procedure slots mix true ICD-9 procedures with diagnosis codes
(generator artifact, flagged in the report).

</td></tr>
</table>

<p align="center">
  <img src="reports/eda/figures/06_cost_distributions.png" alt="Per-event payment distributions" width="49%"/>
  <img src="reports/eda/figures/10_provider_concentration.png" alt="Carrier provider concentration Lorenz curve" width="49%"/>
</p>
<p align="center">
  <img src="reports/eda/figures/04_chronic_conditions.png" alt="Chronic condition prevalence" width="49%"/>
  <img src="reports/eda/figures/05_comorbidity_matrix.png" alt="Comorbidity co-occurrence matrix" width="49%"/>
</p>

<details>
<summary><b>🖼️ Full figure gallery (12 charts)</b></summary>

| # | Figure | Insight |
| --- | --- | --- |
| 01 | [Corpus overview](reports/eda/figures/01_corpus_overview.png) | Event rows vs unique claim IDs per type |
| 02 | [Monthly volume](reports/eda/figures/02_monthly_volume.png) | Stationary seasonality; 2010 tapers mid-year |
| 03 | [Demographics](reports/eda/figures/03_demographics.png) | Age bands, race mix, top states |
| 04 | [Chronic conditions](reports/eda/figures/04_chronic_conditions.png) | 2008 vs 2010 prevalence — flat |
| 05 | [Comorbidity matrix](reports/eda/figures/05_comorbidity_matrix.png) | Co-occurrence (% of beneficiaries) |
| 06 | [Cost distributions](reports/eda/figures/06_cost_distributions.png) | Log-scale payment histograms |
| 07 | [Top diagnoses](reports/eda/figures/07_top_diagnoses.png) | ICD-9 pareto heads per type |
| 08 | [Procedures & HCPCS](reports/eda/figures/08_procedures_hcpcs.png) | IP procedures, OP/carrier HCPCS |
| 09 | [Top NDC drugs](reports/eda/figures/09_top_drugs_ndc.png) | PDE fills per product |
| 10 | [Provider concentration](reports/eda/figures/10_provider_concentration.png) | Lorenz curve + activity histogram |
| 11 | [Utilization](reports/eda/figures/11_utilization.png) | Claims-per-beneficiary cohorts + Lorenz |
| 12 | [Annual reimbursements](reports/eda/figures/12_annual_reimbursements.png) | Part A/B rollups per beneficiary |

</details>

Full analysis: **[`reports/eda/report.md`](reports/eda/report.md)** · condensed: **[`reports/eda/findings.md`](reports/eda/findings.md)**

## 🚀 Quick Start

```bash
git clone https://github.com/Exios66/claims-data-eda.git
cd claims-data-eda

# 1️⃣ Acquire the corpus (8 ZIPs ~356 MB — idempotent, resumable, sha256-manifested)
python scripts/acquire_synpuf.py

# 2️⃣ Build the unified index (~11.2M claim events → gzipped JSONL, ~700 MB)
python scripts/build_corpus_index.py

# 3️⃣ Run the full EDA → reports/eda/{report.md,findings.md,corpus_stats.json,figures/}
python scripts/eda/explore_cms.py

# 4️⃣ Build the pipeline-ready stratified sample → data/cms/pipeline.jsonl
python scripts/build_pipeline_dump.py --n 400

# 5️⃣ Human review artifact + validation (no corpus data needed for tests)
python scripts/spot_check.py        # verbatim audit → reports/eda/spot_check.csv
pytest tests/ -v                    # 30/30 passing
```

<details>
<summary><b>Smoke-test flags</b></summary>

```bash
python scripts/acquire_synpuf.py --dry-run        # probe remote sources
python scripts/build_corpus_index.py --limit 500  # 500 rows per input file
python scripts/build_pipeline_dump.py --dry-run   # plan quotas, write nothing
python scripts/publish_hf_dataset.py --dry-run    # stage + manifest only
```

All data lives under gitignored `data/` (~5 GB raw CSVs, regenerable from the
kept ZIPs at any time — disk-constrained machines can delete `data/raw/*.csv`
post-index and `extract()` re-materializes them).

</details>

## 📁 Repo Layout

```
claims-data-eda/
├── AGENTS.md                           ← agent-facing operational guide
├── scripts/
│   ├── acquire_synpuf.py               ← download + verify + extract (Wayback-aware)
│   ├── build_corpus_index.py           ← normalize 8 CSVs → compact gzipped JSONL
│   ├── render_eob.py                   ← deterministic EOB renderer + GT builder
│   ├── build_pipeline_dump.py          ← stratified reservoir sample (coverage contract)
│   ├── spot_check.py                   ← human-review CSV w/ verbatim audit
│   ├── publish_hf_dataset.py           ← HF Hub publisher (schema guard + VERIFY: GREEN)
│   └── eda/explore_cms.py              ← full-corpus EDA engine → reports/eda/
├── reports/
│   ├── eda/                            ← committed EDA output (12 figures + stats)
│   └── pipeline/README.md              ← wiring into llm-mailroom / llm-entity-extraction
└── tests/test_pipeline.py              ← 30 unit tests (normalizers/renderer/GT/dump shape)
```

## 📦 Pipeline Output Shape

`data/cms/pipeline.jsonl` — the flat streamer-dump format consumed by
[`llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction)
eval runners:

```jsonc
{
  "filename": "carrier:887013386172596.txt",
  "doc_text": "MEDICARE SUMMARY NOTICE -- PHYSICIAN/SUPPLIER CLAIM (Part B) ...",
  "prompt": "",
  "expected": "insurance_claim",
  "expected_subclass": "carrier",          // inpatient | outpatient | carrier | pde
  "metadata": {
    "record_id": "carrier:887013386172596",
    "diagnosis_codes": ["25000"],
    "hcpcs_codes": ["99213"],
    "source_dataset": "cms-de-synpuf-2008-2010-sample1",
    "ground_truth": {
      "claim_number": "887013386172596",
      "policy_number": "942DF76C4B9D257F",
      "insurer": "CMS Medicare",
      "insured_party": "MARTIN, DONNA",    // deterministic pseudonym
      "claim_type": "health",
      "date_of_loss": "2008-09-23",
      "claimed_amount": 110.0,
      "coverage_determination": "approved",
      "denial_reasons": []
    }
  }
}
```

**Stratification**: subtype × service year × log-cost band, allocated by
observed stratum weight with a **coverage contract** that refuses to emit a
sample missing any non-empty stratum (exit code 2).

## ✅ Verbatim GT Contract

Every scalar ground-truth value appears **literally** in the rendered document
text — so the mailroom's deterministic field scorer + factuality audit can
verify extraction without fuzzy fallbacks:

- asserted by `render()` at build time,
- machine-audited in [`reports/eda/spot_check.csv`](reports/eda/spot_check.csv) (**24/24 PASS**),
- unit-tested in [`tests/test_pipeline.py`](tests/test_pipeline.py) (**30/30**).

## 🤗 Hugging Face

The full dump publishes to
[**`Lucius-Morningstar/cms-desynpuf-insurance-claims`**](https://huggingface.co/datasets/Lucius-Morningstar/cms-desynpuf-insurance-claims)
with the family-wide deterministic split (`md5(record_id) % 10 == 0` → test):

```bash
export HF_TOKEN=hf_...
python scripts/publish_hf_dataset.py --dry-run   # stage + manifest only
python scripts/publish_hf_dataset.py             # upload + sha256 VERIFY: GREEN
```

## 📜 Provenance & License

- **Source**: [CMS 2008–2010 DE-SynPUF](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files), Sample 1 — direct download, free, no request.
- **Synthetic**: CMS states the files have "very limited inferential research
  utility" — treat everything here as **pipeline evaluation substrate, not
  epidemiology**. No real PHI exists; beneficiary names are deterministic
  pseudonyms.
- **License**: CMS Data Disclaimer / public-use data; no formal data license
  stated by CMS.

---

<div align="center">

**[llm-mailroom](https://github.com/Exios66/llm-mailroom)** ·
**[llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction)** ·
**[Enron-Evaluation-Environment](https://github.com/Exios66/Enron-Evaluation-Environment)** ·
**[atticus-investigation](https://github.com/Exios66/atticus-investigation)**

<sub>Built by the governed evaluation family under <a href="https://github.com/Exios66">@Exios66</a> · 2026</sub>

</div>
