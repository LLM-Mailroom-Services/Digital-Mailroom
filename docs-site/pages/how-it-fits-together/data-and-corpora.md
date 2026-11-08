---
description: The dataset family behind every evaluation and training run.
icon: database
title: Data and corpora
---

# Data and corpora

Every evaluation, training run and pilot in the constellation draws from one dataset family on Hugging Face, published under the [`Lucius-Morningstar`](https://huggingface.co/Lucius-Morningstar) organization. This page is the constellation-wide rules summary.

The full GitBook breakdown — 55 strata, configs, source cards, EDA reports, and all 30 figures — lives in [**Mailroom dataset**](../mailroom-dataset/mailroom-dataset.md). Live dashboard, Hub Dataset Viewer, and Plotly charts are on [Visualizations](../mailroom-dataset/visualizations.md).

## The canonical dataset

[`Lucius-Morningstar/mailroom-dataset`](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset) is the corpus every repository measures against. It is called "v1" on the Hub and "v9" in the corpus family's lineage; both names refer to the same thing.

| Fact                     | Value                                                                                                                       |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| Documents                | 3,302 (2,979 train, 323 test)                                                                                               |
| Document classes         | 5                                                                                                                           |
| Class-by-subclass strata | 55                                                                                                                          |
| Pinned revision          | `ff4ca546` (tag v9.3)                                                                                                       |
| Frozen parent            | [`mailroom-corpus`](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-corpus) v8, 2,000 rows, revision `eafe1ab4` |

The published pin is `v9.3` (`ff4ca546`). As of 2026-11-08, `llm-mailroom` 0.9.3 still reads the code pin `v9.1` (commit `bc9eab28`, data commit `ed7576b6`), so a result from it must name the pin it used. (The 2026-10-07 snapshot had four consumers on v9.1: eval-environment, mailroom-ml, llm-mailroom 0.8.0 and the sandbox.) See [Mailroom dataset](../mailroom-dataset/mailroom-dataset.md).

### Classes and sources

| Class              |  Rows | Source                                             | License                                                  |
| ------------------ | ----: | -------------------------------------------------- | -------------------------------------------------------- |
| `insurance_claim`  | 1,100 | CMS DE-SynPUF, GNOTHEIA, BDR, INSURBIAS narratives | Apache-2.0 / MIT / CC BY 4.0                             |
| `correspondence`   | 1,000 | Enron de-duplicated corpus                         | research use; contains real names, handle conservatively |
| `contract`         |   600 | CUAD v1 (509) + SEC EDGAR EX-10 (91)               | CC BY 4.0 / US public domain                             |
| `corporate_record` |   450 | SEC EDGAR S-1 and 8-K exhibits                     | US public domain                                         |
| `merger_agreement` |   152 | MAUD v1                                            | CC BY 4.0                                                |

### Configs

| Config         |  Rows | Contents                                                                           |
| -------------- | ----: | ---------------------------------------------------------------------------------- |
| `default`      | 3,302 | Document text and metadata only. No labels, by construction.                       |
| `ground_truth` | 3,302 | Labels (`gt_fields`), hashes, the evaluation contract, matter and group membership |
| `bundles`      |    50 | Synthetic multi-document bundles built over real anchors                           |
| `streams`      |    62 | An interleaved ingress stream with distractors                                     |
| `fixtures`     |    32 | Recovery and adversarial fixtures used for calibration                             |

To use it, load `default` and `ground_truth` separately and join on `filename`:

```python
from datasets import load_dataset
blind = load_dataset("Lucius-Morningstar/mailroom-dataset", "default")
gt = load_dataset("Lucius-Morningstar/mailroom-dataset", "ground_truth")
```

The pipeline itself does not depend on the `datasets` library; it loads the corpus through `pipeline/hf_corpus_loader.py`, which also verifies each row's `content_sha256` against its text.

## Rules everyone follows

* **Pin a revision.** Never read the live tip of a dataset. Code records the revision it used so results are reproducible.
* **Keep labels blind.** The model under test only ever sees the `default` config. Labels live in a separate config precisely so that a missed filter cannot hand the answers to the model.
* **One split rule.** Across the whole family, `md5(filename) % 10 == 0` means test, so a document is in the same split in every dataset that contains it. Because the split is a pure function of the filename, no repository needs to store or share a split file. A training builder must still apply the rule to exclude test rows.
* **Subclasses are strata, not classes.** `expected_subclass` is a second-level label (for example `all_cash` under `merger_agreement`). It is not promoted to a top-level class unless the pipeline's taxonomy adopts it.
* **Retired classes stay retired.** `compliance_filing`, `court_opinion` and `due_diligence` are no longer live classes.

## Other datasets in the family

| Dataset                                             | Role                                                                   |
| --------------------------------------------------- | ---------------------------------------------------------------------- |
| `docclass-pilot`                                    | 48 class-by-subclass examples (of that pack's 48 strata — not the canonical 55), for quick pilots |
| `enron-correspondence-dedup`                        | 247,523-row de-duplicated Enron pool that correspondence is drawn from |
| `mailroom-cuad-contracts-full`                      | Byte-verified CUAD contract mirror                                     |
| `cms-desynpuf-insurance-claims`                     | Rendered CMS EOB documents                                             |
| `mailroom-finetune`, `mailroom-modernbert-training` | Training copies used by mailroom-ml                                    |
| `mailroom-modernbert-classifier`                    | Where mailroom-ml publishes the trained classifier                     |
| `legalbench-full`                                   | LegalBench task pack (not a pipeline-ingest corpus)                    |

## Which repository owns what

| Concern                                          | Repository                                                                                                                                                                           |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Correspondence sample from Enron                 | [Enron-Evaluation-Environment](../repository-guides/repos/enron-evaluation-environment.md)                                                                                           |
| Insurance claims sample from CMS                 | [claims-data-eda](../repository-guides/repos/claims-data-eda.md)                                                                                                                     |
| Full-corpus EDA, dataset cards, upload helpers   | [Mailroom-Corpus-EDA](../repository-guides/repos/mailroom-corpus-eda.md)                                                                                                             |
| Loading the corpus into the pipeline             | [llm-mailroom](../repository-guides/repos/llm-mailroom.md) (`pipeline/hf_corpus_loader.py`)                                                                                          |
| Subset grammar and stratified sampling for evals | [eval-environment](../repository-guides/repos/eval-environment.md) (`src/evals/cases.py`)                                                                                            |
| Taxonomy terminology (v7 onward)                 | [Digital-Mailroom](../repository-guides/repos/digital-mailroom.md) ([v7 taxonomy contract](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/v7-taxonomy.md)) |

The dataset cards (one per source) live in Mailroom-Corpus-EDA under [`docs/dataset-cards/`](https://github.com/Exios66/Mailroom-Corpus-EDA/tree/main/docs/dataset-cards), and `run_all.py` there reproduces every number on this page. GitBook copies of those cards, plus the EDA figures, are in [Mailroom dataset](../mailroom-dataset/mailroom-dataset.md).

## Sources

Every figure on this page is reproduced by `run_all.py` in Mailroom-Corpus-EDA against Hub tag `v9.2` / `670e8bc6`, and is cross-checked against the canonical write-up:

| Claim on this page | Source of record |
| ------------------ | ---------------- |
| Row counts (3,302 total; 1,100 / 1,000 / 600 / 450 / 152), 55 strata | [`reports/tables/strata_counts.csv`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/reports/tables/strata_counts.csv) and [`reports/SUMMARY_REPORT.md`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/reports/SUMMARY_REPORT.md) (generated 2026-09-13) |
| Frozen parent (2,000 rows) and the delta to 3,302 | [Mailroom dataset](../mailroom-dataset/mailroom-dataset.md) |
| Config table (3,302 / 3,302 / 50 bundles / 62 streams / 32 fixtures) | [Configs](../mailroom-dataset/configs.md), asserting `hf_corpus_loader` config names |
| Text-length and token-budget distributions | [`reports/tables/text_length_stats_by_type.csv`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/reports/tables/text_length_stats_by_type.csv), [`token_budget_coverage.csv`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/reports/tables/token_budget_coverage.csv) |
| Per-corpus narrative and caveats | [Source corpora](../mailroom-dataset/source-corpora/README.md), which carries the primary citations |
| Family datasets and their sizes | Each dataset's own Hub card; sizes are asserted by the publishing repo's EDA, not by this page |

Figures and narrative: [EDA reports](../mailroom-dataset/eda-reports.md) and [Visualizations](../mailroom-dataset/visualizations.md).
