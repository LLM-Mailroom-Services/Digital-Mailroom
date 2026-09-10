# Audit State

## Latest Audit
- **Date:** 2026-09-10
- **Scope:** Veracity audit of all 12 unassigned DMR cards (DMR-011 through DMR-029) against actual codebase implementation
- **Claim vs. Evidence verdict:** 10 of 12 cards have missing or incomplete implementations that need to be shipped. Only 2 cards (DMR-012 and DMR-013) are correctly scoped as "needs execution" rather than "needs new code."
- **Actions taken:** Created new DMR cards (DMR-028 through DMR-037) to track the missing implementations identified during the audit. Updated STATE.md.

## Detailed Findings

### DMR-011 — Harden sync_packages.py patch_push
**Status: NOT DONE**
- Card claims race still present at `scripts/sync_packages.py:345-351`
- Verified: line 345 uses `git ls-files` (tracked files list) but line 351 copies from the working tree (`shutil.copy2(src, dst)`)
- The race IS still present — uncommitted changes in the worktree propagate
- **Fix needed:** Use `git archive HEAD` or `git ls-tree` to copy committed blobs instead of working tree files
- **New card:** DMR-028

### DMR-012 — Gmail triage production-readiness residuals
**Status: UNASSIGNED, correctly scoped**
- Card states HUB-037/039/043/048 deliveries are in place
- Work needed: live re-send/provenance operator proof, CI secret-presence check, Langfuse/Phoenix trace checklist, ops-lamp alerting, runbooks
- This is legitimate "remaining work" — no gap between claim and reality
- **No new card needed** — DMR-012 itself is the tracking card

### DMR-013 — Run publish_pages.sh for terminal site
**Status: UNASSIGNED, correctly scoped**
- Script exists at `packages/The-Mailroom/scripts/publish_pages.sh` (197 lines, fully implemented)
- The terminal site code is delivered (M6 milestone complete per AGENTS.md)
- Only the live publish execution is pending
- This is legitimate "needs execution" — no gap between claim and reality
- **No new card needed** — DMR-013 itself is the tracking card

### DMR-014 — Specialist mutations on mailroom-corpus v7+v8
**Status: NOT DONE**
- Card claims "no mutation operators/registry exist yet"
- Verified: confirmed — no specialist mutation operators or fitness/registry infrastructure exists
- This is a "needs new implementation" card, not a "needs execution" card
- **New card:** DMR-035 (to track the implementation of mutation operators)

### DMR-015 — Derive mailroom-named successor keys
**Status: NOT DONE**
- Card claims surfaces still 4-token at `src/prompts.py:1266`
- Verified: line 1266 shows `doc_subclass is carrier, pde, outpatient, or inpatient` — exactly 4 tokens
- The v8 six-token set (carrier/pde/outpatient/inpatient + property/auto) was never implemented
- **New card:** DMR-033

### DMR-016 — Add NEW docclass judge/reviewer/arbiter/boss prompt keys
**Status: NOT DONE**
- Card claims extended-8 grading persists at `src/prompts_docclass.py:92-110,246-250,313-315,371-372`
- Verified: the prompts use the extended 8-class set (contract, corporate_record, due_diligence, correspondence, compliance_filing, court_opinion, insurance_claim, merger_agreement)
- The five-class + `unknown` grading language per plan §67 was never added
- **New card:** DMR-034

### DMR-017 — GEPA prompt mutations on docclass v7+v8
**Status: NOT DONE**
- Card claims only `sorter_mailroom_v0` (HUB-041) exists
- Verified: `SORTER_DOCCLASS_PILOT_PROMPT_V0` and `V1` exist, plus `REVIEWER_DOCCLASS_PILOT_PROMPT_V0`
- But the full `mailroom_v` docclass lineage keys (sorter + judge/reviewer) with same-surface A/Bs were never registered
- **New card:** DMR-036

### DMR-018 — v9 corpus candidate: re-evaluate INSURBIAS
**Status: NOT DONE**
- Card claims "v9 not started, INSURBIAS deferred"
- Verified: no INSURBIAS evaluation or v9 corpus work exists in the codebase
- This is a "needs evaluation" card — the work hasn't started
- **New card:** DMR-037

### DMR-023 — Port DMR-021/DMR-022 to llm-mailroom/deploy/modal_vllm.py
**Status: NOT DONE**
- Card claims 6 specific issues at `packages/llm-mailroom/deploy/modal_vllm.py`
- Verified ALL 6 issues still present:
  - Line 56: `modal.Secret.from_local` (SDK 1.5.x removed this)
  - Line 54: `VLLM_IMAGE_TAG` defaults to `"latest"` (should be pinned)
  - Line 105: `--disable-log-requests` (renamed to `--no-enable-log-requests` in v0.28.0)
  - Line 64: No vLLM cache volume
  - Line 113: No revision knob
  - deploy extra: `modal>=0.73` (should be `modal==1.5.5`)
- **New card:** DMR-029

### DMR-024 — Same hardening for llm-entity-extraction/deploy/modal_vllm.py
**Status: NOT DONE**
- Card claims 3 specific issues at `packages/llm-entity-extraction/deploy/modal_vllm.py`
- Verified ALL 3 issues still present:
  - Line 68: `modal.Secret.from_local` (SDK 1.5.x removed this)
  - Line 66: `VLLM_IMAGE_TAG` defaults to `"latest"` (should be pinned)
  - Line 117: `--disable-log-requests` (renamed to `--no-enable-log-requests` in v0.28.0)
- **New card:** DMR-030

### DMR-025 — Refresh vllm-specialist.md version policy
**Status: NOT DONE**
- Card claims `.opencode/agents/vllm-specialist.md:37` records v0.24.0
- Verified: line 37 states "As of 2026-09-09 the current stable is vLLM v0.24.0"
- Actual current stable is v0.29.0 (2026-09-09), with v0.28.0 as the family pin
- The `--enable-log-requests` opt-in rename and Model Runner V2 default change are not documented
- **New card:** DMR-031

### DMR-026 — Align htcondor/vLLM templates
**Status: NOT DONE**
- Card claims 3 issues in `deploy/htcondor/`
- Verified ALL issues still present:
  - `vllm_serve.sub:25` and `vllm_batch_eval.sub:33` pin `v0.8.5` (should be `v0.28.0`)
  - `serve_vllm.sh:16` uses `--disable-log-requests` (valid for v0.8.5 only, renamed in v0.28.0)
  - Three different engine versions across the package (v0.8.5, v0.28.0, latest)
- **New card:** DMR-032

## Audit Log

| Date | Scope | Findings | Actions | Pitfalls |
|------|-------|----------|---------|----------|
| 2026-09-10 | DMR-011 through DMR-029 veracity audit | 10 of 12 cards have missing implementations; 2 cards correctly scoped as execution-only | Created DMR-028 through DMR-037; wrote STATE.md | None yet |

## Lessons Learned
- **2026-09-10:** Always verify the actual file:line references in DMR cards against the current codebase. Cards synced from HUB issues may reference line numbers that have shifted or implementations that were never actually completed. The card's "Evidence" field describes the problem but does not confirm the fix was shipped.
- **2026-09-10:** DMR cards that say "synced from HUB-XXX" with a specific issue number are mirroring the predecessor board's state, not confirming that work was done in the DMR repo. The sync operation copies the card, not the implementation.
- **2026-09-10:** When auditing deploy files, check both the `modal.Secret.from_local` removal (SDK 1.5.x breaking change) AND the `--disable-log-requests` → `--no-enable-log-requests` rename (vLLM v0.28.0 breaking change). These two issues affect multiple deploy files across the monorepo.
