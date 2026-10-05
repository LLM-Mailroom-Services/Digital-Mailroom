# Dataset cards

`mailroom-dataset.card.md` is the proposed Hub README for
[`Lucius-Morningstar/mailroom-dataset`](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset).
It was written from what this repo documents about the dataset (loader code in
`src/mailroom_sandbox/corpus.py`, run configs, reports and `docs/evals.md`),
without access to the live card or parquet files. Confirm the items below
before publishing.

## Confirm before publishing

| Item | Why it needs confirming | Where the draft stands |
| --- | --- | --- |
| `license` | Contracts (CUAD) and mergers (MAUD) are CC BY 4.0; the other three types have no recorded source in this repo | `cc-by-4.0`, pending owner confirmation |
| Source of corporate records, correspondence and insurance claims | Not recorded here (EDGAR exhibits? synthetic?) | Card defers to the dataset changelog; replace with the real provenance |
| Column names | The loader accepts several aliases (`expected` / `expected_doc_class` / `doc_type`; `doc_text` / `text`; `id` / `document_id`) | Card lists the names the loader prefers; check against the parquet schema |
| Test split per class | Run configs record contract 60, corporate_record 47, correspondence 62, insurance_claim 114 and merger_agreement ~17 test rows (300). The docs and the ModernBERT held-out eval say 323, with 85 correspondence | Card states 323 total with no per-class split table; reconcile before adding one |
| Full `gt_fields` key list | Docs describe a 27-key schema; this repo only shows the subset in `data/fixtures/hf/docclass_mini.jsonl` | Card lists key groups, not all 27 keys |
| Citation author | Hub namespace used as author | Replace with the preferred author and institution |
| v9.1 tag | `FAMILY_HF_REVISION` notes the Hub tag is still pending (#58) | Card cites the revision SHA |

## Publish

```bash
# after reviewing the card
hf upload Lucius-Morningstar/mailroom-dataset docs/datasets/mailroom-dataset.card.md README.md \
  --repo-type dataset --commit-message "Update dataset card"
```

This sandbox's cloud environment cannot reach `huggingface.co`, so publishing
runs from a machine with Hub access and a write token.
