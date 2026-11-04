# Decision Reviewer Proof of Concept Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a decision model as the Lane A reviewer through the full 13-node graph, with every non-accept routed to a person who resolves it in the terminal.

**Architecture:** `llm-mailroom` gains a pure routing function, a pluggable decision backend and durable reviewer fields. The sandbox supplies the Jev backend, a frozen run setting and `sandbox review`, which is a thin client over the existing review API. Pilot 1 runs offline first, then as one bounded live run.

> **Updated 2026-10-31:** the sandbox now supplies four backends, `jev`, `local`, `api` and `mock`, not only Jev. The current routing and backend rules are in `config/experiments/decision-pilot/README.md`. The text above is the original plan.

**Tech Stack:** Python 3.11+, LangGraph, Pydantic, pytest, Pydantic AI (`pydantic-ai-slim[typesafe]`), httpx.

**Spec:** `docs/superpowers/specs/2026-10-30-decision-model-reviewer-design.md`

## Handoff checkpoint — 2026-10-30

- Tasks 1–3 exist in standalone `llm-mailroom` on `feat/decision-reviewer` at
  `1530f496a6c745186bb86d12b5f0472c667a404a`. The focused routing/node/evidence
  suite passes **66 tests** with the pinned Dojo package on `PYTHONPATH`.
  This is not a claim that the complete upstream suite was run.
- Task 4 has an exact-SHA generated **interim branch snapshot**; upstream merge
  and release finalization remain approval-gated. The previous interim snapshot
  predated seven committed source updates and failed the drift guard.
- Tasks 5–6 were committed before this handoff; backend, frozen-spec and CLI
  coverage are in `tests/test_decision_backends.py` and `tests/test_reviewer_spec.py`.
- Tasks 7–8 are implemented locally: terminal client plus six offline exhibits,
  real graph/bin/catalog integration, API-backed approve/reject, and SQLite
  restart recovery. See `tests/test_review_cli.py`, `tests/test_decision_pilot.py`
  and `config/experiments/decision-pilot/README.md`.
- Task 9 is **blocked on operator approvals and data/credential/spend gates**.
  No live run, push or merge has been performed. Later plans remain separate.
- Final sandbox validation: **2006 passed / 20 skipped** (`python -m pytest -q`);
  CLI-reference and requirements generation checks, `uv lock --check`,
  `uv pip check`, and staged/unstaged whitespace checks pass. `SAND-082` tracks
  the remaining operator gates; skipped tests are not live evidence.

The original step checkboxes below are retained as the implementation recipe;
unchecked historical steps are not a replacement for this verified checkpoint.

## Scope and schedule

> **Updated 2026-10-31:** plan 3 (sanitized correspondence) is cancelled (SAND-086). The Enron correspondence is public, so no sanitized dataset is needed and every backend accepts correspondence. The row below is kept as the original plan.

This is plan 1 of 5. The spec covers independent subsystems, so each later plan gets its own document and review. Dates are proposed targets against the December 15, 2026 final presentation.

| Plan | Delivers | Target |
|---|---:|---:|
| 1. This plan | Offline pilot, then one bounded live pilot | Offline Nov 6, live Nov 13 |
| 2. Serving proof | Modal + vLLM, API and hybrid runs covering all 13 nodes | Nov 20 |
| 3. Sanitized correspondence | Private pseudonymized dataset, then Pilot 1 on it | Nov 20 |
| 4. More pilots | Luna adapter, shadow Pilots 2 and 3 | Nov 27 |
| 5. Qualification and demo | Section 10 evidence, exhibits, backup recording | Dec 4, freeze Dec 8 |

## Global Constraints

> **Updated 2026-10-31:** the correspondence bullet below is superseded: correspondence is accepted by every backend and needs no sanitized dataset (SAND-086 cancelled). Failure routes still end in `human_review`, but a decision class now reaches its reviewer at any sorter confidence, and a reviewer may correct a sorter below its low band at the cutoff. See `config/experiments/decision-pilot/README.md`.

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:27caf21551400a2d2e07ae9edfb73c127a428b294812a86a69ab65b15f6735d7 -->

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:957026ee265cb142728a060f197830c1b0b8b7f3ed8684c8fbecbb929b469e91 -->

- Name outside vendors only to describe their products. Do not imply affiliation, endorsement, sponsorship or shared work in any file, commit, PR or report without written clearance from the user.

<!-- /coderabbit-ai-generated:v1 -->

<!-- /coderabbit-ai-generated:v1 -->
- Source changes land in `Exios66/llm-mailroom` first, then reach `vendor/` through the reviewed refresh. Never edit `vendor/` by hand.
- Default behavior is unchanged: without explicit config, the mode is `llm`, and no decision-model call occurs.
- The default test suites make no network calls.
- Failure routes go to `human_review`. There is no LLM fallback and no archive path from the decision lane.
- Pin `jev-1.13.0`. Do not use `jev-latest` or `jev-preview`.
- Pushes, merges, paid runs and credential use each require the user's explicit go-ahead.
- Sandbox cards use `SAND-*`. Do not open `DMR-*` cards in this repo.
- Correspondence rows are out of scope for live pilots until plan 3 finishes.

## Review Focus

1. A model label outside the taxonomy should park the document, not raise or auto-accept. Test: `test_label_outside_taxonomy_parks` (Task 1).
2. NaN or out-of-range confidence should never pass a cutoff. Test: `test_invalid_confidence_parks` (Task 1).
3. A `decision_only` class with no configured cutoff should fail closed. Test: `test_missing_cutoff_parks` (Task 1).
4. Whitespace-only text should park with no model call. Test: `test_blank_text_skips_backend` (Task 2).
5. Resolving a document twice or after a restart should not archive it twice or lose the label override. Tests: `test_override_survives_restart` (Task 3), `test_second_resolve_reports_api_error` (Task 7).

---

### Task 1: Pure review routing (`llm-mailroom`)

> **Updated 2026-10-31:** `decide_review` gained a `sorter_unsure` argument. When the sorter is below its low band, only the reviewer's label must be eligible, and the reviewer may correct the sorter at the cutoff. The override-never-accepts test below covers a sorter at or above its low band, where disagreement still parks.

**Files:**
- Create: `src/pipeline/decision_review.py`
- Modify: `src/pipeline/reconsideration.py`
- Test: `src/tests/test_decision_review.py`

**Interfaces:**
- Produces:
  - `DecisionAnswer` frozen dataclass: `doc_type: str | None`, `doc_subclass: str | None`, `confidence: float | None`, `model: str`
  - `ReviewRoute` frozen dataclass: `destination: Literal["extract", "human_review"]`, `causes: tuple[str, ...]`, `verdict: Literal["decision_accepts", "decision_escalates"]`
  - `decide_review(sorter_type: str | None, answer: DecisionAnswer | None, *, eligible: Collection[str], cutoffs: Mapping[str, float], has_text: bool) -> ReviewRoute`
  - Constants in `reconsideration.py`: `REVIEWER_UNAVAILABLE = "reviewer_unavailable"`, `REVIEWER_NO_TEXT = "reviewer_no_text"`, `REVIEWER_INELIGIBLE_LABEL = "reviewer_ineligible_label"`, `REVIEWER_DISAGREEMENT = "reviewer_disagreement"`, `REVIEWER_LOW_CONFIDENCE = "reviewer_low_confidence"`, each with a `CAUSE_LABELS` entry

- [ ] **Step 1: Create branch `feat/decision-reviewer` from `llm-mailroom` main**

Run: `git switch -c feat/decision-reviewer`
Expected: switched to the new branch.

- [ ] **Step 2: Write failing tests**

```python
ELIGIBLE = {"insurance_claim", "corporate_record"}
CUTOFFS = {"insurance_claim": 0.9, "corporate_record": 0.9}

def route(sorter="insurance_claim", label="insurance_claim", conf=0.95, text=True):
    answer = DecisionAnswer(label, None, conf, "jev-1.13.0")
    return decide_review(sorter, answer, eligible=ELIGIBLE, cutoffs=CUTOFFS, has_text=text)

def test_clean_accept():
    assert route().destination == "extract"
    assert route().causes == ()

def test_records_every_failed_condition():
    r = route(label="contract", conf=0.1)
    assert r.destination == "human_review"
    assert set(r.causes) == {REVIEWER_INELIGIBLE_LABEL, REVIEWER_DISAGREEMENT, REVIEWER_LOW_CONFIDENCE}

def test_no_answer_is_unavailable():
    r = decide_review("insurance_claim", None, eligible=ELIGIBLE, cutoffs=CUTOFFS, has_text=True)
    assert r.causes == (REVIEWER_UNAVAILABLE,)

def test_override_never_auto_accepts():
    r = route(sorter="corporate_record", label="insurance_claim", conf=1.0)
    assert r.destination == "human_review"
    assert r.causes == (REVIEWER_DISAGREEMENT,)

def test_label_outside_taxonomy_parks():
    r = route(label="made_up_class")
    assert r.destination == "human_review"
    assert REVIEWER_INELIGIBLE_LABEL in r.causes

@pytest.mark.parametrize("conf", [float("nan"), float("inf"), -0.1, 1.1, None])
def test_invalid_confidence_parks(conf):
    assert REVIEWER_LOW_CONFIDENCE in route(conf=conf).causes

def test_missing_cutoff_parks():
    r = decide_review("insurance_claim", DecisionAnswer("insurance_claim", None, 1.0, "m"),
                      eligible=ELIGIBLE, cutoffs={}, has_text=True)
    assert r.causes == (REVIEWER_LOW_CONFIDENCE,)

def test_no_text_is_recorded():
    assert REVIEWER_NO_TEXT in route(text=False).causes
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest src/tests/test_decision_review.py -v`
Expected: FAIL with an import error for `pipeline.decision_review`.

- [ ] **Step 4: Implement the constants and `decide_review`**

Evaluate all five conditions and append every failure, in the spec's table order. When `answer` is `None`, record only `REVIEWER_UNAVAILABLE`, plus `REVIEWER_NO_TEXT` when text is absent. The function performs no I/O and reads no config.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest src/tests/test_decision_review.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pipeline/decision_review.py src/pipeline/reconsideration.py src/tests/test_decision_review.py
git commit -m "feat: add pure decision review routing"
```

### Task 2: Decision branch in `review_classify` (`llm-mailroom`)

**Files:**
- Create: `src/agents/decision_backend.py`
- Modify: `src/pipeline/config.py`, `src/config/taxonomy.yaml`, `src/graph/state.py`, `src/graph/build_graph.py:1049` (`review_classify_node`), `src/graph/routing.py:403` (`after_review_classify`), `src/pipeline/reconsideration.py:243` (`collect_review_causes`)
- Test: `src/tests/test_decision_review_node.py`

**Interfaces:**
- Consumes: `decide_review`, `DecisionAnswer`, `ReviewRoute` from Task 1
- Produces:
  - `DecisionBackend = Callable[[str, list[str], dict[str, list[str]]], DecisionAnswer]`, called as `backend(doc_text, doc_types, subclass_catalogs)`
  - `register_decision_backend(backend: DecisionBackend | None) -> None`, `get_decision_backend() -> DecisionBackend | None`
  - `get_reviewer_config() -> dict` returning `{"default_mode": str, "by_class": dict[str, dict]}`
  - `get_review_mode(doc_type: str | None) -> Literal["llm", "decision_only"]`
  - State keys: `review_route: str | None`, `reviewer_causes: list[str]`, `reviewer_model: str | None`
  - Taxonomy block: `reviewer: {default_mode: llm, by_class: {}}`, where each `by_class` entry holds `mode` and `cutoff`

- [ ] **Step 1: Write failing tests**

Use a fake backend and assert on `review_classify_node(state)` and `after_review_classify(state | update)`.

```python
def test_llm_mode_never_calls_backend(): ...  # default config, backend spy call_count == 0
def test_accept_routes_to_extract_with_zero_llm_calls(): ...  # SorterReviewerAgent patched to raise
def test_disagreement_keeps_sorter_label_and_parks(): ...
def test_backend_missing_parks_unavailable(): ...
def test_permanent_error_parks_unavailable_without_llm(): ...
def test_transient_error_uses_node_budget_then_unavailable(): ...
def test_blank_text_skips_backend(): ...  # "   \n" -> spy not called, causes include REVIEWER_NO_TEXT
def test_causes_reach_collect_review_causes(): ...
```

Each stub's assertion is the behavior named in the spec's section 5.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest src/tests/test_decision_review_node.py -v`
Expected: FAIL with an import error for `agents.decision_backend`.

- [ ] **Step 3: Implement the backend registry and config readers**

The defaults in `taxonomy.yaml` keep every class on `llm`. A `by_class` entry without `mode: decision_only` is `llm`.

- [ ] **Step 4: Implement the node branch**

Branch at the top of `review_classify_node` on `get_review_mode(sorter_type)`. In `decision_only` mode:
- Treat `doc_text.strip() == ""` as no text and skip the call.
- On a transient error, reuse the existing `transient_retries_review_classify` return and also set `reviewer_causes=[REVIEWER_UNAVAILABLE]`.
- On any other exception, route with `answer=None`.
- Pass class names with `mode: decision_only` as `eligible`, and their `cutoff` values as `cutoffs`.
- Pass any answer through `apply_classification_guard` before `decide_review`, as the LLM path does. Clear `doc_subclass` when the guard rejects it.
- Apply the reviewer's label and confidence only on `extract`. Otherwise keep the sorter's values.
- Generate `escalation_reason` from the route, labels, confidences and cutoff. It uses no model text.

- [ ] **Step 5: Implement routing and cause merging**

In `after_review_classify`, return `state["review_route"]` when it is set, after the existing transient check. `collect_review_causes` appends `state["reviewer_causes"]`. `_transient_decision` exhaustion already reaches `human_review`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest src/tests/test_decision_review_node.py src/tests/test_decision_review.py -v`
Expected: PASS.

- [ ] **Step 7: Run the full `llm-mailroom` suite**

Run: `pytest -q`
Expected: no failures beyond those present on `main`.

- [ ] **Step 8: Commit**

```bash
git add src/agents/decision_backend.py src/pipeline src/config/taxonomy.yaml src/graph src/tests/test_decision_review_node.py
git commit -m "feat: route decision-only classes through review_classify"
```

### Task 3: Durable review evidence and override (`llm-mailroom`)

**Files:**
- Modify: `src/schemas/manifest.py`, `src/graph/build_graph.py:1800` (`human_review_node`), `src/graph/build_graph.py:3329` (`resume_from_review`), `src/pipeline/review_resolve.py:48` (`serialize_document`)
- Test: `src/tests/test_review_evidence.py`

**Interfaces:**
- Consumes: state keys from Task 2
- Produces: manifest fields `review_causes: list[str] | None`, `review_verdict: str | None`, `reviewer_doc_type: str | None`, `reviewer_doc_subclass: str | None`, `reviewer_confidence: float | None`, `reviewer_model: str | None`. The catalog carries them under `extracted_data["_review"]`. `serialize_document` returns them.

- [ ] **Step 1: Write failing tests**

```python
def test_parked_manifest_keeps_both_opinions(): ...  # reviewer_* and review_causes on saved manifest
def test_queue_row_exposes_review_fields(): ...      # serialize_document output
def test_override_reaches_extract_via_interrupt(): ...  # extract sees the human's doc_type
def test_override_survives_restart(): ...  # sqlite checkpointer, new compiled graph, same doc_type
def test_rejected_never_reaches_archive(): ...  # stage failed, no archive file, no archived catalog row
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest src/tests/test_review_evidence.py -v`
Expected: FAIL on the missing manifest fields.

- [ ] **Step 3: Implement persistence**

Add the fields with default `None`, so older manifests load. Populate them in the parked `DocumentManifest` and `_catalog_upsert` in `human_review_node`.

- [ ] **Step 4: Implement the override carry-through**

If `test_override_reaches_extract_via_interrupt` fails, pass the manifest's `doc_type`, `contract_subtype` and `doc_subclass` into the interrupt resume so the checkpointed sorter label is replaced. Do not change the fallback path.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest src/tests/test_review_evidence.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite and commit**

Run: `pytest -q`
Expected: no failures beyond those present on `main`.

```bash
git add src/schemas/manifest.py src/graph/build_graph.py src/pipeline/review_resolve.py src/tests/test_review_evidence.py
git commit -m "feat: persist review evidence and carry human overrides"
```

### Task 4: Merge upstream and refresh the vendor snapshot

**Files:**
- Modify: `src/mailroom_sandbox/cli.py:1287` (`_VENDOR_PINS`), `vendor/llm-mailroom/**` (generated), `governance/TASKS.md`

**Interfaces:**
- Consumes: merged `llm-mailroom` commit SHA
- Produces: vendored `pipeline.decision_review` and `agents.decision_backend`

- [ ] **Step 1: Get the user's go-ahead, then open and merge the `llm-mailroom` PR**

Expected: merged reviewed commit SHA on `main`. The PR text follows Global Constraints.

- [ ] **Step 2: In the sandbox, add the next free `SAND-*` card and a branch**

Cite the spec path. Create `feat/decision-reviewer-poc` from `docs/decision-model-reviewer-spec`.

- [ ] **Step 3: Update both SHA values in `_VENDOR_PINS`, then refresh**

Run: `sandbox fetch-deps`
Expected: exit 0, and `vendor/llm-mailroom/VENDOR.md` shows the new SHA.

- [ ] **Step 4: Run the sandbox suite**

Run: `pytest -q`
Expected: no failures, including `tests/test_vendor_drift.py`. If the upstream head includes commits after `1a1ec3df`, review those changes for regressions in this step.

- [ ] **Step 5: Commit**

```bash
git add vendor src/mailroom_sandbox/cli.py governance/TASKS.md
git commit -m "chore: vendor llm-mailroom decision reviewer"
```

### Task 5: Decision backends

> **Updated 2026-10-31:** `build_backend` now accepts `jev`, `local`, `api` and `mock`. `api` requires an exact provider id such as `openai/gpt-6-luna` (no `-latest` or `~` aliases), and the Decisions API adapter described below was not built. The `local` and `api` backends run the `sorter_reviewer` agent.

**Files:**
- Create: `src/mailroom_sandbox/decision_backends.py`
- Modify: `pyproject.toml`
- Test: `tests/test_decision_backends.py`

**Interfaces:**
- Consumes: `DecisionBackend`, `DecisionAnswer`
- Produces:
  - `jev_backend(model: str = "jev-1.13.0", *, max_input_chars: int = 12000) -> DecisionBackend`
  - `mock_backend(answers: Mapping[str, tuple[str, float]]) -> DecisionBackend`, keyed by a substring of the document text; an unmatched document returns `("unknown", 0.0)`
  - `build_backend(name: str, model: str) -> DecisionBackend`, for names `jev` and `mock`
  - Optional dependency group `decision = ["pydantic-ai-slim[typesafe]==<exact version>"]`, using the version resolved on the day and recorded in the lock

- [ ] **Step 1: Write failing tests**

```python
def test_mock_backend_matches_text(): ...
def test_mock_backend_unmatched_is_unknown_zero(): ...
def test_jev_rejects_moving_aliases():
    with pytest.raises(ValueError):
        jev_backend("jev-latest")
def test_jev_maps_field_confidence(fake_agent): ...  # provider_details["confidence"]["doc_type"]
def test_jev_truncates_to_input_cap(fake_agent): ...
def test_jev_missing_confidence_returns_none(fake_agent): ...
```

`fake_agent` patches the Pydantic AI `Agent` class, so no network is used.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_decision_backends.py -v`
Expected: FAIL with an import error.

- [ ] **Step 3: Implement the backends**

Import Pydantic AI inside `jev_backend`, so offline installs keep working. Build the output model from the supplied lists, with `doc_type` as a pick-one and `doc_subclass` as an optional pick-one over the union of catalogs. Raise a clear error above 255 options. Use `model_settings` with `max_retries=0`, because the graph owns the retry budget.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_decision_backends.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mailroom_sandbox/decision_backends.py pyproject.toml uv.lock tests/test_decision_backends.py
git commit -m "feat: add Jev and mock decision backends"
```

### Task 6: Frozen reviewer setting

> **Updated 2026-10-31:** `ReviewerSpec.backend` is `Literal["jev", "local", "api", "mock"]`. The correspondence rejection described below was removed, so `test_rejects_correspondence_for_live_backend` no longer applies. Preflight checks each route: `local` needs a `modal-vllm` or `vllm` route, and `api` needs an `openrouter` route.

**Files:**
- Modify: `src/mailroom_sandbox/job/spec.py:382,521,638`, `src/mailroom_sandbox/job/preflight.py`, `src/mailroom_sandbox/runtime.py:222` (`activate`), `src/mailroom_sandbox/experiments.py`, `src/mailroom_sandbox/cli.py`
- Test: `tests/test_reviewer_spec.py`

**Interfaces:**
- Consumes: `build_backend`, `register_decision_backend`
- Produces:
  - `ReviewerSpec(BaseModel)`: `backend: Literal["jev", "mock"]`, `model: str`, `classes: dict[str, float]` mapping class to cutoff
  - `RunSpec.reviewer: ReviewerSpec | None = None`
  - `spec_core` includes `reviewer` only when set
  - `sandbox experiment create --decision-reviewer BACKEND:MODEL --decision-class CLASS=CUTOFF` (repeatable)

- [ ] **Step 1: Write failing tests**

```python
def test_hash_unchanged_without_reviewer(): ...  # matches a stored pre-change spec_hash
def test_hash_changes_with_cutoff(): ...
def test_rejects_correspondence_for_live_backend(): ...  # backend jev + correspondence -> ValidationError
def test_rejects_cutoff_outside_unit_interval(): ...
def test_preflight_requires_typesafe_key_for_jev(): ...
def test_activate_registers_backend_and_class_modes(): ...
def test_llm_only_spec_registers_nothing(): ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reviewer_spec.py -v`
Expected: FAIL with an import error for `ReviewerSpec`.

- [ ] **Step 3: Implement `ReviewerSpec`, hashing, validation and preflight**

Pin validation matches Task 5. The correspondence rejection stays until plan 3 removes it. Preflight checks that `TYPESAFE_API_KEY` is present, and never prints it.

- [ ] **Step 4: Implement activation and CLI flags**

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:bd1c364cb17ac806601d42b287e3062d593324d3e3f799f6f176db9cc2cc89e7 -->

`activate` writes the `reviewer` block into the merged taxonomy and registers the backend. An activation without a reviewer clears the registration. Regenerate the CLI reference.

<!-- /coderabbit-ai-generated:v1 -->

- [ ] **Step 5: Run tests and the CLI surface check**

Run: `pytest tests/test_reviewer_spec.py -v && python scripts/check_cli_surface.py --check`
Expected: PASS, and the CLI reference is current.

- [ ] **Step 6: Commit**

```bash
git add src/mailroom_sandbox tests/test_reviewer_spec.py docs/cli-reference.md
git commit -m "feat: freeze decision reviewer in run specs"
```

### Task 7: `sandbox review`

**Files:**
- Create: `src/mailroom_sandbox/review_cli.py`
- Modify: `src/mailroom_sandbox/cli.py`, `docs/cli-reference.md`
- Test: `tests/test_review_cli.py`

**Interfaces:**
- Consumes: `GET /review/queue`, `POST /review/{doc_id}/resolve`
- Produces:
  - `sandbox review list`
  - `sandbox review show DOC_ID`
  - `sandbox review resolve DOC_ID --decision approved|rejected [--doc-type CLASS] [--notes TEXT]`
  - `MAILROOM_API_URL` selects the API. Reuse the token variable `_require_token` reads in `api/main.py`.

- [ ] **Step 1: Write failing tests using `httpx.MockTransport`**

```python
def test_list_shows_causes_and_both_labels(): ...
def test_show_prints_cutoff_reason_and_opinions(): ...
def test_resolve_sends_disposition_resume_and_override(): ...
def test_disagreement_approval_requires_doc_type(): ...  # exit 2, no POST
def test_api_unreachable_gives_clear_error(): ...
def test_second_resolve_reports_api_error(): ...  # HTTP 400 text shown, non-zero exit
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_review_cli.py -v`
Expected: FAIL with an import error.

- [ ] **Step 3: Implement the client and parser**

Do not reimplement resolve logic. Send `override_doc_type` for `--doc-type`. Require `--doc-type` when causes include `reviewer_disagreement` and the decision is `approved`.

- [ ] **Step 4: Run tests and the CLI surface check**

Run: `pytest tests/test_review_cli.py -v && python scripts/check_cli_surface.py --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mailroom_sandbox/review_cli.py src/mailroom_sandbox/cli.py docs/cli-reference.md tests/test_review_cli.py
git commit -m "feat: add terminal human review"
```

### Task 8: Offline Pilot 1 through the full graph

**Files:**
- Create: `data/fixtures/pilot/decision_review.jsonl`, `tests/test_decision_pilot.py`, `config/experiments/decision-pilot/README.md`

**Interfaces:**
- Consumes: `mock_backend`, `run_pipeline`, `ReviewerSpec`, `sandbox review` resolve payload
- Produces: `run_pilot_row(row: dict, spec: ReviewerSpec) -> dict` in `tests/test_decision_pilot.py`, with final `stage`, `review_causes`, visited nodes and LLM reviewer call count

- [ ] **Step 1: Write six curated rows**

Use original short text, with no copied correspondence rows. Cover: clean accept, disagreement, low confidence, ineligible label, unavailable and no text. Set `contract`, `corporate_record` and `insurance_claim` as the sorter classes. Inject sorter confidence inside the reviewer band.

- [ ] **Step 2: Write failing tests**

```python
def test_clean_accept_reaches_archive_entry(): ...  # record, catalog row, archive file
@pytest.mark.parametrize("row_id, cause", CAUSE_ROWS)
def test_each_cause_parks(row_id, cause): ...
def test_approve_with_override_reaches_archive(): ...
def test_reject_ends_failed(): ...
def test_llm_reviewer_is_never_called(): ...
def test_no_accept_outside_rule(): ...  # any extract without decision_accepts fails
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_decision_pilot.py -v`
Expected: FAIL, because `run_pilot_row` is undefined.

- [ ] **Step 4: Implement `run_pilot_row` and pass the tests**

Reuse the mock patches in `src/mailroom_sandbox/eval/runners.py` and `MAILROOM_CHECKPOINTER=sqlite` in a temp directory. Report nodes visited. This pilot does not need to exercise all 13 nodes; plan 2 does.

Run: `pytest tests/test_decision_pilot.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite and commit**

Run: `pytest -q`
Expected: no failures.

```bash
git add data/fixtures/pilot tests/test_decision_pilot.py config/experiments/decision-pilot
git commit -m "test: add offline decision reviewer pilot"
```

### Task 9: Bounded live pilot

**Files:**
- Create: `config/experiments/decision-pilot/experiment.yaml`, `reports/decision-pilot/README.md`

**Interfaces:**
- Consumes: all earlier tasks
- Produces: redacted run evidence and a pilot report

- [ ] **Step 1: Confirm the gates with the user**

Record: TypeSafe data terms reviewed; credential available without pasting it into chat; the 200 card-like insurance matches cleared or excluded; spend cap approved.

- [ ] **Step 2: Draw the sample**

Use `FAMILY_HF_REVISION`, seed 42, four documents each from `contract`, `corporate_record` and `insurance_claim`. Set initial cutoffs to `0.9` for this pilot only. Label them untuned.

- [ ] **Step 3: Review and preflight**

Run: `sandbox experiment review --config config/experiments/decision-pilot/experiment.yaml && sandbox experiment preflight --config config/experiments/decision-pilot/experiment.yaml`
Expected: both pass, and the plan shows the reviewer model, cap and teardown.

- [ ] **Step 4: Launch after signed approval**

Run: `sandbox experiment launch --config config/experiments/decision-pilot/experiment.yaml`
Expected: every document reaches a terminal or parked state, and any managed Modal app is torn down.

- [ ] **Step 5: Resolve parked documents in the terminal**

Run: `sandbox review list`, then `sandbox review resolve` per document.
Expected: no document remains pending.

- [ ] **Step 6: Write and commit the report**

Report per-document route, causes, measured cost and failures. State that this is a pilot, 12 documents qualify nothing, cutoffs are untuned and `insurance_claim` is synthetic.

```bash
git add config/experiments/decision-pilot reports/decision-pilot
git commit -m "docs: record bounded decision reviewer pilot"
```
