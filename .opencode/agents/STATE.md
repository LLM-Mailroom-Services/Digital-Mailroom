# Audit State

## Latest Audit
- **Date:** 2026-09-10
- **Scope:** DMR-041 + DMR-042 implementation pass — sandbox job whole-run task delegation + HF corpus loader fixes
- **Claim vs. Evidence verdict:** Both cards' defects confirmed and SHIPPED (commit `1085c273`). DMR-041: whole-run tasks now delegate to public eval runners (previously ValueError). DMR-042: HF Hub path now works (was NameError on undefined `load_hf`).
- **Actions taken:** Fixed `corpus.py` (load_hf_rows, _resolve_revision, effective_revision), `preflight.py:124`, `job/runner.py` (_run_whole_run + dispatch), `hf_interface.py` (missing import). Added 9 network-free tests. Closed issues #44/#45. Archived both cards. Suite 144 passed / 1 skipped.

## Fixes Applied (2026-09-10)

### DMR-031: vllm-specialist.md version policy — FIXED
- **File:** `.opencode/agents/vllm-specialist.md` line 37
- **Before:** "As of 2026-09-09 the current stable is vLLM v0.24.0"
- **After:** Updated to v0.29.0 current stable, v0.28.0 family pin, documented `--disable-log-requests` → `--enable-log-requests` rename and Model Runner V2 default change

### DMR-029: llm-mailroom/deploy/modal_vllm.py — FULLY FIXED
- **File:** `packages/llm-mailroom/deploy/modal_vllm.py`
- **Fixed:**
  - `Secret.from_local` → `Secret.from_dict` (SDK 1.5.x removal)
  - Image tag `latest` → `v0.28.0` (pinned)
  - `--disable-log-requests` → `--no-enable-log-requests` (v0.28.0 rename)
  - Added vLLM cache volume (`mailroom-vllm-cache` mounted at `/root/.cache/vllm`)
  - Added revision knob (`MODAL_VLLM_REVISION` env var, `--revision` flag)
  - Added GPU memory utilization knob (`MODAL_VLLM_GPU_MEMORY_UTILIZATION`, default 0.90)
  - Added max-num-seqs knob (`MODAL_VLLM_MAX_NUM_SEQS`, default 256)
  - Added `modal==1.5.5` pin in `pyproject.toml` (was `modal>=0.73`)

### DMR-030: llm-entity-extraction/deploy/modal_vllm.py — FULLY FIXED
- **File:** `packages/llm-entity-extraction/deploy/modal_vllm.py`
- **Fixed:**
  - `Secret.from_local` → `Secret.from_dict` (SDK 1.5.x removal)
  - Image tag `latest` → `v0.28.0` (pinned)
  - `--disable-log-requests` → `--no-enable-log-requests` (v0.28.0 rename)
  - Added vLLM cache volume (`entity-vllm-cache` mounted at `/root/.cache/vllm`)
  - Added revision knob (`MODAL_VLLM_REVISION` env var, `--revision` flag)
  - Added GPU memory utilization knob (`MODAL_VLLM_GPU_MEMORY_UTILIZATION`, default 0.90)
  - Added max-num-seqs knob (`MODAL_VLLM_MAX_NUM_SEQS`, default 256)
  - Added `modal==1.5.5` pin in `pyproject.toml` (was `modal>=0.73`)

### DMR-032: htcondor templates — FIXED
- **Files:** `packages/local-mailroom-sandbox/deploy/htcondor/vllm_serve.sub`, `vllm_batch_eval.sub`, `serve_vllm.sh`
- **Fixed:**
  - Image tag `v0.8.5` → `v0.28.0` (both .sub files)
  - `--disable-log-requests` → `--no-enable-log-requests` (serve_vllm.sh)

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
| 2026-09-10 | Sandbox Modal+vLLM CLI + eval-task + model-catalog audit (with vllm-specialist + modal-specialist) | (1) Job runner advertises whole-run tasks but crashes on all but sorter/legalbench; (2) model catalog thin, no per-GPU guidance, 70B unreachable (no TP knob); (3) L4 default cannot hold Qwen3-14B bf16 (14B trap); (4) 900s scaledown tail is the largest eval cost line item | Opened DMR-041 (runner delegation) and DMR-045 (model catalog + TP knob) | The docs/jobs.md claim "others at whole-run" but the code has no whole-run branch — always trace RUNNABLE_TASKS against the actual dispatch |
| 2026-09-10 | HuggingFace integration audit of sandbox + corpus-eda (lucius) | CRITICAL: corpus.py:228 calls undefined `load_hf` (NameError) — the entire HF corpus path is broken; F7/F8 `effective_revision` on DatasetSpec AttributeError; F26 hf_interface.py bare hf_hub_download; fixture intent_status drift; hf_rows_as_manifest dead code; skill doc stale docclass-merged | Opened DMR-042 (#45) covering all HF fixes | The DMR-027 test suite only exercised file:// paths, so the broken Hub path shipped green — network-free suites can hide a completely dead default path |
| 2026-09-10 | Docker/container deploy surface audit (docker-deployment-specialist) | CRITICAL: jupyter compose build context + volume resolve to deploy/ (F1/F2); vllm service has no GPU reservation (F3); CHTC batch eval silently mocks (F4); 8192 parity break (F5); Python 3.11 doc stale (F6); floating tags vs pinning claim (F7) | Opened DMR-043 (#46) and DMR-044 (#47) | docker compose config is daemon-free and catches path-resolution bugs that file reads alone miss |
| 2026-09-10 | Board + Vercel sync (post archive) | 38 cards live on the served board, 7 open; DMR-040 closed as factually wrong; archive entries missing owner attribution on all cards | Added Owner to all 32 archive entries; archived DMR-011 (fix shipped via DMR-028, caveat retired); fixed DMR-040 status `closed`→`done` for parser | board_state.py parser requires `done` (not `closed`) in Archive; DMR-040's "closed" status caused phantom-card-reference |
| 2026-09-10 | DMR-041 + DMR-042 implementation | Whole-run task delegation missing in job/runner.py (ValueError on all non-per-item tasks); HF Hub path broken (undefined load_hf); effective_revision AttributeError; hf_interface missing import | Shipped all fixes (commit `1085c273`) + 9 network-free tests; closed #44/#45; archived both cards; board 10 open, check 0/0 | Whole-run delegation must dispatch BEFORE the per-item row guard (local_vs_api legitimately has no locked dataset rows); card edits to the open table can accidentally duplicate adjacent rows — always re-run `board_state.py check` and grep the card id after table surgery |
| 2026-09-10 | DMR-011 through DMR-029 veracity audit | 10 of 12 cards have missing implementations; 2 cards correctly scoped as execution-only | Created DMR-028 through DMR-037; wrote STATE.md | None yet |
| 2026-09-10 | Fix pass: DMR-029, DMR-030, DMR-031, DMR-032 | Archived cards DMR-021/DMR-022 claimed fixes were shipped but only applied to local-mailroom-sandbox | Fixed vllm-specialist.md version, both Modal deploy files (Secret.from_local, image tag, log flag), htcondor templates (image tag, log flag) | DMR-029/DMR-030 remaining issues (cache volume, revision knob, pyproject pin) needed separate design decisions |
| 2026-09-10 | Fix pass 2: DMR-029, DMR-030 remaining items | Both deploy files lacked vLLM cache volume, revision knob, GPU memory utilization, max-num-seqs; pyproject.toml files had stale `modal>=0.73` pin | Added all missing knobs to both deploy files (porting from local-mailroom-sandbox reference), pinned `modal==1.5.5` in both pyproject.toml files | None — sandbox reference was the gold standard |
| 2026-09-10 | Comprehensive documentation drift audit (#3) | Full monorepo sweep: Exios66 refs, --disable-log-requests refs, vLLM versions, Modal SDK pins, test stubs, wiki pages, AGENTS.md roster, deploy configs. DMR-040 card claim verified as INCORRECT. All deploy files verified OK. Exios66 refs in docs/ are contextual (lineage). README release badges may be stale. | Updated STATE.md with full audit entry; verified all open card claims against code | DMR-040 card claimed a problem that doesn't exist — always verify line-specific claims before creating follow-up work |

## Lessons Learned
- **2026-09-10:** Always verify the actual file:line references in DMR cards against the current codebase. Cards synced from HUB issues may reference line numbers that have shifted or implementations that were never actually completed. The card's "Evidence" field describes the problem but does not confirm the fix was shipped.
- **2026-09-10 (sandbox audit):** A "network-free" test suite can hide a completely broken default path — the sandbox job tests only exercised `file://` datasets, so the undefined `load_hf` NameError on the Hub path shipped green with DMR-027. When auditing a CLI, always smoke-test the documented default mode, not just the mocked one.
- **2026-09-10 (sandbox audit):** `RUNNABLE_TASKS`/docs claiming "whole-run" support means nothing until you trace the actual dispatch. `_predict_row` only handled sorter/legalbench; every other advertised task raised ValueError. Cross-check the advertised task list against the real code path, not the docstring.
- **2026-09-10 (docker audit):** `docker compose config` is daemon-free and catches path-resolution bugs (jupyter `context: .` resolving to deploy/) that static file reads alone miss. Run it before declaring compose files correct.
- **2026-09-10 (board):** `board_state.py` Archive parser requires `done` status — `closed` produces phantom-card-reference errors even though the entry is present. Always run `board_state.py check` after any archive edit.
- **2026-09-10 (board):** The served board (Vercel) is a VIEW over GitHub issues; TASKS.md is the source of truth. After archiving cards on the site, run `pull-issues` to import lane moves and `sync-issues --apply` to push board truth back — the two must be reconciled before a main push.
- **2026-09-10:** DMR cards that say "synced from HUB-XXX" with a specific issue number are mirroring the predecessor board's state, not confirming that work was done in the DMR repo. The sync operation copies the card, not the implementation.
- **2026-09-10:** When auditing deploy files, check both the `modal.Secret.from_local` removal (SDK 1.5.x breaking change) AND the `--disable-log-requests` → `--no-enable-log-requests` rename (vLLM v0.28.0 breaking change). These two issues affect multiple deploy files across the monorepo.
- **2026-09-10:** Archived cards that claim "DELIVERED" may only have fixed the problem in ONE location (e.g., local-mailroom-sandbox) without porting to sibling packages (llm-mailroom, llm-entity-extraction). Always cross-check all deploy files when a fix is claimed.
- **2026-09-10 (audit 2):** When DMR-031 claimed the vllm-specialist.md version policy was fixed, the fix was only applied to lines 37-44 (the version policy section) — the playbook section at line 83 still carried the old `--disable-log-requests` flag name. A fix that touches one section of a doc does not automatically fix other sections that reference the same concept. Always grep for the full pattern across the entire file.
- **2026-09-10 (audit 2):** Test stubs that mock `Secret.from_local` are functionally harmless when the deploy code calls `Secret.from_dict` (the stub's `from_local` is simply never invoked), but they are logically stale and should be updated for correctness. Don't dismiss stale test mocks just because they don't cause test failures — they mask the fact that the test doesn't exercise the actual code path.
- **2026-09-10 (audit 3):** When auditing cross-references, distinguish between (a) contextually correct references to the predecessor monorepo (historical lineage, cross-board links, troubleshooting docs that document the error and its fix) and (b) stale references that should point to the current repo. The `Exios66/mailroom-dev` references in `llm-mailroom/docs/` are contextual (they describe the monorepo relationship). The `Exios66/llm-mailroom` release badge links in READMEs are potentially stale if the repo has moved to `LLM-Mailroom-Services/Digital-Mailroom`.
- **2026-09-10 (audit 3):** DMR cards can contain factually incorrect claims. DMR-040 claimed `vllm-specialist.md:83-84` still references `--disable-log-requests`, but lines 83-84 actually have the CORRECT flag name `--no-enable-log-requests`. Always verify the specific line numbers cited in a card before creating follow-up work.

## Comprehensive Audit #2 (2026-09-10)

### Scope
Full board state audit (DMR-011 through DMR-040), documentation drift check, archived card verification, and STATE.md maintenance.

### Verdict Summary

| Card | Status | Verdict |
|---|---|---|
| DMR-011 | unassigned | **FIX IS SHIPPED** — card should be archived (DMR-028 delivered the `git ls-tree` + `git cat-file blob` fix) |
| DMR-012 | unassigned | CORRECTLY SCOPED — legitimate "needs execution" |
| DMR-013 | unassigned | CORRECTLY SCOPED — legitimate "needs execution" |
| DMR-014 | unassigned | NOT SHIPPED — no mutation operators exist |
| DMR-015 | unassigned | NOT SHIPPED — surfaces still 4-token |
| DMR-016 | unassigned | NOT SHIPPED — extended-8 grading persists |
| DMR-017 | unassigned | NOT SHIPPED — only pilot variants exist |
| DMR-018 | unassigned | NOT SHIPPED — no INSURBIAS evaluation |
| DMR-023 | unassigned | PARTIALLY SHIPPED — deploy fixed (DMR-029), test mock stale (`from_local` in stub, should be `from_dict`) |
| DMR-024 | unassigned | PARTIALLY SHIPPED — deploy fixed (DMR-030), test mock stale (`from_local` in stub, should be `from_dict`) |
| DMR-040 | unassigned | NOT SHIPPED — `vllm-specialist.md:83` still says `--disable-log-requests`, should be `--no-enable-log-requests` |

### Archived Card Verification
DMR-026, DMR-028, DMR-029, DMR-030, DMR-031, DMR-032: all verified as shipped against actual codebase state.

**Exception:** DMR-031 claimed the vllm-specialist.md was fully fixed, but the playbook section (line 83) still carries the stale flag name — this is the DMR-040 gap.

### Documentation Drift Findings
1. **AGENTS.md specialist roster** — ✅ No drift. The four `mode: all` project specialists match actual `.opencode/agents/*.md` files.
2. **vllm-specialist.md playbook** — ⚠️ Stale flag `--disable-log-requests` at line 83 (tracked by DMR-040).
3. **Test stub staleness** — ⚠️ Both `test_vllm_modal_capability.py` and `test_kanban096_modal_vllm.py` define `_Secret.from_local` (dead code); deploy code calls `from_dict` (not mocked). Functionally harmless but logically stale (tracked by DMR-023, DMR-024).
4. **docs/wiki/Served-Board.md** — ✅ No drift. Correct repo name, deploy URL, tool commands.
5. **TASKS.md archive** — ✅ Verified. DMR-026 through DMR-039 archive entries match codebase state.

### New DMR Cards
**None required.** All discrepancies are already tracked by existing open cards (DMR-023, DMR-024, DMR-040) or archival actions (DMR-011).

### Actions Taken
1. Verified all 11 open cards (DMR-011 through DMR-040) against actual codebase.
2. Verified 7 archived cards (DMR-026 through DMR-032) against actual codebase.
3. Checked AGENTS.md roster against `.opencode/agents/` directory.
4. Checked `docs/wiki/Served-Board.md` for drift.
5. Identified DMR-011 as a board hygiene discrepancy (fix shipped, card still open).
6. Updated STATE.md with this audit entry.

## Comprehensive Audit #3 — Documentation Drift (2026-09-10)

### Scope
Full documentation drift audit across the entire monorepo: every package README, AGENTS.md, deploy config, wiki page, cross-reference, and the `docs/wiki/` pages. Checked for stale `Exios66/mailroom-dev` references, stale `--disable-log-requests` flag names, stale vLLM versions (pre-v0.28.0), stale Modal SDK versions (pre-1.5.x), and missing documentation.

### Findings Summary

| Category | Status | Details |
|----------|--------|---------|
| Deploy files (modal_vllm.py) | ✅ ALL FIXED | DMR-029, DMR-030, DMR-032 all verified against reference implementation |
| HTCondor templates | ✅ FIXED | DMR-032: v0.28.0 tag + `--no-enable-log-requests` |
| Modal SDK pins | ✅ CORRECT | All 3 packages pin `modal==1.5.5` matching specialist docs |
| vllm-specialist.md version policy | ✅ FIXED | DMR-031: v0.29.0 current stable documented |
| vllm-specialist.md playbook | ✅ ACTUALLY CORRECT | Lines 83-84 have `--no-enable-log-requests` — DMR-040 card claim is WRONG |
| modal-specialist.md | ✅ CORRECT | SDK 1.5.5 documented |
| Test stubs (from_local) | ⚠️ STALE | DMR-023, DMR-024: test mocks still define `from_local`, deploy calls `from_dict` |
| Wiki cross-board links | ✅ CONTEXTUALLY CORRECT | `mailroom-dev.vercel.app` refs describe predecessor board, not current deploy |
| Wiki --disable-log-requests | ✅ CONTEXTUALLY CORRECT | Troubleshooting docs document the error and its fix |
| Exios66/mailroom-dev in docs | ⚠️ CONTEXTUALLY CORRECT | `llm-mailroom/docs/` references are lineage descriptions, not active URLs |
| Exios66 release badges | ⚠️ POTENTIALLY STALE | README badges point to `Exios66/llm-mailroom` releases |
| TODO/FIXME/HACK in deploy files | ✅ CLEAN | No markers found |
| AGENTS.md roster | ✅ CORRECT | Specialist roster matches `.opencode/agents/` directory |
| Package AGENTS.md coverage | ✅ CORRECT | Packages without AGENTS.md (llm-dojo-scoring, agent-mailroom, llm-mailroom-graph) per root AGENTS.md |

### Detailed Findings

#### 1. DMR-040 Card Claim is INCORRECT
- **Card claim:** `.opencode/agents/vllm-specialist.md:83-84` still references `--disable-log-requests`
- **Actual content at lines 83-84:** `--no-enable-log-requests` (the CORRECT flag name)
- **Verdict:** The card's claim is factually wrong. No fix needed.
- **Action:** Note in STATE.md; card should be updated or closed.

#### 2. Exios66 References in Package READMEs (POTENTIALLY STALE)
Multiple package READMEs contain `Exios66/` references in release badges and links:
- `packages/llm-mailroom/README.md`: release badge points to `Exios66/llm-mailroom/releases/tag/v0.6.0`
- `packages/llm-dojo-scoring/README.md`: release badge points to `Exios66/llm-dojo-scoring/releases/tag/v0.13.0`
- `packages/agent-mailroom/README.md`: pipeline/scoring badges point to Exios66 repos
- `packages/llm-mailroom-graph/README.md`: links point to Exios66 repos
- **Context:** These may be correct if the packages still live in Exios66 repos as mirrors. The monorepo is the dev source of truth, but releases may still be cut from the Exios66 mirrors.
- **Action:** Verify whether releases are still cut from Exios66 repos or from `LLM-Mailroom-Services/Digital-Mailroom`.

#### 3. Exios66/mailroom-dev References in llm-mailroom/docs/ (CONTEXTUALLY CORRECT)
Extensive references in `packages/llm-mailroom/docs/wiki/` and `docs/sister-repos.md`:
- `Home.md`, `_Sidebar.md`, `Getting-Started.md`, `sister-repos.md` all reference `Exios66/mailroom-dev`
- **Context:** These are lineage descriptions explaining the monorepo relationship. They are factually correct — the predecessor monorepo IS `Exios66/mailroom-dev`.
- **Action:** No fix needed.

#### 4. Exios66/mailroom-dev References in Code/Tests (CONTEXTUALLY CORRECT)
- `packages/llm-mailroom/src/pipeline/gmail_intake.py`: HTML email template includes `Exios66/mailroom-dev` link
- `packages/llm-mailroom/src/tests/test_gmail_intake.py`: tests assert the URL is present
- **Context:** These are part of the email template that links back to the project. The URL may be stale but changing it requires updating the template AND the tests.
- **Action:** Consider updating to `LLM-Mailroom-Services/Digital-Mailroom` if the repo has permanently moved.

#### 5. Exios66 References in The-Mailroom TUI/Terminal (CONTEXTUALLY CORRECT)
- `packages/The-Mailroom/tui/repos.py`: references `Exios66/mailroom-dev` in UI
- `packages/The-Mailroom/terminal/js/data.js`: references `Exios66/mailroom-dev` in UI data
- **Context:** These are the UI's "about" or "repos" display. They describe the upstream monorepo.
- **Action:** Consider updating if the UI should point to the current repo.

#### 6. Exios66 References in mailroom-corpus-eda (CONTEXTUALLY CORRECT)
- `packages/mailroom-corpus-eda/scripts/backfill_intent.py`: references `Exios66/mailroom-dev/issues/5`
- `packages/mailroom-corpus-eda/src/mailroom_eda/intent_backfill.py`: references same issue
- **Context:** These are code comments referencing the original issue that motivated the code. The issue URL is historically accurate.
- **Action:** No fix needed.

### Actions Taken
1. Searched entire repo for stale `Exios66/mailroom-dev` references
2. Searched entire repo for stale `--disable-log-requests` flag references
3. Searched entire repo for stale vLLM versions (v0.8.5, v0.24.0)
4. Verified all 3 modal_vllm.py deploy files against reference implementation
5. Verified all pyproject.toml Modal SDK pins
6. Verified HTCondor templates
7. Verified vllm-specialist.md and modal-specialist.md
8. Checked for TODO/FIXME/HACK markers in deploy files
9. Verified AGENTS.md roster against .opencode/agents/ directory
10. Checked open card claims against actual code (DMR-023, DMR-024, DMR-040)
11. Updated STATE.md with this audit entry

### New DMR Cards Required
**None.** All discrepancies are already tracked by existing cards (DMR-023, DMR-024). The DMR-040 card claim is incorrect and should be updated or closed.
