# TASKS.md — the mailroom-hub task board

The single source of truth for cross-agent task state in the monorepo: what is
**assigned**, **in progress**, **needs attention**, and **done**. Every agent
(and human contributor) reads this board before working and keeps it current
while working. It is a WORKING DOCUMENT, not documentation — modify it as work
happens, never delete history (finished cards move to the Archive at the bottom).

Scope: **monorepo-level work** (workspace wiring, cross-package governance,
sub-package sync, docs, releases). Work scoped to a single package is tracked
by that package's own governance (e.g.
`packages/llm-entity-extraction/governance/MESSAGE_BOARD.md`) — this board
holds the hub view and cross-package cards. Simplified counterpart of the
entity board: same laws, fewer steps.

> This board is the stand-in for inter-agent communication. When the external
> agent communication thread lands (HUB-006), it becomes the discussion
> channel and this file remains the lane table + archive of record.

**Machine-readable state (HUB-014):** this board is computationally readable
via `python scripts/board_state.py` — `status` (snapshot, `--json` for
machines), `card HUB-0NN` (one card + its commits), `check` (invariants:
structural contradictions exit 1; hygiene drift is warned), `sync-issues`
(label sync onto synced issues), `project-init`/`project-sync` (GitHub
Projects v2 mirror). The label taxonomy for issues lives in
`.github/labels.json` (`stage/*` = these lanes, `attention/*` = the
needs_attention tags, `type/*`, `priority/*`, `domain/*`, `kanban` marker);
the CI gate `.github/workflows/board-governance.yml` runs `check` + the
label audit on every change to `governance/`, `scripts/`, or `.github/`.

**SESSION NOTE 2026-09-04 — recent commit-message reword (human directive
"ensure all recent git commits contain fully detailed + explanatory commit
messages"):** the last 15 commits (8f7141f1..f830b9a1) were rewritten
message-only (subjects + full bodies now detail every file and change;
authors, dates, trees described below) and force-pushed to origin/main —
the new tip is `3526cccf`. Pre-rewrite SHAs remain reachable on the local
branch `backup/pre-rewrite` (tip `f830b9a1`). If your session's local main
is based on the old SHAs: `git fetch origin && git reset --hard origin/main`
(your uncommitted work, if any, sits in `git status` — stash first, then
pop). Tree contents are byte-identical to the pre-rewrite history — only
commit messages changed.

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
| HUB-006 | `assigned` | **External agent communication thread integration** — the human is standing up a communication channel for agents outside this repo. When live: link it here as the discussion channel, re-point this board's "stand-in" note, and record the handover in Evidence. | Exios66 | [#23](https://github.com/Exios66/mailroom-dev/issues/23) | opened 2026-08-30 by the human directive |
| HUB-054 | `in_progress` | **Terminal-stylized TUI (typed-command REPL) + terminal GH Pages site for The-Mailroom — dataset viewer + constellation repo browser** — human directive 2026-09-04 ("implement a terminal stylized TUI for the 'THE MAILROOM' package ... improving the TUI and hosted github pages site, that provides viewing access to the dataset, as well as a host of navigation, CLI commands, ability to browse the other repositories involved in the LLM Mailroom", owlcot-style reference). Scope in `packages/The-Mailroom`: (1) **TUI rebuilt as a full typed-command REPL** — `mailroom@floor:~$` prompt over a rich Live frame (status header + scrollback + prompt), raw-key line editor (backspace/arrows/Tab completion/Ctrl+L/Ctrl+C), background floor poller pushing AgentLab banners, split into `tui/commands.py` (registry + man pages) / `tui/views.py` (renderers) / `tui/corpus.py` (Hub corpus client over `mailroom_ui/hf_corpus.py`) / `tui/repos.py` (constellation manifest + fail-soft GitHub enrichment); commands: help/man/clear/history/date/echo/uname/neofetch/floor/review/sessions/metrics/inspect/debug/filter + `corpus ls\\|show\\|search\\|stats` + `repos ls\\|open` + `open <name>`; `mailroom_console.py` re-exports every legacy renderer so the existing 24 TUI tests pass unchanged; new CLI flags `--view corpus\\|repos`, `--corpus list\\|show\\|search\\|stats`, `--repos list\\|open`. (2) **Terminal GH Pages site** — new `terminal/` dir (vanilla HTML/CSS/JS, no build step, NO Actions): owlcot-style shell (CRT overlay, amber/green/cyan themes, ghost-text Tab completion, history + prefs in localStorage, boot sequence) published to `gh-pages:/docs/terminal/` by `publish_pages.sh` (pixel console stays the root); commands cover the snapshot traces (`floor/metrics/review/sessions/inspect`) + LIVE corpus browsing via datasets-server (CORS verified for the Pages origin; slim catalog for instant listing/search, per-row `doc_text`+GT fetched live) + `repos` browser of the 10 constellation repos with links. (3) **Data plumbing** — `scripts/export_corpus_catalog.py` writes slim `site/data/corpus.json` (filename/class/subclass/sha/split + row-index offsets) from both configs, `--check` verifies counts + sha integrity. (4) Tests: extended `test_tui.py` (parser/completion/man/corpus-with-mocked-fetch/repos) + new `tests/test_terminal_site.py` (static contracts + catalog export, no network); docs currency: tui/README.md, AGENTS.md milestone, README, CHANGELOG, docs/wiki mirrors. Release: The-Mailroom MINOR 0.3.0 → 0.4.0. Sync upstream via `sync_packages.py push --package The-Mailroom --patch` (HUB-044 law: never during parallel-session in-flight edits). | opencode (GLM-5.3-Flash) 2026-09-04 | [#25](https://github.com/Exios66/mailroom-dev/issues/25) | claimed at directive time; research complete (owlcot reference anatomy, CORS verification for datasets-server, constellation repo list, existing TUI/site/publish contracts); implementation underway. **DELIVERED (evidence `65507b4f`, full suite 334 passed / 2 skipped):** TUI REPL (`tui/commands.py`/`views.py`/`corpus.py`/`repos.py`, `mailroom_console.py` re-exports legacy renderers — existing 24 TUI tests pass unchanged, extended to 37), corpus browser (windowed ls + live per-row doc_text/GT, slim catalog for search/stats, `CorpusClosed` closed state), constellation manifest contract-tested against `scripts/packages_sync.json` + hub copies (`mailroom-dev`/`mailroom-hub`/`LLM-Postal`) + derived graph sites (13 repos, both TUI and site), terminal GH Pages site (`terminal/` — owlcot-family TTY: ghost-text Tab, 1.06s blink, opt-in keypress sound, CRT toggle, animated man pages, ls/cat/cd/whoami/mail, live Hub corpus via datasets-server CORS, snapshot trace desks), `scripts/export_corpus_catalog.py` (slim 2,000-row catalog, live-verified with the human-supplied HF token: 1,792 train/208 test, classes 950/509/350/152/39), `publish_pages.sh` stages `docs/terminal/` + catalog, `hf_corpus.fetch_rows` gains offset/page_sleep/429 backoff; docs currency (CHANGELOG/README/AGENTS.md/architecture+wiki mirror/tui README). **AUDIT PATCHES (evidence `eca54e8e`, 4 files):** `tui/views.py` status_header api_base default `''` for render_tui_shots.py backward compat; `.env.example` added `MAILROOM_REPOS_TTL=3600`; `terminal/js/terminal.js` observatory `../live/` → `../` (GH Pages-safe); `tui/corpus.py` removed unused `field` import. **COORDINATION NOTE (HUB-044 race, recorded):** the parallel HUB-053 sweep (`3c969ce0`/`3fda47e7`, pushed 05:24Z) swept this session's early-state `terminal/` files + `tui/__init__.py` + this board row into its commits — content verified, refined versions land in `65507b4f` on top; no history rewrite. Pending follow-ups (next session): `sync_packages.py push --package The-Mailroom --patch` upstream + re-baselined cursor (HUB-044 law: never while parallel-session edits are in flight), The-Mailroom release 0.3.0 → 0.4.0 (`scripts/release.py --bump minor`), and a live `publish_pages.sh` run so `/terminal/` goes live. **Taxonomy fix (2026-09-04):** `get_all_doc_types()` now filters `status: retired` entries — the sorter schema/classifier VALID_CLASSES/gmail triage prompts now reflect only the 5 primary doc classes + unknown. Commit `4a24b2b3`. **gmail_intake atomic write (2026-09-04):** `_save_state()` now writes to `.tmp` then `replace()` — crash-safe state persistence. Commit `e0c94be3`. |
| HUB-020 | `assigned` | **docclass eval judge prompts still grade against the retired 8-class "EXTENDED primary set"** — discovered during HUB-019 component 6: `packages/llm-entity-extraction/src/prompts_docclass.py` (judge/reviewer/arbiter/boss docclass prompts) and the byte-mirror `packages/The-Mailroom/mailroom_ui/docclass_prompts.py` instruct judges to grade against the extended 8-class list (incl. retired compliance_filing/court_opinion/due_diligence) while the docclass GT is the canonical five (plan §5/§66/§93; docs/v7-taxonomy.md §5 avoid-list). Land in THIS monorepo (human directive: all work in mailroom-dev): add NEW prompt version keys (never mutate versions that have run) with five-class + `unknown` grading language per plan §67, mirror byte-identical into The-Mailroom, leave default selection unchanged until a same-surface A/B validates v1; option-list ↔ schema-enum test parity maintained. Decision open for the human: whether the docclass arm keeps the extended surface as deliberate eval design (KANBAN-033 lineage) or moves to five-class grading. | unclaimed | [#26](https://github.com/Exios66/mailroom-dev/issues/26) | HUB-019 Evidence 2026-09-02; HUB-041 coordination note 2026-09-03: HUB-041 (insurance-subclass alignment) adds NEW sorter/docclass version keys + subclass vocab in this same neighborhood (`src/prompts_docclass.py` + The-Mailroom mirror) but touches ONLY the sorter rule-40 subclass line — the judge/reviewer/arbiter/boss class-set versions this card owns are untouched; mirror edits in The-Mailroom `docclass_prompts.py` are appended keys, byte-identity of existing entries preserved. |
| HUB-036 | `assigned` | **v9 corpus candidate: INSURBIAS insurance-claim source** — spawned at HUB-028 close (append-only law: the deferred item gets a card before the parent closes). HUB-028 evaluated INSURBIAS for the v8 LOB expansion and deferred it as GT-sparse; v9 (or later) should re-evaluate it alongside the P4 expansion priorities (`docs/reports/audits/docclass_expansion_priorities.md` — insurance_workflow is HIGH: adjuster 0%, partial denial_reasons/supporting_documents), license permitting. | unclaimed | [#27](https://github.com/Exios66/mailroom-dev/issues/27) | spawned from HUB-028 close-out 2026-09-02; see HUB-028 archive entry |
| HUB-044 | `assigned` | **sync_packages.py worktree-race hardening (discovered in the HUB-005 third sweep)** — `patch_push` copies the package subtree from the WORKTREE over `git ls-files` while the clean-tree guard (`assert_clean_tree`) runs only ONCE at script start: a file saved by a parallel session mid-run is silently swept into the upstream propagation commit (2026-09-04 incident: an uncommitted `gmail_intake.py` echo-HTML edit went upstream as llm-mailroom `e496f1d2` and had to be reverted at `29249758`). Fix options (either or both): (a) copy committed blobs (`git archive HEAD -- packages/<pkg>` / pkg_tree read) instead of worktree files so uncommitted work can never propagate; (b) re-assert cleanliness immediately before each package's worktree copy (per-package guard, fail that package not the whole run). Docs currency: record the sanctioned all-packages sweep one-liner (`push --all --patch`) + the never-run-with-in-flight-package-edits caveat in the root AGENTS.md sync section (done alongside this card's spawn). | unclaimed | [#28](https://github.com/Exios66/mailroom-dev/issues/28) | spawned from the HUB-005 third-sweep correction 2026-09-04 |
| HUB-042 | `assigned` | **Frozen docclass prompt surfaces still teach the pre-v8 4-token insurance subclass set + docclass-pilot examples lack the v8 LOB strata** — spawned at HUB-041 close (append-only law: discovered-but-undelivered gets a card before the parent closes). HUB-041 fixed the CODE catalogs + added `sorter_mailroom_v0`/`sorter_mailroom_pilot_v0`, but these FROZEN prompt surfaces (never mutated after a run) still enumerate only carrier/pde/outpatient/inpatient: the vision twin (`sorter_docclass_vision_v0/v1` rule 40 short form), the `_PILOT_CONTEXT` injected into the pilot judge/arbiter/boss prompts (HUB-020's neighborhood — its class-set rewrite should absorb the subclass lines), and the `reviewer_docclass_pilot_v0` subclass section. Also `Lucius-Morningstar/docclass-pilot` (48 strata, v5-era `--examples` surface for `run_hf_pilot.py`) carries no property/auto example rows. Follow-up: next docclass iteration (GEPA loop) derives NEW mailroom-named keys covering these surfaces + an A/B of the HUB-041 sorter keys vs v7/pilot-v3 defaults on the v8 corpus (same-surface, seed-matched); examples dataset refresh is a corpus-eda/Hub decision. | unclaimed | [#30](https://github.com/Exios66/mailroom-dev/issues/30) | spawned from HUB-041 close-out 2026-09-03 |
| HUB-061 | `assigned` | **GEPA prompt mutations on docclass v7+v8** — human directive: GEPA prompt mutation training & refinement based on the v7 docclass merged dataset from Huggingface. Scope: initiate new prompt lineage 'mailroom_v' for the 5 doc class + subclass set in `llm-entity-extraction`. Three pieces: (1) GEPA prompt mutation loop — generate mutated prompt variants, evaluate against docclass GT, accept/reject per fitness, iteratively refine. (2) New docclass GT surface — five-class + unknown grading language per plan §67, subclass vocab per HUB-041. (3) Prompt registry update — register `mailroom_v` version keys in `src/prompts_docclass.py` + mirror byte-identical into The-Mailroom. Decision open: keep extended surface as deliberate eval design (KANBAN-033 lineage) or move to five-class grading. | unclaimed | [#7](https://github.com/Exios66/mailroom-dev/issues/7) | opened 2026-09-04 by human audit |
| HUB-062 | `assigned` | **Specialist mutations on v7+v8 of the Mailroom Corpus** — human directive: specialist prompt mutations on the mailroom corpus v7+v8. Scope: initiate mutation chain based on the docclass merged dataset, begin GEPA-style prompt evolution. Three pieces: (1) Mutation framework — structured prompt mutation operators (class/swap/subclass/shift) applied to sorter/docclass prompts. (2) Fitness evaluation — evaluate mutated prompts against corpus GT, track acceptance rate, document decay. (3) Mutation registry — register new prompt version keys with evidence trail, mirror into llm-entity-extraction + The-Mailroom. Blocked: requires corpus GT integrity verification + tokenizer budget alignment. | unclaimed | [#11](https://github.com/Exios66/mailroom-dev/issues/11) | opened 2026-09-04 by human audit |
| HUB-064 | `assigned` | **Gmail triage team → production-ready (edge cases, debug, config)** — spawned at HUB-043 close (append-only law). HUB-043 (filename-only dedup) is archived as operational on `main`; remaining work is the edge cases, debugging harness, and configuration needed before the Gmail triage lane (`llmmailroom@gmail.com`, free OpenRouter swarm, watcher-embedded poller) is production-ready. Scope (non-exhaustive — claim and refine): (1) live re-send / provenance proof — operator runbook + automated/hermetic proof that same-filename / new-Message-ID claims (HUB-043 scenario) without ad-hoc CoS credentials; (2) config & secrets — documented production `.env` matrix (allowlist roster, free-only guardrail, triage on/off, echoes/reactions, poll interval) + CI secret-presence checks without leaking values; (3) edge cases — multi-attachment pathway, capability handoffs (scan/image/over-budget), allowlist rejects, echo/reaction failure modes, watcher.lock + embed-watcher conflicts, producer Space / durable `/data`; (4) debugging — triage I/O capture discovery, smoke `--real` safety gates, Langfuse/Phoenix checklist for `gmail-triage` traces, ops lamp (`checks.gmail_intake`) alerting; (5) corpus samples — sanctioned mailroom-corpus document-type fixtures for Gmail pilot fires. Out of scope: reopening HUB-043 unless a regression is proven. | unclaimed | [#43](https://github.com/Exios66/mailroom-dev/issues/43) | spawned at HUB-043 close (issue opened 2026-09-09); board card backfilled by the 2026-09-09 reconciliation — the card↔issue law requires every kanban issue to carry a board card |


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
- **Commit discipline.** Reference cards in commits: `HUB-00N: <summary>` or
  `HUB-00N claimed/reopened` in the message body. **Stage targeted paths only
  (HUB-029):** `git add <explicit paths>` for exactly your card's files —
  never `git add .` / `-A` / a bare directory. This is a shared checkout:
  before every commit, `git status --porcelain` and unstage anything you
  don't own (two documented sweeps — HUB-024, HUB-027 — landed other agents'
  in-flight files under the wrong message).

## Issues vs board — the card↔issue law

Every board card has a **synced GitHub issue** in the repo where the work
lands (this monorepo for hub scope, the package repo for package scope) —
one card = one issue, opened from the *Board card (HUB-0NN)* template
(`.github/ISSUE_TEMPLATE/hub_card.yml`). Why this is now a law: the served
board at https://mailroom-dev.vercel.app reads `kanban`-labeled issues, so
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

- **HUB-065** (done 2026-09-09) — **Served board — card text renders as raw escaped markdown** — human directive 2026-09-09 ("ensure that our text is properly formatted in display on the board cards themselves"). **DELIVERED (commit `2cadbb0`):** `board-site/index.html` card `desc`/`evidence` are now rendered through `mdToHtml` — new self-hosted `board-site/lib/md.js` (escape-first; only whitelisted tags p/strong/em/del/code/pre/a/ul/ol/li/blockquote/h1-h4/hr; http(s)-only hrefs, quoted/control chars stripped, javascript:/data: URLs drop to plain link text; zero-dependency — CSP `script-src 'self'` blocks CDNs) — plus a '⋯ more / ⋯ less' expand toggle beating the old 2-line clamp, card click/keyboard guards so the toggle never opens the edit modal, and `.card-md` typography replacing the mono nowrap evidence style. **LIVE VERIFIED (deploy `mailroom-5hnbxerry` — the git-integration build of this commit, Ready 9s, served under the production alias):** `GET /lib/md.js` 200, page includes mdToHtml, `GET /api/board` 200 (no-store + hardened headers). Node smoke VM PASS (bold/code/list/https-link render; `javascript:` URL + `<script>` input neutralized); full inline-script syntax PASS. Board gates at close: board_state.py check 0 errors; the human-pinned previous build was NOT touched — the production alias follows the verified git build (`rootDirectory=board-site` stays set so every push builds the board site). Evidence: `2cadbb0` (renderer + UI + CSS), deploy `5hnbxerry`; issue #46 closed in this commit.
- **HUB-063** (done 2026-09-09) — **Archive Completed-Entries button on the served board — issue-only, resolved without a board card** — board** — opened from the served site itself (issue #40, "Synced from the Mailroom Dispatch Board"): requested an archive action for done cards with automatic routing. The requested functionality was delivered by the served-board UI work (HUB-055 `f813734` + HUB-060 `71dca40`): `board-site/index.html` ships the full archive UI (archiveCard/archiveOpen + auto-archive, drag/move/edit + archive, filters, stats) and AGENTS.md documents it. Issue #40 closed 2026-09-09; recorded in the Archive by the 2026-09-09 board reconciliation (orphan kanban issue — no board card ever existed for it).
- **HUB-043** (done 2026-09-09) — **Watcher filename-only dedup silently drops re-sent Gmail documents (live pilot bug)** — full evidence in the pre-archive card record (git history). Intake-provenance-aware dedup landed (`8f50cc26`: a file's `/upload` sidecar message-id must MATCH the terminal manifest's intake provenance to count as processed — mismatched provenance is a NEW document that must process), watcher restarted on the current code with verified clean sweeps, FULL llm-mailroom suite 890 passed / 36 skipped / 0 errors. Follow-up work (edge cases, debugging harness, prod config) spawned as **HUB-064**. Issue #29 closed 2026-09-09. Archived 2026-09-09 by the board reconciliation (`pull-issues` imported the issue-side done lane; the delta landed upstream in the HUB-005 third sweep, tip `76bc50b6`).
- **HUB-039** (done 2026-09-07) — **Gmail free-triage team — production-pilot readiness sweep** — full evidence in the pre-archive card record (git history). Single-doc Gmail triage lane brought production-pilot READY: `gmail_triage` prompt registration, free-only guardrail (`MAILROOM_LLM_FREE_ONLY`, commit `1f8f6387`), 4-sender allowlist, live watcher, free-model swarm failover (taxonomy `free_model_swarm` + `llm/retry.py` rotation incl. capability-400 detection `d14b049b`), full triage I/O debug capture (`fa7d0be8`), robust JSON recovery, conftest relations-thread hermetic (FULL suite 890 passed / 36 skipped / 0 errors), real end-to-end green path (glm-5.2 429 → ling capability-400 → nemotron-3.5-lightning served; full entity extraction + `triage_*` audits + archived echo). Issue #24 closed 2026-09-07. Archived 2026-09-09 by the board reconciliation (`pull-issues` imported the issue-side done lane).
- **HUB-060** (done 2026-09-06) — **Served Vercel board — production-ready audit + UI improvements + accurate agents/evidence/description** — human directive 2026-09-06. **DELIVERED (commits `71dca40`, `8ef6db4`, `e6a3ebb`):** (1) **AGENTS now reflect the actual agent/persona/harness, not the GitHub profile** — root cause: the board read issue assignees (repo owner → every card showed 'Exios66'). Fixed: agents ride a new `### Owner` body section (synced from the TASKS.md Owner column); `agentsFromIssue` reads it (assignee fallback only when absent); POST/PATCH write it; GitHub assignees are never set to agent names (non-collaborators 422'd). (2) **Evidence trace + descriptions now accurate** — root cause: the old body-section writer glued headings (`### Lane\ndone### Task`) and dropped sections. Rebuilt parseSections/setBodySection glue-proof (line-based, recovers corrupted bodies); `board_state.py sync-issues` now pushes `### Owner`/`### Task`/`### Evidence plan`/`### Card ID`/`### Lane` from TASKS.md into every synced issue (--apply backfilled all 8 open + repaired corrupted #22/#34). (3) **UI/production-readiness** — freshness badge + 30s auto-refresh + tab-refocus refresh (always reads most-recent state), loading + offline states (live-only, never a snapshot), CORS hardened to the served origin (no third-party browser PATCH), CSP/nosniff/X-Frame-Options/Referrer/Permissions-Policy headers. **LIVE VERIFIED (alias mailroom-dev.vercel.app):** all cards show real agents + populated evidence/descriptions; PATCH write-back 200 (agents update via `### Owner`); security headers present; sync-issues dry = everything current. Docs updated (AGENTS.md + wiki Served-Board.md). Evidence: `71dca40` (lib/gh.js + api + index + vercel.json + board_state.py + backfill), `8ef6db4` (Owner section, drop assignees), `e6a3ebb` (docs + wiki); issue #35 closed in this commit. Gates: board_state.py check --with-issues 0 errors (2 pre-existing unclaimed warnings HUB-042/HUB-044); release_chain.py check OK; wiki in sync.
- **HUB-059** (done 2026-09-06) — **Connect the served Vercel board to the live board — live-only, no snapshot** — human directive 2026-09-06 ("connect the Vercel to the live board, not a snapshot"). **DELIVERED (commit `c1eab32`):** the frontend's hardcoded snapshot fallback is GONE — `board-site/index.html` deleted the ~660-line `getRealData()` baked-in copy of TASKS.md cards (incl. a fake HUB-055 card) that was injected when the `/api/board` proxy was unreachable ("● OFFLINE · snapshot"); `refreshBoard()` now drops to a LIVE-ONLY offline state (cards = [], `offlineError` set, badge "● OFFLINE · no live connection") and `renderBoard()` shows an `.offline-banner` (role=alert) with the proxy error — never fake cards. Board = the GitHub issues, nothing else. **REDEPLOYED + VERIFIED live (deploy `5tgrhjkg5`, pinned alias):** `GET /api/board` 200 → 13 live kanban cards (incl. this card's issue #34 picked up automatically — issue-backed); live index.html has zero `getRealData`; PATCH write-back round-tripped issue #34 (same-lane no-op). **ALIAS INCIDENT handled (2026-09-06):** a parallel session's `--prod` deploy (`2i7jbhpxl`) hijacked the shared `mailroom-dev.vercel.app` alias and the live site 404'd on every route; recovered by `vercel alias set` back onto the verified deployment. Docs currency: Served-Board.md redeploy section now mandates pinning the production alias after every deploy. (Unassigned triage lane + CORS + pagination + search-API lookup had already landed in `f813734` by a parallel session.) Evidence: `c1eab32` (snapshot removal + card claim); issue #34 closed in this commit. Gates: board_state.py check --with-issues 0 errors (2 pre-existing unclaimed warnings HUB-042/HUB-044).
- **HUB-058** (done 2026-09-06) — **Full wiki sync + Vercel served-board documentation + governance reconciliation** — human directive 2026-09-06. **DELIVERED (commit `a4645a1`):** (1) NEW wiki page `docs/wiki/Served-Board.md` — full operational doc for the live dispatch board (https://mailroom-dev.vercel.app): `board-site/` layout, the issue→card GET read contract + PATCH write-back contract (lane swap + dated Board-lane-move comment, priority swap, body rewrite, assignees, archive=close/restore=reopen, `X-Mailroom-Actor`), config/env secrets (Vercel production `GITHUB_TOKEN`/`MAILROOM_GH_TOKEN`, `MAILROOM_GITHUB_REPO` override, never-commit), the redeploy workflow + smoke checks, and the `pull-issues`/`sync-issues` reconciliation loop. (2) Stale wiki pages refreshed: Home (corpus v8/2,000 rows, 6 built + 4 virtual, hub v0.4.0, served-board row), Architecture (surfaces + layout incl. `board-site/` + terminal console), Releases (deploy surfaces + actual `--notes-file` cut practice), FAQ (v8/2,000 canonical + 3 new served-board Q&As), Getting-Started (live-board pointer), Sub-Package-Sync (sweep one-liner + HUB-044 caveat), _Sidebar + Board-Governance cross-refs. (3) Governance law reconciled — TASKS.md §"Issues vs board" renamed the card↔issue law: board-only carve-out RETIRED; every card carries a `kanban` synced issue (or it won't appear on the served board), lane moves mirrored both ways, post-served-site-edit `pull-issues --apply` obligation, issue closed in the same commit that archives the card. AGENTS.md served-board section cross-refs the wiki page + CHANGELOG [Unreleased] note. **WIKI LIVE:** `sync-wiki.sh` pushed all 13 pages to the GitHub wiki; `sync-wiki.sh --check` → "wiki in sync"; Served-Board page verified HTTP 200 on the live wiki. Evidence: `a4645a1` (docs + governance); issue #33 closed in this commit. Gates at close: board_state.py check --with-issues 0 errors (2 pre-existing unclaimed warnings HUB-042/HUB-044); release_chain.py check OK.
- **HUB-057** (done 2026-09-05) — **Cut official hub releases v0.3.0 + v0.4.0 with full release notes** — human directive 2026-09-05. The hub had accumulated 84 commits of real work since v0.2.0 with NO hub release. **v0.3.0 CUT** (`67eb0d0`, GitHub Release https://github.com/Exios66/mailroom-dev/releases/tag/v0.3.0): triage/relations/corpus-samples epoch — HUB-040 relations agent + hash-chained ledger + KGs, HUB-041 insurance-subclass alignment + taxonomy-parity layer, HUB-039 free-swarm failover + capability-400 rotation + triage I/O debug capture, gmail echo depth + atomic state writes, HUB-043 intake-provenance dedup, HUB-046 claims-data-eda PDF samples, HUB-047 Enron Markdown samples, HUB-048 triage key-entity extraction, HUB-049 unknown-class fallback + review parking, HUB-050 watcher status channel + external watchdog, HUB-051 relations production-readiness, HUB-052 relations mode toggle, HUB-053 HF loader + Gmail pilot notebook, HUB-005 third propagate sweep + ingest/intake consolidation tail + commit-message doctrine, retired-class doc-type filtering. **v0.4.0 CUT** (`eda8759`, GitHub Release https://github.com/Exios66/mailroom-dev/releases/tag/v0.4.0): visualizer/dispatch-board epoch — HUB-054 terminal-stylized TUI + terminal GH Pages site + export_corpus_catalog, HUB-055 served Kanban Dispatch Board (board-site/ Vercel path + board↔issue seeding + pull-issues reverse-sync), HUB-056 stray-tag retarget. Both via `release_chain.py cut --apply --tag`: `## [0.3.0]`/`## [0.4.0]` sections authored from commit+card evidence, pyproject 0.2.0→0.3.0→0.4.0, annotated `mailroom-hub vX.Y.Z` tags, GitHub Releases cut from each section. Chain green at every step and at close (`release_chain.py check`: OK, 0 warnings; sections 0.4.0>0.3.0>0.2.0>0.1.0; footer compare+release links chained). Evidence: commits `e446df6` (v0.3.0 changelog + card), `67eb0d0` (v0.3.0 cut), `09db9c9` (v0.4.0 changelog), `eda8759` (v0.4.0 cut); issue #32 closed in this commit.
- **HUB-055** (done 2026-09-06) — **Wire the Kanban Dispatch Board into a served path (Vercel, issues-backed, auto-updating + editable)** … **LIVE 2026-09-06:** deployed production to Vercel — https://mailroom-dev.vercel.app (project mailroom-dev, org lucius-projects-54efe0bb; Root Directory cleared; board-site/ deploy root with its own vercel.json). Served END-TO-END VERIFIED: `GET /api/board` returns 11 live kanban cards normalised from GitHub issues (labels=kanban, page 100); the PATCH write-back round-tripped a real lane move (HUB-055: in-progress -> needs-attention, stage/* label swapped on issue #22, then read back at needs-attention) — token proxy works in production. `GITHUB_TOKEN` stored as a Vercel Production secret (scoped gh keyring token, repo scope, issues r/w). Env secret added via `vercel env add GITHUB_TOKEN production`; `.env.local`/`.vercel/` created at link time and gitignored; board-site/.gitignore kept. Documents updated alongside the close (AGENTS.md "Served Kanban board" section now cites the live URL, wiki Board-Governance.md mirror, CHANGELOG Unreleased). Residual: seeded issues #23–#31 remain open as their own cards.
- **HUB-056** (done 2026-09-05) — **Hub release chain red (pre-existing v0.4.0 tag break) — `release_chain.py check` fails on origin/main** — human directive 2026-09-05 (per the board's option (b)): RETARGET THE TAG = remove the stray annotated `v0.4.0` hub tag. Root cause confirmed: `v0.4.0` pointed at `fc55be3` (The-Mailroom's own package-release commit, 'HUB-054: release 0.3.0 → 0.4.0') while the hub `pyproject.toml` was (and is) `0.2.0` — the HUB-054 session cut The-Mailroom's 0.4.0 and accidentally stamped the hub with the same version; no `## [0.4.0]` CHANGELOG section and no GitHub Release for it ever existed (only v0.1.0/v0.2.0 releases). Fix: local `git tag -d v0.4.0` + remote `git push origin :refs/tags/v0.4.0`; chain now resolves to the correct `v0.2.0` — `release_chain.py check` annotated-tag-message-convention errors AND warnings all clear (0 errors, 0 warnings), `release_chain.py status` shows newest tag v0.2.0 == changelog [0.2.0] == pyproject 0.2.0. CHANGELOG [Unreleased] Fixed entry added documenting the retarget. In-tree 'v0.4.0' references (docs/wiki llm-mailroom/sandbox versions) are upstream package versions, not the hub tag. Evidence: this commit (board archive + changelog), the tag deletion pushed to origin in the same session; issue #31 closed.
- **HUB-053** (done 2026-09-04) — **Repo-wide mailroom-corpus HF dataset loader + corpus-sourced Gmail pilot notebook** — human directives 2026-09-04 ("ensure we have an appropriate huggingface dataset loader available within the repo, setting up the streamlining repository wide of any HF dataset loading of the mailroom corpus"; "set up a script to launch a pilot 1 doc fire thru gmail ... make it a fully expertly designed jupyter notebook"; "the data should derive from the mailroom-corpus huggingface dataset"). Landed in `packages/llm-mailroom` (commit `3c969ce0`): (1) **`pipeline/hf_corpus_loader.py`** — the canonical loading path for the mailroom-corpus family (labels from the `ground_truth` config joined with `doc_text` from the blind `default` config on `filename`): /parquet ladder + on-disk cache + the load-time integrity proof (`content_sha256` == sha256(`doc_text`), verified 1792/1792 live), `/rows` pagination fallback, literal-slash single-repo sha provenance (`?author=&search=&expand[]=sha` fallback), `datasets` lib optional (never a dependency); lucius (HF-SME subagent) verified the viewer/hub API facts (incl. `/filter` broken server-side, correct `"col"='value'` grammar documented). (2) **`notebooks/gmail_pilot_lab.py` + `notebooks/14_gmail_pilot.ipynb`** — the expertly designed pilot loop: config → preflight (heartbeat/channel/allowlist/corpus) → corpus pick (committed integrity-verified snapshot `notebooks/fixtures/gmail_pilot_corpus_snapshot.json` offline; live Hub behind `NB-OPT-IN-NETWORK`) → FIRE interlock (mock inbox drop with the poller's exact sidecar | real SMTP with a fail-fast allowlist guard) → watch (incremental watcher-log tail + terminal-manifest wait) → evidence (catalog row, audit hash-chain, relations edges, echo) → corpus ground-truth comparison (class/subclass/stage/insurance fields) → `data/pilot_runs/<stamp>_<token>/report.{json,md}`. Guard-suite integration (PLAN.md roster, PLANNED, lab-module scan tuple). (3) **Unit pins** `test_gmail_pilot_lab.py` (9: snapshot integrity, loader join/integrity, selection filters, email MIME shape, poller-exact mock sidecar, WatchLog offsets, GT checks, report writer). **LIVE PILOT FIRES (real system):** (a) REAL Gmail round trip — corpus doc `carrier:887013387879564.txt` (CMS Medicare Part B notice, 1044 chars) SMTP-sent to the agent mailbox, swept by the IMAP poller, free triage lane archived in **65s**; the first fire exposed the allowlist gap (mailbox not in `MAILROOM_GMAIL_ALLOWED_SENDERS` → `gmail_message_sender_rejected`) — fixed by allowlisting the agent mailbox in `.env` + a fail-fast send guard + a preflight check; watcher restarted to load the new allowlist. (b) Post-fix mock fire — archived in **30s**: `insurance_claim` @ 0.95, extraction matching GT (claim_number 887013387879564, policy_number B81C39C31DF18BEB, insurer CMS Medicare, insured_party SANCHEZ DAVID, coverage APPROVED), audit chain OK (triage_ingested/classified/archived/relations_linked), catalog row, **9 relations edges**, verdict FAIL 7/10 — the honest corpus-GT surface: the FIRST real fire classified the same document `correspondence` @ 0.95 (free-swarm model variance; the GT comparison caught it). Kernel-loop bridge (`_run_coro` thread pattern) fixed the evidence legs inside Jupyter. Gates: FULL llm-mailroom **983 passed / 36 skipped / 0 errors** (incl. notebook guard suite 79), gmail pilot suite 9 passed. Docs currency: AGENTS.md commands + HF-loading bullet; notebooks/PLAN.md roster. Watcher running the worktree incl. the new code (PID 37940). **COORDINATION NOTE (shared-checkout incident):** this commit also swept the parallel The-Mailroom TUI session's 10 STAGED files (`tui/`, `terminal/`, `export_corpus_catalog.py` etc.) — the `git add`+`git commit` ran without unstaging files the parallel session owned (HUB-024/027 law). Content is intact: the committed snapshot is the session's own staged versions (a consistent checkpoint), and their further edits remain uncommitted in the worktree (git status M) — they can commit the remainder on top; nothing was lost or modified. |
- **HUB-052** (done 2026-09-04) — **Relations clerk mode toggle — simple CLI + API live/pilot switching** — human directive 2026-09-04 ("ensure the knobs to configure the toggle of live vs pilot mode are simple and easily adjusted through cli or something even smoother"). Landed in `packages/llm-mailroom` (evidence: `78239433`): `pipeline/relations_mode.py` — the toggle core + CLI (`python -m pipeline.relations_mode status|pilot|live [--model <name>] [--restart-watcher]`). `status` prints the effective posture + every knob (mode, judge model + free/paid, `MAILROOM_LLM_FREE_ONLY` guardrail, kill-switches, thresholds with code-default merge, ledger chain health, edge count, last sweep). `pilot`/`live` edit taxonomy.yaml SURGICALLY (section-tracked line rewrite — `relations.llm` under the top-level block, `agents.relations.model` under agents; comments and every other line preserved byte-for-byte; missing keys inserted after their section header; atomic temp+replace), remove a stale `MAILROOM_RELATIONS_LLM` kill-switch from `.env` that contradicts the requested mode, and clear the in-process config caches (`pipeline/config.py:clear_config_cache` — load_config lru + bins module copy) so the current process honors the flip immediately. Model validation: taxonomy `cost_models` entry or `:free` suffix; a PAID model under the free-only guardrail is refused with an actionable message (the guardrail is a pipeline-wide .env decision, never flipped by the toggle). `--restart-watcher` = the graceful standalone relaunch (watchdog stopped first — no false 🔴 — then watcher, then both back with PYTHONPATH=src, same log files; waits for `watcher_starting` + worker_id + `relations_sweeper_started`). **The smoother path:** authenticated `GET/POST /api/relations/mode` on the FastAPI — the POST applies + clears the API process's caches, so the EMBEDDED watcher honors the flip with NO restart (`restart_required: false`; standalone watchers read the new taxonomy on their next restart). Gates: FULL llm-mailroom suite **969 passed / 36 skipped / 0 errors**, gmail mock smoke PASS, 20 new hermetic tests (readout/editor/refusals/kill-switch removal/CLI/API+auth). **LIVE VERIFICATION (real taxonomy):** CLI round trip `live` → `llm: true` → `pilot` → `llm: false` with the file byte-identical after (zero diff); live `status` reads the real system (PILOT, guardrail ON, ledger OK 209 entries, 7 edges). Docs currency: AGENTS.md commands, docs/api.md endpoints section, docs/agents.md §13, CHANGELOG. |
- **HUB-051** (done 2026-09-04) — **Relations clerk (HUB-040) production-readiness completion — the research/review clerk was archived code-complete but a NO-OP on the live system** — human directive 2026-09-04 ("ensure the review clerk is fully finished & built out — fully operational, production tested, ready for the full LLM-mailroom pipeline"). The audit found four gaps; all closed in `packages/llm-mailroom` (evidence: `dcaf9ae7`): (G1) the Gmail triage lane NEVER wrote the `documents` catalog row — audits/archives/echoes/dispatched the relations scan but no `_catalog_upsert`, so `scan_document` skipped every triage doc `not_in_catalog` and the sweeper scanned nothing (live proof: 4 `triage_archived` docs on disk, ZERO archived catalog rows, 65 sweeps `scanned: 0`, 0 edges). Fixed: `_triage_catalog_upsert` on BOTH triage terminal paths (incl. the HUB-049 LLM-unavailable review park, which now also dispatches the scan) + `write_document_record` persists `file_sha256` (pre-existing gap — no caller ever wrote it). (G2) the LLM judgment pass was DEAD CODE — `RelationsAgent.judge` never called, `llm_pass_enabled()`/`top_k_llm_candidates` unused; even flipping `relations.llm: true` did nothing. Fixed: `_llm_judgment_edges` — ambiguous-band near-misses captured in the signal loop, top-K ranked, judged, `llm_confidence_gate` 0.55, `llm_asserted` edges on the same upsert+ledger path, output re-validated against the scanner's own proposed pairs (defense-in-depth). (G3) the documented `python -m pipeline.relations_scan` CLI crashed (`ModuleNotFoundError` — module never created). Fixed: `pipeline/relations_scan.py`. (G4) live catalog hygiene: 7 stale `processing` rows reconciled (4 archived rows backfilled from the archive sidecars — stage/doc_type/subclass/conf/sha256/extraction; 3 dead rows → failed + escalation_reason). **BONUS PRODUCTION BUG:** the embedding cosine signal NEVER worked outside the test seam — the dojo's public `get_embedding_model()` returns the model NAME string, so `model.encode(...)` was a TypeError on every real run (`relations_embed_failed`); `_embed` now drives the dojo's shared `_EmbeddingMatcher` singleton (local SentenceTransformer + remote fallback, 90s-bounded, fail-soft, taxonomy wiring via the shim's import side effect). Tests: +6 relations (wiring/gate/off-by-default/fail-soft/CLI/embedder real-path+degrade) +2 gmail_triage (catalog row + fail-soft) + the mock-smoke `catalog:` check. Gates: llm-mailroom FULL **949 passed / 36 skipped / 0 errors**, gmail mock smoke **11/11 PASS**. **LIVE PRODUCTION VERIFICATION (2026-09-04, real DB):** 4 archived docs scanned → 7 edges (6 same_matter + 1 party_overlap — shared insurer CMS between the outpatient claims), 1536-dim embeddings stored, ledger chain **OK (189 entries)**, knowledge graphs rendered (matter/global JSON+GraphML+HTML+PNG), advisory RELATED context block live. **REAL LLM JUDGMENT PASS PROOF** (`relations.llm: true` temporarily): the judge fired through the full free-swarm failover (glm-5.2 429 → ling capability-400 → `nvidia/nemotron-3.5-lightning:free` served, 29s) and returned 0.30–0.35 confidence on the genuinely-borderline contract↔claim pairs — correctly refused by the 0.55 gate (the model's conservative read = "coincidence is worse than silence"); positive path proven by the mock wiring test. Taxonomy restored to `relations.llm: false` (pilot posture; the flip is a production config decision — free-only guardrail compatible). **Watcher RESTARTED on the new code** (worker `9476cbfd`, 2026-09-04 07:40Z): `gmail_poller_started` (60s), `relations_sweeper_started` (300s — new relations code), `schema_ready`, 🟢 status email sent. COORDINATION NOTE: a parallel session co-worked this card — their uncommitted `agents/relations.py` judgment debug I/O capture, `recover_processing.py --catalog` row reconciliation, and `test_watcher_reconcile.py` are NOT in `dcaf9ae7` (never commit what you don't own — HUB-029 law); they land under their own commit, then the sweep. Board check 0 errors at close. **DELTA LANDED (same day):** `004fb4b2` — judgment debug I/O capture (LIVE-VERIFIED through the real free-swarm failover: glm 429 → ling capability-400 → nemotron served → `relations_llm_io candidates=1 judgments=1`), `recover_processing.py --catalog` G4 tooling (live dry-run: zero stale rows), 2 reconcile tests, AGENTS.md bullet extensions; watcher restarted on the tip post-commit. |
- **HUB-050** (done 2026-09-04) — **Watcher status notifications — 🔴 down alerts + 🟢 relaunch confirmations to the human's email** — human directive 2026-09-04 ("ensure a concise and stylized alert is sent to my email axios337@gmail.com when the watcher goes down, and send me a confirmation when it relaunches, ensuring I receive timely accurate status reports of the watcher") + anti-spam follow-up ("the status email should also not be firing excessively, only in emergency scenarios, and when the watcher is started or back up and running after a crash" — the periodic 📊 digest was REMOVED at directive time). Landed: `pipeline/status_notify.py` (exactly three kinds — running 🟢 / down 🔴 / still_down 🟠; HTML+text renderers; `set_status_smtp_factory` test seam reusing the gmail channel config; `MAILROOM_WATCHER_STATUS=0` kill-switch; `MAILROOM_STATUS_EMAIL` recipient knob default axios337@gmail.com; every send fails soft), `pipeline/watchdog.py` (EXTERNAL watchdog `python -m pipeline.watchdog` because a dead process cannot email anyone; pure `evaluate()` transition core: pid-dead or missing heartbeat → immediate 🔴, pid-alive-but-stale (hung/asleep) → 2 consecutive stale checks, 🟠 reminders ONLY while an outage is active (60 min default); `MAILROOM_WATCHDOG=0` kill-switch + timing knobs), `bins.py:touch_watcher_heartbeat(extra)` (enriched atomic temp+replace heartbeat: pid/host/started_at/git-sha), watcher hooks (enriched first + rescan heartbeats; 🟢 startup/relaunch notice as a fail-soft daemon thread), conftest hermetics (both channels off in tests). **LIVE DRILL 2026-09-04 06:47–06:48Z (real emails):** killed the live watcher → `status_email_sent kind=down to=axios337@gmail.com` at 06:47:52 (pid_alive=False, heartbeat_age 30.5s) → relaunched → `kind=running` at 06:48:24; multiple 🟢 startup confirmations also fired on the day's restarts. Anti-spam posture verified — no periodic healthy-status emails exist. Tests: 13-case `test_status_notify.py` (renderers, MIME-parsed sends, kill switches, no-creds skip, soft failure, heartbeat roundtrip, full watchdog transition ladder incl. recovery reset + start() hook) — status/triage/intake/dedup/reconcile/embedded/relations/specialists suites 145 passed; gmail mock smoke 10/10. Docs: package AGENTS.md status-channel bullet. Evidence: monorepo `a2ded8f1` (implementation), `b2d0059b` (final docs + evidence).
- **HUB-049** (done 2026-09-04) — **Gmail triage lane: unknown-class extraction fallback + confidence gate + transient-LLM review parking** — spawned at HUB-048 close (discovered-but-undelivered law), implemented on human directive "ensure all doc types will be appropriately handled by the free agent intake, classification, and entity extraction swarm". Three pieces in the single-document triage lane: (1) `gmail_triage.py` — `unknown` primary class no longer yields empty extraction: `_unknown_class_extraction()` merges model-provided correspondence-shaped keys (model wins) with `_deterministic_header_extraction()` (regex `From:/To:/Date:/Subject:` lines + Enron `| From | x |` markdown-table forms; grounded values only, never invented); `validate_triage(result, doc_text=None)` routes unknown → fallback, non-unknown → schema clamp. (2) `watcher.py _run_triage_lane` confidence gate: `unknown` class or confidence < taxonomy `low` (0.88) parks the doc in REVIEW (`escalation_reason` `triage_unknown_class` / `triage_low_confidence`, `triage_reviewed` audit, ⏸ echo) instead of archiving an untrusted read. (3) Transient-read hardening after a LIVE failure (user-reported 2026-09-04: re-sent outpatient PDF → `run_aborted` ❌ failed via `openai.RateLimitError` 429 `upstream_provider_shared_pool` after 5 retries — the shared free pool was saturated, partly by this session's own parallel verification script hammering GLM-5.2, which was killed): `agent.triage()` exceptions now park the doc in REVIEW with `triage_llm_unavailable: <type>: <msg>` — the failed bin stays for real handling errors. Verification: triage suite 49 passed (unknown fallback incl. the Enron markdown-table form + merge/never-invent laws; low-confidence + unknown-class review routes w/ audit+echo; LLM-failure→review replacing the old failed-bin assertion; `compliance_filing` added to the all-doc-types lane parametrize), collateral 83 passed, mock gmail smoke 10/10. Real-model evidence: `z-ai/glm-5.2:free` triage on the real Enron email (allen-p #1003) extracted a full grounded entity set (sender/recipient/communication_type/date/urgency/intent/subject_matter/keywords); lighter free model `inclusionai/ling-3.0-flash-fin:free` classified only 14/24 Enron samples (10 PARSE_ERRORs on short docs — GLM-5.2 remains the lane's tool; ling fits low-stakes classification only). Ops note recorded: real-model verification scripts must never run while the live watcher serves uploads. Evidence: monorepo `679cdea3` (payload — rode the human's own "Free Agent Intake Swarm Calibration" commit, which swept this session's three in-flight files), `95cfe1e9` (board close; claim + close same session, single-owner).
- **HUB-048** (done 2026-09-04) — **Gmail triage agent: key/concise entity extraction for ALL document types via the EXISTING EXTRACTION_SCHEMAS (esp. short correspondence — Enron samples)** — human directive 2026-09-04 ("ensure the enron examples will be properly handled by the triage gmail agent swarm… key, concise entity extraction on all document types, ESPECIALLY THE SHORT EXAMPLES LIKE CORRESPONDANCE" + "It should be the extraction schema that we already have implemented"). `GmailTriageAgent.triage()` now returns BOTH the classification read AND a per-class `extraction` object driven by `schemas.documents.EXTRACTION_SCHEMAS` (the same Pydantic models the paid specialists use): `extraction_schema_for()` derives the field map per class (normalizing `float|None`/`anyOf` typing to real JSON `number`), the prompt instructs the free model (with explicit short-document emphasis), and `_clamp_extraction` drops cross-class fields/caps lists(10)/strings(200). Rides `intake_meta["triage"]["extraction"]` → manifest → echo's "EXTRACTED KEY ENTITIES (triage)" block (`pipeline/gmail_intake.py`). Advisory + fail-soft preserved; `unknown` class yields empty extraction (spawned **HUB-049**). Verification: 10 new tests in `test_gmail_triage.py` (incl. real Enron short-email regression — the 542-byte allen-p/_sent_mail #193), triage suite 41 passed, collateral 83 passed, mock gmail smoke 10/10, FULL llm-mailroom suite 900 passed / 36 skipped / 0 errors; ad-hoc run over the 24 real Enron Markdown samples confirmed extraction fires on short correspondence. Propagated upstream `Exios66/llm-mailroom` (9 files → tip `c09137b0`, cursor re-baselined). Docs currency: package AGENTS.md triage bullet. Evidence: monorepo `76f6c531` (implementation), `c5560dfc` (cursor).
- **HUB-047** (done 2026-09-04) — **Enron-Evaluation-Environment: cleanly formatted Markdown samples of the Enron email correspondence (human directive 2026-09-04)** — new regenerable `scripts/build_samples.py` walks the maildir via the index walker (`build_corpus_index.iter_messages`/`parse_message` — no full index build needed), labels each message with the SHARED 10-key labeler (`label_correspondence`), and renders a taxonomy-stratified, seeded, bounded selection into `samples/`: 16 samples + generated README index (2 per subclass key; reservoir 120 per stratum, walk cap 517,401 = full corpus, body cap 6000, seed 20150507 = the tarball date). Clean formatting law: H1 subject, header metadata table (from/to/cc/date/message-id), maildir provenance (custodian/folder/thread), subclass label + labeler evidence, attachments; body with `>`-quoted reply lines rendered as Markdown blockquotes and forwarded/quoted content split into its own section via the shared `_strip_forwarded`. `voicemail` and `other` strata are empty — the documented text-only labeler limitation (0% corpus-wide). Committed corpus text stays bounded to this folder by design (raw maildir + index are gitignored). Tests: `tests/test_build_samples.py` (11 renderer tests, synthetic rows, no corpus) — package suite 85 passed. Docs currency: package README (setup step 7 + scripts tree) + AGENTS.md (structure + 'Generating the Markdown samples folder' workflow). Upstream sync: `sync_packages.py push --package Enron-Evaluation-Environment --patch` propagated 29 files (tip `47d271bc`), cursor re-baselined (`7ce24188`), 10/10 in sync. Board note: a same-minute dual-insertion collision split this card from the parallel session's claims-data-eda PDFs card (theirs HUB-045/046, mine HUB-047). Evidence: monorepo `f031e40e` (generator + tests + docs), `d4fab946` (samples + board split), `7ce24188` (cursor).
- **HUB-046** (done 2026-09-04) — **claims-data-eda: real insurance-claim dataset samples as PDFs (human directive 2026-09-04)** — 8 real corpus documents from `Lucius-Morningstar/mailroom-corpus` (`ground_truth_hardened.jsonl`, 950 insurance_claim rows; sampled carrier/inpatient/outpatient/pde ×2, seed 42), rendered as byte-faithful A4 PDFs of the verbatim `doc_text` via new deterministic zero-dep `scripts/render_samples.py` (Courier/WinAnsi, xref-valid, multi-page; caught + fixed an object-id collision in multi-page layout), into `docs/examples/` with `manifest.json` (provenance + sha256) + README; guard tests `tests/test_examples.py` (artifacts + writer determinism, no network) — package suite 39/39 green. Prune-doctrine exception recorded in root AGENTS.md (like HUB-008). Propagated to the standalone repo via `sync_packages.py push --package claims-data-eda --patch` (subtree push fractured — HUB-012 patch path; upstream tip read `6da424e8` with zero content drift so README regression was impossible; landed as `bf66fafc`), cursor re-baselined. Evidence: monorepo `eb3c8da4` (payload), `1d893e76` (cursor).
- **HUB-005** (done 2026-09-03) — **Release-train readiness (second sweep) — propagation sweep: all 10 feeder repositories in line with the monorepo** — human directive ("ensure all the feeder repositories are in line with the work from the monorepo"). Propagated the HUB-038/039 payload upstream via `scripts/sync_packages.py`: llm-mailroom (16 files, patch path), The-Mailroom (22, patch), agent-mailroom (7 + the `ingest.py`→`intake.py` renames — the HUB-021 patch path refused the cursor gap, so a REAL subtree pull merged the upstream tip (rename resolved cleanly) and a full-history subtree push `adfe04a7..4598387d` carried the deletions), llm-dojo-scoring (1, patch), local-mailroom-sandbox (1, patch); cursors re-baselined per package in `scripts/packages_sync.json` (commits `6b66f83f`, `bd8f8c76`, `cb81a0e3`, `94fbaecc`, `6f4c4357`, `c5fa8780`, `ee642321`). HUB-039 parallel-session work (llm-free-only guardrail, uncommitted) was stashed around every push and never swept — one stale stash remains for that session to drop. **Hub release v0.2.0** cut on top (human directive: changelog + semantic version + tag + release): CHANGELOG `[Unreleased]` accumulated HUB-037/038/039 + unification + release-train entries, `release_chain.py cut 0.2.0 --apply --tag` stamped the section (driver fixed first: `_stamp_changelog` now locates the header anywhere and preserves the title preamble), pyproject 0.1.0→0.2.0, annotated tag `v0.2.0` (`mailroom-hub v0.2.0`), pushed + GitHub Release cut from the changelog section. Gates: all five touched package suites green (859/295/84/58/365), gmail smoke 10/10, board check OK, release-chain check OK. **Follow-up 2026-09-03 — ingest/intake consolidation tail (human directive: "ensure everything involving the ingest/intake consolidation is properly implemented — all package mentions consolidated, all documentation reflects this"):** the whole constellation was swept for remaining current-state mentions and every one consolidated: llm-mailroom (agent/graph/tests READMEs, `.cursor/skills/langgraph`, `notebooks/PLAN.md`, README mermaid, docs/operational-procedure.md, docs/wiki/Home.md, docs/gmail-intake.md, notebook stored outputs 00/01/02/03/08/09/10/13, CHANGELOG [Unreleased] entry, conftest hermeticity pop for MAILROOM_LLM_FREE_ONLY), The-Mailroom (AGENTS.md span list, docs+wiki Architecture, pixel-console/observatory skills), agent-mailroom (README, docs/ARCHITECTURE, office JS floor/layout stage maps), llm-mailroom-graph (regenerate script prose + the generated site artifacts graph.json/index/graph/tree/report — the frozen v0.6.0 stamp remains historical; the next true graphify rebuild re-stamps). Kept deliberately: the audit-event vocabulary (`ingested`/`triage_ingested` — compliance records), generic English verbs (ingest_event/ingest_token, topic-ingest feed, "not pipeline ingest", "PDF-ingest fixtures"), and stamped historical changelog sections. Gates: llm-mailroom FULL 868 passed / 36 skipped, The-Mailroom + agent-mailroom 379 passed, notebook guard suite green. Feeder propagation: the consolidation tail pushed upstream (llm-mailroom, The-Mailroom, agent-mailroom, llm-mailroom-graph); cursors re-baselined. **Third sweep 2026-09-04 (human directive: "sync the mono repo and all of the feeding repositories"):** post-HUB-040/041/043 propagation via `sync_packages.py push --patch`: llm-mailroom 23 files (HUB-040 relations agent + HUB-041 subclass vocab + HUB-043 dedup; new tip `76bc50b6`), llm-entity-extraction 6 + The-Mailroom 3 + llm-dojo-scoring 3 + local-mailroom-sandbox 1 (all HUB-041; tips `309cf335`, `3b1e850b`, `b3ff3e9e`, `816f29c5`). Shared-checkout discipline: patch_push copies the WORKTREE, so the parallel session's in-flight `watcher.py` (HUB-043) was never swept — the four non-overlapping packages pushed first with `--allow-dirty` (their dirty files provably outside those prefixes), llm-mailroom waited for the HUB-043 commit. No nested `.github/` files in any delta (no workflow-scope wall). Post-sweep `status`: 10/10 in sync, 0 monorepo-ahead, 0 cursor gaps. Evidence: this commit (cursor re-baseline). **Correction 2026-09-04 — all-packages one-liner + worktree-race incident:** the human pointer ("there is an appropriate script to do the work HUB issue 5 did manually") is `sync_packages.py push --all --patch` — run as the verification pass it caught one delta my per-package sweep had gone stale on, BUT it also exposed the driver's race: the clean-tree guard runs ONCE at script start, while `patch_push` copies the WORKTREE — the parallel session saved an in-flight `gmail_intake.py` edit (uncommitted echo-HTML work, HUB-043 follow-up) mid-run and it was swept upstream as `e496f1d2` (1 file). REMEDIATED immediately: upstream revert `29249758` restores `gmail_intake.py` to the monorepo-committed state (76bc50b6); the session's local uncommitted work untouched; llm-mailroom cursor re-baselined to `29249758` (0 ahead / 0 gap); coordination note posted on HUB-043. Driver hardening spawned as **HUB-044** (copy committed blobs / per-package cleanliness re-check). Final state: 10/10 in sync. **Tail note 2026-09-04 (later same hour):** the HUB-043 session committed its gmail echo-HTML work as `5d54824e` (3 llm-mailroom files; the sweep also incidentally carried my modified cursor file — content verified correct, the documented HUB-024/027/029 class). The re-run sweep was refused by the guard: the session is mid-iteration with fresh uncommitted llm-mailroom edits, so `5d54824e`'s delta deliberately rides the NEXT sweep (never propagate in-flight saves — the HUB-044 law). Cursor at `29249758`; llm-mailroom 3 files monorepo-ahead pending.
- **HUB-038** (done 2026-09-03) — **Intake agent v2 — triage + clean + prepare for the full pipeline** — human directive 2026-09-03 (better formulate the main pipeline intake agent beyond its current state, similar in nature to the free triage team, applied to the intake agent responsible for primary text cleaning + processing + preparation; follow-up directive: STOP document truncation — use SLIDING WINDOWS to preserve document text so critical information is never missed). Landed in `packages/llm-mailroom` (evidence `9ef4e4fd`): `agents/intake.py` keeps the deterministic dojo clerk as the mandatory baseline and adds an LLM-assisted pass — ONE fused call per window performing TRIAGE (advisory read: primary class / subclass / confidence / gist / keywords, shared `validate_triage` vocabulary clamp, rides manifest `intake.triage` + Gmail echo + sorter prior, never overrules the sorter), CLEAN (structural repair of messy OCR-ish text, gated, re-normalized through the clerk so `prep_invariants` hold, scored by dojo `score_intake` as `method: llm`), and PREPARE (section map: heading + role + document-absolute char offsets, deterministically validated). **No-truncation doctrine:** `sliding_windows` (paragraph-boundary, 15% overlap, hard-split for pathological paragraphs — no window exceeds the budget, every character read, nothing truncated); the sorter subclass bypasses the vendored HEAD+TAIL (per-window classify + deterministic merge: plurality vote among non-unknown classes, mean confidence of agreeing windows, first non-null subtype/subclass, joined reasoning; `WINDOW i OF n` markers; intake prior + retry preamble on every window); `ingest_node` gate + `intake-llm-prep` span + manifest merge; retry_classify no longer slices `[:12000]`. Cost + efficiency: gate fires only for messy / over-sorter-budget docs (clean short docs pay zero); cheapest paid model `qwen3.7-flash` (free tier stays the Gmail triage lane's privilege); `MAILROOM_LLM_INTAKE=0` disables; failures fail soft to the clerk. Prompt registry 16→17 (`mailroom-intake`). Tests: `test_intake_agent.py` (gate, validation, sliding-window coverage proofs incl. mid-document marker read, merged triage + translated offsets, sorter merge, prior/prefix per window, ingest wiring) + 16→17 invariants + conftest hermetic default. Gates: llm-mailroom FULL suite 859 passed / 36 skipped / 0 failed; gmail smoke 10/10 PASS. Docs currency in AGENTS.md / docs/agents.md (§1 sorter + §8b intake) / docs/configuration.md.
 **Follow-up 2026-09-03 — ingest/intake unification (human directive: "the ingest and intake agents are THE SAME — an unintentional name mistake; the ingest + intake steps should be UNIFIED"):** the pipeline's first node is now a SINGLE `intake` node — the intake agent IS the ingest specialist (graph `entry_route` → `intake`, span `intake-document`, node def `intake_node`; the audit event `ingested` stays — compliance vocabulary). The rename swept the whole constellation: `observability/tracing.py` span-type registry, The-Mailroom (`Stage.INTAKE` enum, `pipeline_schema.py` SPAN_STAGE_MAP/NODE_OBSERVATION_TYPES/STAGE_PHASE/NODE_ORDER, `trace_interpreter.py`, TUI stage labels, web/hosted JS stage maps, tests, demo scripts), agent-mailroom (`pipeline/intake.py` module rename + runner/roster/state/nodes), local-mailroom-sandbox, llm-dojo-scoring, and the pipeline lab notebook. Also fixed the gmail smoke mock hermetics (run_mock now forces the mock sender + allowlist — the HUB-039 `.env` pilot roster had started rejecting the mock sender). Gates: llm-mailroom FULL 859 passed / 36 skipped; The-Mailroom 295 passed; agent-mailroom 84 passed; local-mailroom-sandbox 58 passed; llm-dojo-scoring 365 passed; gmail smoke 10/10 PASS. Evidence: `26f25fc6` (rename sweep), `3c4609f8` (smoke hermetics).
- **HUB-037** (done 2026-09-03) — **Gmail intake channel + free triage lane — llmmailroom@gmail.com as a second intake route** — full evidence in the pre-archive card record (git history); this entry records the completion of the triage work. Landed in `packages/llm-mailroom` (commit `3c969ce0`): the IMAP-SSL poller, watcher embedding, intake awareness, ✅ check reaction, completion echo, and live watcher (pre-archive record) PLUS the **single-document free-triage lane** (human directives 2026-09-03): an email carrying exactly ONE accepted attachment is stamped `route: triage` and handled by the FREE OpenRouter triage team (`agents/gmail_triage.py`, `z-ai/glm-5.2:free` — free models kept deliberately, no excessive spend) — core pipeline steps without the paid agents: deterministic prep → triage classification (class/subclass/confidence/gist/keywords) → auditable-hash archive → completion echo, with its OWN `triage_*` audit-log section (`triage_ingested`/`triage_classified`/`triage_archived`, never conflated with the pipeline's stage events). Emails with TWO OR MORE accepted attachments are `route: pipeline`: the triage approach is dropped and every attachment runs the FULL paid pipeline (triage never dispatched). **Capability pre-check + honest handoff:** a deterministic LLM-free check (`_triage_capability_check`) runs BEFORE the lane — image-only inputs, scanned PDFs, and documents longer than the free `max_input_chars` budget (merger agreements typically exceed it) are handed to the full paid pipeline with `intake.triage_handoff` recording the reason (echo renders it), never a failed free-model run. **Reaction guarantee:** ✅ fires at claim time on BOTH routes, plus a terminal-stage retry inside `send_intake_echo` (deduped per Message-ID; a single-doc claim has one shot, so the terminal retry closes the gap) and a `reactions_failed` status counter. **All doc types validated:** contracts, merger agreements, insurance claims, corporate records, and correspondences through the triage lane (parametrized test matrix) + capability handoff tests (budget/image/scanned). Smoke now 10/10 PASS (single-doc triage lane + multi-doc full pipeline + audit section + reactions on both + echoes). FULL llm-mailroom suite: 837 passed / 36 skipped / 0 failed. Prompt registry 15→16 (`gmail_triage` registered in `llm.prompts.prompt_templates`). Evidence: `1b6d2ed6`, `511ef9b1`, `7c1a1078`, `f93b8213` (committed under the human's git identity; docs currency in AGENTS.md / docs/agents.md / docs/configuration.md).

Finished cards, append-only, newest last.

- **HUB-045** (done 2026-09-04) — **claims-data-eda: real-sample PDF
  examples (human directive 2026-09-04)** — duplicate of archived
  HUB-046 (same claims-data-eda PDFs work, commit `3526cccf`). This
  open row was a same-minute dual-insertion collision with the
  Enron-samples card (HUB-047); removed from open cards 2026-09-04.
- **HUB-032** (done 2026-09-02) — **Post-collision GT reconciliation —
  hardening onto the v8 base** — full evidence in the pre-archive card
  record (git history). Summary: the interleaved HUB-028 (v8) / HUB-022
  (§84) publishes left the Hub mixed; GT was rebuilt on the v8 value base
  (`bba2f750`), the 31 original columns asserted value-identical,
  document_ids drift-free, and republished at `eafe1ab4` (10/10 sha256
  local==hub, §91 gates green). Independently re-verified from downloaded
  bytes by the card claimant (GLM-5.3-Flash): GT 2,000×60, 19 rows/7
  threads, 7-way source split, synthetic 950, bundles 50 + fixtures 32
  intact; the claimant's parallel staging path agreed on every fact and
  stood down (no double-publish). Closed by the human directive "ensure
  all appropriate boards are closed": the datasets-server re-poll noted in
  evidence is Hub-side cache infrastructure (auto-polling), not card scope
  — the authoritative check is the byte-level download verification, which
  passed twice, by two agents independently. Board-close edit note: these
  archives + the HUB-036 spawn rode commit `edc1b033` (another agent's
  sweep — the documented HUB-024/027/029 pattern; content verified).
- **HUB-028** (done 2026-09-02) — **mailroom-corpus v8 — synthetic
  insurance-claim LOB expansion + full GT conformance** — full evidence in
  the pre-archive card record (git history). Summary: 2,000 rows published
  (insurance 950 = 600 CMS + 200 GNOTHEIA property + 150 BDR auto; 50
  strata); 27-key GT fully populated; test-split nullification PASS; blind
  leak clean; sha256 local==hub; card v8 with the §84 section restored
  after the interleaved-publish collision (reconciled forward as HUB-032);
  7 new v8 tests (corpus-eda 73 passed); INSURBIAS deferred → spawned as
  HUB-036; final leg `7f8983ac` retargeted FULL_CORPUS_REVISION to the v8
   hardened tip `eafe1ab4` per §44 pin law (llm-mailroom 775 passed).
   Deferred to v9: INSURBIAS (see HUB-036). Post-close follow-up (2026-09-02,
   same session): **purpose/gist extraction surface** — the v8 corpus GT
   carries subject_matter/keywords on ALL 950 insurance rows but the
   entity-extraction eval surface dropped them (taxonomy field_types,
   specialist schema, prompt); landed: taxonomy `insurance_claim` gains
   `subject_matter` (free_text) + `keywords` (entity_list:name) + `property`
   `/` `auto` subclasses; `INSURANCE_CLAIMS_SCHEMA` gains both fields;
   `insurance_claims_specialist_v2` (9b/9c extraction rules, v0/v1
   byte-stable, mirrored into The-Mailroom registry); specialist runner
   scores them (`INSURANCE_FIELD_KEYS` + `GT_FIELD_TYPES`); v8 dump rebuilt
   against `eafe1ab4` (expected_fields 350/350 property/auto carry both
   fields); coverage matrix regenerated (subject_matter/keywords 100% on
   950 rows; expansion priorities refreshed to 2,000 rows); entity-extraction
   756 passed.
- **HUB-035** (done 2026-09-02) — **Entity package: eval infrastructure for
  sorter + specialists on the v7 + v8 corpus** (hub card only per human
  directive — no MESSAGE_BOARD twin). Survey found: runners defaulted to a
  nonexistent `data/datasets/docclass_merged.jsonl`, no v8 dump path, no
  revision-pinned corpus loader, and the specialist runner wired only
  contracts + insurance arms. Landed in `packages/llm-entity-extraction`:
  (a) `scripts/datasets/build_mailroom_corpus_dumps.py` — revision-pinned
  dump builder pulling the staged parquet shards via `huggingface_hub` (no
  `datasets` dependency), joining textless-GT ↔ default configs on
  `filename`, deriving GT scalar keys DYNAMICALLY (v7's 27-key → v8's 60
  columns flow through untouched), schema-filtering `expected_fields`
  against `config/taxonomy.yaml` field_types (provenance keys like
  document_id/annotation_method must never be scored), preserving full
  `gt_fields` + default-config `metadata` (complete representation of both
  configs), writing per-arm manifests + a sha256 build manifest, and using
  the KANBAN-088 `safe_jsonl_line` writer (enrolled in the adoption sweep);
  (b) specialist runner: all FOUR canonical arms
  (correspondence_specialist + corporate_records_specialist added;
  merger_agreement documented as contracts-arm territory), generic enrich,
  keyless `--dry-run` (key gates moved after the dry-run return in BOTH
  runners, preserving live behavior) with a GT-gap-aware dry-run message;
  (c) 8 offline tests (join, dynamic GT derivation, v8 schema growth,
  manifests, build manifest, per-arm filtering, enrich semantics) +
  runbook in `scripts/eval/README.md`. VERIFIED END-TO-END against the live
  Hub: v7 @ `bb57c5ad` → 1,650 rows (arms 661/600/350/39 — exact HUB-019
  freeze shape), v8 @ `eafe1ab4` (Hub tip) → 2,000 rows (insurance 950 =
  600 CMS + 200 GNOTHEIA + 150 BDR per HUB-028); sorter dry-run keyless on
  v8 (exact class distribution, canonical five-class set); contracts arm
  509/661 scoreable (CUAD clause GT), insurance 950/950; correspondence +
  corporate_records arms wired and dry-run-clean but carry no schema-shaped
  GT yet (corpus GT is intent/subject_matter-shaped — the HUB-022 matrix
  gap; live scoring refuses until the HUB-031/032 reconciliation defines
  it — documented, not invented). Dumps stay local (gitignored) — rebuilt
  deterministically from the pinned revisions. Suite: entity FULL 753
  passed / 28 skipped / 0 failed. Live LLM runs remain a human-keyed
  follow-up. REOPENED same day (human directive: "implement the identified
  fixes"): the correspondence + corporate_records arms scored NOTHING
  because enrich targeted the OUTPUT-SCHEMA keys (sender, recipient,
  filing_number, ...) while the corpus GT carries intent/subject_matter-
  shaped fields. Fix: arms now score the GT THE CORPUS ACTUALLY CARRIES
  (per HUB-022 matrix, empirically rescanned): correspondence = intent ·
  sentiment_label · content_topic (350/350 rows) + subject_matter/keywords
  (96/350); corporate_records = subject_matter/keywords (38/39); explicit
  GT scoring types in `GT_FIELD_TYPES` (deterministic — no heuristic
  fallback); `_decode_listish` adapts the JSON-encoded keywords GT to
  entity_list scoring (house pattern: cuad_labels_to_clause_list);
   output-schema fields stay in the agents' extraction schemas untouched —
   taxonomy.yaml NOT edited (GT-reconciliation semantics remain
   HUB-031/032's lane; this card only wires scoring to existing GT).
   LATER ADDENDUM (2026-09-02, HUB-028 post-close follow-up): taxonomy.yaml
   WAS then edited for the INSURANCE arm only — `subject_matter`/`keywords`
   added to `insurance_claim.field_types` (they exist on the schema and on
   all v8 corpus rows) + `property`/`auto` subclasses; the runner's
   `GT_FIELD_TYPES.insurance_claims_specialist` entry added; insurance
   `INSURANCE_FIELD_KEYS` extended. The correspondence/corporate arms are
   unchanged (their field_types stay output-schema-shaped; GT scoring rides
   GT_FIELD_TYPES as documented above).
   COORDINATION NOTE for the HUB-031/032 landing: the runner merges
  `{**get_field_types(doc_class), **GT_FIELD_TYPES[arm]}` — for the
  correspondence/corporate arms the GT_FIELD_TYPES entries WIN over any
  future taxonomy.yaml field_types for those five keys; if the
  reconciliation types them differently, update GT_FIELD_TYPES in the same
  commit (HUB-035 owner keeping the runner honest, observed 2026-09-02). Dry
  runs verified: correspondence 350/350 scored, corporate_records 38/39.
  Runbook GT paragraph updated. Suite: entity FULL 754 passed / 28 skipped /
  0 failed. Original Evidence: the delivery commit (`557b76e6`); follow-up
  Evidence: this commit — with one correction: the runner-half of the fix
  landed swept inside the parallel agent's `dbd79308` (broad add, same
  incident class as HUB-024/027/029 — see the HUB-029 staging norm).
- **HUB-034** (done 2026-09-02) — **Header diagram: universal auditable-hash-archive
  flow** — human directive ("ALL of the files end up in the auditable hash
  archive, that is the point of the mailroom, not just the failed ones, it
  should ALL be traceable"): the HUB-027 banner implied archiving was a
  failure-only outcome ("Archive — unresolved items"). Diagram restructured
  (both light + dark variants): the failure-only archive box is REPLACED by
  an **Auditable Hash Archive** terminus ("IMMUTABLE · HASH-CHAINED — every
  file & every decision") fed by TWO primary edges — Route → archive
  ("delivered · sealed") and Human Review Queue → archive ("all
  dispositions", covering approve/reject/escalate) — while low-confidence /
  failed-checks keep their dashed review paths and the corrected · resubmit
  loop stays. Subtitle + aria desc + README alt text state the doctrine
  verbatim; legend unchanged; geometry re-balanced (queue narrowed to 320,
  archive x=790 w=360). Verified: xmllint both well-formed, qlmanage renders
  eyeballed (light re-checked after label move). Canonical dark 13-node SVG
  untouched (its ARCHIVE stage already says "source + manifest + hash-chained
  audit" — the doctrine was right there all along). Evidence: this commit.
- **HUB-022** (done 2026-09-02) — **docclass-merged P1 — Mailroom Evaluation
  Hardening (plan §86, §84A sequencing)** — full evidence in the pre-archive
  card record (git history). Summary: P1 landed `846c6e83` (eval_contract
  derivations + closed vocabularies, §40–41 coverage matrix, §5A spans); P2
  groundwork `0b6ff1f9` (lucius HF audit: In-Reply-To structurally absent
  from the CMU maildir — §14A verified; matter.py never-mix guard; live
  audit 19 rows/7 threads); P2/P3/P4/P5 scaffold `f080322b` (bundles.py,
  fixtures.py, expansion_priorities, P5 ledger); §84 PUBLISHED `0cb4c9e6`+
  `bbab0e63` (staging script + sha256 thread-key fix after lucius's
  determinism gate caught PYTHONHASHSEED-salted ids) — Hub commit
  `61c16645`: GT 1,650×60, bundles 50, fixtures 32, sha 11/11 ok, 19/7
  re-confirmed on downloaded bytes, blind default untouched. Interleaved
  publish collision with HUB-028 reconciled forward as HUB-032 (not
  silent). Forensics: /tmp/opencode/hardened_publish_report.json.
- **HUB-022** (done 2026-09-02; entry restored) — **docclass-merged P1 —
  Mailroom Evaluation Hardening (plan §86, §84A sequencing)** — human
  directive; RESTORATION NOTE: the card row was removed from the board
  during the HUB-028/031 v8 close-out instead of being archived (never-
  delete law); this entry is reconstructed from session capture + the
  commit trail. Landed across the card's life: P0 completeness pass
  (`run_pipeline(dataset=...)` trace fields, 8 passed; baseline audit GT
  columns fact corrected 32→31); **P1** `mailroom_eda/eval_contract.py`
  (§59 expected_specialist registry-derived, §57–58 expected_stage, §31
  review/retry closed vocabularies, §43 annotation_provenance verified over
  all 1,650 rows — verified_join 162 / llm_zero_shot 92 / human_annotated
  96 / synthetic 600), `scripts/coverage_matrix.py` → §40–41 report,
  §19 span schema, §68/69/70 fixture vocabularies, §14A decision documented
  (commit `846c6e83`); P2 groundwork — §14A VERIFIED with data (In-Reply-To/
  References structurally absent from the CMU maildir; subject populated
  346/350, 266 meaningful), `MATTER_CONSTRUCTION` heuristic_reconstructed,
  `mailroom_eda/matter.py` (commit `0b6ff1f9`); P2/P3/P4/P5 scaffold —
  `mailroom_eda/bundles.py` (five bundle-family templates), `fixtures.py`
  (calibration quartet at live taxonomy bands), P4 expansion priorities,
  P5 surfaces ledger (commit `f080322b`); suite grew 15→65 passed across
  the scaffold. Card completed by the v8 publication under HUB-028
  (commit `439560f9`: 2,000 rows, 27-key GT conformance, test-split
  nullification, sha256-verified Hub publish) + board-evidence restoration
  (`319a3ebe`). Owner: Lucius (opencode). Evidence: `846c6e83`, `0b6ff1f9`,
  `f080322b`, `439560f9`, `319a3ebe`.

- **HUB-031** (done 2026-09-02) — **resolved without a card (ID-collision
  closure)** — the HUB-031/032 IDs were both claimed concurrently by the v8
  follow-up agent mid-card (live shared-checkout editing); the work settled
  as HUB-032 (GT reconciliation) and HUB-033 (badge audit). This archive
  entry exists so the board checker's phantom-card-reference gate resolves
  the HUB-031 token in historical commit messages (e.g. `c9f9b876`, HUB-035
  coordination note) — there is no HUB-031 work; see HUB-033's own collision
  note.
- **HUB-033** (done 2026-09-02) — **GitHub badge audit — all README badges
  render across paths** — human directive ("ensure all of our github badges
  render properly in the repository across paths and such"). Method:  extracted all 76 unique shields.io URLs from every README, fetched each
  SVG and verified the rendered `<title>` text (catches escape/syntax
  mangling), HTTP-checked all external targets (3 HuggingFace dataset repos
  → 200, incl. the renamed mailroom-corpus), verified every badge's
  relative link target exists on disk (reports/tests/LICENSE paths), and
  cross-checked version badges against the packages' own pyproject pins
  (The-Mailroom 0.3.0, dojo v0.13.0, llm-mailroom v0.6.0,
  agent-mailroom v0.12.1 — the last matches its own pin: upstream lag,
  flagged for the HUB-005 release train, NOT hand-edited per mirror law).
  One defect found + fixed: the root README's License badge linked a
  LICENSE file that did not exist at the hub root — added the MIT LICENSE
  (house template per packages/agent-mailroom/LICENSE; badge already
  claimed MIT publicly). False positives excluded: zod/fast-check/discord
  badges live in .opencode/node_modules (local tooling, never rendered).
  No CI-status badges exist (moot while Actions is billing-locked).
  ID collisions: HUB-031/032 were both claimed concurrently by the v8
  follow-up agent mid-card (live shared-checkout editing); this card
  settled on HUB-033. Evidence: this commit.
- **HUB-030** (done 2026-09-02) — **Dependabot config for the monorepo** —
  human directive ("generate the appropriate dependabot.yml"). Landed
  `.github/dependabot.yml` with three ecosystems and the exclusions that
  make it appropriate to THIS repo: (a) root `pip` (uv workspace; Dependabot
  supports uv.lock via the pip ecosystem) with one grouped PR for the dev
  group, weekly; (b) `github-actions` for `.github/workflows/`, weekly;
  (c) `docker` for `packages/local-mailroom-sandbox/deploy/` (the actively
  maintained offline image; HUB-015 version-pinning doctrine — bumps keep
  the pins honest), monthly, riding the HUB-005 release train upstream.
  DELIBERATELY excluded with an in-file rationale: all `packages/*/`
  pip manifests — subtree mirrors of independent Exios66 repos; Dependabot
  PRs against them would create monorepo-ahead drift against the sync
  driver's cursors AND bump release-time-only git pins against the
  workspace-pins law (AGENTS.md). Claimed + landed in one commit
  (config-only, single-pass). Board check 0/0. Evidence: this commit.
- **HUB-029** (done 2026-09-02) — **Team norm: targeted `git add <paths>`
  only** — human directive ("a team norm of targeted git add <paths> only"),
  codifying the fix for the two shared-checkout sweep incidents (HUB-024,
  HUB-027) where a parallel agent's broad add landed other agents' in-flight
  files under the wrong commit message. Norm landed verbatim in the three
  surfaces the commit-discipline law lives: `governance/TASKS.md` (Rules
  that keep the board honest), root `AGENTS.md` (Commit discipline bullet),
  and `docs/wiki/Board-Governance.md` (rides the next `sync-wiki.sh` push).
  Rule: `git add <explicit paths>` for exactly your card's files — never
  `git add .` / `-A` / a bare directory — and re-check
  `git status --porcelain` before every commit, unstaging anything you
  don't own. ID collision note: HUB-028 was claimed concurrently (corpus v8); this card took HUB-029. Claimed + landed in one commit (docs-only, single-pass edit;
  the board file is itself part of the change). Board check 0/0. Evidence:
  this commit.
- **HUB-027** (done 2026-09-02) — **Root README banner — "Mailroom Processing
  Pipeline" adapted for GitHub** — human directive with the diagram's actual
  SVG source supplied in-session (6 stages Intake → Preprocess → Classify →
  Extract → Validate → Route; Human Review Queue + Archive exception paths
  with low-confidence / failed-checks / corrected-resubmit / reject edges;
  cross-cutting services strip: job queue, object storage, LLM gateway,
  observability, audit trail). Landed: `docs/assets/
  mailroom-processing-banner.svg` (light, source-faithful) +
  `mailroom-processing-banner-dark.svg` (GitHub-dark palette translation —
  canvas/nodes #0d1117/#161b22, borders #30363d, amber review queue
  #d29922/#e3b341, indigo LLM-stage #818cf8); README banner swapped to the
  `<picture>` prefers-color-scheme dual-theme pattern (camo-safe: system
  font stack, no scripts, viewBox-only) — the previous dark 13-node
  `mailroom-pipeline.svg` stays untouched and canonical (self-referenced
  source of truth); fixed the adjacent broken canonical link
  (`docs/assets/mailroom-pipeline-svg` → `.svg`). Verified: xmllint
  well-formed on both, qlmanage renders eyeballed (light + dark). Docs-only,
  board-only. Evidence: this commit.
- **HUB-026** (done 2026-09-02) —
  **Offline sandbox: remote-serving integration completeness (Modal / vLLM /
  conda / SSH tunnels / CHTC) + CHTC annotation pass** — human directive
  ("ensure the sandbox is fully configured for integration with Modal, vLLM,
  a conda environment, SSH tunnels, or interfacing with CHTC"; reopen:
  "add annotations and specifics for the use of the UW Madison CHTC services
  … they have several fully dedicated docs online regarding their operating
  system + requirements"). Delivery leg (`60fe58b5`): Modal (`deploy/
  modal_vllm.py` + `modal-vllm` profile) and vLLM-local verified intact;
  landed the `vllm-remote` profile with a `tunnel:` block (env-var
  indirection, nothing secret in-repo), `mailroom_sandbox/tunnel.py`
  (network-free argv builders, pidfile lifecycle, double-forward refusal),
  `sandbox tunnel plan/up/status/down` (leaf parsers drop
  `parents=[shared]` so leaf defaults can't clobber the parsed profile; the
  before-subcommand clobber is pre-existing CLI-wide and now documented),
  `deploy/conda/environment.yml` (CPU-first portable env, vLLM external,
  conda-pack for staging), and `deploy/htcondor/` two-path templates
  (batch eval for the shared pool / server for owned GPUs).
  Annotation leg (this commit) — every CHTC claim grounded in their live
  user docs: access points ap2001/ap2002 + login requirements (CHTC
  account, NetID, Duo MFA, campus network/UW VPN, ControlMaster reuse with
  the port-forwards-on-initial-connection rule, Mosh lacks forwarding);
  OS strategy (RHEL-family execute nodes; Apptainer containers carry their
  own OS — `docker://vllm/vllm-openai` direct or staged `.sif` via
  `osdf:///chtc/staging` + `HasCHTCStaging`; conda-pack must be BUILT ON
  THE ACCESS POINT for glibc match, never macOS; .sif builds only in
  interactive build jobs); /staging + the live 2026 staging-transition
  notice; the full GPU Lab roster (P100/2080Ti/A100-40/80/L40/L40S/H100/
  H200 with capability+VRAM) + job classes (short 12h / medium 24h / long
  7d + per-user caps, default medium) + `condor_status` exploration;
  submit-file knobs corrected per the roster (batch → `short`,
  `gpus_minimum_memory 24000` excludes 10–16GB cards for Qwen3-8B,
  optional capability 8.0; `CUDA_VISIBLE_DEVICES` is HTCondor-owned;
  `+is_resumable` backfill note) and the `ON_EXIT_OR_GRACEFUL_REMOVAL`
  typo fixed; `condor_ssh_to_job` policy dated (2026-04-22, shared-GPU
  removal; `condor_tail` for monitoring). Suites: sandbox 58 passed /
  1 documented skip / 0 failed; board check 0/0. Evidence: `60fe58b5`
  (delivery) + this commit (annotations).
- **HUB-025** (done 2026-09-02) — **Enron EDA visualization distortions
  (#9)** — human-filed bug: the "Enron Subclass Distribution" donut rendered
  with bunched & distorted labels (email 97.8%; the seven sub-1% subclasses
  collapsed into slivers whose Plotly outside labels piled into the title and
  stretched leader lines into a spike). Root cause: `scripts/
  gen_interactive_charts.py` chart #1 used `textinfo: "label+percent"` with
  default text positioning on a 97.8%-dominated pie — Plotly pushes sliver
  labels outside where they collide. Fix (encoding only, data untouched):
  per-point `textposition` — dominant slice labeled inside, slivers
  unlabeled but kept as visible slices + legend entries, plus a rich
  `hovertemplate` (label / comma count / percent) so no detail is hidden.
  Static twin `01_subclasses.png` verified ALREADY correct (log-scale bar +
  rare-subclass panel) — untouched. Artifact regenerated via the generator:
  only `01_subclasses_interactive.html` changed (all other claims/Enron
  charts byte-identical — determinism held); data self-consistency
  re-verified against the screenshot (attorney_demand 4/517,075 =
  0.000773%). Docs: index.html caption "Subclass Distribution (pie)" stays
  accurate; no doc changes needed. Suite: Enron 74 passed / 0 failed (suite
  does not cover hub tooling; artifact verified structurally). Issue #9
  closed by the fix commit. Evidence: this commit.
- **HUB-024** (done 2026-09-02) — **Core-repo changelog + semantic-version
  release chain** — human directive ("ensure our core repo is keeping a solid
  changelog and GitHub semantic version release chain … as the core repo of
  truth"). Delivered: (a) root `CHANGELOG.md` (Keep a Changelog 1.1.0; hub era
  HUB-001→ backfilled into `[0.1.0]`; scope note separating the hub chain from
  the pre-import standalone-mailroom lineage and from package-level releases);
  (b) `scripts/release_chain.py` (stdlib): `status`/`check`/`cut` — structural
  errors (exit 1): a version tag without its changelog section, duplicate/
  non-semver/out-of-order sections, hub pyproject behind the newest tag;
  warnings: stamped-but-untagged section (prep state), tag-message
  convention, lightweight tags; `cut` stamps `[Unreleased]` → dated section +
  bumps the hub pyproject version (dry-run default, `--apply`/`--tag`, never
  commits or pushes); (c) CI: `release-governance.yml` gate on `v*` tag
  pushes + workflow_dispatch; `board-governance.yml` gains the release-chain
  step + `CHANGELOG.md` path trigger; (d) **v0.1.0 cut**: annotated tag
  `v0.1.0` (`mailroom-hub v0.1.0` message) + GitHub Release from the
  changelog section — first hub release; (e) docs currency: AGENTS.md
  (commands + workspace rule), README (tree + commands), scripts/README.md,
  wiki Releases.md (hub-chain section). Coordination incident (honest
  record): the main deliverables were swept into a parallel agent's broad
  `git add` commit `04e1f604` ("Add hub changelog and contract fixtures")
  from the shared checkout, mixed with that agent's llm-mailroom README
  work; the card claim rode along in `1bc76344`; dedicated follow-ups for
  docs currency (`bac48976`) and this archive. **CI billing-lock incident**:
  Actions compute on the Exios66 account has been locked since ~2026-08-31
  ("The job was not started because your account is locked due to a billing
  issue") — the original board-governance 0s "workflow file issue" failure
  was this lock, and that workflow had been manually disabled in response;
  re-enabled, then ALL billing-failing workflows paused per human directive
  (mailroom-dev `board-governance` + `release-governance`, llm-mailroom
  `Bump llm-dojo-scoring`; Gaze_Calculator-66 `Scheduled` no longer exists
  in-repo) — re-enable after the human resolves github.com/settings/billing;
  `release_chain.py check` verified green locally. Chain post-tag: 0 errors /
  0 warnings; board check green. Suites: none (hub tooling only). Evidence:
  `04e1f604`, `1bc76344`, `bac48976`, tag `v0.1.0`,
  https://github.com/Exios66/mailroom-dev/releases/tag/v0.1.0, this commit.

- **HUB-023** (done 2026-09-02) — **Rename the HF dataset
  `docclass-merged` → `mailroom-corpus`** — human directive ("docclass was
  always a placeholder"). Hub leg (lucius): `HfApi.move_repo` preserves git
  history — pre-flight (no collision, tip `bb57c5ad`, 1,659 files) → move →
  post-flight verified (new repo sha == pin, pin resolves at the new name,
  file count intact, old id = Hub redirect). Monorepo leg: 57 files / 82
  exact-id replacements + composed f-string ids (hf_corpora ×
  llm-mailroom/agent-mailroom/The-Mailroom) + prose (docs, dataset cards,
  wiki, audit manifest); historically preserved: internal slug
  `docclass-merged` + `source-docclass-merged` trace tags (trace-tag
  immutability; `corpus`/`mailroom-corpus` aliases added), release marker
  `docclass-merged-v0.1-working` (version label), prompt-family version
  keys (experiment identity — append-only law), code file/flag names, plan
  text (dated addendum only, no rewrite), CHANGELOGs/governance archives,
  derived EDA/graph artifacts (canonical bytes, refresh rides the release
  train). Contract §6 rename record; §44 pin re-verified post-rename.
  Suites green (corpus-eda, llm-mailroom incl. run_hf_pilot 26 after
  fixing the `dataset` param threading into `_execute_run`, The-Mailroom,
  sandbox, dojo, agent-mailroom); parity gate green. Commits:
  `3ad5d47d`/`77a26d69`/`d064ff9b` (swept P0-completeness legs), `30b1f76c`
  (monorepo rename leg). Pin `bb57c5ad` re-confirmed at the new name
  (lucius, HF audit 2026-09-02).
- **HUB-021** (done 2026-09-02) — **Sync driver: reliable upstream
  propagation** — human directive ("fix the upstream propagation issue").
  The subtree cursor mechanics behind every recent reconciliation incident
  are now structurally guarded in `scripts/sync_packages.py`:
  (a) containment oracle — blob-tree compare (`tree_map`) of
  `packages/<name>` vs the upstream tip, gitignore-aware (pruned heavy
  assets are doctrine, not drift — HUB-004/018) with modified paths
  reported separately as monorepo-ahead delta; (b) `snapshot` refuses to
  advance a cursor past non-contained upstream content unless `--force`
  accepts the gap explicitly (HUB-018 structurally impossible by default);
  (c) `pull` skips the subtree merge and re-baselines when the tip is
  already contained (re-import loop killer); (d) `push --patch` — the
  scripted HUB-012 workaround: tracked package files rebuilt on the real
  upstream tip, ONE fast-forward commit landed upstream, cursor
  re-baselined (`--dry-run` prints the plan; plain-push failure now points
  at `--patch`); (e) `status` surfaces `CURSOR GAP` flags + per-package
  monorepo-ahead file counts (the HUB-005 release-train payload:
  corpus-eda 56, llm-mailroom 23, sandbox 20, entity 17, The-Mailroom 6,
  agent-mailroom 4, Enron 2, claims 1, graph 1, dojo 0). Pushes remain
  explicit (release-time only per workspace rules). Verified: throwaway
  fixture sims of both incidents (HUB-018 gap → refusal; honest cursor →
  clean; HUB-012 → dry-run plan then one fast-forward commit directly on
  the old tip carrying the monorepo fix, post-push cursor verifies clean);
  live `status` 10/10 in sync with 0 cursor gaps; content-verified
  `snapshot` green for all 10; clean-tree guard re-verified. Docs currency:
  README sync section + wiki Sub-Package-Sync. Hub tooling only — no
  package suite impact. Evidence: `80ee2308`.
- **HUB-019** (done 2026-09-02) — **docclass-merged corpus hardening P0 —
  baseline freeze, dataset contract, identity/provenance schema, taxonomy
  parity gate** — human directive: implement the docclass-merged plan §85
  (P0) per §84A sequencing + §84B no-silent-completion. Co-work split (human
  directive, two non-overlapping lanes) with an explicit takeover (human
  directive, "other agent fell asleep"): lane 1 = components 1–4, lane 2 =
  component 5, second agent closed the card for both lanes. (1) **Freeze**
  `docclass-merged-v0.1-working` at the true tip `bb57c5ad` (baseline audit
  Finding 1: the recorded `FULL_CORPUS_REVISION` `b3ec9ee7` predated the
  issue-#5 intent_source fix — pin advanced), audit report + machine-
  readable manifest at `docs/reports/audits/docclass_merged_baseline.{md,
  json}` via `scripts/baseline_audit.py` (revision, counts, splits, schema,
  source inventory, taxonomy/annotation/builder revisions, license/PII
  posture, known limitations; identity verification 100% over 1,650 rows;
  2 exact-duplicate groups recorded — classified, not deleted, §12).
  (2) **`docs/DOCCLASS_CONTRACT.md`** — canonical dataset contract (§80)
  with the §81 mapping table, §6 merger_agreement→contracts_specialist
  semantics, §44 pin discipline, §44A publishing path, §91+§4A release
  gates, §84 release structure; the plan itself text-extracted to
  `docs/docclass-merged-plan.md` as the shared §-reference. (3)
  **Identity/provenance/hashes** — `mailroom_eda/identity.py`
  (`document_id` from source identity, never row index; `source_corpus`
  /`source_document_id`/`source_filename`/`source_revision`;
  `content_sha256`/`normalized_text_sha256`) as §84 groundwork, verified
  100% over the pinned snapshot; published-config wiring is the explicit
  v0.2 release decision (P0 no-pushes respected). (4) **§63/§64 contract
  tests** — corpus-eda gains a suite: 15 passed (row contract + Mailroom
  interface contract, fixture + full-snapshot runs; GT config is textless →
  doc_text joined from the default config for content hashes; hollow-hash
  guard; `other` subclass allowed as explicit fallback, never null).
  (5) **§65A taxonomy-parity gate** — `scripts/taxonomy_parity.py` (stdlib,
  network-free, AST-parsed from literal sources: strict equality on
  HUB_CLASSES / taxonomy.yaml live entries / mailroom sorter vocab /
  specialist registry / v7-taxonomy.md blocks / dojo CORPUS_DOC_TYPES /
  entity PILOT universe / sandbox fixture; alias-aware structural rule for
  documented compat surfaces, §60 retired roster tolerated only as
  remnants; 5 negative tests incl. anchor-edit propagation) wired as a
  blocking `board-governance.yml` step with taxonomy-surface path triggers;
  docs currency in AGENTS.md / README / wiki Board-Governance.
  (6) **Stale-language sweep** — compliance_filing retirement wording
  reconciled across taxonomy.yaml (status: retired marker), hf_corpora,
  prompt_doctrine, graph README, sorter patch comment, v7-taxonomy §1/§4;
  residual spawn: HUB-020 (docclass eval judge prompts still grade against
  the retired 8-class "EXTENDED primary set" — prompt-versioning work, NEW
  keys + A/B, not a hand edit). Suites: corpus-eda 15 passed; llm-mailroom
  surgical 16 passed on the pin-change surfaces (full suite aborted by the
  human mid-run — noted honestly); parity gate + board `check` green.
  Evidence: `120f11d6`, `0bf22b6f`, `be1f56ef`, `de20ef17`, `5cff893e`,
  `ea76a22c`, `8d72f5e1`, `983a9b4b`, `5c744b60`, `02e83633`, `88515225`.

- **HUB-018** (done 2026-09-01) — **Sub-package sync sweep: llm-mailroom +
  mailroom-corpus-eda** — human directive: pull all packages' most recent
  versions, ensure they are synced to the monorepo including EDA reports,
  visuals, and documentation fixes. 8/10 packages already in sync; two legs
  reconciled. **llm-mailroom**: upstream tip `d4940f8a` (operational
  procedure doc + pipeline SVG) pulled with squash base `aace6a49` — the
  cursor had been snapshot-advanced past content never subtree-merged
  (`aace6a49` not an ancestor of the recorded `857fb381`), so the pull
  back-filled the whole range; process note: snapshot-advance without a
  merge creates a cursor/content gap that the next squash pull re-imports.
  Post-merge monorepo-truth reconciliation: re-pruned the gitignored heavy
  assets the merge resurrected (`docs/examples/` 9 sample PDFs + external
  corpus texts, `docs/reports/` incl. the 59,668-line experiment_log.md —
  `.gitignore:56-57`, HUB-004 doctrine); restored clobbered monorepo-side
  wiring (`[tool.uv.sources]` workspace redirect, bump-script release-time
  note, 6 pruned-asset skip guards, dojo pin-flexibility guard, UTC-stamp +
  CWD-anchoring fixes); re-tuned notebook lab scenarios to the monorepo
  taxonomy bands (low 0.90 / high 0.98 / judge band 0.97 — upstream's
  0.80/0.97 retune targets upstream's looser bands): `CLASSIFY_CONTRACT_MEDIUM`
  0.92, `CLASSIFY_INSURANCE_HIGH` 0.98, judge-band scenario extraction 0.93,
  keeping upstream's `court_opinion` override (guardrail-honest —
  court_opinion is out-of-taxonomy on both sides); refreshed stored outputs
  for notebooks 02/03/10; fixed the stale `DOC_CLASSES` pin 6→5 left by the
  compliance-filing retirement commits (pre-existing red). Suite 772 passed
  / 36 skipped / 0 failed; `uv lock --check` green. **mailroom-corpus-eda**:
  upstream moved twice mid-session (`c659789f` source dataset cards + docs
  index; `816fb028` issue #5 intent_source aeslc_join fix on the 162
  join-assisted rows); subtree squash base resolved to a pre-import ancestor
  (`d3198a2a`) → 49 pseudo-conflicts, resolved per the HUB-004/012/013 laws:
  upstream taken byte-verified for the true 13-file delta (README blurb,
  `docs/README.md` index, 5 `docs/dataset-cards/*.md`,
  `SUMMARY_REPORT.{json,md}` with figures=30 preserved, dataset_export /
  docclass_uploader / intent_backfill), monorepo-canonical kept for
  everything outside the delta (`run_all.py` summary-write guard, AGENTS.md,
  tables/, 30 matplotlib-3.11 PNG renders, 19 interactive HTMLs).
  py_compile green; EDA deliverables remain fully tracked (HUB-008
  exception). **Known residue** (discovered, not delivered): upstream's
  notebook narrative still cites upstream-band thresholds (0.85 judge gate,
  0.95 high, 0.88 reviewer labels) — inaccurate under the monorepo taxonomy
  bands; left as upstream-managed content, to reconcile at the release
  train (HUB-005 push) rather than hand-edited monorepo-side.
  `sync status` 10/10 in sync. Evidence: `2d93de6b` (prune + restorations),
  `ce98b043` (scenario re-tune), `6f2ce890` (corpus-eda subtree merge).
- **HUB-017** (done 2026-09-01) — **GitHub wiki for mailroom-dev** — human
  directive. Full version-controlled wiki source landed at `docs/wiki/`
  (entity-repo pattern): **Home** (facts table: pins v0.6.0 / dojo
  v0.12.2 / corpus v7), **Getting-Started** (workspace, per-package
  suites, sandbox quickstart), **Architecture** (full map: 10 packages +
  hub, direct repo links, the 3 GitHub Pages sites, 13-node pipeline with
  the procedural compile_report + live reviewers, layout, heavy-asset
  rule), **Board-Governance** (lanes, laws, `board_state.py` usage incl.
  severity contract + Projects v2 prerequisite, label taxonomy, issue/PR
  forms, CI gate), **Sub-Package-Sync** (current-only doctrine, driver
  commands, prune-resurrection fix, verification contract),
  **HF-Corpus** (docclass-merged v7 facts: 1,650 rows, revs, 27-key GT
  schema, strata vocabulary, P0–P6 + canonical-bytes rule, upload
  helpers), **Offline-Sandbox** (provider profiles, reduced agent profile
  — reporter retired/procedural, reviewers kept — corpus-aligned targets,
  Docker hardening + pins, commands), **Releases** (release train, family
  pins table, deploy surfaces), **FAQ** (10 gotchas incl. prune
  resurrection, tracker warnings, project scope, reporter), plus
  **_Sidebar.md** navigation and **sync-wiki.sh** (clone-or-pull, copy,
  commit + push; `--check` drift mode; syntax-checked). Root docs currency:
  README structure tree gains `docs/wiki/` + wiki paragraph; AGENTS.md
  commands gains `sync-wiki.sh`. Suite green (51 passed / 0 failed).
  **Open prerequisite (human, one-time UI action)**: the wiki git repo is
  NOT materialized until the first page is created in the web UI (no REST/
  GraphQL API for wiki content; first push returns "Repository not found")
  — visit github.com/Exios66/mailroom-dev/wiki once, create any page, then
  `./docs/wiki/sync-wiki.sh` pushes the full content. Evidence: this
  commit.
- **HUB-016** (done 2026-09-01) — **Docs-currency sweep** — systematic
  staleness pass over every surface touched by HUB-014/004/012/015. Fixed:
  sandbox `docs/sister-repos.md` dojo row v0.12.1→v0.12.2;
  `data/fixtures/ATTRIBUTION.md` v0.5.0→v0.6.0; sandbox `CHANGELOG.md`
  [Unreleased] pin bullet updated + HUB-015 Changed entry (reporter
  retirement / zero-LLM compile path / v0.6.0+v0.12.2 alignment / GT
  targets / Docker hardening); `docs/docker-offline.md` documents the
  non-root USER + HEALTHCHECK + the full version-pin table. Verified
  current (no changes needed): root README (architecture map, governance
  tooling, suite list), root AGENTS.md (commands + board law), TASKS.md,
  corpus-eda README/AGENTS (no stale figure counts), entity docs
  (upstream-managed — describes the standalone repo where the pruned dirs
  exist; prune is documented at root level), sandbox README/AGENTS/evals.md
  (HUB-015 pass). Greps for legacy template refs, stale pins, and figure
  counts all clean. Suite: 51 passed / 1 skipped / 0 failed. Evidence: this
  commit.
- **HUB-015** (done 2026-09-01) — **Offline sandbox: current-pipeline
  alignment + reduced agent profile + docclass-merged targets** — human
  directive; one commit. (a) **Version alignment**: sandbox surfaces moved
  off stale mailroom v0.5.0 → **v0.6.0** (`fetch-deps` cli help + tag,
  `overlay.py` hint, README/AGENTS/sister-repos docs); dojo pin bumped
  v0.12.1 → **v0.12.2** (llm-mailroom v0.6.0's own pin; tag verified;
  `uv lock` green); monorepo `[tool.uv.sources]` already resolves the
  current workspace mailroom. (b) **Reduced agent profile — human
  correction applied: the REPORTER agent is retired, reviewers untouched**:
  `components.yaml` moves `reporter` to `retired_agents`, adds the
  `compile_report` node gate; the sandbox eval spec is now the
  **computational procedural reporter** (`compile_report`, kind=nodes,
  observation `compile-report`) — mock + live paths are deterministic
  matter-record assembly, the `get_llm` client acquisition is GONE (zero
  LLM calls on the reporter path; new guard test asserts it). (c) **Full
  docclass-merged GT targets**: `data/fixtures/hf/docclass_mini.jsonl`
  enriched for all 5 corpus doc types with `expected_subclass` from the
  real corpus strata vocabulary (contract→Consulting Agreements,
  merger→all_cash, corporate_record→bylaws, correspondence→attorney_demand,
  insurance→carrier) + `expected_fields` from the 27-key corpus GT schema
  (correspondence: intent=payment_demand + intent_source/confidence/status
  provenance, subject_matter, keywords, claimed_amount, sentiment;
  insurance: policy_number, insured_party, date_of_loss, claimed_amount,
  damages_description); `hf_rows_as_manifest` propagates both into every
  eval row (verified end-to-end: 5/5 rows carry subclass + fields).
  (d) **Docker best practices**: Dockerfile gains non-root `USER sandbox`
  (uid 1000, override documented) + HEALTHCHECK; compose pins all four
  `:latest` images to versioned tags (ollama 0.33.2, vllm v0.28.0, phoenix
  version-20.4.0, minio RELEASE.2025-09-07-16-13-09Z) — zero unpinned
  images remain. (e) **Tests**: suite green 51 passed / 1 skipped / 0
  failed (roster test asserts reporter∉SPECS + gates; pin-guard updated to
  v0.12.2; reviewer evals preserved and passing). Docs currency: AGENTS.md
  gains the Reduced-agent-profile section; docs/evals.md compile_report
  row. Production llm-mailroom graph untouched (sandbox-profile scope per
  human choice). Evidence: this commit.
- **HUB-012** (done 2026-09-01) — **corpus-eda P3 summary counter stale
  (27 vs 30 figures)** — fixed: `visualizations.py::run()` now returns
  `{"figures": 30}` (disk truth — 30 PNGs written by the module), so
  `SUMMARY_REPORT.json` P3 stats match the artifact count. Verified by the
  FULL P0–P6 pipeline in the workspace venv: all 7 phases green, P3 banner
  "30 figures", 1,650 rows / schema v7 / P6 intent coverage 100%
  (350/350, 8/8 classes in test) — in line with the published HF corpus
  (`data 1acd2600`, `card fc1f211c`, API-verified). Determinism held: the
  summary diff is exactly the one-line `figures` correction; all 30 PNGs +
  tables byte-identical; the 19 regenerated interactive HTMLs restored to
  canonical bytes (per-render UUID rule). Published upstream per human
  directive: subtree push was non-fast-forward (cursor ancestry from the
  HUB-013 snapshot, not a graft) — clean 1-commit patch-push to
  Mailroom-Corpus-EDA `main` instead (`43b5232..f3c94f3`, fast-forward),
  cursor re-baselined via snapshot; `sync status` 10/10 in sync. Known
  benign drift: upstream's committed `SUMMARY_REPORT.json` differs from the
  monorepo's in JSON key ORDER only (5 keys, values identical) —
  upstream-side generation artifact, monorepo file is canonical. Evidence:
  `6c343bab` (fix) + upstream `f3c94f3`.
- **HUB-004** (done 2026-09-01) — **Upstream-drift reconciliation** — all
  legs complete, monorepo in sync with every standalone upstream (10/10 via
  `sync_packages.py status`). llm-mailroom leg: pulled `d93894a`+`4e9bf69`
  (`--squash`), heavy-asset prune re-applied, cursor advanced; suite 772
  passed / 36 skipped. llm-mailroom-graph refresh pulled (`fec699d`).
  The-Mailroom tip `fae52e1` reconciled. llm-entity-extraction leg
  (2026-09-01): pulled upstream `4cfac906e`→`2482879f2` — 6 additive
  KANBAN-105 commits (docclass-merged v6 builders/publish machinery:
  `build_docclass_v6.py`, `publish_docclass_v6.py`,
  `attach_original_files.py`, `export_existing_purpose_gt.py`,
  `build_correspondence_append.py`, `build_extra_claims.py` +
  `test_kanban105_docclass_v6.py`); file-level compare pre-verified zero
  overlap with monorepo-side wiring (conflict-free by construction);
  re-applied the heavy-asset prune the subtree merge resurrected
  (`docs/data/`, `docs/posit/`, `docs/posit-src/` — root `.gitignore`
  lines 52-54; gitignore does not apply to tracked files, so explicit
  `git rm --cached` + tree removal); entity suite green 745 passed /
  28 skipped / 0 failed (the 2 transitory failures were the resurrected
  pruned dirs breaking skip-guarded tests — resolved by the prune; all
  skips are documented pruned-asset/live-artifact guards). Monorepo-side
  fixes untouched (guards/markers intact); no stale code imported
  (monorepo = central truth, current-only pulls). Evidence: `a760f698`
  (entity squash) + the prune/archive commit.
- **HUB-014** (done 2026-09-01) — **GitHub governance tooling — templates,
  labels, board state tracker** — human directive: full GitHub integration
  for the hub board. Landed in one commit: YAML issue templates
  (`.github/ISSUE_TEMPLATE/`: hub card / bug / feature / task-TODO +
  `config.yml`, legacy `new-feature.md`+`todo.md` deleted), YAML PR template
  enforcing the hub discipline, declarative label taxonomy
  (`.github/labels.json`: `stage/*` lane mirrors, `attention/*` tags,
  `type/*`, `priority/*`, `domain/*` ×13, `kanban`) +
  `scripts/github_labels.py` (sync/audit), `scripts/board_state.py`
  (live-state tracker: parse open table + archive, `status`/`card`/`check`
  invariants incl. git cross-checks, `sync-issues` label sync,
  `project-init`/`project-sync` Projects v2 mirror with Lane/Owner/Card
  fields, dry-run default), CI gate `.github/workflows/board-governance.yml`
  (board check + label audit blocking; project mirror advisory), docs
  currency in README/AGENTS/TASKS. Verified: `py_compile` green; all 7 YAML
  files parse; `status/check/card/--json` green on the live board (0 errors;
  surfaced hygiene drift → HUB-008/011/013 stale open rows resolved, HUB-011
  properly archived); labels synced live (32 created, `audit` green — 3
  descriptions shortened to GitHub's 100-char limit); all 5 repo issues
  (all closed) retro-labelled with the taxonomy. Open prerequisite (human,
  one-time interactive): `gh auth refresh -s read:project` → `project-init`
  → `project-sync` to stand up the Projects v2 mirror. Suite impact: none
  (hub tooling only). Evidence: this commit.
- **HUB-013** (done 2026-08-31) — **Corpus-EDA v7 reconciliation** — v7
  intent-hydrated corpus (issue #5: aeslc_join/llm_zero_shot hydration of 350
  correspondence rows, intent_source/confidence/status GT columns; HF data
  rev `1acd2600`) is now canonical in the monorepo: subtree-pulled upstream
  (`e68b0631` — run_all P6 default, monorepo phases help text kept), v7
  interactive figures synced byte-identical to upstream `e83250c`
  (`06505812`), full P0–P6 pipeline green in the monorepo venv with
  matplotlib 3.11 renders (`e37100a9`), v7 doc sweep merged (`8d7ce748`),
  schema-v7 bump propagated across The-Mailroom/llm-mailroom/agent-mailroom
  (`41ac512a`), root docs aligned to P0–P6 + `intent_backfill`. Conflict law
  applied: upstream ported the HUB-008/009 rule TEXT to AGENTS.md but not the
  code — monorepo `run_all.py` keeps the summary-write guard + 30-figures
  print (monorepo side wins; upstream ported text matches). Cursor advanced
  to upstream tip `43b5232` via snapshot (`831c9b34`); `sync status` =
  in sync; `py_compile` green. Downloads clone now fully contained in
  upstream — safe to archive locally. HUB-012 remains open (P3 summary
  counter still 27 in v7). Evidence: `831c9b34` + commits above.
- **HUB-011** (done 2026-08-31) — **Prompt-engineer opencode agent adapted
  for the monorepo** — human directive: make the entity repo's GEPA
  prompt-engineer agent operate out of the box in mailroom-dev. Root
  `.opencode/agents/prompt-engineer.md` (workspace bindings: uv-workspace
  commands, per-package AGENTS.md rule, both prompt registries append-only
  — entity `PROMPT_VERSIONS` + mailroom `prompts_docclass.py`, the
  llm-dojo→mailroom direction doctrine, HUB-0NN vs KANBAN-NNN board routing,
  env variables incl. the funding-key gate / `BRAINTRUST_LOGGING` default /
  mailroom `OBSERVABILITY_PROVIDER` Phoenix gotcha / `PYTHONHASHSEED=0` /
  hub-1.x datasets-cache + read-timeout quirks) + the
  `PROMPT_ENGINEER_GEPA_PROVENANCE.md` companion copied verbatim. GEPA
  doctrine (9-step loop, scientific contract, Phases 0–6) preserved — diff
  vs the entity source shows exactly 3 intended binding edits, zero doctrine
  drift. Sessions inside `packages/llm-entity-extraction` keep that package's
  own agent copy (closer project config wins); the global
  `~/.config/opencode` copy stays generic. Board-only card (tooling config,
  single session). Evidence: restart opencode to load; suite impact: none
  (config-only). Archived from the open table by the HUB-014 board-state
  tracker sweep (the archive entry was missing).
- **HUB-010** (done 2026-08-31) — **Full documentation sweep** — human
  directive: update ALL documentation in mailroom-dev. Inventoried ~380
  tracked .md files; scoped the sweep to the OPERATIVE docs (root
  README/AGENTS/TASKS + 10 package README/AGENTS pairs) — historical records
  (memos, skills, wikis, slides) left untouched as standalone-mirror archives
  (llm-mailroom's AGENTS.md itself forbids monorepo-side hand-edits of its
  docs). Fixes: root AGENTS.md gains the Enron suite (74/74, verified green —
  it was missing from both root docs) and corrects the "each package carries
  its own AGENTS.md" claim (3 of 10 packages document conventions in READMEs);
  root README drops the phantom `mailroom-corpus-eda/tests` line (no suite;
  EDA verified via run_all.py P0–P5), documents the two suite-less virtual
  members, clarifies per-package sync cursors (advanced since the issue #2
  baseline), fixes the `uv run pytest` comment; corpus-eda README P3 row +
  run_all.py banner 27→30 (disk truth — 30 PNGs, Reports section and AGENTS.md
  already said 30); Enron AGENTS.md test counts aligned to reality/README
  badge (74 across test_labeler.py + test_content_labels.py). Verified:
  Enron suite 74 passed, claims-data-eda suite 30 passed ("30 tests" claim
  confirmed), run_all.py py_compile green. Spawned HUB-012 (stale P3 summary
  counter). Evidence: `bb854809`.
- **HUB-009** (done 2026-08-31) — **run_all.py subset runs clobber
  SUMMARY_REPORT.\*** — fixed: `run_all.py` now writes
  `reports/SUMMARY_REPORT.json` only when all six phases ran; `--phases`
  subset runs and `--no-interactive` (whose summary would miss the P4
  section) leave it untouched with an explicit stdout notice. Package has no
  test suite, so verification was behavioral: P4-only and `--no-interactive`
  runs leave the summary sha256-identical; a full P0-P5 run rewrites it
  byte-identical to the committed version (determinism holds); scratch
  figure UUIDs restored from git per the canonical-bytes rule; `py_compile`
  green. One transient P3 failure on a `--no-interactive` attempt did not
  reproduce on rerun (phase machinery reported it correctly with exit 1 —
  watch for recurrence). Package AGENTS.md hazard block updated to the new
  behavior; monorepo-side fix, upstream publish deferred to the release
  train (HUB-005). Evidence: `9c0a5321`.
- **HUB-008** (done 2026-08-31) — **Corpus EDA full-fidelity completion** —
  human directive: preserve figures + EDA reports faithfully, full repo in,
  history truncation OK, no republish. Imported the 18 Plotly HTML figures
  (`reports/figures_interactive/`, 74MB) sha256-identical to upstream tip
  `b39245a` (which now equals the monorepo import tip — all 71 pre-existing
  files verified byte-identical; history-truncated content import, not a
  subtree append); un-pruned root `.gitignore`; carved the corpus EDA
  deliverables out of the heavy-assets rule in root AGENTS.md; refreshed the
  stale `packages_sync.json` note — the corpus upstream IS published and
  `sync_packages.py status` shows in sync; aligned root/package docs (README
  prune note, package AGENTS.md canonical-bytes rule: Plotly HTMLs embed a
  random per-render UUID so regenerated variants can never be
  byte-identical). Verification: P4 rebuild green under the shared venv;
  caught + reverted its SUMMARY_REPORT.json clobber (spawned HUB-009); final
  tree sha256-matches upstream. Evidence: `c16cdd18`.
- **HUB-007** (done 2026-08-31) — **Import mailroom-corpus-eda as 10th
  workspace member** — subtree-added the corpus EDA package with FULL history
  appended from a local `monorepo-import` branch (interactive HTML figures
  pruned — regenerable heavy assets; standalone repo keeps them; ignored in
  the monorepo); registered in `sync_packages.py` PACKAGES +
  `packages_sync.json` (cursor at local import tip `9cc339a`, corpus repo NOT
  republished); wired pyproject (virtual member, requires-python>=3.12),
  root dev group (+plotly/seaborn/squarify/huggingface_hub), AGENTS/README
  docs; fixed pandas 3.0/matplotlib 3.11 forward compat (include_groups
  removal, boxplot tick_labels) + deterministic report outputs
  (repo-relative paths, stable diff ordering) so monorepo rebuilds are
  byte-identical; `uv lock`/`uv sync` green, `run_all.py` P0-P5 green under
  the shared venv against the full 1,650-row corpus (v6 rev2). Evidence:
  `39409359` (subtree add), `0a5b498a`, `90b25747`, `989f95bb`.

- **HUB-003** (done 2026-08-30) — **Root documentation + governance foundation** —
  README reworked for the monorepo (structure tree, package↔mirror table, sync
  usage, release flow); `.gitignore` extended (ruff/ipynb/coverage artifacts,
  entity experiment-log prune); AGENTS.md gains sub-package-sync section +
  governance; `governance/TASKS.md` board created. Evidence: `fe4b8d47` (docs
  rework) + the governance commit.
- **HUB-002** (done 2026-08-30) — **Sub-package sync driver (issue
  [#2](https://github.com/Exios66/mailroom-dev/issues/2))** —
  `scripts/sync_packages.py` (status / pull / push / snapshot over git
  subtree, clean-worktree guard) + baseline cursor
  `scripts/packages_sync.json`; all 9 packages verified at upstream tips
  (aligned per issue #2 as of 2026-08-30 19:06 CST). Evidence: `fe4b8d47`,
  issue #2 closed.
- **HUB-001** (done 2026-08-30) — **Monorepo import + workspace wiring** — 9
  packages under `packages/` via git subtree; one uv workspace (dev group +
  `[tool.uv.sources]`, published pins kept); monorepo-aware test repairs
  (monorepo detection, import-shadow `__init__.py` markers, pruned-asset skip
  guards, UTC-stamp and CWD anchoring fixes, notebook regeneration). Evidence:
  `ab4bf9e`, `10c5f8b4`, `fe4b8d47`; all 7 suites green — **2,331 passed /
  72 skipped, 0 failed**.

- **HUB-041** (done 2026-09-03) — **Insurance-claim subclass alignment with
  the v8 synthetic LOB claims** — human directive ("ensure all of our
  insurance claim taxonomies and subclasses are appropriately aligned with
  the new synthetic claims that have been added into the mailroom-corpus
  huggingface dataset"). Phase 1 verified the authoritative vocabulary from
  Hub bytes @ `eafe1ab4` (2,000 rows / 50 strata; insurance = carrier/
  inpatient/outpatient/pde ×150 CMS `claim_type=health` + property ×200
  GNOTHEIA `claim_type=property` + auto ×150 BDR `claim_type=auto`); the
  specialist `claim_type` extract enum already covers health/property/auto —
  aligned, no change. Phase 2 fixed the drifted code catalogs: dojo
  `corpus.py` `DOC_TYPE_SUBCLASSES` + stale `CORPUS_SUBCLASS_SURFACES` +
  `mailroom.py` `HUB_SUBCLASS_INVENTORIES`; entity `sorter_agent.py`
  `INSURANCE_CLAIM_SUBCLASSES` (DOCCLASS/PILOT `doc_subclass` enums can now
  emit property/auto — 350/950 v8 rows were structurally ungradeable);
  The-Mailroom `pipeline_schema.DOC_SUBCLASS_BY_CLASS`; llm-mailroom
  `doc_inventories` fallback catalog + `taxonomy.yaml`/sorter descriptions;
  sandbox `docclass_mini.jsonl` += property/auto rows. Phase 3 added NEW
  prompt versions under the **mailroom naming convention** (human directive
  mid-session; existing `*_docclass_*` keys are frozen experiment identity):
  `sorter_mailroom_v0` (off v7) + `sorter_mailroom_pilot_v0` (off pilot v3)
  extend rule 40 with the two LOB tokens — proven one-region surgical inserts
  (difflib); defaults UNCHANGED until a same-surface A/B; The-Mailroom
  `docclass_prompts.py` mirror updated 31→32 keys with existing entries
  verified byte-identical. Phase 4: **subclass-parity layer** in
  `scripts/taxonomy_parity.py` (ALL classes): Hub GT vocabulary pinned per
  class, covered-by every catalog surface (dojo catalogs, observed-GT table
  exact-check, entity taxonomy `subclasses:` blocks + sorter lists,
  The-Mailroom schema mirror, mailroom doc_inventories fallback + extract
  claim_type inventory), extras only from documented rosters (corporate
  full-enum, legacy FNOL lines, `other` fallback); CI path triggers extended;
  negative mutation checks prove the pre-fix drift is detected. Phase 5:
  `docs/v7-taxonomy.md` §2 v8 subclass-strata note (parsed class blocks
  untouched), CHANGELOG `[Unreleased]`. Aligned-already (verified, no
  change): entity taxonomy.yaml subclasses, llm-mailroom run_hf_pilot
  scoring + local_eval_packs, claims-data-eda `render_eob.py` (CMS-only by
  design, matches corpus exactly), gmail triage clamp (free-text subclass),
  `insurance_claims_specialist_v2` + The-Mailroom registry mirror. HUB-020
  coordination note posted (subclass lines in frozen judge/reviewer prompts
  deferred to its rewrite / HUB-042). Gates: taxonomy parity + board check +
  release chain green; sandbox 58 passed; dojo FULL 365 passed; entity FULL
  756 passed / 28 skipped; The-Mailroom 295 passed; llm-mailroom surgical
  111 passed; `run_hf_pilot.py --check` green @ eafe1ab4 schema v8; v8 dump
  rebuilt + docclass dry-run shows all six insurance subclass GT values
  scoreable (zero LLM spend). Spawned **HUB-042** (frozen docclass prompt
  surfaces + docclass-pilot examples strata). Evidence: `54b8f52f` + this
  commit. **PUSH BLOCKER NOTE (2026-09-03, human-directed skip):** local
  `main` is ahead of `origin/main` by 4 commits — `54b8f52f` + `3f234ae7`
  (HUB-041) plus the parallel session's `9f30fd5e` + `1968d212` (HUB-040
  phases 4–6). Both transports refused: the OAuth credential lacks the
  `workflow` scope (GitHub refuses pushes that create/update
  `.github/workflows/board-governance.yml`, touched by `54b8f52f`) and the
  machine's SSH key is not registered with GitHub; the `gh` token also lacks
  `workflow` scope and the human opted to skip the device-flow authorization.
  Nothing is lost — the commits are on local `main` and a scoped push
  (`gh auth refresh -s workflow` or any credential with `workflow` scope)
  lands everything verbatim; until then origin/main is behind local.
  **RESOLUTION (2026-09-03, later same hour):** the parallel session's scoped
  push landed `88ece63b`/`7c8f8dd6`/`8f7141f1` (HUB-040 close, FULL suite 881
  passed) and carried the HUB-041 commits (`54b8f52f`, `3f234ae7`) to
  `origin/main` as ancestors — the workflow-scope blocker is moot (the
  workflow-file change is already on origin). Only this correction note rides
  the final commit.

- **HUB-040** (done 2026-09-03) — **Relations agent — semantic linking + auditable relations ledger + knowledge graphs** — human
  directive ("add a deterministic + potential LLM agent tasked with linking associated topics, associated documents, and
  semantic relations between archived documents & matters, similar to the philosophy and research methodology of lawyers …
  regularly scanning for new associations … stored in their own tracked auditable log … accessed by the appropriate agents …
  a longitudinal record that allows the mailroom pipeline to improve its operations & efficiency over time" + "generate
  knowledge graphs for relations, connections, and matters"). Landed in `packages/llm-mailroom` (6 commits):
  `storage/relations.py` (relation_edges + relation_embeddings + relation_scan_state + the OWN hash-chained
  `relation_log` — audit hash primitives reused verbatim, `__relations__` scope; WRITER FIX: strictly-monotonic
  timestamps + autoincrement id ordering because `verify_chain` sorts by (timestamp, entry_id) and sub-millisecond
  writes with the uuid tiebreak scrambled prev-links — 20 rapid writes verified, tamper detected);
  `pipeline/relations.py` (deterministic scanner: same-matter / keyword Jaccard / party overlap / embedding cosine via
  the dojo cached model with compute-once per-document embedding cache — O(new + candidates), never O(n²); per-TYPE
  best edges under a per-document cap; upsert novelty from `record_edges.inserted_keys`; post-archive
  `dispatch_relations_scan` at all three terminal manifests (echo pattern, daemon thread); watermark-incremental
  `sweep`; `RelationsSweeper` embedded in `Watcher.start()`; advisory `context_block`); `agents/relations.py`
  (`RelationsAgent` + `mailroom-relations` prompt, registered in `llm/prompts.py` — closed-vocabulary validator that
  refuses unproposed pairs and invented types, so nothing unvalidated reaches the ledger) — CODE-COMPLETE but OFF in
  the pilot (`relations.llm: false`, free model configured for the pilot envelope); hooks: advisory RELATED block in
  `_build_handoff_context` + RELATED section in the Gmail completion echo; `pipeline/relations_graph.py`
  (matter graphs with related-matter bridge nodes, global INTER-matter graph with intra-matter self-loop exclusion,
  doc ego-graphs; GraphJSON + GraphML stdlib, Plotly HTML + PNG optional-dep graceful skip; rendered to
  `<base>/relations/graphs/`, every render a `relations_graph_rendered` ledger event; CLI
  `python -m pipeline.relations_graph`); CLIs `python -m pipeline.relations_scan [--full|--doc|--verify-ledger]`.
  HANG FIX: the real dojo embedder can stall minutes on a first-use model download — `MAILROOM_RELATIONS_EMBEDDINGS`
  env gate (conftest forces off — hermetic law) + 90s bounded load in a worker thread, degrading to "cosine skipped".
  Prompt-registry count 17→18 updated across three suites. Kill-switches: `MAILROOM_RELATIONS`,
  `MAILROOM_RELATIONS_SCAN_SECONDS`, `MAILROOM_RELATIONS_CONTEXT`, `MAILROOM_RELATIONS_LLM`,
  `MAILROOM_RELATIONS_EMBEDDINGS` + taxonomy `relations:` block. Locked decisions honored: post-archive dispatch
  (13-node graph untouched) / deterministic-only pilot / agents+echo injection / all KG formats. Docs currency:
  docs/agents.md §13, docs/configuration.md, docs/gmail-intake.md, CHANGELOG, package AGENTS.md. Suite: FULL
  llm-mailroom **881 passed / 36 skipped / 0 failed**. Evidence: `7a76d1d8`, `8b58ed74`, `aa81643f`, `1968d212`,
  `9f30fd5e`, `88ece63b`, `7c8f8dd6`, this commit.
