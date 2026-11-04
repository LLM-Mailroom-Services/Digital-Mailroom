# Classification reviewer experiments

The Decisions-model reviewer checks the sorter's class and subclass for every document before extraction. Work ran
2026-11-01 under SAND-085 (issue #208). Sources: `reports/reviewer-calibration/`, `config/decisions/LINEAGE.yaml`,
`reports/sorter-handoff/sorter-qwen3.7-flash-audit.md`.

## 1. Scope

Two models are compared: **Qwen 3.7 Flash** (the 1x agent and, since 2026-11-02, a measured 1x reviewer) and the **Decisions
model** (`openai/gpt-6-luna-decisions`, OpenRouter `POST /api/alpha/decisions`), which returns a probability for every option and
bills input tokens only. Earlier reviewer runs on a plain chat model were a configuration mistake: they are superseded in the
repository, their cutoffs do not apply, and they are left out of this analysis. Guards now in the code refuse a Decisions model on a
chat backend, a chat model on the Decisions backend without an explicit opt-in, and a paid reviewer run with no `reviewer:` block.

## 2. Class accuracy across runs

![Class accuracy by run](figures/f06-accuracy.svg)

| Run | Split | n | Correct | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Qwen agent (the sorter) | test | 323 | 309 | 95.7% |
| Qwen reviewer · default prompt (measured 2026-11-02) | test | 323 | 303 | 93.8% |
| Decisions · question set v1 | train | 735 | 723 | 98.4% |
| Decisions · question set v2 | train (in-sample) | 735 | 735 | 100.0% |
| **Decisions · question set v2** | **test** | 323 | **318** | **98.5%** |
| Decisions · question set v3.0.0 | test | 323 | 318 | 98.5% |

Hollow dots in the figure are train runs, where the prompt or question set was tuned on the same documents. They are
not evidence of how the reviewer will do on new documents. **The honest numbers are the filled dots**: about 98.5% on
held-out documents for the Decisions model, against 93.8% for the Qwen reviewer and 95.7% for the Qwen agent alone.

The Qwen 3.7 Flash reviewer is the lowest held-out arm: 93.8% (303 of 323), not distinguishable from the Qwen agent's 95.7% (p = 0.38) and clearly below Decisions v2 (p = 0.003). Its 20 errors are
12 correspondence documents called `unknown`, 7 corporate records called `contract` and 1 contract called a corporate record, and every one
sits at confidence 0.90 or higher. [Cost and effectiveness](02-cost-and-effectiveness.md#the-measured-qwen-reviewer) sets this beside the cost.

The single misroute in both held-out Decisions runs is a "LIMITED POWER OF ATTORNEY" labelled contract / Service. The
reviewer says corporate_record / powers_of_attorney at 1.0, which reads as a label error, and the sorter audit moved the
label. The other test miss at 1.0 is an accounting standard (EITF 96-13) that the reviewer calls `unknown`; `unknown`
is not a decision class, so it parks for a person.

## 3. Does confidence separate right from wrong?

A cutoff only helps if wrong answers sit below it.

![Wrong answers at high confidence](figures/f07-wrong-conf.svg)

| Run | Wrong at confidence 0.90 or higher |
| --- | --- |
| Qwen agent, train (0.95 threshold) | 122 of 127 |
| **Qwen reviewer, default prompt, test** | **20 of 20** |
| Decisions v2, test | 2 of 5 |
| Decisions v1, train | **0 of 12** (all at 0.52 to 0.84) |

Qwen's confidence is its own, written into the answer: 203 of the Qwen reviewer's 303 right answers sit at 1.0, and all 20 wrong
ones at 0.90 or higher, so no cutoff separates them. The Qwen agent is the same (122 of 127 errors at 0.95 or higher). The Decisions
probabilities spread: on the test split 3 of 5 errors fall below 0.90, and on the train draw all 12 question-set-v1 errors sit at 0.84
or lower. The train rows are in-sample for the question set, so the plain reading is that the Decisions advantage is *in the
confidence*, supported on train and suggestive on test; the half-train run in [section 9](#9-question-set-310-with-the-sorter-handoff-on-half-the-train-split) adds 2 of 20 wrong answers at 0.90 or higher for question set 3.1.0.

## 4. Cutoffs

![Cutoffs by question set](figures/f08-cutoffs.svg)

Cutoffs come from five-fold cross-fit at a 95% held-out accuracy target with Wilson 95% intervals, on the 735-document train draw.

| Class | Decisions v1 | Decisions v2 |
| --- | ---: | ---: |
| contract | 0.62 | 0.78 |
| corporate record | 0.66 | 0.96 |
| correspondence | 0.52 | 0.64 |
| insurance claim | 0.41 | 0.70 |
| merger agreement | 0.99 | 0.99 |

Two things to take from it:

- **Cutoffs are unstable.** Corporate record goes 0.66 to 0.96 between question sets; insurance claim 0.41 to 0.70. With no
  wrong answers in a class, the cutoff is just the lowest probability of a right answer, so a 150-document draw sets it. Use the
  cutoffs from a full-train run before the pilot goes live (a half-train run now exists: section 9). Issue #208 keeps them provisional.
- **The 95% target was missed once.** Decisions v1 missed correspondence (96.1% held out, lower bound 91.8%) because of First
  Notice of Loss errors, fixed in v2. Every class meets it on v2.

## 5. The v1 to v2 improvement loop

v1 made 12 class errors on the train draw, all at probability 0.52 to 0.84:

| Error | Count | v2 change |
| --- | ---: | --- |
| insurance claim (First Notice of Loss) read as correspondence or unknown | 8 | FNOL forms named in the insurance criterion; correspondence excludes claim paperwork |
| corporate record (untitled subsidiary table) read as unknown | 2 | A bare table of company names and jurisdictions is a subsidiary list |
| merger agreement ("Transaction Agreement" with merger subsidiaries) read as contract | 2 | Transaction and business-combination agreements that merge through a Merger Sub are mergers |

![Subclass accuracy, v1 to v2](figures/f09-dumbbell.svg)

Six of seven weak subclasses improved; `correspondence / meeting_request` fell from 18 of 21 to 14 of 21 as the
correspondence markers became yes/no questions. Train subclass accuracy rose from 78.0% to 82.6%, and to 88.0%
(604 of 686) once the 49 merger documents labelled `other` are excluded.

**What limits subclass accuracy now is the labels**, not the reviewer:

1. Merger `other` means "unannotated" (no MAUD Type of Consideration), so no reader can predict it. On the 86 annotated
   mergers v2 is right on 84 (97.7%).
2. Correspondence subclasses are keyword labels. An ordinary email that mentions demand letters is labelled `demand`.
3. Corporate records carry label noise: 9 "Certificate of Amendment" documents labelled `board_resolution`, bylaws labelled
   `articles_of_incorporation`.

The sorter audit applied 28 train and 4 test label corrections; 49 train and 8 test merger `other` rows are scored for
class only.

## 6. Question set v3.0.0: the verdict question

v3.0.0 added the sorter's answer to the request and a verdict question (continue, correct the subclass, reclassify, or
human review). On the held-out test it kept class accuracy and added people-work:

![Verdict given, by what the handoff needed](figures/f10-verdict.svg)

| What the sorter handoff needed | Documents | Verdict: continue | Correct subclass | Reclassify | Multiple docs | Human review |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sorter was right | 174 | **170** | 2 | 0 | 1 | 1 |
| Subclass was wrong | 135 | 125 | **4** | 2 | 3 | 1 |
| Class was wrong | 14 | 10 | 0 | **1** | 0 | 3 |

The verdict does not follow the model's own `doc_type` answer: with the class wrong on 14 documents it said "continue"
10 times, and with only the subclass wrong on 135 it said "continue" 125 times. Subclass accuracy slipped from 265 to
263 of 323.

![Documents parked for a person, v2 against v3.0.0](figures/f11-human-by-class.svg)

| Class | v2 parked | v2 rate | v3.0.0 parked | v3.0.0 rate |
| --- | ---: | ---: | ---: | ---: |
| contract | 1 / 59 | 1.7% | 1 / 60 | 1.7% |
| corporate record | 1 / 48 | 2.1% | 5 / 48 | 10.4% |
| correspondence | 1 / 83 | 1.2% | 7 / 81 | 8.6% |
| insurance claim | 0 / 114 | 0.0% | 2 / 114 | 1.8% |
| merger agreement | 0 / 17 | 0.0% | 5 / 17 | 29.4% |
| unknown | 2 / 2 | 100% | 3 / 3 | 100% |
| **all** | **5 / 323** | **1.5%** | **23 / 323** | **7.1%** |

Four of nine human verdicts were email forwards called `multiple_documents`. v3.0.0 is cheaper per call (about 20%) and
sends nearly five times as many documents to a person. **It is not an improvement.** `LINEAGE.yaml` already marks 3.1.0
(insurance subclasses cover the whole taxonomy; a forward is not `multiple_documents`) as the frontrunner, and proposes
deriving the verdict *in code* from the doc_type and subclass answers for 4.0.0, keeping only the human edge cases as a
model question. This report agrees with that plan.

## 7. The sorter the reviewer checks

![Sorter class errors by pattern](figures/f12-sorter-errors.svg)

The Qwen sorter gets 95.7% of classes right on train (2,852 of 2,979) and 69 to 72% of subclasses. Its 127 class errors
are three patterns, and the Decisions reviewer had already agreed with the label on 33 of them. They are sorter errors,
not label errors. Sorter prompt V15 (llm-mailroom #135) encodes the fixes and has not yet been validated by a run.

## 8. Pipeline smoke

`pipeline-luna-decisions-qwen-smoke`: ten documents through the full pipeline, Qwen3.7 Flash on every node, the
Decisions reviewer on all five classes with v2 cutoffs. All ten classified correctly; the reviewer accepted nine at 0.98
to 1.0 and sent a property claim at 0.65 (cutoff 0.70) to a person as `reviewer_low_confidence`, which is the routing the
cutoff is for. 176 s wall; the longest document (a 442,000-token merger) took 173 s end to end.

## 9. Question set 3.1.0 with the sorter handoff, on half the train split

Run `reviewer-calibration-luna-decisions-v3.1.0-train-half` (2026-11-02, signed JB): `openai/gpt-6-luna-decisions`, question set 3.1.0,
the saved Qwen sorter answer attached to every request, **1,491 of the 2,979 train documents**, drawn per class in proportion (seed 42). All
1,491 were answered, none failed, and every request carried the sorter's primary type, subclass and confidence (checked item by item
against the saved handoff). The other half, and the full-split run, have not been run.

**Cost and speed.** $1.0648 billed (usage records), 10.65M input tokens, median 0.62 s and 95th percentile 0.98 s per document. That is
$0.000714 per document, **0.92x** of the Qwen agent's $0.000776 per document on the same split (tiered price).

### Primary type and subclass against the verified targets

![Sorter against reviewer accuracy](figures/f17-sorter-vs-reviewer.svg)

| Measure (train, in-sample for the question wording) | Qwen sorter | Decisions reviewer | Reviewer fixed / broke | McNemar p |
| --- | ---: | ---: | ---: | ---: |
| Primary type, 1,488 scored | 95.9% (1,427) | **98.7% (1,468)** | 45 / 4 | < 0.001 |
| Subclass, 1,463 scored | 72.4% (1,059) | **84.0% (1,229)** | 266 / 96 | < 0.001 |
| **Clean subset** (1,096 documents, see below): primary type | 97.0% (1,063) | 98.3% (1,077) | 18 / 4 | 0.004 |
| **Clean subset**: subclass | 74.5% (817) | 82.8% (908) | 181 / 90 | < 0.001 |

| Subclass by class | Documents | Sorter | Reviewer |
| --- | ---: | ---: | ---: |
| contract | 269 | 82.9% (223) | 86.6% (233) |
| corporate record | 201 | 53.2% (107) | **91.5% (184)** |
| correspondence | 457 | 54.3% (248) | 60.8% (278) |
| insurance claim | 493 | 89.5% (441) | **100% (493)** |
| merger agreement | 43 | 93.0% (40) | 95.3% (41) |

- **The reviewer fixes far more than it breaks**: 45 sorter class errors corrected against 4 introduced, and 266 subclass errors against 96.
- **Correspondence is the weak class** (61% subclass): its subclasses are keyword labels in the corpus, as in section 5.
- **Contracts**: the reviewer is not better on primary type (267 of 269 against the sorter's 269 of 269) and gains 4 points on subclass.
- **Insurance at 100%** follows the new subclass coverage, but the corpus labels only the CMS tables, auto and property, so the figure is easy to reach.
- **Confidence on wrong answers.** The reviewer gave 20 wrong primary types: 14 are `unknown` (which always parks), 18 sit below 0.90 (10 of them at 0), and only
  **2 are at 0.90 or higher**. The Qwen reviewer's wrong answers were 20 of 20 at 0.90 or higher.

### Successful routing instances

A routed document is a **success** when it goes on to extraction with the right primary type and no person involved. Two rules are shown.
The pipeline rule is the live behaviour: reaching extraction needs the reviewer to agree with the sorter at its class cutoff; any disagreement parks for a person,
because 1,485 of the 1,491 sorter answers are at 0.95 or higher, which leaves no low band for a reviewer to correct on its own. "Reviewer alone" lets the reviewer's answer decide
and is the script's `routing_at_cutoffs` definition.

![Routing outcomes](figures/f16-routing-outcomes.svg)

| Cutoffs · rule | Scored | **Routed correctly, no person** | Misrouted (wrong class, no person) | Parked: sorter wrong (caught) | Parked: sorter right |
| --- | ---: | ---: | ---: | ---: | ---: |
| v2 · **pipeline rule** | 1,488 | **1,367 (91.9%)** | 2 (0.15% of 1,369) | 59 | 60 |
| v2 · reviewer alone | 1,488 | **1,398 (94.0%)**, incl. 31 corrected sorter errors | 2 (0.14% of 1,400) | 28 | 60 |
| 3.1.0 · pipeline rule | 1,488 | 1,392 (93.5%) | 4 (0.29% of 1,396) | 57 | 35 |
| 3.1.0 · reviewer alone | 1,488 | 1,432 (96.2%), incl. 40 corrected | 6 (0.42% of 1,438) | 17 | 33 |

- **The v2 cutoffs were fixed before this run**, so the first two rows are the clean reading. The 3.1.0 cutoffs (contract 0.53, corporate record 0.50, correspondence
  0.48, insurance claim 0.64, merger agreement 0.94) were cross-fitted on this same run, which flatters them; merger agreement misses the 95% target on 68 documents.
- **The sorter alone, if trusted, misroutes 61 of 1,488 (4.1%).** The reviewer handles 59 of those 61 (fixed or parked) at the v2 cutoffs, leaving **2 misrouted (0.15%)**.
- **The price of that safety is parked documents**: 119 at the pipeline rule, of which 60 had a correct sorter answer. Reviewer-alone parks 88 (5.9%).
- **The 3.1.0 cutoffs are looser and let more through**: 4 misrouted under the pipeline rule and 6 under reviewer-alone routing (2 of the 6 are sorter-right documents the reviewer broke), against 2 under either rule at the v2 cutoffs.
- A person also gets any document with a human verdict: 47 documents carry one, of which 29 are `multiple_documents`, 18 of those on documents where the sorter was right. The forward fix
  in 3.1.0 did not remove the verdict; this run cannot say how many of the 29 are real forwards.

### The verdict question, again

| What the handoff needed | Documents | continue | correct subclass | reclassify | human / other |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sorter right | 1,084 | 1,056 | 3 | 5 | 20 |
| Subclass wrong | 343 | 312 | **13** | 6 | 12 |
| Class wrong | 61 | 44 | 0 | **3** | 14 |

The verdict still says "continue" for 44 of 61 documents whose class was wrong and for 312 of 343 whose subclass was wrong, as in 3.0.0. The routing value above comes from the
reviewer's primary-type and subclass **answers and probabilities**, not from the verdict. This supports deriving the verdict in code (4.0.0).

### What this run does and does not show

- **Sample integrity checked before spending:** 1,491 unique documents, class mix proportional to the corpus, 100% handoff coverage, request body inspected, estimated cost $1.02 against $1.06 billed.
- **In-sample for the question wording.** 368 of the 1,491 documents were in the 735-document draw that question set v2 was written from, and 27 were checked by the Decisions model to
  settle their verified targets, so those targets already contain this model's answers. The **clean subset** (1,096 documents) removes both groups. All 68 mergers are in the excluded group, so
  the clean subset has no mergers.
- **Not held out.** It is a half of the train split, not the test split, and 3.1.0 was designed after seeing the test split's errors. The test split can no longer test 3.1.0 cleanly.
- **Compared with 3.0.0 on test**: 98.5% class accuracy (318 of 323) and 7.1% parked at the v2 cutoffs; here 98.7% and 6.0% (90 of 1,491). The documents differ, so this is consistent, not a like-for-like result.
