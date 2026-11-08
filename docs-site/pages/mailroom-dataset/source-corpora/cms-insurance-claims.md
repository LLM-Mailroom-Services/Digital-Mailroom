---
description: Insurance claim rows from CMS data.
icon: file-medical
title: CMS insurance claims
---

# CMS insurance claims

`insurance_claim` · **1,100 rows** (33.3%) · 6 strata · train 986 / test 114 · mixed **Apache-2.0 / MIT / CC BY 4.0** plus CMS public-use (synthetic, no real PHI).

Canonical card: [`docs/dataset-cards/cms-desynpuf-insurance-claims.md`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/docs/dataset-cards/cms-desynpuf-insurance-claims.md) in Mailroom-Corpus-EDA. Some card sections still describe the 600-row CMS-only block; **live v9 is 1,100 rows** across six LOBs.

## What this block is

A **rendered evaluation corpus**: one row = one plain-text EOB / pharmacy statement whose extraction gold is aligned to llm-mailroom's `InsuranceClaimExtraction` schema. Health LOB rows come from **CMS 2008–2010 DE-SynPUF Sample 1** (fully synthetic Medicare FFS), rendered by [claims-data-eda](../../repository-guides/repos/claims-data-eda.md). v8 added GNOTHEIA **property** (200) and BDR **auto** (300) narratives; v9 added 150 INSURBIAS rows.

| Subclass     | Rows | Origin                                 |
| ------------ | ---: | -------------------------------------- |
| `auto`       |  300 | BDR motor-claims narratives (150) + INSURBIAS claim narratives (150, v9) |
| `property`   |  200 | GNOTHEIA                               |
| `carrier`    |  150 | CMS DE-SynPUF physician/supplier       |
| `inpatient`  |  150 | CMS DE-SynPUF                          |
| `outpatient` |  150 | CMS DE-SynPUF                          |
| `pde`        |  150 | CMS DE-SynPUF prescription-drug events |

Source: per-subclass counts from Mailroom-Corpus-EDA `reports/tables/strata_counts.csv` (P2, 2026-09-13) and the `source_corpus` / `source_revision` columns on the Hub rows; each lineage links to its dataset card under [`docs/dataset-cards/`](https://github.com/Exios66/Mailroom-Corpus-EDA/tree/main/docs/dataset-cards). Canonical sources are tabulated under [Attribution](#attribution).

CMS Sample-1 archives were recovered from Internet Archive captures; sha256 manifests live in claims-data-eda. A stable `metadata.record_id` survives across revisions. The family split re-keys on `md5(filename)`; 96/600 CMS-source rows differ from the source repo's `md5(record_id)` placement — the `split` column here is authoritative.

## Purpose in the mailroom

1. Largest gold `insurance_claim` class (transactional documents against the formal legal blocks).
2. Six LOB subtype labels.
3. 13-field extraction contract on `ground_truth`, verbatim-grounded in `doc_text` for the rendered CMS rows.
4. Homogeneous short-text block (EDA mean **692 characters**, σ = 953) for isolating format compliance from length effects.

## Field coverage (EDA figures 16–19)

Claimed amount is present on 1,062 rows (median $1,250). The EDA summary reports 13/13 fields filled across all six LOB subtypes for the current surface. `adjuster` is empty on CMS DE-SynPUF, GNOTHEIA property, and INSURBIAS rows (no adjuster in those sources); BDR auto rows carry pseudonyms.

**PAID-only caveat for SynPUF:** CMS DE-SynPUF contains adjudicated-paid FFS claims. Do not read “coverage determination fully populated” as a balanced approved/denied label space for the health LOB.

<figure><img src="https://raw.githubusercontent.com/Exios66/Mailroom-Corpus-EDA/main/reports/figures/16_claim_amount_distribution.png" alt="Insurance claim amount distribution"><figcaption><p>Claim amounts (figure 16).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/Mailroom-Corpus-EDA/main/reports/figures/17_coverage_determination.png" alt="Insurance coverage determination counts"><figcaption><p>Coverage determination (figure 17).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/Mailroom-Corpus-EDA/main/reports/figures/18_claim_dates_timeline.png" alt="Insurance claim date-of-loss to date-filed timeline"><figcaption><p>Claim dates (figure 18).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/Mailroom-Corpus-EDA/main/reports/figures/19_claim_subtype_fields.png" alt="Insurance claim field fill by subtype"><figcaption><p>Subtype field fill (figure 19).</p></figcaption></figure>

Tables: [`claim_amount_stats.csv`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/reports/tables/claim_amount_stats.csv), [`claim_field_coverage.csv`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/reports/tables/claim_field_coverage.csv).

## Attribution

Centers for Medicare & Medicaid Services, **Linkable 2008–2010 Medicare Data Entrepreneurs' Synthetic Public Use File (DE-SynPUF)** — <https://cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf> (Sample 1; [codebook](https://cms.gov/files/document/cms08-10desynpufcodebookpdf)). Fully synthetic; CMS's "very limited inferential research utility" caveat applies — an evaluation substrate, not epidemiology.

The three sibling line-of-business sources are separately licensed synthetic corpora and carry their own attribution:

| Source | Rows here | Line of business | License | Canonical source |
| ------ | ---------: | ---------------- | ------- | ---------------- |
| GNOTHEIA | 200 | `property` (FNOL documents, stratified by loss event) | Apache-2.0 | [`gratex/GNOTHEIA-synthetic-insurance-dataset`](https://huggingface.co/datasets/gratex/GNOTHEIA-synthetic-insurance-dataset) (Gratex International a.s., InnovAIte) |
| BDR | 300 | `auto` (motor-claims decision letters: `APPROVE` / `REVIEW` / `REJECT`) | MIT | [`bdr-ai-org/insurance-motor-claims-decision-v1`](https://huggingface.co/datasets/bdr-ai-org/insurance-motor-claims-decision-v1) |
| INSURBIAS | 150 (v9 addition) | `auto` (claim narratives) | see dataset card | [`feihuangfh/INSURBIAS`](https://huggingface.co/datasets/feihuangfh/INSURBIAS) — Fei Huang and Md Mushahidul Islam Shamim, "Gender Bias in AI-Assisted Insurance Claim Processing: A Counterfactual Audit of Large Language Models", [SSRN 6324800](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6324800) |

All three are fully synthetic with no real PII. `coverage_determination` is **pending** for GNOTHEIA property rows (the source carries no adjudication) — see the honest-gap note in [Agents](../../pipeline-reference-llm-mailroom/agents.md).

## Caveats

* Health LOB is US Medicare coding (HCPCS, NDC, NPIs), 2008–2010 era.
* `insured_party` on SynPUF rows is a deterministic pseudonym from `DESYNPUF_ID`.
* Synthetic-data caveats apply to every rendered EOB.

Strata table: [Classes and strata](../classes-and-strata.md#insurance_claim-1-100-rows-33.3).
