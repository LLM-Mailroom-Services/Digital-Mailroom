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

## [0.15.0] - 2026-09-14

### Added

- **`configure_from_taxonomy(taxonomy)` — the single taxonomy→settings wiring
  path** (hub #62). Consuming projects (llm-mailroom, llm-entity-extraction,
  agent-mailroom) load their own `taxonomy.yaml` and pass the parsed dict
  here; the package applies the `field_scoring:` block (including the new
  `type_bands` overrides and `factuality_verification`), equivalence sets,
  cost models, doc-class field-type maps, and display labels in ONE place.
  Honors the `LLM_DOJO_SCORING_CONFIG` env-file escape hatch (external file
  wins wholesale). Before, each consumer re-implemented the coercion
  (`_apply_taxonomy_settings` / `apply_taxonomy_settings` in three copies).
- **Mailroom glue promoted into the package** — `get_type_bands()`,
  `field_is_ambiguous(field_type, score)`, and `warm_embedding_model()`
  (off-document-path embedding preload, O-10) now live in
  `llm_dojo_scoring.field_scoring` instead of per-package shims.
- **`get_field_types(doc_class)` auto-resolves** from the taxonomy wired via
  `configure_from_taxonomy()` (captured in `Settings.doc_class_field_types`)
  — no need to pass the taxonomy on every call.
- **`FieldScoringSettings.type_bands`** — per-field-type ambiguous-band
  overrides (`"always"` / `"never"` / `(low, high)`), populated by
  `configure_from_taxonomy()`.
- New top-level re-exports so dependants can `from llm_dojo_scoring import
  ...` instead of deep submodule imports: `get_type_bands`,
  `field_is_ambiguous`, `warm_embedding_model`, `configure_from_taxonomy`,
  `get_field_types`, `normalize_text`, `parse_date`, `parse_money`,
  `score_category_presence`, `peel_non_extraction_fields`, `get_jaccard`,
  `INTAKE_SPAN_KEYS`.

### Changed

- Package version **0.15.0**. Consumers upgrade their pin to
  `llm-dojo-scoring @ git+https://github.com/Exios66/llm-dojo-scoring.git@v0.15.0`
  and can drop their local field-scoring shims.

## [0.14.0] - 2026-09-13

### Changed

- **Corpus identity migrated to `Lucius-Morningstar/mailroom-dataset`**
  (v1, canonically **v9** of the mailroom corpus family, 3,302 rows; issue
  hub #18). `CORPUS_ID` in `llm_dojo_scoring/corpus.py` now points at
  `mailroom-dataset` — the old `docclass-merged` repo is deleted, and the
  frozen v8 `mailroom-corpus` remains only as lineage baseline. Module
  titles/docstrings aligned (`mailroom-dataset corpus alignment`).
- **v9 GT surface:** `doc_bundles.py` headline grounding count updated to
  3,302 GT rows; `suites.py` docclass-family prose aligned; insurance
  subclass vocabulary notes the v8/v9 synthetic LOB lines (`property` /
  `auto`, HUB-028/HUB-041) alongside the CMS DE-SynPUF source tokens.
- **Docs sweep:** README/SCORING/tests module docstrings updated to the
  `mailroom-dataset` identity (historical `docclass-merged` prompt-family
  identifiers retained as product names).
- Package version **0.14.0**. Consumer pin:

  ```
  llm-dojo-scoring @ git+https://github.com/Exios66/llm-dojo-scoring.git@v0.14.0
  ```

## [0.13.0] - 2026-08-30

### Changed

- **Pared extraction field maps** aligned to llm-mailroom **v0.6.0**
  (`EXTRACTION_SCHEMAS` / `taxonomy.yaml` field_types):
  - **Retired from live `DEFAULT_FIELD_TYPES`:** open-ended
    `key_obligations`, `termination_clauses`, `key_provisions`, long
    `key_points`, `referenced_communications`.
  - **Contracts / mergers:** key entities + `cuad_clauses` / `maud_clauses`
    checklists (11 fields).
  - **Corporate / correspondence / insurance:** semantic trio
    (`intent` / `subject_matter` / `keywords`); insurance also has
    `claim_checklist`.
  - Default `partial_gt_fields` / `containment_fields` match mailroom
    (checklists + `subject_matter`; no obligation dumps).
  - Diagnostics `list_*` headlines prefer `cuad_clauses` →
    `claim_checklist` → legacy `key_obligations`.
  - `score_category_presence` default field is `cuad_clauses`.
- Package version **0.13.0**. Consumer pin:

  ```
  llm-dojo-scoring @ git+https://github.com/Exios66/llm-dojo-scoring.git@v0.13.0
  ```

  Typed-field scoring formulas are unchanged; only which fields enter the
  soft overall mean / field-micro board changed.

### Added

- `LEGACY_FULL_EXTRACTION_FIELD_TYPES` — pre-v0.6.0 maps that still score
  free-text obligation dumps (historical rescoring only).
- `suite.score(..., presence_expectations=...)` wires
  `extraction_category_presence` the same way Enron/MAUD extras are peeled.
- `tests/test_pared_extraction.py` + `docs/MIGRATION.md` §3i.
- `docs/SCORING.md` field-map tables updated to the pared schema.

## [0.5.0] - 2026-08-21

### Added — unified scoring layer (KANBAN-061, entity-extraction issue #27)

- **`registry`** — YAML-backed metric definitions registry: every metric name
  mapped to a tier (`T0 HEADLINE` / `T1 CORE` / `T2 DEEP` / `T3 LOG`), units,
  aggregation, applicable agents, and the existing package function that
  computes it. Built-in default embeds the full current surface including all
  37 flat llm-mailroom `SCORE_CONFIGS` names as preserved aliases/notes.
  Override via `LLM_DOJO_SCORING_REGISTRY` env var or explicit path.
