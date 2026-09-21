# BERT Intake Doctrine (M6 lane) <!-- #85 M6a–M6e, #90, #91, #108 -->

The ModernBERT fast path is the **primary type authority of ingest**. This
page is the doctrine: what the lane is allowed to do, what it must never do,
and how to roll it back. It is enforced by the graph code — this page only
explains and links the enforcement points.

Status: **SHADOW-capable; VERIFY wired; SKIP allowlisted-start**. Promotion
beyond the current envelope requires the #107/#92 sign-off recorded on
issue #92 (eval numbers, agreement floor, per-domain allowlist).

## The tier ladder

| Tier | Condition | Path | `classification_method` |
|---|---|---|---|
| 0 — full skip | doc_type AND subclass heads PASS (gate PASS, allowlisted, `BERT_INTAKE_MODE=skip`) | `after_intake → extract` | `bert_intake` |
| 1 — prior-scoped | doc_type PASS above calibrated threshold; subclass FAIL/uncertain | `after_intake → classify` with verified-type prior | `bert_scoped` |
| 2 — full sorter | lane unavailable / doc_type FAIL / messy / oversize | today's path (advisory intake prior only) | `llm_sorter` |

Enforcement: `graph/routing.py::after_intake` (tier routing), `_bert_triage_scoped`
(Tier-1 predicate), `agents/bert_intake.py::format_bert_type_prior` (Tier-1
prior — refuses to emit when `doc_type_pass` is False), and
`graph/build_graph.py::classify_node` / `retry_classify_node` (method stamps,
scoped budget 2048→1024).

## Precedence rules

1. **BERT > intake-agent triage** on the type/subclass axes (BERT is
   deterministic, free, calibrated). One `intake_prior` string is composed
   by the node; precedence order BERT, then intake gist/keywords.
2. **The prior is advisory.** The sorter may overrule the type with cited
   evidence — the overrule path is pinned (`test_lanes_064_tier1.py`).
3. **Reviewer blindness is absolute** (M5a): the reviewer classifies blind
   — no sorter label, no BERT label, by kwargs or pages. Agreement is
   computed in code. The gate consumes sorter/reviewer verdicts as INPUTS;
   no triage label ever flows into the reviewer path.

## Gate semantics (#90)

`evaluate_intake_gate` (mailroom-ml, the single gate implementation — never
re-implemented in graph code) evaluates P1–P7 for a PASS:

- **skip** — PASS + allowlisted class → eligible for sorter-skip;
- **verify** — the gate is exercised WITHOUT skipping: fast-path → sorter
  runs; PASS requires sorter agreement (P6). A gate-failed triage routes to
  the reviewer guard (`review_classify`) and fails open to the sorter;
- **shadow** — metrics only, nothing routes on the gate.

Terminal manifests (archive + human review) record
`intake.bert.gate_outcome` — verdict/mode/failures/failed_checks/
eligible_for_sorter_skip/recommended_action — evaluated against the real
sorter/reviewer results. `classification_method` (llm_sorter | bert_intake |
bert_scoped) persists on the manifest.

## Fail-open doctrine (never blocks a run)

- Flag off (`MAILROOM_BERT_INTAKE=0`, default) → deterministic clerk, sorter
  authority; byte-identical to pre-BERT (pinned).
- Missing package / missing bundle / model error → same, `reason=flag_off |
  no_package | no_model | error`.
- A raising or missing gate → no `gate_outcome` key; the manifest and the
  run proceed.
- **Intake can never alone mark a run FAILED** (pinned by the shape sweep +
  e2e).

## Rollback

| Failure signal | Action |
|---|---|
| Any correctness regression | `MAILROOM_BERT_INTAKE=0` — instant, no code change |
| Skip-mode disagreement spike | `BERT_INTAKE_MODE=shadow` (demote a step) |
| `bert_sorter_agreement` < 95% over a shadow window (drift rule #108) | Demote prior strength or raise the type-pass threshold |

The lane's handoff is ALWAYS emitted, so telemetry exists even while the
lane is off.

## Promotion gates (issue #92 sign-off, pending run-3)

- Shadow eval on the short-doc cohort: agreement, calibrated ECE, $/doc,
  p50/p95 latency — recorded on #92.
- Verify canary green (disagreement → LLM authority).
- Skip enabled only for allowlisted classes (§ rollout) with the cost/
  accuracy sign-off recorded on #92 — currently `GATE_ALLOWLISTED_START`
  in mailroom-ml.