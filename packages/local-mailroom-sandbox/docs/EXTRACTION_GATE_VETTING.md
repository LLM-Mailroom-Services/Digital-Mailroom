# Extraction gate vetting: question set 1.3.0 and the interim GT labels

The Decisions-model extraction gate (`openai/gpt-6-luna-decisions`) is to stand in as the extraction reviewer in next week's full mailroom pipeline experiments. This note covers:

- what was vetted;
- every dataset and ground-truth limitation found, and how each is handled;
- what the gate can and cannot be trusted with.

## Evidence

**Data.** 1,596 real `qwen/qwen3.7-flash` specialist extractions of mailroom-dataset `ground_truth` rows. No document was extracted twice.

| Class | Docs |
| --- | ---: |
| insurance_claim | 986 |
| correspondence | 300 |
| corporate_record | 200 |
| contract | 80 |
| merger_agreement | 30 |

**Gate runs.**

| Run | Documents | Cost |
| --- | --- | ---: |
| `extraction-gate-luna-v1.2.0-rereview` | 880 | $0.41 |
| `extraction-gate-luna-v1.2.0-r3` | 686 | $0.25 |
| `extraction-gate-luna-v1.3.0` | all 1,596 | $0.87 |

**Method.**

1. Every case where the gate's field answer and the dojo's field truth disagreed was grouped by class, field and subclass.
2. Each group was sampled and read against the document text.
3. For insurance, every ground-truth value was located in the printed line it comes from, on all 986 rows.

**Reports.** In `reports/extraction-gate/`:

- `extraction-gate-luna-v1.3.0.calibration.json` (dojo truth);
- `extraction-gate-luna-v1.3.0-corrected.calibration.json` (`--corrected-truth`);
- `extraction-gate-luna-v1.2.0-{rereview,r3,pooled}.calibration.json`.

## Readiness

| Class | Gate as reviewer | Gating score AUROC (key fields) | Suggested use |
| --- | --- | ---: | --- |
| insurance_claim | **ready** | 0.865 (verdict 0.783) | Accept at `key_field_score >= 0.5`: precision 0.986, recall 0.56. For more volume, accept at `>= 0.10`: precision 0.90, recall 0.84. |
| corporate_record | **ready** | 0.891 (verdict 0.521) | Accept at `>= 0.01`: precision 0.90, recall 0.79. At `>= 0.5`, precision is 1.00 and recall 0.37. |
| contract | **usable on corrected truth** | 0.844 excl. CUAD recall (verdict 0.686) | Accept at `>= 0.5`: precision 0.76, recall 0.70. Score CUAD clauses with the dojo, not the gate. |
| merger_agreement | **no signal (25 labelled, 96% right)** | 0.54 | Accept; the gate is too conservative on merger parties. |
| correspondence | **advisory only** | 0.584 | No cutoff reaches precision 0.9. The intent labels are too noisy to calibrate against; see below. Route a sample to human review. |

**`key_field_score` is the gating score**, not the verdict. It is the product of the key-field support probabilities (`decision_backends.key_field_score`, emitted with every gate answer).

The verdict question is answered on its own and does not apply the field rules. Its answers were byte-identical between 1.2.0 and 1.3.0, so its AUROC did not move. The field answers carry everything 1.3.0 fixed.

**Pipeline requirement.** 1.3.0 picks template rules by subclass. Calibration used the labelled subclass, which amounts to an oracle sorter. In the pipeline, the handoff must carry the sorter's subclass. Expect three things:

- A wrong sorter subclass gives the gate the wrong template rules.
- Pipeline gate numbers therefore sit below these by the sorter's subclass error rate.
- Without a subclass, the gate falls back to the class rules, which are the 1.2.0 behaviour.

**Running the gate in the pipeline.** Add this block to a `task: pipeline` run spec:

```yaml
extraction_gate:
  model: openai/gpt-6-luna-decisions
  questions: extraction_gate_v1.3.0
```

- **Preflight** freezes the question set into the lock.
- **Activation** registers the gate with llm-mailroom's `agents.extraction_gate` hook (llm-mailroom #136). The vendored llm-mailroom must include that hook, or activation refuses.
- **Per extraction**, `extract_node` and `retry_extract_node` send `{doc_type, doc_subclass, fields}`, where `doc_subclass` is the sorter's subclass. The sandbox backend (`decision_backends.extraction_gate_backend`) passes that subclass and nothing else: unlike calibration runs, there is no fallback to `expected_subclass`.
- **Records:** each pipeline record carries `doc_subclass` and `extraction_gate` (verdict, `key_field_score`, `field_support`, question set).
- **Advisory:** routing does not read the gate yet. Measure in-pipeline `key_field_score` against the dojo before routing on the cutoffs below.
- **Spend:** gate calls count against the run budget and the OpenRouter key reserve.

## Field-level agreement (gate yes/no vs dojo field truth)

| Field | 1.2.0 | 1.3.0 | What changed |
| --- | ---: | ---: | --- |
| insurance claim_type | 0.87 | **0.98** | CMS token accepted for the document's own table only |
| insurance insurer | 0.85 | **0.95** | property: Product line is the insurer |
| insurance date_filed | 0.57 | **0.80** | per-template filing line |
| insurance claimed_amount | 0.95 | **0.98** | per-template amount line |
| insurance policy_number | 0.96 | **0.99** | property: number printed in attachments when header is `[REDACTED]` |
| insurance coverage_determination | 0.95 | 0.82 | **regressed**: 159 conservative "no" on correct Medicare outcomes |
| insurance date_of_loss | 0.99 | 0.97 | 32 conservative "no" on correct property dates |
| corporate intent | 0.76 | **0.90** | intent fixed by record kind; false accepts 47 → 0 |
| contract parties (corrected truth) | — | support AUROC 0.81 | dojo truth fixed, see below |
| contract effective_date (corrected truth) | — | support AUROC 0.90 | dojo truth fixed, see below |
| correspondence intent | 0.63 | 0.63 | unchanged on purpose |

The two regressions are false "no" answers on correct values. They cost re-extraction, never a wrong accept. They are candidates for 1.4.0.

## Dataset and GT limitations, and their patches

| Limitation (evidence) | Patch | Where |
| --- | --- | --- |
| **Insurance: each template takes each value from one fixed printed line.** Inpatient: date_of_loss = Claim period start (not the Admission date), date_filed = Claim period end. Outpatient/carrier: Service start/end date. Part D: Date of service for both. Property: Date of Report, Estimated Damage (Total incl. VAT when there is none: 5 of 134). The 1.2.0 gate rejected values equal to GT: date_filed 298, insurer 148, claim_type 131. | Per-template rules (`subclass_fields`) | `config/decisions/extraction_gate_v1.3.0.yaml` |
| **Property FNOL header shows `Policy Number: [REDACTED]`, but the number is printed in the attachments** (71 of 184 only there). 1.2.0 told the gate "empty when withheld", which was wrong. | Rule: use the attachment number | 1.3.0 |
| **Property FNOL: no insurer company is named; GT uses the Product line.** | Rule | 1.3.0 |
| **Property FNOL: no decision stated; GT = `pending`** (143 not in the text). The extractor often leaves it empty; 1.2.0 accepted empty 45 times. | Rule: pending, and empty is wrong | 1.3.0 |
| **CMS `claim_type`: the Hub collapses all 400 CMS rows to `health`; the specialist emits table tokens** (dojo #93). 1.2.0 rejected `carrier` (0.03) but accepted `outpatient` on carrier notices. | Rule: `health` or the document's own table token. Interim label `cms_source_table` (derived from the subclass, 536 rows). | 1.3.0, overlay |
| **Corporate intent is a function of the record kind** (heuristic GT). 1.2.0 accepted 47 intents that contradict it. | Rule per record kind | 1.3.0 |
| **Corporate `record_type` and correspondence `communication_type` have no GT field, but the Hub subclass is exactly that label.** A model-read record_type ("bylaws" off a board consent's exhibit title) contradicts the subclass. | Interim label derived from `expected_subclass` (200 + 300). The question should name the subclass vocabulary: 1.4.0. | overlay |
| **Corporate entity, jurisdiction, effective date, filing number and signatories have no GT** (#52). | Interim gap fills: 806 labels on 200 documents | overlay |
| **Correspondence sender, recipient and date have no GT; subject_matter/keywords are templated** (#94). | Interim gap fills: 702 labels. subject_matter and keywords stay out of every target. | overlay |
| **Correspondence intent labels are noisy by source.** Extraction agrees with the label: manual 0.69, llm_zero_shot 0.61, aeslc_join 0.55, heuristic **0.31**. The gate supports the extraction on 89% of the heuristic rows. | Not tuned toward the labels. 72 `disputed` labels, carrying the Hub value and source, are exported for human review; they are not truth. | overlay (`disputed`) |
| **CUAD `Parties` spans mix legal names, defined terms and pronouns** ("we", "you", "Seller"). The dojo's parties truth is 34% right on extractions that name every party correctly. | `correction` when every extracted party is a CUAD Parties span (32). `--corrected-truth` raises the parties truth rate to 0.825. | overlay, `extraction_gate.py` |
| **CUAD `Effective Date` is empty when only an agreement date is given;** the dojo marks the agreement date wrong. | `correction` when the value equals the CUAD Agreement Date (13) | overlay, `--corrected-truth` |
| **CUAD clause presence is a recall measure over 41 categories, which a reader cannot verify.** | The gate judges precision only: every listed clause is present with its own evidence. The dojo keeps scoring recall. | 1.3.0 |
| **Merger document name, parties, dates and governing law have no GT** (#95). | Interim gap fills: 93 labels on 30 documents. The gate rejects correct merger party lists (0.39), so no party labels yet. | overlay |
| **Free text labelled from mailbox/template metadata** (subject_matter, keywords, damages_description, supporting_documents, maud_clauses: truth rate 0–6%). | Out of the verdict and the key-field target (`UNGROUNDED`) | 1.2.0+ |

## Interim GT labels (`data/labels/interim/`)

**What they are.** The unpublished enhancements expected in the next dataset revision. They act as ground truth until the Hub publishes them. See `data/labels/interim/README.md` and `mailroom_sandbox.interim_labels`.

**Counts.**

| Class | Truth labels | Disputed |
| --- | --- | ---: |
| corporate_record | 806 gap fills + 200 derived | — |
| correspondence | 702 gap fills + 300 derived | 72 |
| insurance_claim | 536 derived | — |
| contract | 45 corrections | 12 |
| merger_agreement | 93 gap fills | 1 |

**Admission rule.** A label is admitted when field support is at least 0.9 (0.95 for "not stated"), the verdict is not human_review, and every token of the value is in the document. The same rule, applied to fields the Hub does label, gives these right rates (dojo):

| Class | Right rate |
| --- | ---: |
| insurance | 0.999 |
| corporate | 1.00 |
| merger | 0.96 |
| contract | 0.82 (before corrections) |
| correspondence | 0.66 (intent only: noisy labels) |

**Use.** Off by default. With `dataset.interim_labels: true`, a run merges the truth labels into its locked rows; the Hub's own labels always win. The run's spec hash and lock carry the overlay fingerprint, so the scores are never mixed with Hub-GT scores (dojo #97).

**Keeping them current.**

- After every gate run: `python scripts/interim_labels.py build --add-run <gate-run>`. The latest question set wins per document.
- `python scripts/interim_labels.py check` refuses a hand-edited or stale overlay, meaning a newer local gate run that has not been folded in.
- `check --rows <hub rows> [--prune]` drops the labels a new Hub revision publishes.
- `tests/test_interim_labels.py` keeps the committed files consistent.

## 1.4.0 candidates (not yet run)

1. Drop or rewrite the verdict question. `key_field_score` already gates, so this saves about 15% of the request.
2. Make the Medicare coverage rule and the property date_of_loss rule harder to refuse: the 159 + 32 conservative "no" answers.
3. Name the subclass vocabulary in the `record_type` and `communication_type` questions.
4. Merger parties: Parent, Merger Sub and Target given by their legal names.
5. Re-run only the rows whose questions change, so each run stays within the remaining weekly spend.
