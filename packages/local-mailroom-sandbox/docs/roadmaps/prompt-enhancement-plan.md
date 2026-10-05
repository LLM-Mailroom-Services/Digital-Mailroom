<!--
Draft for a GitHub Discussion in LLM-Mailroom-Services/Digital-Mailroom
(suggested category: Ideas or General). Title and body below.
Full report: docs/roadmaps/PROMPT-ENHANCEMENT-PLAN-v2.md (SAND-034).
-->

# Title

Prompt enhancement plan for the mailroom pipeline: sorter, specialists and exception-lane nodes (SAND-034)

# Body

This proposes how to make every LLM prompt in the LangGraph pipeline shorter and
structurally simpler without losing the lexical cues the classification and
extraction tasks depend on. It is meant to sit alongside the GEPA work in
eval-environment, not replace it. Everything below comes from predictions and
reports already logged; no API or GPU spend went into it.

**Full report:** [`docs/PROMPT-ENHANCEMENT-PLAN.md`](https://github.com/Exios66/local-mailroom-sandbox/blob/claude/dreamy-bohr-455nr1/docs/PROMPT-ENHANCEMENT-PLAN.md)
in local-mailroom-sandbox.

## What is failing

The largest losses are not in the wording GEPA tunes. They sit in the contract
between prompt, schema, scorer and router.

1. **Specialists return `null` where the schema needs a list.** Replaying 286
   logged API predictions through the extraction schemas:

   | class | schema-valid |
   | --- | --- |
   | insurance claims | 3 / 60 |
   | correspondence | 8 / 60 |
   | contracts | 8 / 58 |
   | merger agreements | 36 / 48 |
   | corporate records | 41 / 60 |

   The prompts already say "unstated list → []". The eval call asks for JSON
   but never sends the schema.
2. **The sorter prompt is 81% contract rules** (14.0k of 17.2k characters).
   Its main error is routing other classes to `contract`: 35 of 136 corporate
   records and 10 of 18 merger agreements in the 1,000-document run. Its output
   spec omits `doc_subclass`, which Qwen3-8B left empty on 13 of 20 documents.
3. **Label vocabularies disagree across layers.** Corporate records: 11 sorter
   labels, 5 specialist `record_type` values, 10 mailroom-ml labels. Contract
   ground truth uses CUAD folder names that the eval scorer never maps to the
   sorter's keys.
4. **The contracts schema carries merger-agreement fields**, which the prompts
   then have to tell the model to skip.
5. **Instruction text leaks into outputs.** Granite copied prompt examples as
   JSON keys; DeepSeek's merger outputs were cut off mid-JSON in 10 of 20 cases.
6. **Scores are confounded.** Flat means hide subclass trade-offs (corporate v2:
   −0.158 on charter amendments, +0.098 on subsidiary lists); prompt lineage is
   mixed into the v2 comparison; eval-environment cuts sorter input at 12k
   characters while the pipeline reads whole documents.
7. **Exception routing trusts confidence that does not track quality.** The
   judge, retry and review lanes fire on the specialist's self-reported
   confidence. Its correlation with the actual score is −0.22 for insurance
   and about 0 for contracts on Qwen3-8B; corporate records emits none.

## Other graph nodes

Intake, sorter reviewer, the three judges, arbiter and boss have no scored live
runs yet (only 2-document smoke runs), so this part is a prompt and routing
audit:

- The reviewer and classification-judge base prompts still name "court opinion"
  as a class; the doctrine appended after them says it maps to `unknown`.
- The same doctrine paragraphs (five-class boundaries, numeric zero, vision) are
  appended to six prompts; deduplicating them should remove roughly a quarter
  to a third of each prompt without dropping a rule.
- Judges and the arbiter are told to check "registered schema fields" but never
  see the field list; the arbiter must name `fields_to_fix` from prose.
- Intake does triage, OCR repair and a contract-shaped section map in one call.
- The boss prompt carries both its in-graph and its ops-monitor role on every
  call.

## Proposal

- **Phase 0, code fixes (no spend):** send the schema or coerce list nulls;
  remove merger fields from the contracts schema; sorter parse error → `unknown`;
  map CUAD folder names in the scorer; one sorter input policy; blend schema
  validity and guard issues into the routed confidence; give judges and the
  arbiter the field list.
- **Phase 1, one prompt skeleton:** ROLE / SCOPE / CUES / PRECEDENCE / FIELDS /
  OUTPUT for every node. The sorter's long contract rules become a short
  precedence table by document family. A cue inventory plus a coverage test
  guarantees no cue is dropped when a prompt is shortened.
- **Phase 1b, other nodes:** fix stale V0 text, deduplicate doctrine, split the
  boss prompt, trim or class-scope the intake section map, and add a Langfuse
  drift check (served `production` prompt vs local fallback).
- **Phase 2, GEPA under new gates:** mutate inside the skeleton, with a
  cue-coverage gate, a per-subclass non-regression gate and prompt size as a
  Pareto objective. Promote through a Langfuse `candidate` label before moving
  `production`.

Targets for the promotion gate, not claims: sorter prompt about 60% shorter with
all 65 title cues and 41 worked decisions kept; schema validity ≥ 0.95 for every
class; no subclass with n ≥ 5 dropping by more than 0.05.

## Open questions

- Should the Phase 0 schema and confidence fixes land in llm-mailroom via the
  monorepo first, or in eval-environment's harness first?
- Who owns the corporate `record_type` mapping against the Hub ground truth?
- The Braintrust trace review (phase 0c) is still pending; it needs network
  access to `api.braintrust.dev` from the environment that runs it.

---
_Generated by [Claude Code](https://claude.ai/code)_
