# Method, data quality and open measurements

## How the numbers were made

- **Two paid runs, then nothing else.** The first version of this report called no model. On 2026-11-02 two runs were
  made: the 3.1.0 half-train run (1,491 documents, $1.06 billed; below) and
  `reviewer-validation-qwen-flash-test` (Qwen 3.7 Flash as reviewer, 323 test documents, OpenRouter, signed JB), which replaced the
  modelled 1x reviewer with a measurement: $0.2099 at the price sheet, $0.2146 billed. Every figure comes from files tracked in this
  repository, rebuilt by `python reports/decisions/build_decisions_report.py` (stdlib only). `--check` exits 1 if a
  figure, CSV, `summary.json` or the dashboard is stale.
- **Computed from data:** the Qwen agent's cost (per-document tokens priced against the tiered OpenRouter sheet), its
  latency and class accuracy, the per-class breakdowns, cutoffs, routing rates and every extraction-gate number.
- **Taken from prose reports:** class and subclass accuracy and the run costs of the Decisions reviewer runs.
  Each sits in `RECORDED` / `RUNS` in the script with its source file. The recorded inputs are echoed under
  `recorded_inputs` in `data/summary.json`.
- **Measured on 2026-11-02:** the 3.1.0 half-train run (`reviewer-calibration-luna-decisions-v3.1.0-train-half.{json,routing.json,run.json,items.jsonl}`, per-document answers with the sorter's answer, targets and routing flags, no document text) and the 1x Qwen reviewer (`reports/reviewer-calibration/reviewer-validation-qwen-flash-test.json` and
  `.items.jsonl`, per-document tokens, answers and latency; no document text).
- **Modelled:** nothing remains modelled.

## Colour and accessibility

Colour follows the entity in every figure: **blue** is the Qwen agent, **orange** the Qwen reviewer,
**aqua** the Decisions model, grey the baseline or comparison. The three slots come from the dataviz reference palette
and were run through the validator in light and dark, on adjacent and all-pairs lists:
[`data/palette-validation.txt`](data/palette-validation.txt). All checks pass. One WARN remains (light aqua at 2.74:1
against the surface); its relief is a visible value on every mark or a table view. Heatmaps use one blue ramp, with the
anchor flipped in dark mode. Every figure has a `<title>` hover on each mark, keyboard focus, and a CSV twin in
[`data/`](data/); the [dashboard](decisions-dashboard.html) adds tooltips and a table view under each chart.

## Data-quality notes

These are source inconsistencies found while assembling the report. None changes a conclusion, and none was edited at the source.

| # | Where | What | How the report handles it |
| --- | --- | --- | --- |
| 1 | Qwen handoff manifest vs price sheet | `list_cost_usd` ($0.1298 test, $1.2007 train) prices every call at the lowest tier ($0.03 / $0.13). The price sheet in `config/api_prices.yaml` bills 3.3x per token from 32k prompt tokens. | Uses the sheet: $0.2513 test, $2.3119 train. Shows the flat figure as a sensitivity. |
| 2 | `reviewer-calibration-luna-decisions.md` vs `LINEAGE.yaml` | Decisions v2 test subclass accuracy: the report says 83.3%; the lineage compares v3.0.0's 263 of 323 against v2's 265 of 323 (82.0%). | Subclass accuracy is not charted across versions; the lineage figure is quoted for v2 vs v3.0.0. |
| 3 | Same report | Train v2 cost read $0.69 and was corrected to $0.86 (8.55M tokens). | Uses $0.86. |
| 4 | `extraction-gate-luna-v1.1.0-r2.yaml` | The cost comment repeats the 220-document estimate (about 2.4M tokens, $0.24) for 690 documents. | Gate cost is not used anywhere. |
| 5 | Latency | Qwen agent and reviewer: 323 test documents. Decisions: 735 train documents at concurrency 16. | Presented as direction only; the figure says so. |
| 6 | Cutoffs | With no wrong answers in a class, the cutoff is the lowest right-answer confidence, so it tracks sample size. | Called out in the figure subtitle and in [03](03-classification-reviewer.md#4-cutoffs). |
| 7 | Routing counts | Per-class routing counts use the reviewer's class (59 / 48 / 83 / 114 / 17 plus `unknown`), not the true class (60 / 47 / 85 / 114 / 17). | Each table is labelled with its own basis. |
| 8 | Qwen reviewer cost | The price-sheet figure ($0.2099) and the key-usage delta ($0.2146) differ by 2%. The delta assumes no other use of the key during the 75 s run. | Ratios use the sheet figure, so the reviewer and the agent are priced the same way. |
| 9 | `preflight.py` | The same-model guard ("a reviewer on the sorter's model only repeats its answer") also fired on `task: sorter_reviewer` runs, where the sorter never runs and the engine model is the reviewer by rule. | Scoped to non-calibration runs in this change, with a test; pipeline runs keep the guard. |
| 10 | Half-train run overlap | 368 of the 1,491 documents were in the 735-document draw question set v2 was written from, and 27 were used by a Decisions run to settle their verified targets, so those targets already contain this model's answers. | A clean subset (1,096 documents, no mergers) is scored beside the full sample. |
| 11 | Subclass denominators | The calibration script scores subclass by the reviewer's predicted class (1,443 scored, 85.2%); the report scores by true class so the sorter is comparable (1,463 scored, 84.0%). | The report's figure is used throughout; the script's is in `reviewer-calibration-luna-decisions-v3.1.0-train-half.json`. |
| 12 | Routing definitions | The script counts a document as routed unattended when the reviewer's answer clears its cutoff. The live pipeline also parks any disagreement with a medium or high sorter. 1,485 of 1,491 sorter answers are at 0.95 or higher, so the pipeline rule is the stricter, faithful one. | Both are shown; the pipeline rule leads. |
| 13 | 3.1.0 cutoffs | Fitted by cross-fit on the same run they are applied to. | Labelled optimistic; the v2 cutoffs, fixed before the run, lead. |

## Limits of the cost comparison

1. **The Qwen reviewer is one prompt on one split.** It used the `code-default` reviewer prompt and did not see the sorter's
   answer, so it does not test a reviewer that reads a handoff. A prompt that states the corpus conventions could change its
   accuracy; its cost would move little.
2. **Run costs are rounded to the cent** in the source reports ($0.24, $0.1905).
3. **No human cost is assumed.** The break-even figures ($0.0022 per review) say what a review has to be worth, not
   what it is worth.
4. **The reviewer ran on every document in these experiments.** In the pipeline today the LLM reviewer runs only on
   medium-confidence sorter results, while a `decision_only` class reaches its reviewer at any confidence. The
   traditional pipeline would therefore pay for fewer reviewer calls than the 1.84x line assumes.
5. **Held-out means 323 documents.** One misroute is 0.3%; the intervals around any single rate are wide.

## What to measure next

| # | Measurement | Why | Rough cost |
| --- | --- | --- | --- |
| 1 | Qwen reviewer with a prompt that states the corpus conventions, and one that reads the sorter's handoff | Separates "Qwen" from "this prompt" in the 93.8% | about $0.2 each |
| 2 | The other half of the train split with 3.1.0 and the handoff, then 3.1.0 with cutoffs frozen first on documents unseen during question-set development | Cutoffs that are not fitted on the data they are scored on; the full-split run is `reviewer-calibration-luna-decisions-v3.1.0-train`. The 323 test documents are **not** independent of 3.1.0 (their errors informed it), so a run there must be labelled non-independent | about $1.04, plus the held-out set |
| 2b | A Qwen reviewer on the same 1,491 train documents | The Qwen comparison exists only on the test split | about $0.5 |
| 3 | Validate sorter prompt V15 with `config/runs/sorter-v15-qwen-train-errors.yaml` | Lowers the 1x agent's error rate before the reviewer sees it | about $0.49 |
| 4 | Question set 4.0.0: derive the verdict in code | Removes the 5x human-review penalty of 3.0.0 | none new |
| 5 | A per-field extraction gate scored against field-level truth, with a Qwen-judge baseline | The gate's one signal is at field level; extraction has no 1x comparison yet | open |

Each paid run needs a signed `sandbox run start --initials XX`; nothing in this table has been started.
