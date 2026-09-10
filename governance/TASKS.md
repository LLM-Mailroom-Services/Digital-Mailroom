# TASKS.md — the Digital-Mailroom task board

The single source of truth for cross-agent task state in the **Digital-Mailroom
standalone repo** (`LLM-Mailroom-Services/Digital-Mailroom`): what is
**assigned**, **in progress**, **needs attention**, and **done**. Every agent
(and human contributor) reads this board before working and keeps it current
while working. It is a WORKING DOCUMENT, not documentation — modify it as work
happens, never delete history (finished cards move to the Archive at the bottom).

**Lineage (DMR-001, 2026-09-09):** this board was restarted fresh for the
standalone Digital-Mailroom version. The predecessor board — the `HUB-*` cards
of the original `Exios66/mailroom-dev` monorepo — remains canonical for that
repo; HUB-era history and evidence live there and in this repo's git history
(`git log --follow -- governance/TASKS.md`). The `DMR-` namespace starts at
DMR-001 and never reuses HUB numbers.

Scope: **this repo's monorepo-level work** (workspace wiring, cross-package
governance, board tooling, docs, releases). Work scoped to a single package is
tracked by that package's own governance — this board holds the hub view and
cross-package cards.

**Machine-readable state (DMR-001):** this board is computationally readable
via `python scripts/board_state.py` — `status` (snapshot, `--json` for
machines), `card DMR-0NN` (one card + its commits), `check` (invariants:
structural contradictions exit 1; hygiene drift is warned), `sync-issues`
(label sync onto synced issues), `pull-issues` (import served-board lane moves
back into this file), `project-init`/`project-sync` (GitHub Projects v2
mirror). The label taxonomy for issues lives in `.github/labels.json`
(`stage/*` = these lanes, `attention/*` = the needs_attention tags, `type/*`,
`priority/*`, `domain/*`, `kanban` marker); the CI gate
`.github/workflows/board-governance.yml` runs `check` + the label audit on
every change to `governance/`, `scripts/`, or `.github/`.

**Served board:** the live, issue-backed dispatch board for this repo is
**https://digital-mailroom-theta.vercel.app** (Vercel project
`digital-mailroom`, deploy root `board-site/`, `GITHUB_TOKEN` production
secret). It reads `kanban`-labeled issues in
`LLM-Mailroom-Services/Digital-Mailroom`; writes (move/edit/archive) PATCH
back to those issues. The canonical board stays this file — run
`board_state.py pull-issues` to import site-side lane moves, `sync-issues` to
push this file's truth into the issues.

## How to use — four steps

1. **Read first.** Read this board (and open GitHub issues) at session start,
   before any task: cards claimed by others, cards covering the work you were
   about to do, and open needs-attention items. Never duplicate or race a
   claimed card.
2. **Claim.** Claim an `unassigned` card by moving it to `assigned` and setting
   Owner to your agent name + date. The moment ANY work exists — a first edit,
   a diff, a branch, a run in flight — the card moves to `in_progress`. Label
   it before the code, never after; the table must never lie about reality.
3. **Work with the card current.** Update status and Evidence as you go.
   Stuck or awaiting review? Move to `needs_attention` with a tagged note
   (`needs:` blocked-on / `review:` evidence / `decision:` the question).
   Anything discovered but not delivered spawns its own card BEFORE your card
   closes.
4. **Close with proof.** `done` requires: the package suite(s) for the touched
   packages green, `git status` clean for the card's scope, Evidence naming
   the commit(s), and — for synced cards — the GitHub issue closed in the same
   commit. Then move the card to the Archive. An agent is NOT done until its
   card says so.

## Lanes

| Lane | Meaning |
|---|---|
| `unassigned` | Queued and unclaimed — free for the next available agent or team to claim. Owner must be `unclaimed`. |
| `assigned` | Claimed (or queued with an owner), nothing underway — no draft, no diff, no branch. |
| `in_progress` | ANY work exists and an owner holds it. ONE owner per card. |
| `needs_attention` | Blocked, awaiting review, or awaiting a decision — the Evidence note says which (`needs:` / `review:` / `decision:`). |
| `done` | Finished, verified, evidenced — moved to the Archive below. Never deleted; reopen by moving back to `unassigned` with a dated note. |

## Open cards

| Card | Status | Task | Owner | Issue | Evidence |
|---|---|---|---|---|---|
| DMR-011 | `unassigned` | Harden `sync_packages.py patch_push` so uncommitted work can never propagate: copy committed blobs (`git archive HEAD` / `git ls-tree`) and/or re-assert a per-package clean-tree guard before each package copy; retire the AGENTS.md + wiki race caveat when done. **Status:** the committed-blob extraction fix is shipped (DMR-028); the AGENTS.md + wiki race caveat retirement may still be pending — verify. | unclaimed | [#16](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/16) | synced from HUB-044 [#28](https://github.com/Exios66/mailroom-dev/issues/28); DMR-028 shipped `git ls-tree -r -z HEAD` + `git cat-file blob` fix |
| DMR-012 | `unassigned` | Gmail triage production-readiness residuals: live re-send/provenance operator proof, CI secret-presence check (`GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD`), Langfuse/Phoenix trace checklist for `gmail-triage`, ops-lamp alerting on `checks.gmail_intake`, and watcher-stability/free-swarm/failed-bin runbooks. HUB-037/039/043/048 deliveries are in place — do not redo. | unclaimed | [#17](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/17) | synced from HUB-064 [#43](https://github.com/Exios66/mailroom-dev/issues/43) |
| DMR-013 | `unassigned` | Run the live `packages/The-Mailroom/scripts/publish_pages.sh` so the terminal site goes live at the Pages root (currently the v0.3.0 pixel console is served; `/terminal/` 404s) and verify `publish_pages.sh --status`; TUI/site code, 0.4.0 release, and upstream sync are already delivered. | unclaimed | [#18](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/18) | synced from HUB-054 [#25](https://github.com/Exios66/mailroom-dev/issues/25); only the live publish is pending |
| DMR-014 | `unassigned` | Specialist mutations on mailroom-corpus v7+v8: implement structured specialist mutation operators + fitness/registry and run the first evolution pass. `needs:` tokenizer-budget alignment (GT-integrity half now evidenced by the HUB-032 reconciliation + `content_sha256` loader proof). | unclaimed | [#19](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/19) | synced from HUB-062 [#11](https://github.com/Exios66/mailroom-dev/issues/11); no mutation operators/registry exist yet; DMR-035 confirmed 2026-09-10 |
| DMR-015 | `unassigned` | Derive mailroom-named successor keys for the frozen pre-v8 insurance-subclass surfaces — vision sorter rule 40 (`sorter_docclass_vision_v1`), `_PILOT_CONTEXT`, `reviewer_docclass_pilot_v0` — teaching the v8 six-token set (carrier/pde/outpatient/inpatient + property/auto), plus the docclass-pilot examples refresh; same-surface A/Bs before any default change. Coordinate `_PILOT_CONTEXT` with DMR-016. | unclaimed | [#20](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/20) | synced from HUB-042 [#30](https://github.com/Exios66/mailroom-dev/issues/30); surfaces still 4-token at `src/prompts.py:1266`; DMR-033 confirmed 2026-09-10 |
| DMR-016 | `unassigned` | Add NEW docclass judge/reviewer/arbiter/boss prompt keys with five-class + `unknown` grading language per plan §67, mirror byte-identical into The-Mailroom (and re-sync the stale 32→59-key mirror), defaults unchanged until a same-surface A/B. `decision:` keep the extended 8-class surface as deliberate eval design (KANBAN-033 lineage) or move to five-class grading. | unclaimed | [#21](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/21) | synced from HUB-020 [#26](https://github.com/Exios66/mailroom-dev/issues/26); extended-8 grading persists at `src/prompts_docclass.py:92-110,246-250,313-315,371-372`; DMR-034 confirmed 2026-09-10 |
| DMR-017 | `unassigned` | GEPA prompt mutations on docclass v7+v8: run the prompt-engineer/GEPA loop against the five-class corpus surface and register the first `mailroom_v` docclass lineage keys (sorter + judge/reviewer) with same-surface A/Bs. `needs:` the DMR-016 five-class decision; never mutate frozen `docclass_*` keys. | unclaimed | [#22](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/22) | synced from HUB-061 [#7](https://github.com/Exios66/mailroom-dev/issues/7); only `sorter_mailroom_v0` (HUB-041) exists; DMR-036 confirmed 2026-09-10 |
| DMR-018 | `unassigned` | v9 corpus candidate: re-evaluate INSURBIAS (CC-BY-4.0 insurance-claim narratives) as a v9 source alongside the P4 expansion priorities — insurance workflow is now MEDIUM with adjuster 150/950 after v8 — license permitting and only with decision/adjudication GT or an explicit GT-gap convention. | unclaimed | [#23](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/23) | synced from HUB-036 [#27](https://github.com/Exios66/mailroom-dev/issues/27); v9 not started, INSURBIAS deferred; DMR-037 confirmed 2026-09-10 |
| DMR-023 | `unassigned` | **[RESCOPED]** Update Modal deploy test stubs in `packages/llm-mailroom/src/tests/test_vllm_modal_capability.py` to stub `Secret.from_dict` instead of `Secret.from_local` (the removed API). The deploy file itself is fully fixed (DMR-029); only the test mock is stale. | unclaimed | [#28](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/28) | Deploy file fixed 2026-09-10 (DMR-029); test stub at line 30 still mocks `from_local` |
| DMR-024 | `unassigned` | **[RESCOPED]** Update Modal deploy test stubs in `packages/llm-entity-extraction/tests/test_kanban096_modal_vllm.py` to stub `Secret.from_dict` instead of `Secret.from_local` (the removed API). The deploy file itself is fully fixed (DMR-030); only the test mock is stale. | unclaimed | [#29](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/29) | Deploy file fixed 2026-09-10 (DMR-030); test stub at line 30 still mocks `from_local` |
| DMR-040 | `unassigned` | **[NEW — audit finding]** Fix `vllm-specialist.md:83-84` serving playbook: still references `--disable-log-requests` (the old flag name) — should say `--no-enable-log-requests`. One-line doc fix. | unclaimed | — | Audit 2026-09-10: `.opencode/agents/vllm-specialist.md:83-84` stale flag name in serving playbook |

## Rules that keep the board honest

- **One owner per card.** Never work a card someone else owns — offer help on
  the issue or take over by an explicit handoff recorded in Evidence.
- **Claim before edit.** A card you are about to touch is claimed by you in
  the same session the work starts; an unclaimed card is fair game but must
  be claimed at its first edit.
- **Update, don't duplicate.** Work that addresses an existing card's problem
  updates THAT card — never a parallel card, never a duplicate issue.
- **Later timestamp wins.** If two edits collide on one card, the later dated
  note stands; the overwritten party posts a correction rather than reverting.
- **No silent completion.** A card without its closing Evidence is, to every
  other agent, still in flight.
- **Commit discipline.** Reference cards in commits: `DMR-00N: <summary>` or
  `DMR-00N claimed/reopened` in the message body. **Stage targeted paths
  only:** `git add <explicit paths>` for exactly your card's files — never
  `git add .` / `-A` / a bare directory. This is a shared checkout: before
  every commit, `git status --porcelain` and unstage anything you don't own.

## Issues vs board — the card↔issue law

Every board card has a **synced GitHub issue** in this repo — one card = one
issue, opened from the *Board card (DMR-0NN)* template
(`.github/ISSUE_TEMPLATE/hub_card.yml`). Why this is a law: the served board
at https://digital-mailroom-theta.vercel.app reads `kanban`-labeled issues, so
a card without a synced issue never appears on it. Concretely:

- Open the card's issue before (or while) claiming it; fill the card's
  Issue column with the full link. Apply the `kanban` + `stage/*` +
  `priority/*` + `domain/*` labels (`board_state.py sync-issues` does the
  label mapping from the board).
- **Mirror lane moves both ways** — board → issue: post a dated "Board lane
  move" comment; issue → board (a move made on the served site): run
  `python scripts/board_state.py pull-issues` to report the drift, then
  `--apply` to rewrite the Lane cell + append a dated Evidence note.
- **Close the issue in the SAME commit that archives the card.** A `done`
  card with an open issue (or an open card with a closed one) is a board
  inconsistency — fix it immediately.

## Archive

- **DMR-039** (done 2026-09-10) — **Comprehensive offline sandbox documentation** — DELIVERED: `docs/SANDBOX-GUIDE.md` (14-section complete reference: prerequisites, setup, configuration, provider profiles, full CLI reference, Docker/Jupyter, evaluations, job system, Modal deployment, SSH tunnels, tracing, datasets, metrics, troubleshooting), `docs/wiki/Sandbox-Jobs.md` (job runner deep-dive), `docs/wiki/Sandbox-Modal.md` (Modal deployment guide), updated `docs/wiki/Offline-Sandbox.md` (expanded with quick-start checklist, CLI reference, all features), `_Sidebar.md` nav updated with new pages.
- **DMR-037** (done 2026-09-10) — **Merged into DMR-018** — INSURBIAS v9 evaluation duplicate. Audit finding confirmed the gap (no evaluation exists); work scope already covered by DMR-018.
- **DMR-036** (done 2026-09-10) — **Merged into DMR-017** — GEPA mailroom_v docclass lineage duplicate. Audit finding confirmed the gap (only pilot variants exist); work scope already covered by DMR-017.
- **DMR-035** (done 2026-09-10) — **Merged into DMR-014** — Specialist mutation operators duplicate. Audit finding confirmed the gap (no code exists); work scope already covered by DMR-014.
- **DMR-034** (done 2026-09-10) — **Merged into DMR-016** — Five-class docclass prompt keys duplicate. Audit finding confirmed the gap (extended-8 grading persists); work scope already covered by DMR-016.
- **DMR-033** (done 2026-09-10) — **Merged into DMR-015** — Insurance subclass successor keys duplicate. Audit finding confirmed the gap (4-token set persists); work scope already covered by DMR-015.
- **DMR-032** (done 2026-09-10) — **Audit finding — DMR-026 gap: align htcondor vLLM templates** — VERIFIED + FIXED: both `.sub` files now pin `v0.28.0` (lines 25/33); `serve_vllm.sh:16` uses `--no-enable-log-requests`. Commit `c69f1537`.
- **DMR-031** (done 2026-09-10) — **Audit finding — DMR-025 gap: refresh vllm-specialist.md version policy** — VERIFIED + FIXED: `.opencode/agents/vllm-specialist.md` line 37 states v0.29.0 current stable, v0.28.0 family pin; lines 41-44 document the `--enable-log-requests` rename and Model Runner V2 change.
- **DMR-030** (done 2026-09-10) — **Audit finding — DMR-024 gap: port Modal vLLM fixes to llm-entity-extraction** — VERIFIED + FIXED: `Secret.from_dict` (line 90), image `v0.28.0` (line 66), `--no-enable-log-requests` (line 133), `entity-vllm-cache` Volume (line 113), `MODAL_VLLM_REVISION` (lines 70/89/155-157), `modal==1.5.5` pin.
- **DMR-029** (done 2026-09-10) — **Audit finding — DMR-023 gap: port Modal vLLM fixes to llm-mailroom** — VERIFIED + FIXED: `Secret.from_dict` (line 96), image `v0.28.0` (line 69), `--no-enable-log-requests` (line 149), `mailroom-vllm-cache` Volume (line 101), `MODAL_VLLM_REVISION` (lines 58/77/143-145), `modal==1.5.5` pin.
- **DMR-028** (done 2026-09-10) — **Fix `sync_packages.py patch_push` race condition** — DELIVERED: replaced `git ls-files` + `shutil.copy2` (copies from working tree, propagating uncommitted changes) with `git ls-tree -r -z HEAD` + `git cat-file blob` (extracts committed blobs only). Retired the HUB-044 race caveat from `AGENTS.md` and `docs/wiki/Sub-Package-Sync.md`. **Verified:** `board_state.py check` 0/0, `scripts/sync_packages.py` no longer touches the working tree during `patch_push`.
- **DMR-026** (done 2026-09-10) — **Align htcondor vLLM templates** — VERIFIED + FIXED by DMR-032: both `.sub` files now pin `v0.28.0`, `serve_vllm.sh` uses `--no-enable-log-requests`.
