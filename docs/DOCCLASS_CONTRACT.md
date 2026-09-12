# DOCCLASS_CONTRACT.md — the mailroom-dataset corpus contract

**Status:** canonical bridge between the `Lucius-Morningstar/mailroom-dataset`
corpus (v9, 3,302 rows — published 2026-09-12 as the successor of the frozen
v8 baseline `Lucius-Morningstar/mailroom-corpus`) and the Mailroom pipeline.
Companion to `docs/v7-taxonomy.md`
(taxonomy doctrine) and `docs/reports/audits/docclass_merged_baseline.md`
(frozen v0.1-working baseline). Plan reference: `docs/mailroom-corpus-plan.md`
§80–§81.

## 1. What mailroom-dataset is

mailroom-dataset is the **canonical Mailroom ingress/evaluation corpus** — the
controlled document universe used to simulate documents arriving at the
Mailroom (plan §1, §93). It exists to answer:

> Given this incoming document or document stream, does Mailroom correctly
> ingest, classify, route, extract, group, validate, adjudicate, retry when
> necessary, and reach the correct final state?

Its multi-source fusion (CUAD + MAUD + EDGAR + Enron + CMS DE-SynPUF) is
intentional: those sources are the document families Mailroom must handle,
not a statistically natural population. Do not "fix" the fusion.

## 2. What it is not

- **Not a model-training dataset** (§1, §93). Splits are evaluation
  partitions for sampling/reproducibility, not ML train/test semantics (§49).
- **Not a generic benchmark** — no artificial class balance, no blind
  leaderboard config (§33, §47, §83). The `default` config is agent-blind
  (no label columns) for evaluation hygiene, not a benchmark surface.
- **Not complete** — it is the current working corpus; coverage gaps are
  recorded honestly in the baseline audit, not papered over.

## 3. Classes

The corpus represents exactly the **five-class live Mailroom taxonomy**
(docs/v7-taxonomy.md): `contract`, `merger_agreement`, `corporate_record`,
`correspondence`, `insurance_claim`. There is no extended live taxonomy
awaiting corpus coverage. `compliance_filing`, `court_opinion`, and
`due_diligence` are **retired former classes** — historical/changelog
vocabulary only (§60); the pipeline config retains a `status: retired`
`compliance_filing` entry as inert machinery (see v7-taxonomy.md §4).
Reintroducing any retired class is a new taxonomy decision with its own
`taxonomy_version` bump — never a silent "restoration".

`merger_agreement` is a **distinct classification class** that shares
extraction machinery with `contract` (§6):

| | |
|---|---|
| classification | `merger_agreement` |
| routing | `contracts_specialist` |
| extraction_schema | `ContractExtraction` |

Classification taxonomy and specialist implementation are separate concerns;
never merge `merger_agreement` into `contract` because they share a
specialist.

## 4. Core concepts

- **Document** — one incoming artifact; the corpus row. Identity is
  `document_id`: unique, deterministic, stable across rebuilds, independent
  of row order / split / Hub config, never a row index (§9). Derivation:
  `mailroom_eda.identity.document_id`.
- **Matter** — the real-world legal/insurance matter a document belongs to
  (grouping concept; `matter_id`). **Group** — a logical bundle within a
  matter (`group_id`, `group_role`). Both are P2 ground truth, gated on the
  §14A backfill methodology (source-native vs. synthetically constructed,
  never silently mixed).
- **`expected_fields`** — the canonical extraction ground truth (§18), scored
  by llm-dojo-scoring's deterministic field scorer (`date`/`id`/`money`/
  `name`/`free_text`/`entity_list`). Never replaced by generic `entities[]`.
- **Provenance** — `source_corpus` / `source_document_id` /
  `source_filename` / `source_revision` (§10): where the document originated.
  Source is an evaluation dimension, separate from taxonomy (§8).
  `annotation_provenance` (§43: source/method/model/prompt_version/
  confidence/reviewer/timestamp) distinguishes source_native, verified_join,
  human_annotated, human_adjudicated, LLM_assisted, LLM_zero_shot, heuristic,
  synthetic ground truth (§20) — P1.
- **Ground truth** — the 27-key GT schema on the `ground_truth` config:
  classification (`expected`, `expected_subclass`), per-class extraction GT,
  enrichment (content_topic, sentiment), and correspondence intent
  (`intent`, `intent_source`, `intent_confidence`, `intent_status` — §21;
  intent is its own dimension, never a subclass).
- **Evaluation** — cascaded, never collapsed (§22): classification_correct →
  routing_correct → extraction_correct → grouping_correct →
  final_pipeline_success. Reuse llm-dojo-scoring; never duplicate it (§24).

## 5. Dataset → Mailroom mapping (§81)

| Dataset concept | Mailroom concept |
|---|---|
| `document_id` | document identity |
| `matter_id` | matter/session grouping (`session_id`) |
| `document_type` (`expected`) | sorter output |
| `document_subtype` (`expected_subclass`) | sorter subtype |
| `expected_fields` | specialist ground truth |
| `source_corpus` | provenance |
| `simulation_run_id` | evaluation session |
| `expected_stage` | pipeline terminal expectation |
| `review_expected` | review routing |
| `retry_expected` | recovery behavior |
| `relationships` | document grouping/association |

## 5A. Evidence spans (§19)

Extraction ground truth gains optional span-level evidence where the source
corpus has exact annotations (field, value, start, end) — CUAD clauses,
dates, monetary values, identifiers, parties. The v7 `ground_truth` config
carries no spans (label-level GT only; verified 31 columns), so the span
schema is defined here as the contract and population rides the first
sanctioned schema revision (v0.2 release decision, §84) — never silently
absent: absent spans are the explicit `''` corpus convention.

## 6. Revision discipline (§44–§46)

- **Dataset renamed 2026-09-02** (human directive): the Hub repo
  `Lucius-Morningstar/docclass-merged` is now
  `Lucius-Morningstar/mailroom-corpus` — "docclass" was always a
  placeholder. The move preserved git history; the pinned revision
  `bb57c5ad` resolves unchanged at the new name and the old id serves a
  Hub redirect. The internal pipeline slug (`docclass-merged`) and the
  `source-docclass-merged` trace tag are retained for trace-tag
  immutability; the release marker `docclass-merged-v0.1-working` names
  the frozen §4 baseline and is a version label, not the dataset name.

- The corpus is consumed **pinned**: `FULL_CORPUS_REVISION` in
  `packages/llm-mailroom/src/pipeline/hf_corpora.py`. Never evaluate against
  unpinned `main`/`latest` — and never against a stale pin: re-check the pin
  after every corpus-side push (baseline Finding 1).
- Every evaluation trace records: dataset_name, dataset_revision,
  document_id, matter_id, simulation_run_id, taxonomy_version (§45).
  Implemented in llm-mailroom `run_pipeline(dataset=...)`: `dataset_name` /
  `dataset_revision` come from the pinned corpus constants;
  `taxonomy_version` currently equals the corpus schema label (`v7`, the
  five-class label surface of `docs/v7-taxonomy.md`) until the first
  explicit taxonomy decision gets its own `taxonomy_version` bump (§62 —
  taxonomy and dataset version independently); live non-corpus runs carry
  no dataset identity rather than a fabricated one.
- Every experiment is reproducible from the tuple: dataset revision +
  taxonomy revision + prompt version + model/provider + runtime
  configuration (§46).
- Publishing goes ONLY through the centralized helpers in
  `packages/mailroom-corpus-eda/src/mailroom_eda/` (`hf_interface`,
  `dataset_export`, `docclass_uploader`, `intent_backfill`) — cast-safe
  metadata, line-boundary-safe JSONL, sha256 verification, surgical card
  renders, blind-config label guard (§44A). No ad-hoc upload code.

## 7. Release gates (§91 + §4A)

A corpus release fails validation if: `document_id` is not unique; a taxonomy
value is invalid; a subtype does not belong to its document type (catch-all
`other` excepted); `expected_fields` violates the specialist schema; required
provenance is missing; the dataset revision is not pinned; annotation
provenance is missing; or source/document identity is ambiguous. **Plus
(§4A):** a release fails if any row lacks a resolvable license/provenance
chain, or if a non-synthetic, non-previously-cleared source is added without
an explicit PII review note in Evidence. Matter-aware and recovery releases
add their own gates (§91).

## 8. Releases (§84)

## 9. Matter/group backfill methodology (§14A — the P2 prerequisite decision)

Grouping ground truth is backfilled by an explicit, honestly-labeled method —
never a silent default:

1. **`source_native_thread`** (used first, where it genuinely exists):
   Enron correspondence carries real thread/date/sender structure — a reply
   chain is a legitimate `group_role: correspondence` sequence with real
   matter structure. `matter_construction: source_native_thread`.
   **Verified structurally unavailable in this corpus family** (HF audit
   2026-09-02, pin `bb57c5ad`): the CMU maildir itself carries no
   `In-Reply-To`/`References` headers — 0/350 raw correspondence files, and
   0/247,523 upstream `enron-correspondence-dedup` rows. No backfill can
   recover them; the implementation exists (`matter.source_native_threads`)
   and yields 0 matters, guarded so it can never silently co-exist with
   other constructions.
2. **`heuristic_reconstructed`** (the only source-field grouping available):
   normalized-subject + custodian + 30-day-window conversation
   reconstruction (degenerate `Re:`/`FW:`-only subjects excluded). Uses real
   fields but is NOT ground truth — every assignment is flagged, and live
   coverage is measured: **266/350 meaningful subjects; 19 rows in 7
   multi-member threads; 331 unassigned** (`test_matter.py` §84B checks).
   Counted separately everywhere; never merged into a "matters" total.
3. **`synthetic_constructed`** (only where no natural sibling exists):
   standalone contracts/records get manufactured bundles (e.g. contract +
   plausible amendment/exhibit) declared a matter FOR GROUPING-EVALUATION
   PURPOSES. `matter_construction: synthetic_constructed` — flagged, never
   presented as discovered structure. Given finding 2, this is the primary
   path to meaningful multi-document grouping evals for the non-correspondence
   classes.

The two constructions are never mixed silently: any coverage report that
counts "matters" reports source-native, heuristic-reconstructed, and
synthetically-constructed rows as separate columns (a merged count
overstates how much real multi-document behavior is tested — with header
threads structurally absent and subject threads at 19/350, the honest
current total of *real* grouping structure is near zero). Vocabulary
(closed): `MATTER_CONSTRUCTION`, `GROUP_ROLES` (§16), `RELATIONSHIP_TYPES`
(§15), `DUPLICATE_TYPES` (§12), `FAILURE_STAGES` (§58) — all machine-read
constants in `mailroom_eda.eval_contract`; derivations in
`mailroom_eda.matter` (header threads + subject reconstruction + the
never-mix guard). This decision unblocks P2
(group_role/relationships/multi-document cases).

### 9A. Synthetic bundle families (§14 — the `synthetic_constructed` builder)

`mailroom_eda.bundles` manufactures §14 bundle instances over REAL anchor
rows: five family templates (`legal_contract_family`,
`insurance_claim_family`, `merger_family`, `corporate_record_family`,
`correspondence_thread_family` — the first two are §14's worked examples and
must span ≥2 classes), each instance = one real anchor (keeps its filename
and text, `group_role: primary`) + manufactured siblings whose `doc_text` is
an explicit scaffold template marked
`[SYNTHETIC SIBLING — grouping-evaluation scaffold]`. All members carry
`matter_construction: synthetic_constructed`; manufactured members add
`synthetic: true`, `bundle_family`, and a `MATTER-SYN-*` filename namespace
that cannot collide with snapshot filenames. `with_duplicates` adds a
`template_variant` duplicate per instance (§87/§12 — the only duplicate type
a scaffold can honestly manufacture). Roles/relationships are validated
against the closed vocabularies at build time. Seeded (`seed=42`), fully
deterministic, returns `(rows, manifest)` — **writes nothing; publishing
bundle rows is the §84 `v0.3-matter-aware` decision.**
**PUBLISHED 2026-09-02** (bundles config, 50 rows) — together with the
§27–§29/§48 STREAM tier: `bundles.build_streams` interleaves the bundle
matters round-robin (`RUN-SIM-001`, `simulation_run_id` +
`sequence_position` per row, §27) with no-matter `distractor` rows on a
fixed cadence (§29), so the published `streams` config (62 rows/39 cols) is
the Mode B ingress simulation.

### 9B. Evaluation fixture content (§68–§72A — the P1/P3 content layer)

`mailroom_eda.fixtures` builds the fixture CONTENT on top of the P1
vocabularies (which stay the single source of truth — every row's
review/retry expectations are derived through `eval_contract`, never
hardcoded):

- **§70 calibration quartet** — per class, the four
  `correct_high/correct_low/wrong_high/wrong_low` cells probed AT the live
  routing bands (`probes_confidence` sits just inside the band edge being
  probed, so off-by-epsilon routing bugs are visible). Cell → fixture-kind
  mapping is closed (`CONFIDENCE_CELL_FIXTURE_KIND`): `correct_high` →
  `high_confidence` (archive), `correct_low` → `low_confidence` (review),
  `wrong_high` → `conflicting` (the silent-archive failure mode under
  test — judge catch → review), `wrong_low` → `retry_review` (retry →
  human_review).
- **§72A review/arbiter scenarios** — review-correction (human fixes an
  extraction from an unreadable scan → archive) and one scenario per closed
  arbiter outcome (`ARBITER_OUTCOMES = stands / re_extract /
  escalate_human_review`).
- **§58 failure-stage matrix** — one minimal failure fixture per stage of
  `FAILURE_STAGES` (ingestion → archival), the spine P3 needs to score
  first-pass vs. recovered success per stage.

All rows use the `fixture:` filename namespace (no snapshot collisions) and
derive specialist routing from the same registry as P1. **Scaffold-only;
publishing fixtures is the §84 `v0.4-recovery-suite` decision.**

### 9C. P4 priorities and the P5 ledger (§89–§90)

- **P4**: `scripts/expansion_priorities.py` generates
  `docs/reports/audits/docclass_expansion_priorities.{md,json}` from the
  committed §40–41 coverage matrix — priority is evaluation value, not raw
  row count (§89's own discipline): class families score on zero/partial
  field gaps and scarcity (half the median class size); the corpus-level
  scenario axes (grouping, adversarial) are high by construction;
  `format_diversity` carries the backlog's single documented override
  (sequencing: it pays off only once P3 fixtures graduate).
- **P5**: `docs/reports/audits/docclass_p5_surfaces.md` is the honest
  status ledger for every §90 surface and §25 metric group — scaffolded /
  blocked-on-runs / blocked-on-expansion, each with its unlock. P5 surfaces
  compute only after the §84 publication decision feeds them real runs.

| Marker | Content |
|---|---|
| `v0.1-working` | frozen baseline (this contract's companion audit) |
| `v0.2-mailroom-hardened` | identity + provenance + content hashes ship on the published configs; taxonomy/evaluation contract |
| `v0.3-matter-aware` | grouping + relationships + multi-document cases |
| `v0.4-recovery-suite` | review + retry + arbiter scenarios |
| `v1.0-mailroom-evaluation` | stable regression/evaluation corpus |

Conceptual targets, not mandates to manufacture releases (§84).
