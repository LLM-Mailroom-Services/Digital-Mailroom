# Correspondence extraction floor — offline diagnosis (`run-20-correspondence-awq-c8`)

Issue: [#21](https://github.com/Exios66/local-mailroom-sandbox/issues/21).

This note is **offline**. It uses tracked reports, the vendored scorer, and
the specialist schema/prompt. It does **not** replay Modal, spend GPU, or
call a live LLM.

| | |
|---|---|
| run_id | `run-20-correspondence-awq-c8` |
| twin (same draw) | `run-20-correspondence-awq` (concurrency 5) |
| fingerprint | `285f423d3708` |
| seed / n | 42 / 20 correspondence docs |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 |
| prompt | `correspondence_specialist_production` (local pin) |
| headline | `overall_extraction_score` = **0.08714** (20/20 ok, 0 errors) |
| serving | healthy (see [`RUN-20-CORRESPONDENCE-AWQ-C8-SERVING.md`](../reports/RUN-20-CORRESPONDENCE-AWQ-C8-SERVING.md)) |

## Artifact search (what exists vs what does not)

| Location | Present in this checkout? | What it holds |
|---|---|---|
| `reports/RUN-20-CORRESPONDENCE-AWQ-C8-REPORT.md` | yes | per-doc scores, token counts, latency |
| `reports/serving/run-20-correspondence-awq-c8.serving.json` | yes | aggregate serving + `scores` |
| `data/runtime/runs/<run_id>/items.jsonl` | **no** (gitignored operator state) | per-item `predicted` as `str(dict)`, **not** raw LLM text |
| `reports/experiment_log.jsonl` | **no** (gitignored) | run-level record only |
| `artifacts/` | **no** | unused for specialist jobs |

Isolated / job evals persist the **parsed** specialist dict (or
`{"confidence": 0.3, "_parse_error": True}`). The correspondence agent
**drops** `_raw` on JSON parse failure
(`vendor/llm-mailroom/src/agents/correspondence_specialist.py`), so even a
local `items.jsonl` would not contain the model’s original completion for
parse failures. Job `items.jsonl` further stringifies with `str(value)`
(Python repr, not JSON) — `mailroom_sandbox.eval.schema_adherence` accepts
that repr for offline re-scoring.

**Implication:** the 2–3 “raw completions” below are reconstructed from the
only durable evidence (per-doc scores + completion-token counts + schema /
prompt / scorer). They are **not** verbatim model text. Re-run diagnosis
against `items.jsonl` when that operator dir is available:
`assess_extraction_payload(item["predicted"], "correspondence")`.

## Docs inspected (best + worst + truncated twin)

Per-doc table: [`RUN-20-CORRESPONDENCE-AWQ-C8-REPORT.md`](../reports/RUN-20-CORRESPONDENCE-AWQ-C8-REPORT.md).
Same draw, concurrency 5: [`RUN-20-CORRESPONDENCE-AWQ-REPORT.md`](../reports/RUN-20-CORRESPONDENCE-AWQ-REPORT.md).

| role | doc id | subclass | c8 overall | c8 F1 | c8 compl tok | c5 overall | c5 F1 | c5 compl tok |
|---|---|---|---|---|---|---|---|---|
| **best** | `DOC-38a7cb4be93dbecd` | notice | **0.2121** | **0.1538** | 228 | 0.2121 | 0.1538 | 228 |
| mid (F1>0) | `DOC-56a2f3a613f97dee` | meeting_request | 0.1917 | 0.0769 | 208 | 0.1917 | 0.0769 | 208 |
| **worst c8** | `DOC-f1db54435294f184` | email | **0.0091** | **0.0** | 191 | 0.0 | 0.0 | **10** |

No PII is quoted here: Hub rows are not in this checkout; reports only
expose opaque `DOC-*` ids, subclasses, and scores.

### Token-budget sanity (schema JSON, not prose)

Live correspondence schema is 11 extraction fields
(`sender`, `recipient`, `additional_recipients`, `communication_type`,
`communication_date`, `demand_amount`, `action_items`, `urgency`, `intent`,
`subject_matter`, `keywords`) plus `confidence`. A filled JSON object is
typically **~120–250 tokens**. Empty/`{}` or a one-line refusal is **≪ 30**.

### Classification against issue #21’s (a)/(b)/(c)

**(a)** reasonable extraction, wrong format · **(b)** reasonable extraction,
scorer rejects · **(c)** genuinely bad extraction.

1. **`DOC-f1db54435294f184` (c5, 10 completion tokens, overall 0.0)** —
   **(c) / likely (a) truncated.** Ten tokens cannot hold an 11-field JSON
   object. The row still recorded `error=None` (the specialist returned a
   dict, possibly `_parse_error` or a stub). This is the only doc that
   **moved** between c5 and c8 (0.0 / 10 tok → 0.0091 / 191 tok): the c8
   decode is long enough to be structured, the c5 decode is not.

2. **`DOC-f1db54435294f184` (c8, 191 tokens, overall 0.0091, F1 0.0)** —
   **mostly (c), with (b) as a contributor.** 191 tokens is enough for valid
   JSON, so a pure prose-wrapper / truncated-JSON story is unlikely on this
   pass. F1 0.0 means **zero fields hit typed score ≥ 1.0**. Overall 0.0091
   is consistent with almost every populated GT field scoring ~0, plus maybe
   one empty-list 1.0 or a tiny fuzzy crumb. Not “the scorer threw away a
   perfect extract.”

3. **`DOC-38a7cb4be93dbecd` (best, 228 tokens, overall 0.2121, F1 0.1538)** —
   **(c) with partial credit working.** F1 0.1538 ⇒ at least one TP (a field
   at 1.0). Overall 0.2121 > F1 ⇒ some **graded** field scores between 0 and
   1 (name / date / free_text / list F1) are contributing. Identical scores
   on c5 and c8 (same tokens) — not batch-order noise on this doc.

**Headline:** serving is fine; the floor is **extraction quality** (wrong or
empty values on populated GT fields), not a silent parse-failure epidemic.
Parse failures **cannot be counted separately on this run** because
`parse_error` / `schema_valid` were not on the payload — that instrumentation
is what this PR adds. The 10-token c5 row is the one smoking gun for a
format/truncation event, and it is **not** the c8 typical case (11/20 c8
rows have F1 0.0 *and* 120–322 completion tokens).

### Prompt vs schema mismatch (hypothesis, not proven without payloads)

`config/prompts/correspondence_specialist_production.txt` extraction rules
name the **live** fields (`intent` / `subject_matter` / `keywords`). The
appended production doctrine still lists **legacy** fields `key_points` and
`referenced_communications` (dojo `LEGACY_FULL_EXTRACTION_FIELD_TYPES`). If
the model emits those legacy keys, they are **extra** relative to the live
schema and do not credit `intent` / `subject_matter`. The new
`legacy_schema_keys` / `extra_schema_keys` fields will show this on the next
run that retains predictions.

Hub GT also carries content differentiators (`sentiment_label`,
`content_topic`, …) and provenance (`intent_source`, …). Dojo
`peel_non_extraction_fields` strips sentiment/topic before
`score_extraction`; it does **not** strip `intent_source` /
`intent_confidence` / `intent_status`. Non-empty provenance keys would be
heuristic-scored as misses if they land in `expected_fields`. Empty Hub keys
are skipped (see below). Confirm on `dataset.jsonl` when a lock is present.

## Empty-field scoring (verified in code + tests)

Source: `llm_dojo_scoring.field_scoring.score_extraction` and
`extraction_binary_metrics`. Correspondence extraction map is 11 keys; Hub
GT dumps more (~18 reported on this draw), many empty on non-insurance rows.

| GT value | Predicted | `overall_extraction_score` | `extraction_f1` |
|---|---|---|---|
| `None` or `""` | omitted / `null` / `""` | **not an event** (skipped) | skipped (not FN) |
| `None` or `""` | **spurious string** | **not an event** (still skipped) | skipped; extra *keys* not in expected are FP |
| `[]` (empty list) | `[]` | **1.0** on that field | skipped as an F1 event |
| `[]` | invented items | **0.0** on that field (same as a miss) | skipped as FN; unmatched pred items are **not** FP because the empty list was skipped |
| populated scalar/list | missing | **0.0** on that field | FN |
| populated | exact typed match | **1.0** | TP if score ≥ 1.0 |

**Read the number this way:**

- Correctly leaving a **null/blank scalar** empty does **not** boost or
  hurt overall. Spurious text on those scalars also does **not** hurt
  overall (prompt-discipline is free on empty scalars).
- Correctly leaving an **empty list** empty **does** score 1.0. Inventing
  CCs / keywords / action items on an empty-list GT field **zeros that
  field**, same as missing a populated one. On a ~11-field mean, one such
  list is ~0.09 of overall — on the order of this draw’s entire headline.
- `extraction_f1` is stricter still: empty lists are not events, and only
  score ≥ 1.0 counts as TP. Partial name/date/list credit **never** becomes
  F1.

The metric **does** punish empty-list prompt-discipline as hard as an
extraction miss for **overall**. It does **not** punish empty-scalar
inventions in overall. Say so when reading 0.087.

Tests: `tests/test_schema_adherence.py`
(`test_empty_gt_scalar_*`, `test_spurious_items_on_empty_list_*`).

## Partial credit (deliberate current behavior)

`exact_match == overall_extraction_score` on the serving JSON is **not**
proof that grading is off. Isolated eval (`eval/runners.py`) copies
`overall_extraction_score` into `scores["exact_match"]` when the row has no
classification `match`. They are equal **by construction**.

What is actually graded:

| Layer | Grading |
|---|---|
| `overall_extraction_score` | mean of **typed** per-field scores: name (Jaro-Winkler / token-set / optional embedding rescue), date (ISO + containment fallbacks), money (±$0.01), free_text (token F1), entity_list (list F1) |
| `extraction_f1` | binary events; TP only if typed score **≥ 1.0**. Near-miss spans are FN |
| entity lists, 1×1 | thresholded element similarity; **no Hungarian** |
| entity lists, n>1 | `scipy.optimize.linear_sum_assignment` (SAND-019). This draw is mostly single-item lists, so the assignment fix does not move the aggregate (confirmed on the AWQ reports) |

Partial credit **is** the overall path. It is **not** the F1 path. On the
best doc, overall 0.2121 vs F1 0.1538 is the gap those graded fields explain.
There is no separate “near-miss span” scorer beyond typed field functions.

## Schema-adherence metric (this PR)

Per row (additive on `score_extraction_row`): `parse_error`, `schema_valid`,
`schema_adherence` (1.0 iff parsed and valid), `parse_failure_reason`,
`extra_schema_keys`, `legacy_schema_keys`, `prose_wrapper`.

Per run (additive on isolated / extract / pipeline summaries):
`parse_error_rate`, `schema_valid_rate`, `schema_adherence_rate`, counts.
Existing keys (`exact_match`, `overall_extraction_score`, `n`, …) unchanged.

`sandbox metrics compare` quality extraction now also reads
`overall_extraction_score` / `extraction_f1` / the three rates when present.

## AWQ vs FP16 — prepared, not run

Config: [`config/runs/run-20-correspondence-fp16-c8.yaml`](../config/runs/run-20-correspondence-fp16-c8.yaml).
Same seed/strata/prompt/concurrency 8; checkpoint `Qwen/Qwen3-8B` (no AWQ).
Required engine delta: `max_model_len=16384` (L4-bf16 boot cap). **Do not
start this run** until spend/auth are approved. See
[`docs/jobs.md`](jobs.md) §AWQ vs FP16 isolation.

## Acceptance target (**owner-locked**)

Baseline floor on fingerprint `285f423d3708`: **0.08714**.

| Gate | `overall_extraction_score` | Format health | Meaning |
|---|---|---|---|
| Floor (measured) | 0.087 | unknown (not instrumented on this run) | current AWQ c8 |
| **Diagnostic** (owner-locked) | **≥ 0.25** | `parse_error_rate = 0` and `schema_valid_rate ≥ 0.95` | out of the floor; format/scorer no longer confounded with quality |
| **Pipeline-viable** (owner-locked) | **≥ 0.50** | same format bar | correspondence specialist usable as a pipeline stage on this draw |

Rationale: 0.25 is ~3× the measured floor and above the best-doc 0.21 if
*mean* quality merely matches today’s *best* row. 0.50 is still well below
a production IE board (~0.7–0.9) but is the lowest bar at which “quality is
the bottleneck” stops meaning “near-zero F1 on most docs.” These two
overall-score gates are **owner-locked** for correspondence on this draw.

Remaining after this PR: live FP16 vs AWQ on this fingerprint; optional
re-inspect of operator `items.jsonl` with the new metric.
