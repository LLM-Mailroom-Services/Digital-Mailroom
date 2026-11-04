# Cost and effectiveness against a 1x Qwen call

**Question.** Take the Qwen 3.7 Flash call on OpenRouter as the base cost, 1x, for each task. What does the
Decisions model cost as a reviewer next to one more Qwen call, and what does that money buy?

**Update 2026-11-02.** The first version of this report *modelled* the Qwen reviewer as a second 1x call. It is now
**measured**: `reviewer-validation-qwen-flash-test` ran Qwen 3.7 Flash as the reviewer over the same 323 held-out test
documents through OpenRouter (323 of 323 answered, no failures, 75 s wall). Two assumptions changed.

**Short answer.**

- **Cost: no reliable saving against Qwen.** The measured Qwen reviewer costs **0.84x** of the Qwen agent call, not 1.00x.
  A Decisions review costs **0.91x (v3.0.0) to 1.14x (v2)** of a Qwen review. Agent plus Decisions is **1.76x to 1.95x**,
  against **1.84x** for agent plus the Qwen reviewer: **4% cheaper (v3.0.0) or 7% dearer (v2)**. The 2% to 12% saving
  in the first version came from the modelled 2.00x and does not survive the measurement.
- **Effectiveness: the Decisions model is much better.** Qwen as reviewer got 93.8% of classes right (303 of 323),
  against 98.5% for Decisions. All 20 of its wrong answers carry confidence of 0.90 or higher, so no cutoff catches them:
  about **25 wrong documents per 1,000** are routed with no person, against **3** for Decisions. Decisions v2 costs
  $0.093 more per 1,000 documents and stops 22 of those, **$0.0043 per wrong document avoided**.

All figures rebuild with `python reports/decisions/build_decisions_report.py`. Source data and the arithmetic are in
[`data/summary.json`](data/summary.json); the new run's per-document results are in
[`reports/reviewer-calibration/reviewer-validation-qwen-flash-test.items.jsonl`](../reviewer-calibration/reviewer-validation-qwen-flash-test.items.jsonl).

---

## 1. How 1x is defined

| Term | Definition | Source |
| --- | --- | --- |
| **1x agent call** | One `qwen/qwen3.7-flash` call that reads a whole document (the sorter task). Priced per call with the OpenRouter sheet's long-prompt tiers: $0.03 / $0.13 per 1M tokens below 32k prompt tokens, $0.10 / $0.40 from 32k, $0.20 / $0.80 from 256k. | `config/api_prices.yaml` |
| **Measured agent tokens** | The saved Qwen pass: 323 test documents, 4,132,455 prompt tokens and 45,021 completion tokens. Per-document tokens, so each call lands in its own tier. | `data/handoff/sorter-qwen3.7-flash/test.jsonl` |
| **1x unit** | **$0.000778 per document** ($0.778 per 1,000), tiered. The handoff manifest records $0.1298 for the same pass because it prices every call at the lowest tier; section 3 shows both. | computed |
| **1x LLM reviewer (measured)** | `qwen/qwen3.7-flash` on the `sorter_reviewer` route, `code-default` prompt, the same 323 documents: 2,994,203 prompt and 50,206 completion tokens. **$0.2099** at the price sheet; OpenRouter's key usage rose by **$0.2146** over the run (2% above the sheet figure). Per document: $0.000650, **0.835x** of the agent unit. | `reviewer-validation-qwen-flash-test.json` |
| **Decisions reviewer** | `openai/gpt-6-luna-decisions`: $0.10 per 1M input tokens, nothing for output. Cost is the recorded run cost over the same test documents. | calibration reports, `LINEAGE.yaml` |

The test split is the held-out one (323 documents), so every arm below is priced and scored on the same documents
unless a row says otherwise. The Qwen reviewer reads less than the agent (9,270 prompt tokens per document against
12,794); the reviewer prompt is shorter than the sorter prompt.

## 2. Cost per document, in 1x units

![Pipelines in multiples of one Qwen agent call](figures/f01-cost-stack.svg)

| Pipeline | Basis | Agent | Reviewer | Total | USD per 1,000 docs | vs agent + Qwen reviewer |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Qwen agent alone | measured | 1.00x | – | 1.00x | $0.78 | – |
| **Agent + Qwen reviewer** | **measured** | 1.00x | 0.84x | **1.84x** | $1.43 | base |
| **Agent + Decisions, question set v2** | measured | 1.00x | 0.95x | **1.95x** | $1.52 | **6.5% dearer** |
| **Agent + Decisions, question set v3.0.0** | measured | 1.00x | 0.76x | **1.76x** | $1.37 | **4.2% cheaper** |

What the table says:

- **A Decisions review costs about what a Qwen review costs**: 1.14x (v2) or 0.91x (v3.0.0). Neither is a saving
  worth planning around. v3.0.0 is cheaper because its criteria are compact (`config/decisions/LINEAGE.yaml`).
- **Every Decisions call carries about 3,100 tokens of questions**, which is why a review is not cheaper than a Qwen read of
  the same document even at $0.10 per 1M input tokens and no output charge.
- **A Decisions call is a different request, not a cheaper read of the same one.** No output tokens, a probability for
  every option, and class, subclass and verdict in one call. What it returns is the subject of section 4.

**Question set 3.1.0 measured on half the train split.** The Decisions reviewer with the sorter handoff cost **$1.0648 billed for 1,491 train documents**
($0.000714 per document, 10.65M input tokens, median 0.62 s). On the train split the Qwen agent costs $0.000776 per document at the tiered price, so a 3.1.0 review is **0.92x** of an agent call.
No Qwen reviewer was run on the train split, so the 0.84x Qwen figure above (test split) is not directly comparable. What that review bought is in
[03](03-classification-reviewer.md#9-question-set-310-with-the-sorter-handoff-on-half-the-train-split): 91.9% to 94.0% of documents routed correctly with no person and 0.15% misrouted at the v2 cutoffs.

### Where a Qwen bill comes from

![Qwen agent cost by class](figures/f03-qwen-by-class.svg)

| Class | Documents | Mean prompt tokens | Tiered USD | Flat USD | Share of bill |
| --- | ---: | ---: | ---: | ---: | ---: |
| merger agreement | 17 | 77,254 | $0.1323 | $0.0397 | **53%** |
| contract | 60 | 15,554 | $0.0464 | $0.0291 | 18% |
| corporate record | 47 | 12,308 | $0.0298 | $0.0182 | 12% |
| insurance claim | 114 | 6,530 | $0.0244 | $0.0244 | 10% |
| correspondence | 85 | 6,623 | $0.0184 | $0.0184 | 7% |

Seventeen merger agreements, 5% of the documents, are 53% of the Qwen agent bill, because 24 documents (7%) cross the
32k-token tier and are billed 3.3x per token. The Decisions model reads at most 120,000 characters of a document
(about 25,000 tokens, plus about 3,100 of questions), so a single call is capped near **$0.0028** and cannot cross a
price tier. The merger agreements average 77,254 prompt tokens in the Qwen pass. That cap is where a Decisions review can
be cheaper than a Qwen call, and it only matters on long documents.

## 3. When the saving disappears, and when it never appeared

![Total cost under tiered and flat prices](figures/f02-sensitivity.svg)

| Pipeline | Tiered Qwen price | vs Qwen reviewer | Flat $0.03 / $0.13 | vs Qwen reviewer |
| --- | ---: | ---: | ---: | ---: |
| Agent + Qwen reviewer (measured) | 1.84x | base | 1.74x | base |
| Agent + Decisions v3.0.0 | 1.76x | **+4.2%** | 2.47x | **-41.6%** |
| Agent + Decisions v2 | 1.95x | **-6.5%** | 2.85x | **-63.5%** |

If every Qwen call were billed at the lowest tier, a Qwen review would cost $0.0964 for the 323 documents and the
Decisions pipeline would be 42% to 64% dearer. A Qwen call is the cheaper call on the 92.6% of documents under 32k tokens.
The fair statement is:

> A Decisions reviewer costs about one Qwen reviewer. It is cheaper only for the compact v3.0.0 question set at the tiered
> Qwen price, and then by 4%. Cost is not the reason to use it.

The manifest's flat figure ($0.1298 for the agent pass) understates what OpenRouter bills by about half: the price sheet puts it at $0.2513.
The Qwen reviewer's own billed figure ($0.2146) is within 2% of the sheet ($0.2099), which supports using the sheet.

## 4. What the money buys: effectiveness

The sorter alone cannot say which of its answers to trust: its 127 wrong classes on the 2,979 train documents have a
median confidence of 0.95, the same as its right answers, and 122 of the 127 sit at 0.95 or higher. A reviewer is worth
buying if it separates the documents that need a person from those that do not. **A reviewer whose confidence is no better
than the sorter's does not.**

### The measured Qwen reviewer

![Class accuracy by run](figures/f06-accuracy.svg)

| Measure (323 held-out test documents) | Qwen agent alone | **Qwen reviewer** | Decisions v2 |
| --- | ---: | ---: | ---: |
| Class accuracy | 95.7% (309) | **93.8% (303)** | **98.5% (318)** |
| Wrong answers | 14 | 20 | 5 |
| Wrong answers with confidence 0.90 or higher | 122 of 127 (train, 0.95) | **20 of 20** | 2 of 5 |
| Answered `unknown` (parks for a person) | – | 12 | 2 |
| Wrong and routed with no person | not separable | **8 (24.8 per 1,000)** | 1 (3.1 per 1,000) |
| Median latency, p95 | 2.5 s, 7.6 s | 2.7 s, 8.3 s | 0.5 s, 0.9 s (train) |

Where the Qwen reviewer is wrong: **12** correspondence documents it calls `unknown` (bare URLs, attachment stubs,
one-line messages), **7** corporate records it calls `contract` (the same indenture and rights-instrument boundary that
trips the Qwen agent), and **1** contract it calls a corporate record. Per class: insurance claims 114 of 114, mergers 17 of
17, contracts 59 of 60, correspondence 73 of 85, corporate records 40 of 47. Its 93.8% is 1.9 points below the Qwen agent's 95.7%, a difference within sampling noise
(Fisher exact p = 0.38), so a second Qwen call adds nothing measurable over the first, and its errors sit on the same boundaries.

### Silent errors and people

![Wrong documents routed with no person, per 1,000](figures/f15-silent-errors.svg)

The 12 `unknown` answers park for a person. The 8 wrong decision-class answers do not: all 20 wrong answers sit at 0.90
or higher (3 at 0.90, 12 at 0.95, 5 at 1.0), so no cutoff separates them from the right ones.

| Qwen reviewer, illustrative cutoff | Routed with no person | Wrong among them | Parked per 1,000 |
| --- | ---: | ---: | ---: |
| none, or 0.90 | 311 | 8 (2.6%) | 37 |
| 0.95 | 308 | 6 (1.9%) | 46 |
| 1.00 | 207 | 4 (1.9%) | 359 |

At the cutoff that parks 359 per 1,000, 4 wrong documents still get through. These are not calibrated cutoffs: a Qwen
reviewer has no train calibration, and none was fitted on the test split. They show that the curve is flat.

![Documents needing a person, per 1,000](figures/f04-person-load.svg)

| Arm (held-out test) | Class accuracy | Needing a person, per 1,000 | Wrong and routed with no person, per 1,000 | Per document vs 1x |
| --- | ---: | ---: | ---: | ---: |
| Qwen agent alone | 95.7% (309 / 323) | **356** | not separable by confidence | 1.00x |
| **Qwen reviewer, default prompt** | **93.8% (303 / 323)** | 37 | **24.8** | 0.84x |
| **Decisions v2** | **98.5% (318 / 323)** | **15** | **3.1** | 0.95x |
| Decisions v3.0.0 | 98.5% (318 / 323) | 71 | 3.1 | 0.76x |

### Reading the effectiveness table

1. **A calibrated reviewer cuts the people-needed load by 80% to 96%**, from 356 per 1,000 for the Qwen agent alone, but the
   number to watch is the next column. The Qwen reviewer parks only 37 per 1,000 because it is *confident about everything*, and 25 of
   those 1,000 are wrong.
2. **The Decisions model's extra cost is small per wrong document stopped.** Decisions v2 costs $0.093 more per 1,000
   documents than the Qwen reviewer ($0.743 against $0.650) and lets 21.7 fewer wrong documents through: **$0.0043 per
   wrong document avoided**. Decisions v3.0.0 is $0.060 per 1,000 *cheaper* and also lets 21.7 fewer through, but parks 34 more
   documents for a person per 1,000 (71 against 37).
3. **Against the Qwen agent alone, Decisions v2 pays for itself if a person review costs more than $0.0022.** It adds
   $0.743 per 1,000 documents and avoids 341 person reviews per 1,000. v3.0.0: $0.590 and 285, or $0.0021. No human cost is
   assumed: these are break-even figures, not savings.
4. **The Decisions model's edge is in its confidence.** All 20 of the Qwen reviewer's wrong answers sit at 0.90 or higher
   (the Qwen agent: 122 of 127 at 0.95 or higher). Decisions' wrong answers are spread: 2 of 5 at 0.90 or higher on the test
   split, and none of its 12 question-set-v1 errors on the train draw above 0.84. Train is in-sample for the question set, so this is
   supported on train and suggestive on test; the 3.1.0 half-train run adds 2 of 20 wrong answers at 0.90 or higher (03, section 9).

   ![Wrong answers at high confidence](figures/f07-wrong-conf.svg)

5. **v3.0.0 costs less per call and more in people.** Its verdict question parked 23 test documents against 5 for v2. See
   [03](03-classification-reviewer.md#6-question-set-v300-the-verdict-question).

### Latency

![Latency by call](figures/f05-latency.svg)

A Decisions call returns in a median 0.5 s (p95 0.9 s). The Qwen agent pass was 2.5 s (p95 7.6 s), the Qwen reviewer
2.7 s (p95 8.3 s). The load differs between runs (see the figure note), so read this as
direction, not a benchmark. Summing medians, agent plus Qwen reviewer is about 5.2 s; agent plus Decisions about 3.0 s.

## 5. The extraction task

The 1x for extraction is the Qwen 3.7 Flash specialist call. The Decisions model was tried there as a gate over the
specialist's extraction (`task: extraction_gate`). **Cost parity cannot be computed from tracked files**: the run
configs carry token and dollar *estimates* ($0.24 for 220 documents), not usage records. More to the point, the gate did
not work, so its price is moot:

- Pooled over 910 documents, the gate's accept confidence ranks good extractions *below* bad ones (AUROC 0.41).
- It says "accept" on 26.8% of documents; 11.3% of extractions really score 0.80 or higher.
- It says "retry" on 72.4% (659 of 910). Acting on that verdict would trigger up to 0.72 extra specialist calls per
  document, at 1x each, for no measured gain.

Details in [04](04-extraction-gate.md). **Do not wire the gate into a pipeline as it stands.** No Qwen-judge baseline for
extraction was run, so the comparison section 4 makes for classification has no counterpart here.

## 6. Bottom line

| Claim | Holds? |
| --- | --- |
| Decisions as reviewer is cheaper than a second Qwen call | **No**: 4% cheaper (v3.0.0) to 7% dearer (v2) than the measured Qwen reviewer; 42% to 64% dearer at the flat price |
| A Decisions call is faster than a Qwen call | **Yes**: median 0.5 s against 2.5 to 2.7 s (different loads) |
| Decisions is more accurate than a Qwen reviewer | **Yes**: 98.5% against 93.8% on the same 323 documents |
| Decisions lets fewer wrong documents through | **Yes**: 3 against 25 per 1,000, for $0.0043 per wrong document avoided |
| A calibrated reviewer cuts people-needed documents | **Yes**: 356 to 15 per 1,000 (v2) |
| Decisions' confidence can drive cutoffs; the Qwen reviewer's cannot | **Yes against Qwen** (20 of 20 Qwen errors at 0.90+); Decisions is supported on train, suggestive on test |
| The Decisions extraction gate is usable | **No** |
