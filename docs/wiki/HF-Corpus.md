# HF corpus — mailroom-corpus

The corpus family is published on the
[Lucius-Morningstar HF org](https://huggingface.co/Lucius-Morningstar) via
the **centralized** helpers in
`packages/mailroom-corpus-eda/src/mailroom_eda/` — never ad-hoc upload code.

## mailroom-corpus (v8 — verified 2026-09-02, HUB-028; renamed from `docclass-merged` 2026-09-02)

| Fact | Value |
| --- | --- |
| Dataset | [Lucius-Morningstar/mailroom-corpus](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-corpus) |
| Schema | **v8** (insurance LOB expansion, HUB-028; §84 hardening rebuilt on v8, HUB-032) |
| Rows | **2,000** — insurance_claim 950 (carrier/inpatient/outpatient/pde 600 · property 200 · auto 150) · contract 509 · correspondence 350 · merger_agreement 152 · corporate_record 39 |
| Configs | `default` (blind, 4 cols) + `ground_truth` (60 cols: 31-key GT schema incl. intent provenance + §84 hardened identity/eval-contract/matter columns) + `bundles` (38 cols, 50 rows) + `streams` (39 cols, 62 rows — §27–§29/§48 STREAM tier: `RUN-SIM-001` interleaved ingress, 12 no-matter distractors) + `fixtures` (30 cols, 32 rows) |
| Split | train 1,792 / test 208 on `default` + `ground_truth`; md5(filename) % 10 == 0 → test (stable) |
| Strata | 50 (expected × expected_subclass) |
| HF revs | data tip `bba2f750` (v8); hardened-on-v8 at `eafe1ab4` |

### v8 insurance LOB expansion (HUB-028, 2026-09-02)

- **property (200)**: `gratex/GNOTHEIA-synthetic-insurance-dataset` (Apache-2.0)
  — FNOL bundles (notice + invoices + police confirmations + photo evidence)
  stratified by loss event (fire/water/storm/burglary/…); determination
  `pending` (honest — no adjudication in the source).
- **auto (150)**: `bdr-ai-org/insurance-motor-claims-decision-v1` (MIT) —
  decision letters stratified by accident type × APPROVE/REVIEW/REJECT (all
  reject rows included); feature-grounded denial reasons; adjuster pseudonyms;
  determination approved/pending/denied.
- **Full GT conformance**: all 950 insurance rows carry intent/subject/
  keywords + intent provenance (CMS backfilled template-derived; property/auto
  authored at build); claimed_amount recovered from doc text on 10 v7 gap
  rows; 3 train-only outpatient `:2` date gaps documented as source-N/A;
  test-split nullification enforced (zero empty class-relevant keys).
- **Metadata**: source_dataset / source_revision / source_row_id / lob /
  peril / license ride every row (cast-safe union).
- **License note**: corpus CC-BY-4.0; v8 additions Apache-2.0 + MIT.
  XpertSystems ins001/007/hlt015 (CC-BY-NC-4.0) excluded; INSURBIAS
  (CC-BY-4.0) deferred to v9.

### §84 hardening rebuilt on v8 (HUB-032, 2026-09-02 — commit `eafe1ab4`)

- **Repair**: the interleaved HUB-028/HUB-022 publishes left the Hub mixed
  (blind `default` 2,000 rows vs `ground_truth` 1,650×60); the hardened
  `ground_truth` is now rebuilt over ALL 2,000 rows (identity →
  eval_contract → §14A matter chain via `scripts/publish_hardened.py`).
- **Stability**: published v7 `document_id`s unchanged (0 drift over the
  v7 train rows); v8 LOB rows carry their own `source_corpus` /
  `annotation_source` (GNOTHEIA / BDR) + pinned upstream `source_revision`
  via `metadata.source_dataset` / `.source_revision` — the class map stays
  authoritative so published IDs never churn.
- **Annotation provenance** (2,000 rows): synthetic 950 (600 DE-SynPUF +
  200 GNOTHEIA + 150 BDR) · source_native 700 · verified_join 162 ·
  llm_zero_shot 92 · human_annotated 96.
- **Matter**: 19 rows in 7 threads (`heuristic_reconstructed`, all
  correspondence — insurance rows carry no custodian); 1,981 unassigned.
- **Bundles/fixtures**: re-derived over the v8 base (insurance family now
  spans carrier + auto anchors); fixtures byte-identical. All §91 release
  gates green; sha256 local==hub (10/10 files).
- **Streams (v0.3 addendum, 2026-09-02)**: NEW `streams` config — §27–§29/
  §48 STREAM eval tier. `RUN-SIM-001` interleaves the 10 bundle matters
  round-robin (A1 B1 A2 C1 B2 … — never matter-contiguous, §28) with 12
  `distractor` rows injected every 4 positions (real corpus rows carrying no
  matter/group, §29); every row is `simulation_run_id` + `sequence_position`
  reproducible (§27). 62 rows total (39 cols).

## The ground-truth schema (27 keys)

`label_evidence, content_topic, topic_evidence, sentiment_score,
sentiment_label, sentiment_evidence, claim_number, policy_number, insurer,
insured_party, claim_type, date_of_loss, date_filed, claimed_amount,
adjuster, damages_description, coverage_determination, denial_reasons,
supporting_documents, cuad_clause_labels, maud_clause_labels, intent,
subject_matter, keywords, intent_source, intent_confidence, intent_status`

Corpus strata vocabulary (per doc type, used by eval targets):

| Doc type | Subclasses (examples) |
| --- | --- |
| contract | 26 incl. Consulting Agreements, Development, IP, Hosting |
| corporate_record | articles_of_incorporation, bylaws, other, powers_of_attorney, rights_instrument |
| correspondence | attorney_demand, demand, email, letter, meeting_request, memo, notice, press_release |
| insurance_claim | carrier, inpatient, outpatient, pde, property, auto |
| merger_agreement | all_cash, all_stock, mixed_cash_stock, mixed_cash_stock_election, other |

## The EDA pipeline (P0–P6)

```bash
cd packages/mailroom-corpus-eda
uv run python run_all.py                 # full pipeline; only a full run writes SUMMARY_REPORT.*
uv run python run_all.py --phases P3 P4  # figures only (subset runs never clobber the summary)
```

P0 download/manifest → P1 integrity → P2 composition → P3 static PNGs
(**30**) → P4 interactive Plotly HTMLs (18) → P5 JSONL/parquet export →
P6 intent-coverage audit. Deterministic (`RANDOM_STATE=42`); rebuilds of
JSONL/parquet are byte-identical.

**Canonical-bytes rule**: the committed `reports/` figures are canonical —
regenerated interactive HTMLs embed a random per-render UUID and are never
byte-identical; treat local regeneration as scratch output only (HUB-008).
`SUMMARY_REPORT.json` reports `figures: 30` (HUB-012 fixed the stale 27
counter and published the fix upstream).

## Upload helpers

`hf_interface` (Hub client, sha256 verify) · `dataset_export` (cast-safe
metadata, line-boundary-safe JSONL, parquet staging) · `docclass_uploader`
(v7 publish, surgical card render, leak guard) · `intent_backfill`
(checkpointed correspondence intent hydration). See the `huggingface`
opencode skill for the full workflow.
