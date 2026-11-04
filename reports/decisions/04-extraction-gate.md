# Extraction gate experiments

The Decisions model was also tried as a gate over extraction (`task: extraction_gate`). It reads a document together
with a Qwen 3.7 Flash specialist's real extraction of it, and returns a verdict (`accept`, `retry_extraction` or
`human_review`) plus one yes/no "is this field supported by the text" question per key field. The truth it is scored
against is the Dojo score of the extraction it judged; "good" means a score of 0.80 or higher.

Sources: `reports/extraction-gate/*.calibration.json`, `config/decisions/extraction_gate_v1.*.yaml`,
`reports/run-ledger.md`, CHANGELOG (Unreleased).

## Rounds

| Round | Question set | Documents | Gate run |
| --- | --- | ---: | --- |
| Baseline | 1.0.0 (read cut at 120k characters; merger 240k) | 220 | `extraction-gate-luna-v1.0.0-baseline` |
| Baseline, whole documents | 1.1.0 (limit 1,000,000 characters) | 220 | `extraction-gate-luna-v1.1.0-baseline` |
| Round 2 | 1.1.0 | 690 new documents, no repeats | `extraction-gate-luna-v1.1.0-r2` |
| **Pooled** | 1.1.0 | **910** | `extraction-gate-luna-v1.1.0-pooled` |

The 220 baseline documents are 60 insurance claims, 60 correspondence, 40 contracts, 40 corporate records, 20 mergers.
Round 2 adds 240 insurance, 240 correspondence, 160 corporate record, 40 contract and 10 merger. All signed JB on
2026-11-01 (`reports/run-ledger.md`). Round 2's insurance extractions used `insurance_claims_specialist_condensed_v2`; the
baseline round used the frozen prompt; condensed v3 came after.

## Result: the gate does not tell good extractions from bad

![Gate accept rate against real quality](figures/f13-gate-accept.svg)

| Class | Documents | Gate accept | Gate retry | Gate human review | Really good | Mean score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| contract | 80 | 9 (11.2%) | 71 | 0 | 22.5% | 0.715 |
| corporate record | 200 | 56 (28.0%) | 144 | 0 | **0.5%** | 0.397 |
| correspondence | 300 | 109 (36.3%) | 184 | 7 | **3.3%** | 0.315 |
| insurance claim | 300 | 68 (22.7%) | 232 | 0 | 24.7% | 0.773 |
| merger agreement | 30 | 2 (6.7%) | 28 | 0 | 0.0% | 0.117 |
| **all** | **910** | **244 (26.8%)** | **659 (72.4%)** | **7** | **11.3%** | 0.513 |

Of the 244 documents the gate accepted, about 14 were good: **an accept precision of 5.7%**, against a base rate of 11.3%.
The gate accepts a quarter of corporate records when 0.5% of their extractions are good.

![AUROC of the gate's accept confidence](figures/f14-gate-auroc.svg)

| Class | v1.0.0 baseline | v1.1.0 baseline | v1.1.0 round 2 | **Pooled** |
| --- | ---: | ---: | ---: | ---: |
| contract | 0.500 | 0.500 | 0.672 | 0.591 |
| corporate record | 0.192 | 0.244 | – | 0.327 |
| correspondence | 0.602 | 0.602 | 0.249 | 0.335 |
| insurance claim | 0.546 | 0.546 | 0.378 | 0.409 |
| merger agreement | – | – | – | n/a |
| **all** | 0.484 | 0.455 | 0.397 | **0.410** |

An AUROC of 0.5 is a coin flip. Pooled, the gate ranks good extractions **below** bad ones in three classes. Merger
agreements have no good extraction at all (mean score 0.12), so the AUROC does not exist. **No class reached the 90%
precision target at any cutoff**; every cutoff entry in the calibration files is `null`.

Moving from 1.0.0 to 1.1.0, so that the gate reads every document whole, changed the totals by two documents (accept 42 to 44). The
cut at 120k characters was not the cause of the weak ranking.

## One field-level signal, with caveats

The per-field support questions rank extractions better than the overall verdict does for a few fields:

| Field | n | Support AUROC | Truth rate |
| --- | ---: | ---: | ---: |
| insurance_claim.date_of_loss | 298 | 0.983 | 99.7% |
| contract.renewal_terms | 80 | 0.890 | 82.5% |
| contract.governing_law | 80 | 0.849 | 95.0% |
| correspondence.intent | 300 | 0.595 | 55.3% |
| contract.effective_date | 80 | 0.574 | 66.3% |

Treat `date_of_loss` with care: its truth rate is 99.7%, so one document is the whole negative class and an AUROC of
0.98 says almost nothing. `renewal_terms` (n=80, balanced enough) is the one genuine signal. Fields at or below 0.5 include
`contract.parties` (0.46), `contract.cuad_clauses` (0.47), `contract.term_length` (0.41) and `insurance_claim.insurer`
(0.44). Four insurance fields and `maud_clauses` have no AUROC because their truth rate is 0 or 1.

## What it means for cost

- The 1x for extraction is a Qwen specialist call. **Cost parity cannot be computed from tracked files**: the run configs
  hold estimates (about 2.4M input tokens, $0.24 for the 220-document baseline) and no usage records are committed.
  The round-2 config repeats the same estimate for 690 documents, so it is not a measurement either.
- The gate's `retry_extraction` verdict fires on 72.4% of documents. If a pipeline acted on it, each document would take
  up to 0.72 extra specialist calls, 1x each, with no evidence that a retry improves the score, since the gate does not
  pick the bad extractions.
- **Recommendation: do not wire the gate into a pipeline.** Spend the next round on the per-field questions that show a
  signal, and score them against field-level truth instead of the whole-document verdict.

## Specialist-prompt work done on the way

Specialist-condensed prompt lineage, each version validated against the frozen prompt before the gate saw it:

| Class | Version | Mean score before | Mean score after | Note |
| --- | --- | ---: | ---: | --- |
| insurance_claim | v3 | 0.770 | 0.899 | better on 60 of 60 documents |
| corporate_record | v1 | 0.352 | 0.427 | |
| correspondence | v2 | +0.002 | | 28% fewer input tokens; v1 rejected (over-predicted `update`) |

Contracts and mergers keep their frozen prompts. These prompt changes lower the 1x input-token cost and raise the
1x extraction score for the classes they cover, which the gate has not yet done for any class.
