# Changelog

All notable changes to `llm-dojo-scoring` are documented here.
Format based on Keep a Changelog; versioning is SemVer.

## [Unreleased]

## [0.16.0] - 2026-09-27

### Added

- **BERT fast-path registry surface (#106 / mailroom-ml intake gate)** — five
  emitter-only metrics registered for llm-mailroom `SCORE_CONFIGS`:
  `bert_pass`, `bert_sorter_agreement`, `bert_fail_soft`, `bert_elapsed_ms`,
  `fast_path_est_cost_usd` (with `metric_meta` citations). Covered by
  `tests/test_consumer_compat.py` and registry preservation tests.

### Changed

- **Classification alignment with live mailroom taxonomy** — doc-class regex
  order prefers `merger_agreement` over `contract`; retired classes
  (`court_opinion`, `due_diligence`) drop out of default normalization;
  `accuracy` / macro helpers skip `ERROR:` rows like sibling eval loops;
  `confusion_matrix` extends explicit label lists with observed classes;
  `macro_prf(..., normalize=False)` no longer zeroes when labels are raw.
- **Corpus prose** — mailroom-dataset v9 GT-closure pin (`46a4d3c2`, 3,302
  rows) and Enron sentiment population counts.
- **Prompt catalog** — docclass family versions renamed to
  `*_mailroom_prompts_v0` / `sorter_mailroom_v0` (templates synced from the
  Digital-Mailroom constellation monorepo).
- Package version **0.16.0**. Consumer pin:

  ```
  llm-dojo-scoring @ git+https://github.com/Exios66/llm-dojo-scoring.git@v0.16.0
  ```

### Unchanged

- All calculation modules and their APIs — this release is purely additive
  organization on top of the engine (Hungarian matching, embedding rescue,
  bootstrap CI, CUAD equivalences untouched).
