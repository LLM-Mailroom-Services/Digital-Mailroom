# CMS DE-SynPUF (Sample 1) — Full-Corpus EDA Report

_Generated 2026-08-23 · scripts/eda/explore_cms.py · data: data/cms/{beneficiaries,index}.jsonl_

## 1. Corpus Inventory

| Metric | Value |
| --- | --- |
| Beneficiaries (merged 3 yearly summaries) | 116,352 |
| Total claim/PDE event rows (segments & lines kept) | 11,151,319 |
| Unique claims (CLM_ID) / fills (PDE_ID) | 11,140,276 |
| Beneficiaries with >=1 event | 103,935 |
| Source archives | 8 ZIPs (see data/raw/MANIFEST.json; 3 recovered via Wayback Machine) |

| Claim type | Event rows | Unique claim IDs |
| --- | --- | --- |
| Inpatient | 66,773 | 66,705 |
| Outpatient | 790,790 | 779,815 |
| Carrier (physician) | 4,741,335 | 4,741,335 |
| PDE (drug) | 5,552,421 | 5,552,421 |

![corpus](figures/01_corpus_overview.png)

## 2. Referential Integrity & Linkage

| Type | Events linked to beneficiary summary | Orphan events |
| --- | --- | --- |
| Inpatient | 66,773 | 0 |
| Outpatient | 790,790 | 0 |
| Carrier (physician) | 4,741,335 | 0 |
| PDE (drug) | 5,552,421 | 0 |

## 3. Beneficiary Demographics

| Sex | Count |
| --- | --- |
| Male | 52,005 |
| Female | 64,347 |

| Age band (2008) | Count | % |
| --- | --- | --- |
| <65 | 19,120 | 16.4% |
| 65-74 | 49,547 | 42.6% |
| 75-84 | 32,882 | 28.3% |
| 85+ | 14,803 | 12.7% |

Deaths recorded across window: **5,461** (2008: 1,814, 2009: 1,784, 2010: 1,863)

![demographics](figures/03_demographics.png)

## 4. Chronic Conditions & Comorbidity

| Condition (2010 flag) | % of beneficiaries |
| --- | --- |
| Ischemic Heart Disease | 36.2% |
| Diabetes | 28.3% |
| Heart Failure | 25.1% |
| Depression | 17.2% |
| Alzheimer's/Dementia | 16.1% |
| Chronic Kidney Disease | 13.4% |
| Osteoporosis | 12.6% |
| Rheumatoid/Osteo Arthritis | 9.4% |
| COPD | 8.7% |
| Cancer | 4.9% |
| Stroke/TIA | 2.5% |

![chronic](figures/04_chronic_conditions.png)

![comorbidity](figures/05_comorbidity_matrix.png)

## 5. Temporal Patterns

Claim volumes are flat-to-seasonal with no year-over-year growth trend — consistent with synthetic generation from stationary templates rather than real utilization drift.

![monthly](figures/02_monthly_volume.png)

## 6. Cost Distributions

| Type | p10 | p25 | p50 | p75 | p90 | p95 | p99 | Σ paid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Inpatient | $3.0K | $4.0K | $7.0K | $11.0K | $19.0K | $29.0K | $57.0K | $639.26M |
| Outpatient | $20.00 | $40.00 | $80.00 | $200.00 | $800.00 | $1.7K | $3.3K | $224.52M |
| Carrier (physician) | $10.00 | $30.00 | $60.00 | $100.00 | $200.00 | $340.00 | $660.00 | $414.60M |
| PDE (drug) | $10.00 | $10.00 | $20.00 | $90.00 | $170.00 | $250.00 | $570.00 | $340.94M |

All four payment distributions are heavy-tailed (p99 ≫ p50); inpatient is the widest ($57.0K at p99).

![costs](figures/06_cost_distributions.png)

## 7. Diagnosis Codes (ICD-9)

**Inpatient — top 15 diagnosis codes:**

| Code | Occurrences |
| --- | --- |
| 4019 | 23,512 |
| 25000 | 11,987 |
| 2724 | 11,898 |
| 41401 | 10,449 |
| 4280 | 10,218 |
| 42731 | 10,127 |
| 5990 | 8,805 |
| 53081 | 8,078 |
| 2449 | 6,952 |
| 496 | 6,617 |
| 5849 | 6,544 |
| 486 | 6,064 |
| 2859 | 5,411 |
| 40390 | 5,150 |
| 41400 | 4,834 |

**Outpatient — top 15 diagnosis codes:**

| Code | Occurrences |
| --- | --- |
| 4019 | 93,932 |
| 25000 | 45,218 |
| 2724 | 42,390 |
| V5869 | 36,302 |
| 4011 | 35,664 |
| V5861 | 28,242 |
| 2720 | 23,901 |
| 42731 | 20,913 |
| 2449 | 20,045 |
| 78079 | 15,564 |
| 53081 | 14,699 |
| 2859 | 14,624 |
| 496 | 14,376 |
| 4280 | 13,808 |
| 28521 | 13,751 |

**Carrier (physician) — top 15 diagnosis codes:**

| Code | Occurrences |
| --- | --- |
| 4019 | 310,654 |
| 4011 | 264,695 |
| 2724 | 166,879 |
| 25000 | 146,903 |
| 2720 | 100,668 |
| 42731 | 81,981 |
| V5869 | 70,983 |
| 2449 | 70,262 |
| 78079 | 69,359 |
| 2859 | 65,669 |
| 7295 | 60,875 |
| 2722 | 59,449 |
| 4280 | 59,145 |
| 496 | 57,372 |
| 78650 | 53,705 |

Empty-diagnosis rate: Inpatient 0.1%, Outpatient 0.7%, Carrier (physician) 0.0%, PDE (drug) 0.0%

![dx](figures/07_top_diagnoses.png)

## 8. Procedures, HCPCS & Drugs

**Top inpatient ICD-9 procedure-slot codes:**

_Data quirk: SynPUF's generator populated `ICD9_PRCDR_CD_*` slots with a mix of true procedure codes (9904 transfusion, 8154 joint replacement, 3893 vessel repair, 3995 hemodialysis) and high-frequency _diagnosis_ codes (4019, 25000). Treat procedure-slot GT with care when evaluating extraction._

| Code | Claims |
| --- | --- |
| 4019 | 3,266 |
| 9904 | 1,861 |
| 2724 | 1,659 |
| 8154 | 1,646 |
| 25000 | 1,566 |
| 3893 | 1,424 |
| 0066 | 1,401 |
| 41401 | 1,360 |
| 3995 | 1,284 |
| 42731 | 1,171 |
| 4280 | 1,161 |
| 4516 | 1,049 |
| 53081 | 1,026 |
| 3722 | 982 |
| 5990 | 806 |

**Top outpatient HCPCS:**

| Code | Claims |
| --- | --- |
| 36415 | 221,899 |
| 97110 | 162,090 |
| A4657 | 134,778 |
| Q4081 | 130,928 |
| 85025 | 129,941 |
| 90999 | 123,847 |
| 80053 | 98,819 |
| 85610 | 94,280 |
| J2501 | 75,754 |
| 80048 | 67,865 |
| 80061 | 56,601 |
| 97530 | 54,910 |
| 99213 | 47,227 |
| 93005 | 43,763 |
| 97116 | 42,308 |

**Top carrier-line HCPCS:**

| Code | Lines |
| --- | --- |
| 99213 | 600,006 |
| 99214 | 429,649 |
| 36415 | 369,023 |
| 99232 | 253,417 |
| 85025 | 174,739 |
| 80053 | 147,680 |
| 85610 | 123,820 |
| 80061 | 122,920 |
| 97110 | 119,740 |
| 99212 | 118,284 |
| 93010 | 116,120 |
| 71010 | 114,672 |
| 99233 | 108,599 |
| 71020 | 87,358 |
| 98941 | 86,613 |

**Top NDC products (PDE fills):**

| NDC | Fills |
| --- | --- |
| 00002840001 | 206 |
| 54868540600 | 193 |
| 64378033202 | 187 |
| 00065033230 | 183 |
| 54569489700 | 182 |
| 62381840001 | 179 |
| 00078048634 | 177 |
| 62381897101 | 174 |
| 00002897101 | 174 |
| 00065033209 | 173 |
| 52959081303 | 173 |
| 58016089232 | 170 |
| 00247219630 | 169 |
| 54569562500 | 168 |
| 66267056520 | 168 |
| 54569560600 | 167 |
| 58016060618 | 166 |
| 60312096001 | 165 |
| 66267052340 | 165 |
| 00002840099 | 165 |

![procedures](figures/08_procedures_hcpcs.png)

![drugs](figures/09_top_drugs_ndc.png)

## 9. Provider Concentration

Across 4,742,114 sampled carrier lines, **23.9%** of lines concentrate in the top 1% of providers — a pareto tail any entity-extraction target set should stratify against.

**Top DRGs (inpatient):**

| MS-DRG | Claims |
| --- | --- |
| 882 | 282 |
| 177 | 281 |
| 886 | 275 |
| 887 | 274 |
| 880 | 264 |
| 181 | 264 |
| 189 | 260 |
| 883 | 259 |
| 876 | 259 |
| OTH | 258 |
| 183 | 257 |
| 939 | 253 |
| 202 | 252 |
| 198 | 252 |
| 175 | 252 |

![providers](figures/10_provider_concentration.png)

## 10. Utilization Concentration

| Metric | Value |
| --- | --- |
| Active beneficiaries | 103,935 |
| Mean events per active beneficiary | 107.3 |
| Max events for one beneficiary | 410 |
| Share of events from top 20% of patients | 42.4% |

![utilization](figures/11_utilization.png)

## 11. Annual Reimbursement Rollups (Beneficiary Files)

| Year | IP | OP | CAR |
| --- | --- | --- | --- |
| 2008 | $257.62M | $72.40M | $135.21M |
| 2009 | $250.84M | $88.14M | $153.23M |
| 2010 | $139.99M | $48.76M | $95.57M |

2010 totals sit ~45% below 2009 because the claims window tapers after mid-2010 -- visible in the monthly volume chart above; treat 2010 as a partial year.

![reimbursements](figures/12_annual_reimbursements.png)

## 12. Pipeline Fit Assessment (llm-mailroom `insurance_claim`)

| Specialist field | GT source in SynPUF | Coverage note |
| --- | --- | --- |
| claim_number | CLM_ID (+segment suffix) | exact, verbatim-renderable |
| policy_number | DESYNPUF_ID | exact; stable join key |
| insurer | 'CMS Medicare Part A/B' | constant by construction |
| insured_party | deterministic pseudonym from DESYNPUF_ID | rendered; no real names exist |
| claim_type | 'health' constant + subtype metadata | line-of-business always health |
| date_of_loss | CLM_FROM_DT / SRVC_DT | exact ISO |
| date_filed | CLM_THRU_DT / discharge_dt | proxy (adjudication date absent) |
| claimed_amount | CLM_PMT_AMT / TOT_RX_CST_AMT | exact; paid amount |
| adjuster | — | **absent** — synthetic corpus has none |
| damages_description | template from dx/proc/hcpcs codes | clinically faithful summary text |
| coverage_determination | 'approved' | ALL SynPUF claims are adjudicated-paid; no denials exist |
| denial_reasons | [] | always empty — see above |
| supporting_documents | provider/facility refs | rendered list |

### Evaluation caveats

1. **No negative class**: every rendered document will be an approved health claim; denial-letter and reservation-of-rights ground truth must come from another source.
2. **Fully synthetic**: CMS warns of limited inferential utility — treat as _pipeline substrate_, not epidemiology. Distributions here characterize the eval artifact itself.
3. **Verbatim contract**: every GT value above is rendered verbatim into doc_text so the mailroom field scorer's factuality audit can verify extraction without fuzzy fallback.
