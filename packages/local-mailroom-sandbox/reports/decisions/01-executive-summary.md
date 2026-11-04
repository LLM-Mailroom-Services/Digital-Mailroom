# Executive summary: the decision-reviewer experiments

Experiments of 2026-11-01 (SAND-085, issue #208) tried the Decisions model, `openai/gpt-6-luna-decisions`, as a reviewer in
two places: checking the sorter's class and subclass, and gating the specialist's extraction. This report prices it
against **one Qwen 3.7 Flash call on OpenRouter as 1x** and sets the cost beside what it bought.

## The six findings

**1. A Decisions review costs about one Qwen review, not less.** The Qwen reviewer was measured on 2026-11-02 (Qwen 3.7 Flash,
the same 323 test documents, OpenRouter): **0.84x** of the agent call. A Decisions review is **0.91x (v3.0.0) to 1.14x (v2)** of
that. Agent plus Decisions is **1.76x to 1.95x**, against **1.84x** for agent plus a Qwen reviewer: **4% cheaper or 7%
dearer**. The 2% to 12% saving in the first version of this report came from a modelled 2.00x and does not survive the
measurement. [Detail](02-cost-and-effectiveness.md#2-cost-per-document-in-1x-units)

![Pipelines in multiples of one Qwen agent call](figures/f01-cost-stack.svg)

**2. Cost is not where the Decisions model wins, and Qwen's long-prompt tier decides even the narrow cost result.** Qwen's price
triples at 32k prompt tokens. Seventeen merger agreements, 5% of the test documents, are 53% of the Qwen agent bill. The
Decisions model reads at most 120,000 characters, so one call is capped near $0.0028. Price every Qwen call at the lowest tier
and agent plus Decisions costs **42% to 64% more** than agent plus a Qwen reviewer. [Detail](02-cost-and-effectiveness.md#3-when-the-saving-disappears-and-when-it-never-appeared)

**3. A Qwen reviewer lets wrong answers through unflagged.** On the same 323 documents it got **93.8%** of classes right (the Qwen agent alone:
95.7%; Decisions v2: **98.5%**), and **all 20 of its wrong answers carry confidence of 0.90 or higher**, so no cutoff catches
them. About **25 wrong documents per 1,000** are routed with no person, against **3** for Decisions. For $0.093 more per 1,000
documents (Decisions v2), 22 fewer wrong documents get through: **$0.0043 per wrong document avoided**.
[Detail](02-cost-and-effectiveness.md#4-what-the-money-buys-effectiveness)

![Wrong documents routed with no person, per 1,000](figures/f15-silent-errors.svg)

**4. A calibrated reviewer is repaid in people's time.** The Qwen agent alone sends 356 of every 1,000 documents to a person,
because its confidence does not separate its errors (122 of its 127 train errors sit at 0.95 or higher). Decisions v2 cuts that to **15
per 1,000**; it pays back against the agent alone if a review costs more than **$0.0022**. On held-out accuracy it ties the
Qwen reviewer (98.5% against 93.8%): its confidence advantage is shown on train and only suggestive on test. [Detail](03-classification-reviewer.md#3-does-confidence-separate-right-from-wrong)

![Documents needing a person, per 1,000](figures/f04-person-load.svg)

**5. Question set 3.1.0 with the sorter handoff routes 92% to 96% of documents correctly with no person, and fixes far more sorter errors than it causes.**
On half the train split (1,491 documents, the Decisions model, the saved Qwen sorter answer attached to every request): primary type 98.7% against the
sorter's 95.9% (45 fixed, 4 broken), subclass 84.0% against 72.4% (266 fixed, 96 broken). At the v2 cutoffs, fixed before the run, 1,367 of 1,488 scored documents (91.9%) reach extraction
correctly with no person under the live pipeline rule, 2 are misrouted (0.15%) and 119 park for a person, 59 of them real sorter errors; if the reviewer's answer alone decides, 1,398 (94.0%).
The sorter alone would misroute 61 (4.1%). On the 1,096-document clean subset the gains shrink but hold (primary type 98.3% against 97.0%, subclass 82.8% against 74.5%). It cost
$1.06 billed, 0.92x of the Qwen agent per document. [Detail](03-classification-reviewer.md#9-question-set-310-with-the-sorter-handoff-on-half-the-train-split)

![Routing outcomes](figures/f16-routing-outcomes.svg)

**6. The Decisions extraction gate does not work.** Pooled over 910 documents its accept confidence ranks good
extractions below bad (AUROC 0.41), it accepts 26.8% of documents when 11.3% are good, and it says "retry" on 72.4%.
No class reaches the 90% precision target. No usage records are committed to price it, and acting on its verdicts would add up
to 0.72 specialist calls per document. [Detail](04-extraction-gate.md)

![Gate accept rate against real quality](figures/f13-gate-accept.svg)

## Where the Decisions model wins and where it does not

| Dimension | Against | Result |
| --- | --- | --- |
| Per-document API cost | Qwen reviewer (measured) | 4% cheaper (v3.0.0) to 7% dearer (v2) at the tiered price; 42% to 64% dearer at the flat price |
| Latency | Qwen agent, Qwen reviewer | faster: median 0.5 s against 2.5 s and 2.7 s (loads differ) |
| People-needed documents | Qwen agent alone | 15 against 356 per 1,000 |
| Held-out accuracy | Qwen reviewer | **better**: 98.5% against 93.8% |
| Wrong documents routed with no person | Qwen reviewer | **better**: 3 against 25 per 1,000 |
| Confidence usable for cutoffs | Qwen reviewer | **better**: all 20 Qwen errors sit at 0.90+; 2 of Decisions' 5 test errors do |
| Extraction gating | no gate | no useful signal |

## Decisions the data supports

1. **Use a Decisions review instead of a Qwen reviewer for accuracy and confidence, not for cost.** Cost is a wash (-4% to
   +7%); 22 fewer wrong documents per 1,000 reach no person for about $0.09 per 1,000. Do not describe it as a saving.
2. **Keep question set v2's routing; do not adopt v3.0.0.** v3.0.0 is 20% cheaper per call and parks 23 test documents for a
   person against 5. Its verdict question mostly answers "continue" whatever the class. The lineage's next step, to derive
   the verdict in code (4.0.0), is the right one.
3. **Finish the 3.1.0 calibration before turning on cutoffs.** Half of the train split is done (1,491 documents, $1.06). The other half is not, and no held-out check exists: the 323-document test split informed 3.1.0, so a clean check needs documents unseen during question-set development. Cutoffs moved by up to 0.30
   between question sets, and the 3.1.0 cutoffs from this run (0.48 to 0.64, merger 0.94) are far below the v2 ones.
4. **Do not wire the extraction gate into a pipeline.** Redesign it around the per-field questions, one of which
   (`contract.renewal_terms`, AUROC 0.89) shows a real signal.
5. **Test whether a better-prompted Qwen reviewer closes the gap.** The Qwen reviewer ran once, on the default prompt and without the
   sorter's answer. A prompt that states the corpus conventions targets the two boundaries behind 19 of its 20 errors
   (mailbox fragments as correspondence, corporate records against contracts). About $0.2 per variant.

## What is established, and what is not

These results are **classification-level measurements on the 323 held-out test documents**, scored against the corpus labels. They
are real runs with tracked per-document data for the Qwen runs and tracked summaries for the Decisions runs. They are not yet a
measurement of the reviewer **inside the running pipeline**.

| Claim | Status | Basis |
| --- | --- | --- |
| Decisions v2 beats the Qwen reviewer on class accuracy | **Established** | 318 vs 303 of 323; 98.5% (CI 96.4-99.3) vs 93.8% (CI 90.6-96.0); Fisher exact p = 0.003 |
| Decisions v2 lets fewer wrong documents through | **Established, small counts** | 1 of 318 vs 8 of 311 routed with no person; p = 0.019; the Decisions side is one document |
| Qwen reviewer is worse than the Qwen agent | **Not shown** | 93.8% vs 95.7%, p = 0.38 |
| Decisions v2 beats the Qwen agent alone | **Suggestive** | 98.5% vs 95.7%, p = 0.06 |
| Agent + Decisions costs about the same as agent + Qwen reviewer | **Established** | measured on both sides; Qwen billed $0.2146 vs $0.2099 at the sheet; Decisions costs are rounded report figures |
| Decisions' confidence supports cutoffs where Qwen's does not | **Supported on train, suggestive on test** | 12 of 12 v1 errors below 0.85 on the train draw (in-sample); only 5 test errors; Qwen's 20 of 20 are at 0.90+ |
| The Decisions reviewer (3.1.0, with the sorter handoff) routes correctly under the pipeline's rule | **Measured on train, in-sample for the wording** | 1,367 of 1,488 correct with no person, 2 misrouted, at v2 cutoffs; clean-subset gains hold; not held out |
| The Decisions reviewer inside the running graph | **Not measured** | the routing rule was applied to saved answers; the only graph run is the 10-document smoke |
| Effect of the handoff | **Not isolated** | v2 (no handoff) and 3.0.0 / 3.1.0 (handoff) differ in question set too; the Qwen reviewer cannot take a handoff in the current code |
| Cutoffs | **Provisional** | v2: a 735-document draw; 3.1.0: cross-fitted on the same half-train run, flattering; merger agreement misses the 95% target on 68 documents |
| Extraction gate | **Does not work** | pooled AUROC 0.41 over 910 documents |

The Qwen reviewer ran once, on the default prompt. Part of its gap to Decisions may be the prompt, not the model. What the data
does not yet contain, and what would turn this into an in-pipeline claim: the 323 test documents run through the full graph with the
Decisions reviewer and with the Qwen reviewer, scoring end-to-end routing, parked documents and extraction outcomes.

Method, source inconsistencies and limits of the comparison are in [05](05-method-and-data-quality.md).
