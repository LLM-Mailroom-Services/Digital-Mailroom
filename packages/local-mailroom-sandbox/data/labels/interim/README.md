# Interim ground-truth labels

These are the unpublished enhancements to the mailroom-dataset `ground_truth` labels. They act as ground truth until the next dataset revision publishes them.

**Do not edit these files by hand.** `scripts/interim_labels.py` builds them, and `scripts/interim_labels.py check` and `tests/test_interim_labels.py` verify them against `MANIFEST.json`.

## Contents

| File | Contents |
| --- | --- |
| `<class>.jsonl` | One record per document: `doc_id`, `doc_subclass`, `doc_sha256` (the exact text the labels were read from), `labels`, and `source` (the extraction run and prompt, the gate run, the question set, the verdict). |
| `MANIFEST.json` | Sources, admission rules, counts, the admission precision proxy, the file hashes, and the dojo issue that supersedes each class. |

Each label has a `status`:

| Status | Truth | Meaning |
| --- | --- | --- |
| `gap_fill` | yes | The Hub has no label. A real extraction the gate supports (field support >= 0.9) and whose every token is in the document. |
| `derived` | yes | Computed from the row, with no model involved: `cms_source_table`, `record_type` and `communication_type` from `expected_subclass`. |
| `correction` | yes | The Hub label is a known defect. The value is checked against the Hub's own CUAD evidence (`cuad_party_spans`, `cuad_agreement_date`). |
| `disputed` | **no** | The Hub label and a gate-supported extraction disagree. It carries `hub_value` (and `hub_source`) for human review. |

## Use

Nothing reads these files by default. A run opts in with:

```yaml
dataset:
  interim_labels: true
```

The run then merges the truth labels into its locked rows' `expected_fields`; Hub labels always win. It records the overlay's sha256 in both the spec hash and the lock (`dataset.metadata.interim_labels`).

## Updates

```bash
python scripts/interim_labels.py build --add-run <new gate run>   # after every gate run
python scripts/interim_labels.py build                            # rebuild from the listed runs
python scripts/interim_labels.py check                            # integrity + staleness
python scripts/interim_labels.py check --rows <hub rows.jsonl> --prune   # after a Hub revision
```

Rules and evidence: `docs/EXTRACTION_GATE_VETTING.md`.
