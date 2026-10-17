# Local prompt variants

> Every eval-environment prompt version (archived / frozen / mutation, with memos and diffs) is catalogued in
> [`docs/prompts/`](../../docs/prompts/README.md) and runs with `--prompt-version <key>`. The stems in this
> directory are a different namespace: `sorter_v1.txt` here is the MAILROOM `sorter_v1`, not eval-environment `sorter_v1`.

These templates override mailroom's Langfuse-managed prompts (`get_managed_prompt`)
or the LangChain `PROMPT_VERSIONS` dict (Family B: sorter / contracts_specialist)
for a single experiment cell. Resolution: `src/mailroom_sandbox/prompt_registry.py`
(`source: local` + `file: <stem>` → `config/prompts/<stem>.txt`).

## Specialist production pins (DMR-074) — vendor mirrors

Byte-identical exports of vendored `llm-mailroom` code-defaults. **Not** a
floating Langfuse `production` label. Kept so historical reports and a vendor
refresh stay reproducible. `python scripts/sync_specialist_prompts.py` writes
**only** these stems.

| Stem | Agent | Source of truth | Notes |
| --- | --- | --- | --- |
| `contracts_specialist_v33` | `contracts_specialist` | `langchain_agents.prompts.PROMPT_VERSIONS["contracts_specialist_v33"]` | Mailroom production pin (entity-extraction has experimental v34–v41; **not** promoted). ~32k chars; doctrine lists retired `key_obligations` / `termination_clauses` then a PARED footer that forbids them. |
| `merger_agreement_specialist_production` | `merger_agreement_specialist` | `agents.merger_agreement_specialist.SYSTEM_PROMPT` | MAUD production (V0 + doctrine); **not** CUAD v33 |
| `corporate_records_specialist_production` | `corporate_records_specialist` | `agents.corporate_records_specialist.SYSTEM_PROMPT` | Base + `llm.prompt_doctrine` (doctrine still lists retired `key_provisions`) |
| `correspondence_specialist_production` | `correspondence_specialist` | `agents.correspondence_specialist.SYSTEM_PROMPT` | Base + doctrine (doctrine lists retired `key_points` / `referenced_communications`; V0 lists live `intent` / `subject_matter` / `keywords`) |
| `insurance_claims_specialist_production` | `insurance_claims_specialist` | `agents.insurance_claims_specialist.SYSTEM_PROMPT` | Base + doctrine (doctrine omits live `intent` / `subject_matter` / `keywords` / `claim_checklist`) |

Refresh vendor mirrors after a vendor sync:

```bash
python scripts/sync_specialist_prompts.py          # writes vendor stems only
python scripts/sync_specialist_prompts.py --check  # vendor identity + simplified stems present
```

## Specialist simplified pins (SAND-026 / issue #32) — experiment surface

These stems **are** the eval-environment frozen v1 catalog
(`contracts_specialist_v1` … `merger_agreement_specialist_v1`, sha256-locked in
[`eval_environment_lineage.json`](eval_environment_lineage.json)). Modal + vLLM
specialist evals inject this text (not vendor `SYSTEM_PROMPT` / Langfuse
`production`). Promotion issues #4–#8 are **closed**; do not edit the stems
without a sanctioned eval-environment re-freeze (eval-environment issue #19
tracks cross-repo alignment).

**Re-freeze (dojo #30):** `correspondence_specialist_simplified` and
`corporate_records_specialist_simplified` carry the corrected text the dojo ships
as `production_prompts` (eval-environment mutations `correspondence_specialist_v7`
and `corporate_records_specialist_v6`; the file body equals the dojo template
body, with no provenance comment). Their lineage rows name the `_v7` / `_v6`
keys and new sha256/chars; each row's `superseded` block keeps the original v1
key, sha256, chars and `frozen_at`. The other three stems are unchanged v1 bytes.
Default `sync_specialist_prompts.py` never rewrites these stems.

Parallel `*_simplified` stems for the offline sandbox. They intentionally
diverge from vendor: **class-specific** extractors (not a lightly edited
generic template). Each stem names the live registered schema, typical
document shape, what “empty” means for *that* class, and class-specific
traps (CUAD vs MAUD, FNOL vs demand letter, exhibit vs parent agreement,
Hub `claimed_amount` vs correspondence `demand_amount`). Shared
“Empty rules (every field)” boilerplate is forbidden. Hub intent /
subclass tokens, null / `[]` / `0`, do-not-invent. **Current run-20 /
run-30 specialist YAMLs pin these.**

### Extraction rules in the re-frozen v1 stems

- [`config/prompts/corporate_records_specialist_simplified.txt`](corporate_records_specialist_simplified.txt#L11),
  line 11: `subsidiary_list` emits `record_type: other`, the parent as
  `entity_name`, a subsidiary listing in `subject_matter`, and subsidiary names
  in `keywords`. `filing_number` is null unless an official filing or document
  number is present. An exhibit ID never qualifies as that number.
- [`config/prompts/correspondence_specialist_simplified.txt`](correspondence_specialist_simplified.txt#L14),
  lines 14 and [33](correspondence_specialist_simplified.txt#L33):
  `communication_type` is null when no registered token fits the visible text;
  still extract sender, recipient, and date from headers. Otherwise use exactly
  one of `email`, `letter`, `memo`, `notice`, `demand`, `attorney_demand`,
  `press_release`, or `meeting_request`. Do not emit `other` or invent a type.

### Simplified framing contract (issue #50)

Every `*_simplified` specialist stem follows the same narrative shape:

1. **System role** — one opening paragraph: which doc class this agent owns
   and what it is *not*.
2. **Situation** — the sorter handed `doc_type` plus that class’s subclass
   dimension (`contract_subtype` for contracts, `doc_subclass` otherwise).
   Subclass is **situational context**: prioritize the registered fields and
   checklist lines typical for that key, then **verify against visible text**.
   Never treat handoff as ground truth; never invent values the text does not
   support; never echo routing tokens as extra JSON keys.
3. **Executive brief by subclass** — for each live catalog key from
   `llm_dojo_scoring.corpus.DOC_TYPE_SUBCLASSES` (contracts: CUAD
   `CONTRACT_SUBTYPE_KEYS` + `other`), 2–5 lines mapping document shape →
   registered schema fields to read first.
4. **Class-specific empty/trap rules** + **registered field list** (live keys
   only; retired keys named as do-not-emit).

Subclass catalogs are defined in vendored dojo (`DOC_TYPE_SUBCLASSES`) and
surfaced to the sorter via `langchain_agents.doc_inventories`. Corporate
`record_type` on the extraction schema is narrower than the sorter catalog —
the brief explains how each sorter `doc_subclass` maps onto the five
`record_type` tokens plus `other`.

| Stem | Agent | Live schema (do not emit retired keys) |
| --- | --- | --- |
| `contracts_specialist_v33_simplified` | `contracts_specialist` | `document_name`, `parties`, `effective_date`, `term_length`, `governing_law`, `contract_value`, `renewal_terms`, `cuad_family`, `merger_consideration`, `cuad_clauses`, `maud_clauses`, `reasoning`, `confidence` — not `key_obligations` / `termination_clauses` |
| `merger_agreement_specialist_simplified` | `merger_agreement_specialist` | `document_name`, `parties`, `effective_date`, `effective_time`, `governing_law`, `merger_consideration`, `maud_clauses`, `intent`, `subject_matter`, `keywords`, `reasoning`, `confidence` — not `cuad_family` / `cuad_clauses` |
| `corporate_records_specialist_simplified` | `corporate_records_specialist` | `entity_name`, `record_type`, `effective_date`, `signatories`, `jurisdiction`, `filing_number`, `intent`, `subject_matter`, `keywords`, `confidence` — not `key_provisions` |
| `correspondence_specialist_simplified` | `correspondence_specialist` | `sender`, `recipient`, `additional_recipients`, `communication_type`, `communication_date`, `demand_amount`, `action_items`, `urgency`, `intent`, `subject_matter`, `keywords`, `confidence` — not `key_points` / `referenced_communications` |
| `insurance_claims_specialist_simplified` | `insurance_claims_specialist` | `claim_number`, `policy_number`, `insurer`, `insured_party`, `claim_type`, `date_of_loss`, `date_filed`, `claimed_amount`, `adjuster`, `damages_description`, `coverage_determination`, `denial_reasons`, `supporting_documents`, `intent`, `subject_matter`, `keywords`, `claim_checklist`, `confidence` |

These stems are listed in `scripts/sync_specialist_prompts.py` as
`EXPERIMENT_STEMS`. Default sync **refuses** to write them. Resetting a
simplified file back to vendor text requires an explicit opt-in:

```bash
python scripts/sync_specialist_prompts.py --overwrite-experiment
```

That copies current vendor text onto the matching `*_simplified` stem (loud;
almost never what a quality experiment wants).

## SAND-042 repaired stems (frozen as eval-environment v4)

Repaired stems from the SAND-042 schema-adherence root-cause analysis
(`docs/SAND42-SCHEMA-ADHERENCE-RCA.md`), frozen in eval-environment as
full-text mutations `insurance_claims_specialist_v4` and
`merger_agreement_specialist_v4` (parents: the v3 GEPA keys). Their sha256
and char counts are pinned under `frozen_successors` in
`eval_environment_lineage.json`. Byte drift is refused when a run resolves
the stem as a local prompt (`assert_catalog_sha`) and when
`verify_local_catalog` runs (the lineage tests), the same as for the v1 stems. They do **not** change the default v1 stem a
run gets: a run uses them by pinning the stem, as `config/runs/rca/*.yaml`
does.

| Stem | Agent | Frozen key | Built from | Change |
| --- | --- | --- | --- | --- |
| `insurance_claims_specialist_simplified_v2` | `insurance_claims_specialist` | `insurance_claims_specialist_v4` | `insurance_claims_specialist_simplified` (frozen v1) | Layout cues for all five corpus sources (CMS MSN A/B/carrier, Part D pde, GNOTHEIA property FNOL, BDR auto decision letters, INSURBIAS narratives); no phantom "sorter handed you doc_subclass" (the isolated harness passes none); bare-number `claimed_amount`; a printed payment/approval is a stated `approved`. |
| `merger_agreement_specialist_maud_v2` | `merger_agreement_specialist` | `merger_agreement_specialist_v4` | `merger_agreement_specialist_maud_v1` | Answer catalog **generated** from `llm_dojo_scoring.maud_schema.render_maud_question_block` (`scripts/gen_maud_v2_prompt.py --check` keeps it fresh); no free text inside `maud_clauses`; per-chunk answering duty instead of "answer everything". |

## Run YAML inventory (`config/runs/**`)

Specialist extract runs (task = specialist agent) currently pin simplified
stems, except the `rca/` re-check runs, which pin the SAND-042 repaired stems above. Sorter / scale / example runs do not load specialist prompts.

| Run YAML | `run_id` | Task | Local stem(s) |
| --- | --- | --- | --- |
| `run-20-correspondence-awq-c8.yaml` | `run-20-correspondence-awq-c8` | `correspondence_specialist` | `correspondence_specialist_simplified` |
| `run-20-correspondence-awq.yaml` | `run-20-correspondence-awq` | `correspondence_specialist` | `correspondence_specialist_simplified` |
| `run-30-correspondence-specialist.yaml` | `run-30-correspondence-specialist` | `correspondence_specialist` | `correspondence_specialist_simplified` |
| `run-20-contracts-specialist.yaml` | `run-20-contracts-specialist` | `contracts_specialist` | `contracts_specialist_v33_simplified` |
| `run-20-contracts-awq.yaml` | `run-20-contracts-awq` | `contracts_specialist` | `contracts_specialist_v33_simplified` |
| `run-20-contracts-awq-c8.yaml` | `run-20-contracts-awq-c8` | `contracts_specialist` | `contracts_specialist_v33_simplified` |
| `run-30-contracts-specialist.yaml` | `run-30-contracts-specialist` | `contracts_specialist` | `contracts_specialist_v33_simplified` |
| `run-30-corporate-records-specialist.yaml` | `run-30-corporate-records-specialist` | `corporate_records_specialist` | `corporate_records_specialist_simplified` |
| `run-20-insurance-claims-specialist-awq.yaml` | `run-20-insurance-claims-specialist-awq` | `insurance_claims_specialist` | `insurance_claims_specialist_simplified` |
| `run-30-insurance-claims-specialist.yaml` | `run-30-insurance-claims-specialist` | `insurance_claims_specialist` | `insurance_claims_specialist_simplified` |
| `run-30-merger-specialist.yaml` | `run-30-merger-specialist` | `merger_agreement_specialist` | `merger_agreement_specialist_simplified` |
| `rca/rca-50-insurance-v2-awq-1l4-c8.yaml` | `rca-50-insurance-v2-awq-1l4-c8` | `insurance_claims_specialist` | `insurance_claims_specialist_simplified_v2` (frozen v4) |
| `rca/rca-check-5-merger-maud-v2-awq-1l4-c8.yaml` | `rca-check-5-merger-maud-v2-awq-1l4-c8` | `merger_agreement_specialist` | `merger_agreement_specialist_maud_v2` (frozen v4) |
| `suites/run-30-specialists-full.yaml` | suite | (chains the five run-30 YAMLs) | same as those YAMLs |
| `suites/run-30-specialists-track-a.yaml` | suite | contracts + corporate + correspondence | same as those YAMLs |
| `suites/run-30-specialists-track-b.yaml` | suite | merger + insurance | same as those YAMLs |
| `run-400-sorter-qwen3-14b-awq-a100.yaml` | `run-400-sorter-qwen3-14b-awq-a100` | `isolated` | `sorter_v1` |
| `example.yaml` | `fixture-sorter-smoke` | `sorter` | `sorter_reviewer_local_v0`, `judge_local_v0` |
| `pilot-sorter-modal-hf.yaml` | `pilot-sorter-modal-hf` | `sorter` | `sorter_reviewer_local_v0`, `judge_local_v0` |
| `run-50-modal-hf.yaml` | `run-50-modal-hf` | `sorter` | `sorter_reviewer_local_v0`, `judge_local_v0` |
| `run-50-five-types.yaml` | `run-50-five-types` | `sorter` | none (`code-default`) |
| `run-50-subclass.yaml` | `run-50-subclass` | `sorter` | none (`code-default`) |
| `run-50-gemma3-4b.yaml` | `run-50-gemma4-e4b` | `sorter` | none (`code-default`) |
| `example-per-class.yaml` | `example-per-class-20` | `sorter` | none (`code-default`) |
| `scale-c1-4xl4-c16.yaml` | `scale-c1-4xl4-c16` | `sorter` | none (`code-default`) |
| `scale-d1-awq-4xl4-c16.yaml` | `scale-d1-awq-4xl4-c16` | `sorter` | none (`code-default`) |

Historical scorecards (`reports/RUN-20-CORRESPONDENCE-AWQ-C8-REPORT.md` and
peers, fingerprint `285f423d3708`) recorded the **vendor production** stems
in use at run time. Re-running the YAMLs above now uses simplified stems
(new `spec_hash`). Do not rewrite those reports.

`src/mailroom_sandbox/job/specialist_posture.py` `prompt_file` values must
match the YAML pins (`sandbox run benchmark-check` hard-fails on drift).
`tests/test_eval_environment_lineage.py` sha256-locks those stems to the
eval-environment frozen v1 catalog. Runtime injection (Family A rebind +
LangChain `PROMPT_VERSIONS`) lives in `prompt_registry.apply_runtime_overrides`.

## Local 7B/8B smoke variants

Shorter JSON-strict templates for Ollama smoke. Pass `--prompt sorter_local_v0`
to `sandbox eval` / `sandbox matrix`. Unset = mailroom in-code fallbacks.

| Stem | Extraction-facing? | Used by `config/runs/**`? | SAND-026 action |
| --- | --- | --- | --- |
| `sorter_v1` | no (classification) | `run-400-sorter-qwen3-14b-awq-a100.yaml` | vendored Family-B `sorter_v1` text; isolated sorter pin |
| `sorter_local_v0` | no (classification) | no (CLI `--prompt` only) | audit only — left as-is |
| `sorter_reviewer_local_v0` | no (classification review) | `example.yaml`, `pilot-sorter-modal-hf.yaml`, `run-50-modal-hf.yaml` | audit only — left as-is |
| `judge_local_v0` | grades an extraction; does not extract fields | same three sorter YAMLs | audit only — left as-is |
| `extract_local_v0` | yes (generic extract smoke) | **not** referenced by any run YAML; `--prompt extract_local_v0` only | kept short; null / `[]` / `0` / do-not-invent made explicit |

## Audit (SAND-026)

Correspondence quality on `run-20-correspondence-awq-c8` (fingerprint
`285f423d3708`) was ~0.087 `overall_extraction_score` with clean serving.
Owner-locked gates on issue #21: diagnostic ≥0.25 / pipeline-viable ≥0.50.
This prompt pass is a lever, not a scored rerun (zero Modal spend).

What was redundant or conflicting on the vendor pins:

1. **Two instruction blocks.** Family-A specialists append
   `PRODUCTION DOCTRINE` after a numbered extraction-rules list. The doctrine
   restates grounding / zero / vision / handoff and then a **stale**
   "registered schema fields" line that does not match
   `langchain_agents.specialist_agents` / `schemas.documents`.
2. **Correspondence schema drift.** Live fields are `intent` / `subject_matter`
   / `keywords`. Doctrine still lists retired `key_points` /
   `referenced_communications`. V0 says "do not dump key_points" while doctrine
   tells the model those keys are registered. `intent` is scored as an exact
   `name`; V0 examples used `demand_payment` while Hub GT uses `payment_demand`.
3. **Contracts length + retired-field novel.** `contracts_specialist_v33` is
   ~32k characters of CUAD `key_obligations` span discipline, then a PARED
   footer that forbids emitting `key_obligations` / `termination_clauses`.
   Doctrine still lists those as registered. Live product is key entities +
   `cuad_clauses` checklist.
4. **Corporate / insurance doctrine vs live schema.** Doctrine lists
   `key_provisions` (retired) and omits the semantic trio + insurance
   `claim_checklist`.

Simplified stems merge rules + fields into **one class-specific** block
aligned with the live JSON schema and Hub tokens. Scoring of those
extractions against Hub union GT drops empty / other-class fields before
the dojo suite runs — see [`docs/evals.md`](../../docs/evals.md)
§Extraction scoring vs empty / class-mismatched Hub GT.
