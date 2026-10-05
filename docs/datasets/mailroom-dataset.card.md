---
pretty_name: Mailroom Dataset
language:
  - en
license: cc-by-4.0  # owner to confirm; see docs/datasets/README.md
task_categories:
  - text-classification
  - text-generation
task_ids:
  - multi-class-classification
tags:
  - legal
  - insurance
  - document-classification
  - information-extraction
  - document-ai
size_categories:
  - 1K<n<10K
configs:
  - config_name: default
    data_files:
      - split: train
        path: parquet/default/train/train-00000-of-00001.parquet
      - split: test
        path: parquet/default/test/test-00000-of-00001.parquet
  - config_name: ground_truth
    data_files:
      - split: train
        path: parquet/ground_truth/train/train-00000-of-00001.parquet
      - split: test
        path: parquet/ground_truth/test/test-00000-of-00001.parquet
---

# Mailroom Dataset

A labeled corpus of 3,302 business and legal documents for evaluating
document-intake systems. Each document belongs to one of five types: contracts,
corporate records, correspondence, insurance claims and merger agreements.
Each is labeled with its type, a subclass and field-level extraction targets.
It is the evaluation corpus for the LLM-Mailroom pipeline and its specialist
extraction agents, and for the ModernBERT intake classifier.

## Quick start

Pin a revision. Labels and row counts are versioned together, and scores are
only comparable on the same revision.

```python
from datasets import load_dataset

REPO = "Lucius-Morningstar/mailroom-dataset"
REV = "ed7576b676343e0b402ec5412cded301e629bdee"  # v9.1

docs = load_dataset(REPO, "default", revision=REV)
labels = load_dataset(REPO, "ground_truth", revision=REV)

# Join the two configs on filename to get labeled documents.
gt = {row["filename"]: row for row in labels["test"]}
row = docs["test"][0]
print(row["filename"], gt[row["filename"]]["expected_subclass"])
```

`gt_fields` is stored as a JSON string. Decode it with `json.loads`. An empty
string means no field targets.

## Dataset structure

### Configurations

| Config | Contents | Use |
| --- | --- | --- |
| `default` | Document text and identifiers, without labels | Blind inference: classify or extract without seeing labels |
| `ground_truth` | Labels for the same documents, keyed by `filename` | Scoring, and training where permitted |

Keeping labels in a separate config lets a system run blind on `default` and
be scored against `ground_truth` afterwards. Both configs have the same
splits, and `filename` is unique across the whole dataset.

### Splits

| Split | Documents |
| --- | ---: |
| train | 2,979 |
| test | 323 |
| **total** | **3,302** |

The test split is small for merger agreements (about 17 documents). Draws
that need more documents per class use train and test together.

### Document types and subclasses

| Document type | Documents | Subclasses |
| --- | ---: | --- |
| `insurance_claim` | 1,100 | auto, carrier, property, inpatient, outpatient, pde |
| `correspondence` | 1,000 | email, letter, memo, press_release, meeting_request, demand, notice |
| `contract` | 600 | CUAD agreement categories, 19 in the test split (e.g. service, supply, distributor, co_branding, ip, development, maintenance, strategic_alliance, sponsorship) |
| `corporate_record` | 450 | subsidiary_list, charter_amendment, officer_certificate, board_resolution, articles_of_incorporation, indenture, powers_of_attorney, rights_instrument, bylaws |
| `merger_agreement` | 152 | Deal consideration: all_cash, all_stock, mixed_cash_stock, mixed_cash_stock_election, other |

Class sizes are imbalanced. Report per-class metrics and per-class sample
sizes alongside any aggregate score.

### Fields

`default`

| Field | Type | Description |
| --- | --- | --- |
| `filename` | string | Unique document key; joins to `ground_truth` |
| `id` | string | Document identifier (`DOC-` + 16 hex characters) |
| `doc_text` | string | Full document text |
| `content_sha256` | string | SHA-256 of `doc_text`, for integrity checks |

`ground_truth`

| Field | Type | Description |
| --- | --- | --- |
| `filename` | string | Joins to `default` |
| `expected_doc_class` | string | One of the five document types |
| `expected_subclass` | string | Subclass within the document type |
| `gt_fields` | string (JSON) | Field-level extraction targets (see below) |

### Ground-truth fields (`gt_fields`)

`gt_fields` uses one schema that is the union of every specialist's fields,
so each row also carries keys that belong to other document types, usually
empty. The keys fall into these groups:

- **Intent and provenance:** `intent`, `intent_confidence`, `intent_source`, `intent_status`
- **Content:** `content_topic`, `keywords`, `subject_matter`, `sentiment_label`
- **Insurance claims:** `claim_number`, `policy_number`, `insured_party`, `adjuster`, `date_of_loss`, `claimed_amount`, `coverage_determination`, `denial_reasons`, `damages_description`
- **Contracts and mergers:** `cuad_clause_labels`, `maud_clause_labels`

**Scoring guidance.** An empty value (`null`, `""` or `[]`) on a field that
does not apply to the document's type is not an extraction target. Drop
empty and other-type keys before scoring. Otherwise a correct extraction is
penalized for leaving another type's fields blank.

## Intended uses

- Benchmarking document-type classification and subclass routing.
- Benchmarking structured extraction per document type, with scores reported
  per class.
- Comparing serving setups (local vs hosted models, quantization,
  concurrency) on a fixed, pinned draw.

## Out-of-scope uses

- **Contract field extraction.** Contract rows carry triage labels (intent,
  keywords, CUAD clause labels), not a full contract extraction schema
  (parties, governing law, term length). Extraction scores on contracts are
  not meaningful against this ground truth.
- **Legal, insurance or financial decisions.** Labels support evaluating
  software. They are not legal or claims determinations.

## Known limitations

- The `gt_fields` union schema means most keys on any row are empty. Scorers
  that count empty targets as misses under-report extraction quality,
  especially on correspondence.
- Merger ground truth follows MAUD clause categories. A contracts-style (CUAD)
  extractor run on merger documents will not match it.
- The merger test split is small (about 17 documents), so per-class test
  metrics for mergers have wide confidence intervals.
- Subclass labels are more reliable signals for some types than others:
  insurance subclasses are well separated, while contract and correspondence
  subclasses are close to their class priors for current classifiers.

## Source data and licensing

- **Contracts:** drawn from CUAD (Contract Understanding Atticus Dataset),
  released by The Atticus Project under CC BY 4.0.
- **Merger agreements:** drawn from MAUD (Merger Agreement Understanding
  Dataset), released by The Atticus Project under CC BY 4.0.
- **Corporate records, correspondence and insurance claims:** see the
  dataset changelog for provenance by version.

Reuse must keep the attribution required by the upstream licenses.

## Versions

| Version | Revision | Notes |
| --- | --- | --- |
| v9.1 | `ed7576b676343e0b402ec5412cded301e629bdee` | Current pinned revision for the LLM-Mailroom family |
| v9 | `46a4d3c240a36671cde0182fff4960f6b8b73aca` | Revision used by the September 2026 specialist extraction runs |

## Related resources

- [`Lucius-Morningstar/mailroom-modernbert-classifier`](https://huggingface.co/Lucius-Morningstar/mailroom-modernbert-classifier): intake classifier evaluated on this dataset's test split.
- [`Lucius-Morningstar/mailroom-modernbert-training`](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-modernbert-training): windowed training table derived from this corpus.
- [`Exios66/llm-mailroom`](https://github.com/Exios66/llm-mailroom): the pipeline this dataset evaluates.
- [`Exios66/local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox): evaluation harness and tracked run reports.

## Citation

```bibtex
@misc{mailroom_dataset_2026,
  title        = {Mailroom Dataset},
  author       = {Lucius-Morningstar},
  year         = {2026},
  howpublished = {\url{https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset}},
  note         = {Revision ed7576b676343e0b402ec5412cded301e629bdee (v9.1)}
}
```

Please also cite CUAD (Hendrycks et al., 2021) and MAUD (Wang et al., 2023)
when using the contract or merger documents.
