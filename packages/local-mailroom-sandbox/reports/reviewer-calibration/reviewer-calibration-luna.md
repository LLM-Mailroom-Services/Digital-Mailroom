# Decision reviewer calibration pilot: `openai/gpt-6-luna` (SAND-085, issue #208)

> **Superseded (2026-11-01).** Every run in this report used the chat model
> `openai/gpt-6-luna` through the `api` backend, not the Decisions-API model
> `openai/gpt-6-luna-decisions` the reviewer is meant to be. Its cutoffs do not
> apply. The calibration on the Decisions model is
> [`reviewer-calibration-luna-decisions.md`](reviewer-calibration-luna-decisions.md).
> The class conventions, subclass rules and label-noise findings below carried
> into its question sets.

Run `reviewer-calibration-luna`, 2026-11-01, signed JB. Spec
`config/runs/reviewer-calibration-luna.yaml` (spec hash `9fe4f4da…`, dataset
sha256 `1975326bfa88`, pinned revision `ed7576b6`). Cutoffs:
`reviewer-calibration-luna.json` (target accuracy 0.95, seed 42, five-fold
cross-fit, Wilson 95% intervals).

## Run

| | |
| --- | --- |
| Documents | 735 train documents with task ground truth, balanced across subclasses (150 per class; all 135 train mergers) |
| Failures | 0 of 735 (no errors, no throttling at concurrency 16) |
| Wall time | 100 s at concurrency 16 |
| Latency per call | p50 2.05 s, p95 2.83 s, max 5.88 s |
| Tokens | 2,249,830 in, 73,410 out (100 out per document; 0 reasoning tokens) |
| Cost at list price | $0.262: $0.225 input, $0.037 output |

Output is the required JSON answer: `doc_type`, `doc_subclass`, `confidence`
and a one-sentence `reasoning` that the prompt asks for. Removing `reasoning`
would change the reviewer that production runs, so the calibration would not
carry over.

## Accuracy

Overall 709 of 735 correct (96.5%).

| truth \ predicted | contract | corporate_record | correspondence | insurance_claim | merger_agreement | unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| contract | **147** | 3 | | | | |
| corporate_record | 18 | **132** | | | | |
| correspondence | | | **145** | | | 5 |
| insurance_claim | | | | **150** | | |
| merger_agreement | | | | | **135** | |

Every error came from one of these subclasses:

| Subclass | Correct | Predicted instead |
| --- | ---: | --- |
| corporate_record / rights_instrument | 2 / 16 | contract (14) |
| corporate_record / indenture | 13 / 16 | contract (3) |
| corporate_record / articles_of_incorporation | 16 / 17 | contract (1; the document is titled "Registration Rights Agreement", so the label looks wrong) |
| contract / Joint Venture _ Filing | 5 / 8 | corporate_record (3; Rule 13d-1(k) joint filing agreements) |
| correspondence / email | 18 / 21 | unknown (3: an Evite notice, an AP news article, a scheduling log) |
| correspondence / demand | 19 / 21 | unknown (2: a newswire digest, a satirical piece) |

## Cutoffs (target 95%)

| Class (predicted) | Answers | Cutoff | Held-out accuracy | 95% interval | Accepted | Meets target |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| merger_agreement | 135 | 0.98 | 100% | 97.2–100% | 100% | yes |
| correspondence | 145 | 0.71 | 100% | 97.4–100% | 99.3% | yes |
| insurance_claim | 150 | 0.61 | 100% | 97.5–100% | 98.7% | yes |
| corporate_record | 135 | 0.86 | 98.5% | 94.7–99.6% | 99.3% | no (lower bound 94.7%) |
| contract | 165 | 1.00 | 88.2% | 73.4–95.3% | 20.6% | no |

## What the pilot shows

1. **The errors are taxonomy boundaries, not confidence noise.** All 26 wrong
   answers have confidence 0.86–0.99, and 16 are at 0.98 or above. Luna reads a
   registration-rights agreement or an indenture as an agreement, which it is,
   and calls it a contract. The corpus files these as corporate records. No
   cutoff can separate them: the only contract cutoff that reaches 95% is 1.0,
   which keeps 21% of contracts and still scores 88%.
2. **The reviewer prompt never states these boundaries.** The subclass catalog
   it sees says only "rights_instrument (stock/warrant/rights agreements)". It
   does not say that registration-rights agreements and indentures are
   corporate records, or that Schedule 13D/13G joint filing agreements are
   contracts. Rule 4 of the prompt ("purpose and form") points the model
   toward "contract" for any signed agreement.
3. **Confidence is compressed.** 549 of 709 correct answers are at 0.99, and
   most of the rest are at 0.94–1.00. The model separates easy from hard
   documents weakly, so cutoffs mostly decide whether a class can be trusted
   at all, not how far to trust it.
4. **Three classes are ready:** merger_agreement, correspondence and
   insurance_claim had no wrong answers. Their cutoffs keep 99–100% of the
   reviewer's answers.
5. **Concurrency 16 cost nothing in quality** (the calls are independent) and
   produced no throttling. 32 is safe to try on the full run.

## Reframed reviewer prompt: `sorter_reviewer_decision_v1`

The code-default reviewer prompt gives the model class *names* only. Its user
message lists the taxonomy keys and subclass catalogs, but none of the class
descriptions the sorter receives (`config/mailroom.taxonomy.base.yaml`). It
also says "classify the substantive form, not the filing context", which
pushes signed securities instruments toward "contract".
`config/prompts/sorter_reviewer_decision_v1.txt` (a `source: local` override;
no code change) frames the review as the routing decision it is:

- **Decision framing:** what a confidence at or above a cutoff does (the
  document is routed without a person) and which error is costly
  (overconfident wrong).
- **Class definitions** from the taxonomy descriptions and the dataset card.
- **Corpus conventions** that override a plain reading. Securities instruments
  (registration-rights, investor-rights and subscription agreements, warrants)
  and indentures are corporate_record, as in the sorter_v4 doctrine checked
  against the train split (`docs/prompts/sorter.md`). Rule 13d-1(k) joint
  filing agreements are contracts (sorter_v4 rule 12). Mailbox messages are
  correspondence (`COMMUNICATION_TYPE_DESCRIPTION`: "Enron-style inbox
  messages are email").
- **The sorter_v4 corporate-record subclass doctrine.**
- **An anchored confidence scale:** each band is defined by observable
  conditions, and the model must name the strongest competing class before
  committing.

Output tokens did not change (96 per document), so the cost rise is input
only: the longer prompt.

### Same 735 train documents (in-sample: some conventions were written from the pilot's errors)

| | code-default | decision_v1 |
| --- | ---: | ---: |
| Accuracy | 96.5% (709) | **99.7% (733)** |
| Wrong at confidence ≥ 0.90 | 25 | **2** |
| Classes meeting the 95% target | 3 of 5 | **5 of 5** |
| Cost (list) | $0.262 | $0.320 |

| Class | Cutoff | Held-out accuracy | 95% interval | Accepted |
| --- | ---: | ---: | --- | ---: |
| contract | 0.91 | 100% | 97.5–100% | 98.7% |
| corporate_record | 0.90 | 100% | 97.5–100% | 98.7% |
| correspondence | 0.57 | 100% | 97.5–100% | 99.3% |
| insurance_claim | 0.90 | 100% | 97.5–100% | 99.3% |
| merger_agreement | 0.93 | 100% | 97.2–100% | 99.3% |

### Out-of-sample check: test split, 317 documents not used for the prompt or the cutoffs

Runs `reviewer-validation-luna-default-test` and
`reviewer-validation-luna-prompt-v1-test`, on the same documents (dataset
sha256 `b38ee36bf530`). Each prompt's train-picked cutoffs were applied without
re-tuning.

| | code-default | decision_v1 |
| --- | ---: | ---: |
| Accuracy | 95.6% (303) | **98.1% (311)** |
| Wrong at confidence ≥ 0.90 | 14 | **3** |
| corporate_record → contract errors | 4 | **0** |
| Routed with no person (cutoffs of the 3 passing classes / all 5) | 64.7% / 79.2% | **98.1%** (all 5) |
| Misrouted among those routed | 0 / 0.4% | **0.3%** (1 of 311) |
| Cost (list) | $0.097 | $0.122 |

The single misroute is a document titled "LIMITED POWER OF ATTORNEY" that
the corpus labels as a Service contract. The reviewer named it
corporate_record / powers_of_attorney at 0.99, a defensible reading that
deserves a label check. The other five errors are `unknown` predictions: Enron
scheduling logs, an accounting abstract filed as a memo, and a message whose
only text is "it is 2.79". `unknown` is not a decision class, so each of these
parks for a person instead of being misrouted.

### Reading the cutoffs

With no wrong answers in four of five classes, each cutoff is just the lowest
confidence the reviewer gave a right answer. The data shows that answers at
or above it were all right; it does not show where accuracy starts to fall.
The interval's lower bound (97.2–97.5%) is set by the sample size, not by
errors. More documents tighten it, which is the job of the full run.

## Applied to the pipeline

> **Historical.** This page records the chat-model pilot (`openai/gpt-6-luna`), which preflight now
> refuses as a decision reviewer. The current reviewer is the Decisions model; see
> `reviewer-calibration-luna-decisions.md`.

`config/runs/pipeline-luna-qwen-smoke.yaml` (the chat-model decision-reviewer smoke) now
carries the reviewer on all five classes with the `sorter_reviewer_decision_v3` prompt and the
cutoffs of the full-corpus calibration, `reviewer-calibration-luna-v3-train-all.json`
(0.79 / 0.90 / 0.88 / 0.54 / 0.78). Its first run used the pilot's three-class cutoffs and the
code-default prompt; it is recorded in `pipeline-luna-qwen-smoke-3class.json`.

## Next (as of the pilot)

1. ~~Full calibration with decision_v1~~: done on the chat model as
   `reviewer-calibration-luna-v3-train-all.json` (all train documents, v3 prompt);
   the reviewer then moved to the Decisions model.
2. Take decision_v1 upstream as the `sorter_reviewer` code default in
   `llm-mailroom` (and the class descriptions into the reviewer's user
   message). The sandbox override then becomes a vendor mirror.
3. Check the labels of the "LIMITED POWER OF ATTORNEY" (test, labelled
   contract / Service) and "REGISTRATION RIGHTS AGREEMENT" (train, labelled
   articles_of_incorporation) documents.
4. Schema order: the reviewer's JSON puts `confidence` before `reasoning`, so
   the model commits to a number before writing its evidence. Putting
   `reasoning` first is a code change upstream, worth its own A/B.
