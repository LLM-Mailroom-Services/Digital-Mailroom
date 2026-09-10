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
| DMR-001 | `in_progress` | **Standalone board bootstrap — fresh DMR TASKS.md + tooling re-point** — restart the task board for this clone with a fresh `DMR-` namespace and re-point every board tool at `LLM-Mailroom-Services/Digital-Mailroom`: fresh TASKS.md (this file); `board_state.py` (DEFAULT_REPO + card/archive/lane/issue regexes + project title); `github_labels.py` + `.github/labels.json`; `release_chain.py` + `release_notes.py`; `hub_card.yml` template; kanban label taxonomy seeded in the new repo; card↔issue law live. | opencode (deepseek-v4-flash-vision-exp) | [#5](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/5) | opened 2026-09-09 by human directive (standalone version under the llm-postal plan; org fallback LLM-Mailroom-Services). Gates at close: `board_state.py check` 0 errors; `github_labels.py audit` in sync; `release_chain.py check` OK. |
| DMR-002 | `in_progress` | **Served dispatch board for the standalone clone — new Vercel project** — new project `digital-mailroom` (team lucius-projects-54efe0bb) serving this repo's `board-site/`: Root Directory `board-site`, Vercel Authentication disabled, `GITHUB_TOKEN` production secret, `gh.js`/`api/board/[id].js`/`index.html` re-pointed to the new repo + DMR namespace + new CORS origins, `.vercelignore` so CLI deploys from the repo root ship only `board-site/`. Open: push-triggered deploys via Vercel Git integration (needs the Vercel GitHub App on LLM-Mailroom-Services) vs a GitHub Actions deploy workflow with `VERCEL_TOKEN`. | opencode (deepseek-v4-flash-vision-exp) | [#6](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/6) | opened 2026-09-09 by human directive. Live at https://digital-mailroom-theta.vercel.app (`GET /api/board` returns this repo; PATCH round-trip verified). Gates at close: JS syntax check; deploy Ready; write-back verified. |
| DMR-003 | `in_progress` | **Original mailroom-dev board access — write path + deployment URL** — verify the predecessor board stays modifiable: live PATCH through https://mailroom-dev.vercel.app/api/board/<id> (project `mailroom-dev` token must carry Issues write), and disable Vercel Authentication (`ssoProtection`) on project `mailroom-dev` so raw deployment URLs (e.g. https://mailroom-4sc2d0sxd-lucius-projects-54efe0bb.vercel.app/) serve publicly instead of 302-ing to Vercel login. | opencode (deepseek-v4-flash-vision-exp) | [#7](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/7) | opened 2026-09-09 by human directive. VERIFIED LIVE: `PATCH /api/board/HUB-064` via the original proxy returned the updated card (issue #43, priority/high); `ssoProtection` cleared via Vercel API — raw deployment URL + `/api/board` now 200. |

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

_No archived cards yet — the DMR board starts fresh (see the Lineage note above)._
