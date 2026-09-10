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
| DMR-011 | `unassigned` | Harden `sync_packages.py patch_push` so uncommitted work can never propagate: copy committed blobs (`git archive HEAD` / `git ls-tree`) and/or re-assert a per-package clean-tree guard before each package copy; retire the AGENTS.md + wiki race caveat when done. | unclaimed | [#16](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/16) | synced from HUB-044 [#28](https://github.com/Exios66/mailroom-dev/issues/28); race still present at `scripts/sync_packages.py:345-351` |
| DMR-012 | `unassigned` | Gmail triage production-readiness residuals: live re-send/provenance operator proof, CI secret-presence check (`GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD`), Langfuse/Phoenix trace checklist for `gmail-triage`, ops-lamp alerting on `checks.gmail_intake`, and watcher-stability/free-swarm/failed-bin runbooks. HUB-037/039/043/048 deliveries are in place — do not redo. | unclaimed | [#17](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/17) | synced from HUB-064 [#43](https://github.com/Exios66/mailroom-dev/issues/43) |
| DMR-013 | `unassigned` | Run the live `packages/The-Mailroom/scripts/publish_pages.sh` so the terminal site goes live at the Pages root (currently the v0.3.0 pixel console is served; `/terminal/` 404s) and verify `publish_pages.sh --status`; TUI/site code, 0.4.0 release, and upstream sync are already delivered. | unclaimed | [#18](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/18) | synced from HUB-054 [#25](https://github.com/Exios66/mailroom-dev/issues/25); only the live publish is pending |
| DMR-014 | `unassigned` | Specialist mutations on mailroom-corpus v7+v8: implement structured specialist mutation operators + fitness/registry and run the first evolution pass. `needs:` tokenizer-budget alignment (GT-integrity half now evidenced by the HUB-032 reconciliation + `content_sha256` loader proof). | unclaimed | [#19](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/19) | synced from HUB-062 [#11](https://github.com/Exios66/mailroom-dev/issues/11); no mutation operators/registry exist yet |
| DMR-015 | `unassigned` | Derive mailroom-named successor keys for the frozen pre-v8 insurance-subclass surfaces — vision sorter rule 40 (`sorter_docclass_vision_v1`), `_PILOT_CONTEXT`, `reviewer_docclass_pilot_v0` — teaching the v8 six-token set (carrier/pde/outpatient/inpatient + property/auto), plus the docclass-pilot examples refresh; same-surface A/Bs before any default change. Coordinate `_PILOT_CONTEXT` with DMR-016. | unclaimed | [#20](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/20) | synced from HUB-042 [#30](https://github.com/Exios66/mailroom-dev/issues/30); surfaces still 4-token at `src/prompts.py:1266`, `src/prompts_docclass.py:702-703,752-755` |
| DMR-016 | `unassigned` | Add NEW docclass judge/reviewer/arbiter/boss prompt keys with five-class + `unknown` grading language per plan §67, mirror byte-identical into The-Mailroom (and re-sync the stale 32→59-key mirror), defaults unchanged until a same-surface A/B. `decision:` keep the extended 8-class surface as deliberate eval design (KANBAN-033 lineage) or move to five-class grading. | unclaimed | [#21](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/21) | synced from HUB-020 [#26](https://github.com/Exios66/mailroom-dev/issues/26); extended-8 grading persists at `src/prompts_docclass.py:92-110,246-250,313-315,371-372` |
| DMR-017 | `unassigned` | GEPA prompt mutations on docclass v7+v8: run the prompt-engineer/GEPA loop against the five-class corpus surface and register the first `mailroom_v` docclass lineage keys (sorter + judge/reviewer) with same-surface A/Bs. `needs:` the DMR-016 five-class decision; never mutate frozen `docclass_*` keys. | unclaimed | [#22](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/22) | synced from HUB-061 [#7](https://github.com/Exios66/mailroom-dev/issues/7); only `sorter_mailroom_v0` (HUB-041) exists |
| DMR-018 | `unassigned` | v9 corpus candidate: re-evaluate INSURBIAS (CC-BY-4.0 insurance-claim narratives) as a v9 source alongside the P4 expansion priorities — insurance workflow is now MEDIUM with adjuster 150/950 after v8 — license permitting and only with decision/adjudication GT or an explicit GT-gap convention. | unclaimed | [#23](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/23) | synced from HUB-036 [#27](https://github.com/Exios66/mailroom-dev/issues/27); v9 not started, INSURBIAS deferred at `packages/mailroom-corpus-eda/AGENTS.md:131` |

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

- **DMR-019** (done 2026-09-09) — **Adopt the `unassigned` lane — unclaimed cards free to claim** — DELIVERED (commit `6e8d02b`): the served board's five-lane flow is now the canonical board's too — `scripts/board_state.py` `LANES`/`LANE_LABELS` gain `unassigned`/`stage/unassigned` with lane-owner coherence rules (`unassigned` + named Owner = error; `assigned` + `unclaimed` = warning) and `sync-issues` now removes stale `stage/*`/`attention/*` labels on a lane move; `.github/labels.json` (33-label manifest, synced live) + `hub_card.yml` add the lane; `governance/TASKS.md` documents five lanes and moves DMR-011..DMR-018 (all Owner `unclaimed`) into `unassigned`, keeping their `needs:`/`decision:` attention labels (lane is ownership, not blockage); `AGENTS.md`, `governance/README.md`, and the wiki (`Board-Governance` + `Served-Board`, republished) document the flow. Verified: board check 0/0 (with issues), all 8 issues swapped to `stage/unassigned` with no stale stage labels, served board shows the 8 cards in `unassigned` (agents `unclaimed`), labels audit in sync, release chain OK, taxonomy parity OK, reference audit clean. Issue #24 closed 2026-09-09.
- **DMR-010** (done 2026-09-09) — **HUB → DMR open-issue sync — 8 still-open HUB cards mirrored with synced issues + cross-links** — DELIVERED (commit `570f2b9`; the board rows first landed in `ec83b04`): the 9 open `kanban` issues on the predecessor board (`Exios66/mailroom-dev`) were verified against this checkout (atom board-sync report); 8 carried open work and are mirrored as DMR-011..DMR-018 (#16–#23) — HUB-044 worktree-race hardening, HUB-064 Gmail-triage residuals, HUB-054 terminal-Pages residual, HUB-062 specialist mutations (blocked), HUB-042 pre-v8 frozen docclass surfaces, HUB-020 five-class/`unknown` keys (decision), HUB-061 GEPA `mailroom_v` lineage (blocked), HUB-036 v9 INSURBIAS — each preserving lane/priority/domain with the HUB issue as lineage and a `### Scope detail` issue section carrying the atom file:line evidence. HUB-006 (#23) was reviewed and skipped (predecessor-board stand-in note; no equivalent surface here). Cross-link comments posted on all 8 HUB issues + the HUB-006 skip note. Gates: board check 0/0 (with issues), `sync-issues --apply` normalized 9 issue bodies, labels in sync (32), release chain OK, taxonomy parity OK, reference audit clean. Issue #15 closed 2026-09-09.
- **DMR-009** (done 2026-09-09) — **Repo hygiene + wiki publication — dead-branch prune, residual Speed Insights lockfile delta, subagents + board configs on the wiki** — DELIVERED (commit `da0ea35`): all 8 dead remote branches deleted (only `main` remains) — the merged Vercel/eng-ops branches (#2/#4 etc.), the stale HUB-era `cos/hub-064-archive-043` WIP (its TASKS.md content would have deleted the DMR board; preserved in the predecessor repo), and the orphan `gh-pages` snapshot (GitHub Pages is not enabled on this repo). All PRs were already merged; the only branch with residual content (`vercel/install-and-configure-vercel-s-q0r6d5`) carried the missing `@vercel/speed-insights@2.0.0` lockfile entry — landed surgically in `packages/The-Mailroom/ui/package-lock.json` (registry integrity + peer deps verified; `npm ci --dry-run` clean) instead of merging the stale branch (it lacks `@vercel/analytics` + the newer board-site). The wiki was published for the first time (14 pages; `sync-wiki.sh --check` green), including new `Subagents.md` (DMR-008 specialist roster + `.opencode/agents/` project files + rules), cross-board tabs (DMR-005), `POST /api/board` + two-project Vercel hygiene (DMR-007), and DMR-0NN namespace fixes; `scripts/audit_references.py` allowlists the two cross-board wiki pages. Gates: board check 0/0 (with issues), labels in sync (32), release chain OK, taxonomy parity OK, reference audit clean, The-Mailroom suite 334 passed / 2 skipped. Issue #13 closed 2026-09-09.
- **DMR-008** (done 2026-09-09) — **Specialist subagent roster in AGENTS.md + dedicated vLLM/Modal subagents** — DELIVERED (commit `468f731`): `AGENTS.md` carries the "Specialist subagents — call them, don't impersonate them" section (full roster table, one-specialist-per-concern, brief-like-a-card, caller-owns-the-work, current-docs verification, skills second layer); new project subagents `.opencode/agents/vllm-specialist.md` (vLLM stable v0.24.0-grounded serving playbook + repo wiring + guardrails) and `.opencode/agents/modal-specialist.md` (Modal Python SDK 1.5.5-grounded primitives/CLI/GPU discipline + repo deploy apps) both require checking current upstream docs before writing config. Gates at close: `board_state.py check` 0 errors / 0 warnings; both frontmatters parse (`mode: subagent`); `audit_references.py` clean; `release_chain.py check` OK; labels audit in sync. Issue #12 closed 2026-09-09. **Action: restart opencode** so the Task tool loads the new subagents.
- **DMR-007** (done 2026-09-09) — **Retire stray `board-site` Vercel project + served-board write-path proof** — DELIVERED (card commit `f3a4042`): the duplicate project `board-site` (`prj_8zQcxU0FxqXPW4qmE8reQQuXFciu`, board-site-gamma.vercel.app → 404, linked to `Exios66/mailroom-dev` with Root Directory unset) was deleted via the Vercel API (204); only `digital-mailroom` (digital-mailroom-theta.vercel.app) and `mailroom-dev` (mailroom-dev.vercel.app) remain. Write-path proof for the human directive ("new DMR issues tracked in the org repository and displayed on the new Vercel deployment"): DMR-007 was created through `POST /api/board` on the served site, landed as a kanban issue in `LLM-Mailroom-Services/Digital-Mailroom` (#11), displayed live, and its lane was corrected via `PATCH /api/board/DMR-007`. Issue #11 closed 2026-09-09.
- **DMR-006** (done 2026-09-09) — **Org-migration reference audit + wiring sweep + CI gate** — DELIVERED (commit `849663a`): `docs/reports/audits/org_migration_audit.md` + `.json` (three-tier inventory: migrate / package-mirror / historical), new `scripts/audit_references.py` (gated patterns `Exios66/mailroom-dev` + `mailroom-dev.vercel.app`, classified allowlist, CHANGELOG-footer rule, `--json`), wired into `.github/workflows/board-governance.yml`; sweep of the issue-template config, CHANGELOG scope+footer, wiki pages (incl. the stale Root-Directory FAQ), README family, LICENSE, `.opencode`, plan doc, SVG caption, dependabot comment, sync propagation message; GitHub About topics (10) + board-link description. Intentionally unchanged (allowlisted): package mirrors/wiring, HUB-era history, the cross-board switcher. Original-repo leg: HUB-067 (`0f06fb4`, archive `a589c49`). Gates at close: audit clean; board check 0/0; labels in sync; release chain OK; taxonomy parity OK. Issue #10 closed 2026-09-09.
- **DMR-004** (done 2026-09-09) — **Push-triggered deploys for the served board — Vercel Git integration** — DELIVERED (commit `4347055`): the Vercel GitHub App was installed on the `LLM-Mailroom-Services` org (human, 2026-09-09) and `vercel git connect` linked project `digital-mailroom` to `LLM-Mailroom-Services/Digital-Mailroom` (production branch `main`, Root Directory `board-site`). **LIVE VERIFIED:** pushing `4347055` produced git-sourced production deployment `digital-mailroom-3fsp2ua9z-lucius-projects-54efe0bb.vercel.app` (state READY, `githubCommitRef: main`, sha `4347055`), and the production alias https://digital-mailroom-theta.vercel.app serves it (`/api/board` 200, repo correct). Manual CLI from the repo root remains the documented fallback (`.vercelignore` ships `board-site/` only). Docs currency: `docs/wiki/Served-Board.md` deploy section + root `AGENTS.md` now state the integration is live. Issue #8 closed 2026-09-09.
- **DMR-001** (done 2026-09-09) — **Standalone board bootstrap — fresh DMR TASKS.md + tooling re-point** — DELIVERED (commit `be75d1e`): fresh DMR board (this file) + full tooling re-point to `LLM-Mailroom-Services/Digital-Mailroom` — `scripts/board_state.py` (DEFAULT_REPO, card/archive/lane/issue regexes, project title), `scripts/github_labels.py`, `.github/labels.json` (note + descriptions), `scripts/release_chain.py`, `scripts/release_notes.py`, `.github/ISSUE_TEMPLATE/hub_card.yml`; 32-label kanban taxonomy seeded in the new repo. Gates at close: `board_state.py check` 0 errors / 0 warnings; `github_labels.py audit` in sync (32 labels); `release_chain.py check` OK; `taxonomy_parity.py` OK. Issue #5 closed 2026-09-09.
- **DMR-002** (done 2026-09-09) — **Served dispatch board for the standalone clone — new Vercel project** — DELIVERED (commit `be75d1e`): new Vercel project `digital-mailroom` (Root Directory `board-site`, Vercel Authentication disabled, `GITHUB_TOKEN` production secret), board-site re-pointed to the new repo + DMR namespace + new CORS origins, repo-root `.vercelignore` limiting CLI deploys to `board-site/`. LIVE VERIFIED: https://digital-mailroom-theta.vercel.app — `GET /api/board` returns `repo: LLM-Mailroom-Services/Digital-Mailroom`, PATCH write-back round-tripped DMR-003 (issue #7, agent from `### Owner`). Auto-deploy mechanism deferred to spawned **DMR-004** (append-only law). Issue #6 closed 2026-09-09.
- **DMR-003** (done 2026-09-09) — **Original mailroom-dev board access — write path + deployment URL** — DELIVERED (commit `be75d1e`): live write path verified — `PATCH /api/board/HUB-064` through https://mailroom-dev.vercel.app returned the updated card (issue #43, priority/high); Vercel Authentication (`ssoProtection`) disabled on project `mailroom-dev` via the API, so raw deployment URLs (e.g. https://mailroom-4sc2d0sxd-lucius-projects-54efe0bb.vercel.app/) and their `/api/board` now return 200 instead of 302 to Vercel login. Issue #7 closed 2026-09-09.
- **DMR-005** (done 2026-09-09) — **Cross-board navigation tabs — DMR ↔ HUB served boards** — DELIVERED (human directive 2026-09-09): a board-switcher (`board-tabs` segmented control) now cross-links both served boards. DMR side (this commit): `board-site/index.html` — `DMR Board` active chip + `HUB Board ↗` link to https://mailroom-dev.vercel.app, DMR title/branding, meta description; deployed via CLI (production alias `digital-mailroom-theta.vercel.app`). HUB side: `Exios66/mailroom-dev` commit `3d57a60` (HUB-066, issue #47) — `HUB Board` active chip + `DMR Board ↗` link to https://digital-mailroom-theta.vercel.app, deployed by that project's Git integration. LIVE VERIFIED: both sites serve the switcher (markup present, `board-tabs`), both cross-links resolve 200, both `/api/board` proxies 200. Issue #9 closed 2026-09-09.
