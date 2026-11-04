# Decision-Model Reviewer for the Mailroom: Design

**Date:** 2026-10-30
**Status:** Written for review
**Audience:** Capstone reviewers

## 1. Purpose

Show how typed decision models can do useful work in a document mailroom, using
the governed `llm-mailroom` pipeline and public or sanitized evaluation data. The
design offers one concrete use case: a low-cost reviewer with an explicit,
enforced route to a human.

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:eabd32c20eaf4f6e03ce3be4f3bde7c1758f20f271acb14e1e0f77514dfd1643 -->

External naming: this spec and its artifacts must not imply affiliation,
endorsement, sponsorship or shared work without written clearance from the user.
Vendor names may be used to identify products and sources.

<!-- /coderabbit-ai-generated:v1 -->

Success has two levels:

1. **Pilot (first priority):** short, working examples of decision models
   running against mailroom documents, with real outputs, routing and human
   decisions.
2. **Qualification (second):** per-class evidence on whether a decision model
   can review without a backup LLM call.

A pilot shows that the approach works mechanically. It does not qualify a class
for production use, and no pilot result may be presented as if it does.

## 2. Decisions made

> **Updated 2026-10-31:** the sanitization row is superseded. The Enron correspondence is public, so no backend refuses correspondence and no sanitized copy is needed (SAND-086 cancelled; see section 9). The routing row is superseded by the note under section 5.

| Topic | Decision |
|---|---|
| Role | Option A: a decision model serves as the Lane A `sorter_reviewer` |
| Routing | Per-class; eligible classes get no backup LLM call |
| Failure route | Anything short of the accept rule goes to human review |
| Risk bar | Working default: at most 1% wrong auto-accepts, 95% upper bound |
| Demo surface | Live terminal review, with a recording of a real run as backup |
| Sanitization scope | Correspondence only; other classes get a PII scan |
| Pipeline edits | In scope and first in order |
| Serving | Full pipeline on Modal + vLLM, API, or a hybrid |

The final presentation is December 15, 2026. Pilots come first, and section 11
orders the work by dependency.

## 3. Decision models

> **Updated 2026-10-31:** the shipped backends are `jev`, `local`, `api` and `mock`. The `api` backend runs the `sorter_reviewer` agent on an OpenRouter route pinned to one model id (for example `openai/gpt-6-luna`, set through `agent_routes.sorter_reviewer`). The `local` backend runs the same agent on the run's own serving route. No Decisions API adapter exists, so the "Interface" row and the Decisions API sentence below describe the original plan only.

| | Jev (`jev-1.13.0`) | GPT-6 Luna Decisions |
|---|---|---|
| Vendor | TypeSafe AI | OpenAI |
| Input price | $0.042/M | $0.10/M, provisional |
| Output price | Free | Free |
| Context | 32k | 1.05M |
| Inputs | Text | Text and images |
| Status | Early release | Public beta |
| Interface | `TYPESAFE_API_KEY`, Pydantic AI `typesafe:` models | `POST /v1/decisions` |

Figures are vendor or third-party reported. Measured costs replace them as soon
as runs exist. Luna access is unverified: OpenRouter states it does not work
through chat-completions SDKs, so the adapter targets the Decisions API.

Jev is the primary model. Luna is the comparison model and the only candidate
for documents that need image input.

A decision model is still a paid external call. The saving comes from low
input pricing, no output charge and a bounded answer shape. It does not come
from removing the call.

## 4. Pilots

All pilots run in the sandbox against pinned data. Pilot 1 changes routing.
Pilots 2 and 3 run in shadow: they record what the model would have decided and
change nothing.

### Pilot 1: Reviewer with human routing

The decision model answers `doc_type` and `doc_subclass` as pick-one questions.
The accept rule in section 5 then either continues to `extract` or parks the
document for a person, who resolves it in the terminal.

### Pilot 2: Classification audit (shadow)

The decision model answers the existing judge labels: `correct`, `incorrect` or
`ambiguous`. Output is compared with the judge. Completeness and correctness
judging stay on the LLM because they need cited findings and Jev is documented
as weak on dates, counting and arithmetic.

### Pilot 3: Retry avoidance (shadow)

For a medium-confidence document, record what the decision model answers before
`retry_classify` runs. The output estimates how many full LLM retries could be
avoided. This estimate does not change routing.

## 5. Routing contract

> **Updated 2026-10-31:** where the rules below conflict with this note, this note wins. A decision class reaches its reviewer at any sorter confidence, after the sorter's retries. Agreement at the cutoff goes to `extract`. A sorter below its low band may be corrected by a reviewer at the cutoff: only the reviewer's label must be an eligible class, and it replaces the sorter's label. An unsure reviewer, or disagreement with a medium or high sorter, parks for human review. The "overrides never auto-accept" rule no longer holds. Cutoffs are provisional until issue #208.

Each class is configured as either `llm` or `decision_only`. Classes set to
`llm` keep the existing reviewer and do not call a decision model.

A `decision_only` document reaches `extract` only when all of these hold:

| Required condition | Cause recorded on failure |
|---|---|
| The model returned a valid answer | `reviewer_unavailable` |
| The document has usable text | `reviewer_no_text` |
| Sorter and model labels are both eligible classes | `reviewer_ineligible_label` |
| Sorter and model labels agree | `reviewer_disagreement` |
| Confidence meets the tuned class cutoff | `reviewer_low_confidence` |

Rules:

- Every failed condition is recorded, not only the first.
- Any failure goes to `human_review`. There is no LLM fallback and no archive
  path from this lane.
- Overrides never auto-accept in `decision_only` mode.
- Transient provider errors use the existing per-node retry budget, then become
  `reviewer_unavailable`.
- The decision is a pure, config-driven function. The graph and the evals call
  the same function.
- The class list and cutoffs are tied to a pinned model version. A new version
  requires requalification.
- Cutoffs are tuned per class and are not assumed to match the existing LLM
  cutoffs of 0.95 to 0.98.

## 6. Human review changes

Existing behavior stays: `human_review_node` parks the document, interrupts, and
resolves through the review queue and resolve logic.

Required changes in `llm-mailroom`:

1. Add the five causes in section 5 to `review_causes`, with labels.
2. Persist `review_causes`, `review_verdict` and the `reviewer_*` fields on the
   manifest and catalog. A decision model writes no reasoning, so a prose
   `escalation_reason` is not enough.
3. Generate `escalation_reason` deterministically from those fields.
4. Require a person resolving a disagreement to choose a label, and confirm the
   override carries through the interrupt resume path.

Required change in the sandbox: `sandbox review list|show|resolve`, showing both
opinions and the causes, and offering approve, reject and override.

The demo sets `MAILROOM_CHECKPOINTER=sqlite`, so a restart does not silently
change the path to the fresh-extract fallback.

## 7. Full pipeline serving

> **Updated 2026-10-31:** the `api` and `local` backends reach their model through `agent_routes.sorter_reviewer`, so that route does carry the reviewer's transport. The frozen `reviewer` block still pins backend and model. The sentence beginning "`AgentRoute` only describes" below is superseded for those two backends.

Pilots run through the full pipeline, not only an isolated reviewer eval. "Full
pipeline" means the complete 13-node `llm-mailroom` graph, from document intake
to an organized archive entry per document:

`intake`, `classify`, `retry_classify`, `review_classify`, `extract`,
`retry_extract`, `judge_verify`, `arbiter`, `human_review`, `boss_escalation`,
`compile_report`, `catalog_write`, `archive`.

The graph is not reimplemented or skipped. It must operate in three modes:

| Mode | LLM agents | Reviewer |
|---|---|---|
| Modal + vLLM | Modal vLLM | LLM route or decision model |
| API | API routes | LLM route or decision model |
| Hybrid | Per-agent mix through `agent_routes` | LLM route or decision model |

`sandbox experiment create --task pipeline` and `agent_routes` already support
the hybrid shape, but offline tests are the recorded evidence so far.
`reports/experiment_log.jsonl` has no live full-pipeline row under the check
used for this spec. A live run in each mode is therefore a deliverable, not an
assumption.

`AgentRoute` only describes OpenAI-compatible transports, and decision models do
not use that interface. The reviewer backend is therefore a separate typed
setting. It joins the frozen run config, signed review and preflight checks, so
a reviewer model cannot change without review.

A mode counts as operational when one bounded run of a few documents per class:

- Takes every document through intake to a terminal stage.
- Ends each accepted document with a compiled record, a catalog entry and an
  archive entry.
- Ends each rejected document in `failed`, never in the archive.
- Parks at least one document and resolves it through `sandbox review`.
- Exercises all 13 nodes across the run. Conditional nodes such as
  `boss_escalation`, `arbiter` and `retry_extract` will not fire on clean
  documents, so curated documents must trigger them.
- Records per-document routes, causes and measured cost.
- Tears down any Modal app it started.

Live runs use the signed, capped run path.

## 8. Ownership and integration

- Graph, routing, schema and agent changes land in standalone `llm-mailroom`
  first, then reach the sandbox through the reviewed vendor refresh. Vendored
  files are not edited by hand. The source is
  <!-- coderabbit-ai-generated:v1 -->

  <!-- coderabbit-ai-generated-section:v1:478bf37d72a99d552d93622f5bc4b8de24d205c78ea395aa626fb5f281eec39e -->

  https://github.com/Exios66/llm-mailroom (public, vendored at
  `1530f496a6c745186bb86d12b5f0472c667a404a`). A source checkout is needed
  for upstream changes. Commits there follow the external naming rule in section 1.

  <!-- /coderabbit-ai-generated:v1 -->
- Backend adapters and pilots live behind an opt-in sandbox path. The default
  profile, offline runs and the default test suite make no decision-model call.
- Sandbox work uses a `SAND-*` card. Family-wide work cites a related `DMR-*`.
- Credentials stay out of the repo. Paid runs use the existing signed, capped
  run path.

## 9. Sanitized correspondence dataset

> **Superseded 2026-10-31:** the Enron correspondence is already public, so this copy is not needed and no backend refuses correspondence (SAND-086 cancelled).

### Goal

A private, separately versioned copy in which the 1,000 Enron correspondence
rows use realistic fictional identities. The source dataset is not changed. The
result is pseudonymized, not anonymous: the Enron corpus is public, so a
verbatim sentence may still be traceable.

### Pipeline

1. Run locally only. No third party or hosted LLM sees raw text.
2. Parse headers directly, then use local detection such as Presidio with spaCy.
3. Group variants of one person into a single identity.
4. Give each identity one fictional name from a pool screened against every real
   name found. Do not shuffle real name parts.
5. Replace emails, phones and addresses with format-preserving fakes, and replace
   `Enron` with a fictional company.
6. Apply replacements across `doc_text`, `prompt`, filenames, metadata and
   ground-truth text fields, including `label_evidence`, `sentiment_evidence`,
   `topic_evidence`, `keywords` and `subject_matter`.
7. Regenerate identity columns and hashes. Labels stay unchanged.
8. Keep the real-to-fake mapping outside every repo.

### Gates

- Zero hits against the real-identifier list in any output column.
- A second detection pass over the output.
- Row and label counts match the source.
- A person reviews a random sample of at least 100 rows.
- A local sorter comparison shows classes score the same on both versions.
- Failing rows are dropped and counted, never published.

The new repo stays private. The other classes get a PII scan, including the 200
card-like matches in `insurance_claim`, with no rewriting.

## 10. Evaluation

### Data

> **Updated 2026-10-31:** correspondence needs no sanitized copy, because the Enron corpus is public (SAND-086 cancelled). The bullet below is superseded.

- Freeze `FAMILY_HF_REVISION` (`bc9eab28`) as the source revision. Configs
  currently also cite `ed7576b6`, and `main` is `670e8bc6`.
- Correspondence is evaluated only from the sanitized copy.
- `ground_truth` scores class labels only. In the profiled revision, every row
  has `review_expected=false`, so it cannot score routing.
- The `fixtures` config scores routing with injected confidences only, because
  the same text appears under several labels. Inconsistent rows are corrected in
  a curated exhibit set, not assumed correct.

### Stages

1. **Broad pass:** Jev and Luna on all eligible rows. This screens out weak
   classes. Easy documents dominate it, so it cannot qualify a class.
2. **Reviewer-band pass:** the sorter runs on surviving classes and keeps
   documents that reach the reviewer band. The decision models and the current
   reviewer run on the same documents.

### Reporting

Per class and per model: accuracy, calibration, wrong-accept upper bound,
human-review rate, cause counts, measured cost and sample size.

- A class needs about 300 clean accepts for the 1% bound, and each error raises
  that number. A class that cannot reach the bar stays on `llm`, and the report
  gives the bound the data supports.
- It is a valid outcome if no class qualifies at first.
- `insurance_claim` is entirely synthetic. Results there may not be presented as
  evidence about real insurance claims.
- Any document reaching `extract` outside the accept rule fails the run.

## 11. Order of work

> **Updated 2026-10-31:** item 4 is no longer a prerequisite. Correspondence needs no sanitized dataset (SAND-086 cancelled).

1. **Pilot enablers:** `llm-mailroom` routing function, causes, persisted fields
   and override path; backend adapters with mocks.
2. **Serving proof:** one bounded full-pipeline run in each section 7 mode.
3. **First live pilot:** Pilot 1 on insurance, contract and corporate documents,
   after the card-like insurance matches are cleared and credentials and data
   terms are checked.
4. **Sanitized dataset:** correspondence, then Pilot 1 on it.
5. **Shadow pilots:** Pilots 2 and 3.
6. **Demo:** `sandbox review`, curated exhibits, and the backup recording.
7. **Qualification:** the section 10 stages, with results fed into class config.

Demo exhibits stay short: one clean accept through to an archive entry, then one
exhibit per review cause, including a person overriding a disagreement.

## 12. Testing

- A table test covers every failure combination and asserts the destination,
  causes and zero LLM calls.
- Adapter tests use recorded or mocked responses. The default suite makes no
  network calls.
- Human decision tests cover approve, reject, override and restart.
- A rejected document cannot reach the catalog as archived.
- Sanitization tests cover variant grouping, repeat-run consistency and every
  replaced column, using invented data.

## 13. Risks

| Risk | Handling |
|---|---|
| Vendor calibration is unproven | Tune and test per class, report as measured |
| Models are early release or beta | Pin versions, keep a recording backup |
| Vendor data terms are unverified | Check before any non-public text is sent |
| Adversarial text in documents | Disagreement and low confidence park for a person |
| Jev ignores page images | No usable text routes to a person |
| More human review than today | Report the review rate per class |
| Sparse reviewer-band documents | Report the supported bound, keep the class on `llm` |
| Pilot read as production evidence | Label pilots and qualification separately |

## 14. Out of scope

- Replacing the sorter, specialists, boss or arbiter.
- Replacing completeness or correctness judging.
- Using a decision model for extraction.
- Rewriting PII in contract, corporate, merger or insurance classes.
- A browser review action, which stays with SAND-069.
- Changing or deleting the published source dataset.
- Sending real customer or partner documents to any vendor.
