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
2. **Claim.** Move the card to `assigned` (if queued) and set Owner to your
   agent name + date. The moment ANY work exists — a first edit, a diff, a
   branch, a run in flight — the card moves to `in_progress`. Label it before
   the code, never after; the table must never lie about reality.
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
| `assigned` | Queued or claimed, nothing underway — no draft, no diff, no branch. Owner may be `unclaimed` (up for grabs: claim it per step 2). |
| `in_progress` | ANY work exists and an owner holds it. ONE owner per card. |
| `needs_attention` | Blocked, awaiting review, or awaiting a decision — the Evidence note says which (`needs:` / `review:` / `decision:`). |
| `done` | Finished, verified, evidenced — moved to the Archive below. Never deleted; reopen by moving back to `assigned` with a dated note. |

## Open cards

| Card | Status | Task | Owner | Issue | Evidence |
|---|---|---|---|---|---|
| — | — | _No open cards — the DMR board's current epoch is delivered. New work spawns its own card._ | — | — | — |

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

- **DMR-008** (done 2026-09-09) — **Specialist subagent roster in AGENTS.md + dedicated vLLM/Modal subagents** — DELIVERED (commit `468f731`): `AGENTS.md` carries the "Specialist subagents — call them, don't impersonate them" section (full roster table, one-specialist-per-concern, brief-like-a-card, caller-owns-the-work, current-docs verification, skills second layer); new project subagents `.opencode/agents/vllm-specialist.md` (vLLM stable v0.24.0-grounded serving playbook + repo wiring + guardrails) and `.opencode/agents/modal-specialist.md` (Modal Python SDK 1.5.5-grounded primitives/CLI/GPU discipline + repo deploy apps) both require checking current upstream docs before writing config. Gates at close: `board_state.py check` 0 errors / 0 warnings; both frontmatters parse (`mode: subagent`); `audit_references.py` clean; `release_chain.py check` OK; labels audit in sync. Issue #12 closed 2026-09-09. **Action: restart opencode** so the Task tool loads the new subagents.
- **DMR-007** (done 2026-09-09) — **Retire stray `board-site` Vercel project + served-board write-path proof** — DELIVERED (card commit `f3a4042`): the duplicate project `board-site` (`prj_8zQcxU0FxqXPW4qmE8reQQuXFciu`, board-site-gamma.vercel.app → 404, linked to `Exios66/mailroom-dev` with Root Directory unset) was deleted via the Vercel API (204); only `digital-mailroom` (digital-mailroom-theta.vercel.app) and `mailroom-dev` (mailroom-dev.vercel.app) remain. Write-path proof for the human directive ("new DMR issues tracked in the org repository and displayed on the new Vercel deployment"): DMR-007 was created through `POST /api/board` on the served site, landed as a kanban issue in `LLM-Mailroom-Services/Digital-Mailroom` (#11), displayed live, and its lane was corrected via `PATCH /api/board/DMR-007`. Issue #11 closed 2026-09-09.
- **DMR-006** (done 2026-09-09) — **Org-migration reference audit + wiring sweep + CI gate** — DELIVERED (commit `849663a`): `docs/reports/audits/org_migration_audit.md` + `.json` (three-tier inventory: migrate / package-mirror / historical), new `scripts/audit_references.py` (gated patterns `Exios66/mailroom-dev` + `mailroom-dev.vercel.app`, classified allowlist, CHANGELOG-footer rule, `--json`), wired into `.github/workflows/board-governance.yml`; sweep of the issue-template config, CHANGELOG scope+footer, wiki pages (incl. the stale Root-Directory FAQ), README family, LICENSE, `.opencode`, plan doc, SVG caption, dependabot comment, sync propagation message; GitHub About topics (10) + board-link description. Intentionally unchanged (allowlisted): package mirrors/wiring, HUB-era history, the cross-board switcher. Original-repo leg: HUB-067 (`0f06fb4`, archive `a589c49`). Gates at close: audit clean; board check 0/0; labels in sync; release chain OK; taxonomy parity OK. Issue #10 closed 2026-09-09.
- **DMR-004** (done 2026-09-09) — **Push-triggered deploys for the served board — Vercel Git integration** — DELIVERED (commit `4347055`): the Vercel GitHub App was installed on the `LLM-Mailroom-Services` org (human, 2026-09-09) and `vercel git connect` linked project `digital-mailroom` to `LLM-Mailroom-Services/Digital-Mailroom` (production branch `main`, Root Directory `board-site`). **LIVE VERIFIED:** pushing `4347055` produced git-sourced production deployment `digital-mailroom-3fsp2ua9z-lucius-projects-54efe0bb.vercel.app` (state READY, `githubCommitRef: main`, sha `4347055`), and the production alias https://digital-mailroom-theta.vercel.app serves it (`/api/board` 200, repo correct). Manual CLI from the repo root remains the documented fallback (`.vercelignore` ships `board-site/` only). Docs currency: `docs/wiki/Served-Board.md` deploy section + root `AGENTS.md` now state the integration is live. Issue #8 closed 2026-09-09.
- **DMR-001** (done 2026-09-09) — **Standalone board bootstrap — fresh DMR TASKS.md + tooling re-point** — DELIVERED (commit `be75d1e`): fresh DMR board (this file) + full tooling re-point to `LLM-Mailroom-Services/Digital-Mailroom` — `scripts/board_state.py` (DEFAULT_REPO, card/archive/lane/issue regexes, project title), `scripts/github_labels.py`, `.github/labels.json` (note + descriptions), `scripts/release_chain.py`, `scripts/release_notes.py`, `.github/ISSUE_TEMPLATE/hub_card.yml`; 32-label kanban taxonomy seeded in the new repo. Gates at close: `board_state.py check` 0 errors / 0 warnings; `github_labels.py audit` in sync (32 labels); `release_chain.py check` OK; `taxonomy_parity.py` OK. Issue #5 closed 2026-09-09.
- **DMR-002** (done 2026-09-09) — **Served dispatch board for the standalone clone — new Vercel project** — DELIVERED (commit `be75d1e`): new Vercel project `digital-mailroom` (Root Directory `board-site`, Vercel Authentication disabled, `GITHUB_TOKEN` production secret), board-site re-pointed to the new repo + DMR namespace + new CORS origins, repo-root `.vercelignore` limiting CLI deploys to `board-site/`. LIVE VERIFIED: https://digital-mailroom-theta.vercel.app — `GET /api/board` returns `repo: LLM-Mailroom-Services/Digital-Mailroom`, PATCH write-back round-tripped DMR-003 (issue #7, agent from `### Owner`). Auto-deploy mechanism deferred to spawned **DMR-004** (append-only law). Issue #6 closed 2026-09-09.
- **DMR-003** (done 2026-09-09) — **Original mailroom-dev board access — write path + deployment URL** — DELIVERED (commit `be75d1e`): live write path verified — `PATCH /api/board/HUB-064` through https://mailroom-dev.vercel.app returned the updated card (issue #43, priority/high); Vercel Authentication (`ssoProtection`) disabled on project `mailroom-dev` via the API, so raw deployment URLs (e.g. https://mailroom-4sc2d0sxd-lucius-projects-54efe0bb.vercel.app/) and their `/api/board` now return 200 instead of 302 to Vercel login. Issue #7 closed 2026-09-09.
- **DMR-005** (done 2026-09-09) — **Cross-board navigation tabs — DMR ↔ HUB served boards** — DELIVERED (human directive 2026-09-09): a board-switcher (`board-tabs` segmented control) now cross-links both served boards. DMR side (this commit): `board-site/index.html` — `DMR Board` active chip + `HUB Board ↗` link to https://mailroom-dev.vercel.app, DMR title/branding, meta description; deployed via CLI (production alias `digital-mailroom-theta.vercel.app`). HUB side: `Exios66/mailroom-dev` commit `3d57a60` (HUB-066, issue #47) — `HUB Board` active chip + `DMR Board ↗` link to https://digital-mailroom-theta.vercel.app, deployed by that project's Git integration. LIVE VERIFIED: both sites serve the switcher (markup present, `board-tabs`), both cross-links resolve 200, both `/api/board` proxies 200. Issue #9 closed 2026-09-09.
