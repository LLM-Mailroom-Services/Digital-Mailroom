# SAND-042 schema-adherence RCA — Qwen3-8B-AWQ

Root-cause analysis of the three SAND-042 specialists whose headline numbers
were driven by the harness rather than the model: insurance claims
(schema-valid 26–34 %), correspondence (quality 0.388, SD 0.24) and merger
agreements (quality 0.027, MAUD accuracy 2.7 %).

**Limits.** The HF corpus is unreachable from the analysis container and no
run store (`items.jsonl`) is committed, so no raw model output was
inspected. Every mechanism below is reproduced against the vendored code
with probe payloads. Per-subclass validity comes from the committed
SAND-032 history. Anything inferred is marked *(inference)*.

## Summary

| Class | Symptom | Dominant cause | Kind | Fixed by |
| --- | --- | --- | --- | --- |
| insurance_claim | schema-valid 0.26–0.34 | Five scalars `str = ""` in the pydantic schema while the prompt, grammar and dojo all say `null`. The harness's own `"" → None` normalizer guarantees the failure. | **Schema** | Nullable fields + `contract_violations` CI guard |
| insurance_claim | quality −0.03 | Prompt says CMS rows → `pde`/`inpatient`/`outpatient`/`carrier`; GT labels all 400 CMS rows `health` | **Prompt ↔ GT** | Scorer equivalence (CMS token ≡ `health`) |
| insurance_claim | money fails validation | `claimed_amount: float`; grammar sends a string; `"$18,530.00"` rejected | **Schema** | Currency-tolerant validator; v2 prompt asks for a bare number |
| corporate_record | schema-valid 0.96 | Same nullability bug on `entity_name` / `record_type` | **Schema** | Same fix |
| correspondence | quality 0.39, bimodal | Only `intent` / `keywords` / `subject_matter` carry GT; `intent` is ⅓ of the score. The JSON-schema hint taught off-vocab labels (`demand_payment`, `acknowledge`, …) | **Harness + GT design** | In-vocab hints + guard test; vendored scorer refresh |
| merger_agreement | MAUD acc 0.027 | The frozen stem demands the exact Hub `valid_class` but never lists the answers (`maud_v1`, which lists them, read 0.14 on SAND-040) | **Prompt** | `maud_v2` stem generated from the dojo catalog |
| merger_agreement | precision capped | ~8 chunks answer every question; the merge keeps every string; the scorer kept the **first** (preamble) answer | **Harness/scorer** | Reducer: drop non-answers, count conflicts, never position-wins |
| merger_agreement | over-credit | `_fold` stripped `>`, so `"> 5 business days"` ≡ `"5 business days"` | **Scorer** | Comparators spelled out in the fold |
| all | stale metric | The sandbox vendored llm-dojo-scoring **v0.15** while the dojo is at v0.21: no `label` intents, no stringified-GT parsing, no MAUD valid-class catalog | **Harness** | Vendor refreshed |

## 1. Insurance claims — schema-valid 26–34 %

**Mechanism.** Per-item `schema_valid` comes from
`eval/schema_adherence.py::_pydantic_valid`. That function validates against
the vendored `schemas/documents.py::InsuranceClaimExtraction`, and nothing
strips nulls before validation. Five fields were declared `str = ""`:
`insurer`, `insured_party`, `claim_type`, `damages_description` and
`coverage_determination`. Three sources all define these fields as
`string|null` and say "unstated → null":
- the frozen prompt
- the JSON-schema grammar (`specialist_agents.py`)
- `llm-dojo-scoring/docs/EXTRACTION_SCHEMAS.md`

`normalize_extraction` also rewrites `""` to `None` before scoring. So a
model that emitted `""` failed too. `adjuster` had been fixed earlier for
exactly this reason (see the comment in `documents.py`), but the other five
were missed.

**Evidence.**
- Validity is deterministic by subclass. Over four committed SAND-032 runs:
  auto 0/81, carrier 0/30, outpatient 0/26, pde 1/23, inpatient 26/29,
  property 16/36.
- Reweighting those rates to the SAND-042 mix predicts about 21/50 valid.
  Observed was 13–17/50.
- Correspondence escaped only because `extraction_normalize.py` special-cases
  `None → ""` for its four `str` fields.

**Is the prompt at fault?** Not for validity. All four insurance prompt
variants carry the same null contract, and a prompt rewrite cannot make
pydantic accept `None`. The suspicion that the prompt was too narrow is
partly right, but on quality rather than validity:
- the prompt contradicts the GT on `claim_type` for CMS rows
- it has no layout cues for three of the five corpus sources (GNOTHEIA,
  BDR, INSURBIAS)
- it claims a sorter handoff that the isolated harness never sends

**Fixes.**
- **Schema.** Contract-nullable scalars, and a currency-tolerant
  `claimed_amount` / `demand_amount`.
- **Dojo.** `schema_contract.contract_violations` plus a sandbox CI test
  (`tests/test_schema_contract.py`) that probes every vendored schema field by
  field.
- **Scorer.** CMS `claim_type` tokens now match GT `health`.
- **Prompt.** Candidate `insurance_claims_specialist_simplified_v2`.

## 2. Correspondence — quality 0.388, SD 0.24

- **Only three fields are scored.** Enron GT populates only `intent`,
  `keywords` and `subject_matter`, and empty GT is dropped. The other eight
  schema fields are never scored. Per-document scores line up with a
  three-field mean: exactly 6 documents sit at ⅓.
- **The bimodality is `intent`.** 18 documents score below ⅓ (intent
  missed) and 32 at or above ⅓. A document's score is a property of the
  document, not of sampling: across the 5 cells, per-document correlation is
  0.94–0.995.
- **The grammar hint taught wrong labels.** The JSON-schema hint appended to
  every call listed `demand_payment`, `request_information`,
  `threaten_litigation`, `acknowledge` and `schedule_meeting`. None of
  those are in the scored 8-label vocabulary. The insurance and
  corporate-record hints had the same defect.
- **The vendored scorer typed `intent` as fuzzy `name`.** A wrong label
  earned 0.1–0.64. The v0.21 scorer scores it exact `label`, which is more
  honest but lower (about −0.03, estimated).
- **GT appears templated** *(inference)*. The `subject_matter` /
  `keywords` GT looks templated from metadata ("Correspondence concerning
  general_business.", folder and timestamp tokens). A grounded answer scores
  0 on those fields. This needs a GT relabel, not a prompt change.
- **The stale correspondence stem is not a cause.** It differs from the dojo
  re-freeze only in two lines about `communication_type`, and that field has
  no GT.

## 3. Merger agreements — MAUD accuracy 2.7 %

- **The prompt never lists the answers.** The frozen `simplified` stem
  says "Answer is the Hub valid_class, not a paraphrase" and then lists only
  the 22 question names. The grammar is plain `array of string`, which is
  why schema-valid was 100% while accuracy was near zero.
  - Same model and documents: `maud_v1` (which lists the answers) scored
    **0.14** on SAND-040; the simplified stem scored **0.028** on SAND-042.
  - Correct-concept paraphrases score 0/10 in probes.
- **Chunk merge with first-answer-wins.** About 8 chunks answer every
  question. `_merge_extractions` keeps each distinct string, and
  `maud_scoring.py` kept the first, so the preamble chunk's guess beat the
  chunk that held the clause. The dojo scorer instead turned the merged list
  into an always-wrong "ambiguous" answer.
- **Six scorer defects** (dojo):
  - the `>` fold collision
  - multi-class answers were order-sensitive
  - a single-space emission of the double-space fiduciary question name was
    lost
  - newline-joined spans parsed only the first question
  - `{q: null}` counted as present-but-invalid
  - four legitimate Tail Period classes containing `" / "` made their GT rows
    `unscorable`
- **The 0.027 is MAUD-only.** The document_name, parties, dates,
  governing_law and consideration fields carry no GT on Hub merger rows, so
  the number is not comparable to contracts' CUAD presence F1.
- **Truncation is not a cause.** Chunks are about 12k tokens, inside the
  32k window.

## What changed

**llm-dojo-scoring** (branch `claude/schema-adherence-rca`):
- `cuad_schema`: the 41 categories and 25 families, with questions.
- `maud_schema`: the 22 questions with answer catalogs, both grammar shapes
  and the prompt block.
- `schema_contract`.
- All the MAUD scorer fixes above.
- The CMS `claim_type` equivalence.

**local-mailroom-sandbox** (this branch):
- Vendored dojo refreshed to that branch.
- Vendored mailroom schemas made contract-nullable and currency-tolerant.
- In-vocab `intent` hints.
- MAUD reducer in `eval/maud_scoring.py`.
- Guard tests.
- Two candidate stems, `config/runs/rca/*.yaml` re-check configs, and this
  report.

**Upstream follow-up** (not in this session's repo scope): port the
`schemas/documents.py` and `specialist_agents.py` edits to llm-mailroom (the
monorepo `packages/llm-mailroom`) so the vendor drift guard stays
byte-identical.

## Freeze status

Both repaired stems are frozen in eval-environment as full-text mutations
(2026-10-15) and pinned in `config/prompts/eval_environment_lineage.json`
under `frozen_successors`:

| Stem | eval-environment key | sha256 | chars |
| --- | --- | --- | --- |
| `insurance_claims_specialist_simplified_v2` | `insurance_claims_specialist_v4` | `1ca6e83c…58ea` | 8461 |
| `merger_agreement_specialist_maud_v2` | `merger_agreement_specialist_v4` | `da316691…1946` | 33125 |

The freeze fixes the bytes so the re-checks below measure a pinned version.
The default stem for each specialist is still the frozen v1. Making v4 the
default is a separate promotion decision, to be made on the re-check numbers.

## Re-check before re-running the grid

```bash
sandbox run start --config config/runs/rca/rca-50-insurance-v2-awq-1l4-c8.yaml   # expect schema_valid ≈ 0.95–1.0
sandbox run start --config config/runs/rca/rca-check-5-merger-maud-v2-awq-1l4-c8.yaml  # expect MAUD acc ≫ 0.028
```

Persist `items.jsonl` (the predicted JSON for each document) on the card.
Without it, none of the SAND-042 attributions could be confirmed against raw
output.

> **Comparability:** scores from the refreshed scorer are not comparable to
> SAND-032 … SAND-042 cards. Re-score historical run stores before putting
> them in one table.
