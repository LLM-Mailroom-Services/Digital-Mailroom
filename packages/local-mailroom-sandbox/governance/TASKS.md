# SAND task list — local-mailroom-sandbox

**Prefix: `SAND`** · Board rules: [`README.md`](README.md) · Cheat-sheet:
[`PREFIX.md`](PREFIX.md)

Cross-family work stays on llm-entity-extraction's MESSAGE_BOARD as
**`DMR-*`**. This file is the **only** sandbox-local task board — do not
open `DMR-*` cards here.

**Next ID: `SAND-016`**

Lanes: `todo` → `in_progress` → `needs_attention` → `done`.

---

## Open / in progress

| ID | Title | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| SAND-010 | Finish 50-subclass Modal sorter mission (teardown + interpret + monorepo sync) | jarvis / athena | **in_progress** | Epic for archived `SANDBOX-050` mission — see sub-cards below + [`archive/SANDBOX-050.md`](archive/SANDBOX-050.md) |
| SAND-010-3 | Preflight + guards loud (1-row live smoke pending) | test-suite-auditor | **in_progress** | was `SANDBOX-050-3`; DMR-072 silent-fallback fixed |
| SAND-010-5 | Run start → watch → completion | test-suite-auditor | **in_progress** | was `SANDBOX-050-5`; attempt 1 invalidated |
| SAND-010-6 | Teardown: app stop, zero containers, volumes persist | jarvis | todo | was `SANDBOX-050-6` |
| SAND-010-7 | Interpret: per-stratum accuracy, confusion, readiness | athena/lucius | todo | was `SANDBOX-050-7` |
| SAND-010-8 | Monorepo sync + close SAND-010 epic | atom | todo | was `SANDBOX-050-8` |
| SAND-014 | Modal doc-jobs Phase A human gates (3 decisions) | human | todo | Close rows in this board when decided — see `docs/modal-doc-jobs.md` §6 |
| SAND-014-1 | Gate: Stage A extraction depth (CPU OCR vs GPU vision) | human | todo | Plan default: pypdf/pdfplumber + pytesseract |
| SAND-014-2 | Gate: `process_document` graph scope (full vs reduced) | human | todo | Plan default: full 13-node |
| SAND-014-3 | Gate: CLI surface (`doc-jobs` vs `sandbox run` mode) | human | todo | Plan default: own `sandbox doc-jobs` family |

---

## Done (recent)

| ID | Title | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| SAND-001 | Establish SAND local board + prefix (isolated from DMR) | orchestrator | **done** | `governance/` README + PREFIX + TASKS; AGENTS.md / sister-repos wording |
| SAND-015 | Confirm SAND prefix adopted in AGENTS.md / sister-repos docs | orchestrator | **done** | Governance cutover shipped with SAND-001 |
| SAND-010-1 | Verify stratified 50-subclass sample | athena | **done** | was `SANDBOX-050-1`; strata QA green |
| SAND-010-2 | Amend run spec to GPU cap + lock | orchestrator | **done** | was `SANDBOX-050-2`; `run-50-five-types.yaml` |
| SAND-010-4 | Deploy sandbox-vllm v0.29.0 + verify endpoint | jarvis | **done** | was `SANDBOX-050-4`; health ok |
| SAND-011 | Qwen Modal specialist posture (per-doc-type runbooks) | orchestrator | **done** | Sandbox-local; *Related: DMR-078* on family board for merger vendor story |
| SAND-012 | `merger_agreement_specialist` sandbox plumbing | orchestrator | **done** | Taxonomy / components / eval / run-30 merger YAML; *Related: llm-mailroom #64 / DMR-078* |
| SAND-013 | Requirements surface completeness (`requirements/` + pipeline extras) | orchestrator | **done** | aiosqlite/greenlet/PDF stack; `scripts/sync_requirements.py`; *Related: DMR-078b* |

---

## How to add a card

1. Take **Next ID**, bump the counter in this file.
2. ID must match `SAND-<digits>` or `SAND-<digits>-<digits>` (see
   `tests/test_governance_sand.py`).
3. If the work is cross-family, file **`DMR-*`** on MESSAGE_BOARD instead
   (or in addition, with `Related: DMR-NNN` in notes).
4. Keep evidence links short (PR URL, run_id, commit SHA).
