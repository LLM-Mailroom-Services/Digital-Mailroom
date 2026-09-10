# AGENTS.md

Monorepo for the LLM-Mailroom constellation. One uv workspace, one lockfile
(`uv.lock`), one virtualenv. Never add cross-repo imports outside the
workspace — dependency between members resolves via `[tool.uv.sources]`
workspace redirects.

## Layout

- `packages/llm-dojo-scoring` — scoring engine (dist `llm-dojo-scoring`)
- `packages/llm-mailroom` — pipeline (dist `mailroom`, `src/` layout)
- `packages/llm-entity-extraction` — eval loop (flat `agents`/`src`/`config` layout)
- `packages/The-Mailroom` — visualizer (dist `the-mailroom`)
- `packages/agent-mailroom` — walking-office-floor mailroom (dist `agent-mailroom`)
- `packages/local-mailroom-sandbox` — local experiment sandbox (dist `mailroom-sandbox`)
- `packages/Enron-Evaluation-Environment` — corpus feed (virtual member, no build)
- `packages/claims-data-eda` — corpus feed (virtual member, no build)
- `packages/llm-mailroom-graph` — derived graph site (virtual member, no build)
- `packages/mailroom-corpus-eda` — corpus EDA + centralized HF upload helpers (virtual member, no build)

Most packages carry their own `AGENTS.md` with project-specific conventions —
read it before changing code inside a package. `llm-dojo-scoring`,
`agent-mailroom`, and `llm-mailroom-graph` have no AGENTS.md; their READMEs
carry the conventions.

## Commands

```bash
uv sync            # install workspace + dev group into .venv (editable)
uv lock            # after touching any pyproject dependency spec
uv run pytest ...  # run against the shared venv
```

Per-package test suites:

```bash
uv run pytest packages/llm-dojo-scoring/tests
uv run pytest packages/llm-mailroom/src/tests
uv run pytest packages/llm-entity-extraction/tests
uv run pytest packages/The-Mailroom/tests
uv run pytest packages/agent-mailroom/tests
uv run pytest packages/local-mailroom-sandbox/tests
uv run pytest packages/claims-data-eda/tests
uv run pytest packages/Enron-Evaluation-Environment/tests
```

Governance tooling (hub board + labels; see README "GitHub governance
tooling" for the full command list):

```bash
python scripts/board_state.py status            # live board snapshot (--json for machines)
python scripts/board_state.py check             # board invariants; exit 1 on structural errors
python scripts/board_state.py sync-issues       # push board lane labels -> synced issues (--apply)
python scripts/board_state.py pull-issues       # reverse-sync served-board lane moves back into TASKS.md (--apply)
python scripts/github_labels.py audit           # label taxonomy drift (CI gate)
python scripts/taxonomy_parity.py               # doc-class taxonomy drift (CI gate, HUB-019 §65A)
python scripts/release_chain.py status          # hub release-chain snapshot (tags, sections, version)
python scripts/release_chain.py check           # chain invariants; exit 1 on structural errors (CI gate)
python scripts/release_chain.py cut X.Y.Z       # stamp [Unreleased] -> section + bump hub version (dry run; --apply/--tag)
python scripts/release_notes.py X.Y.Z           # render the GitHub Release body from the changelog section + PRs + commits (template: .github/RELEASE_TEMPLATE.md)
./docs/wiki/sync-wiki.sh                        # push docs/wiki/ source to the GitHub wiki (--check for drift)
```

## HF Hub uploads

The `mailroom-corpus` dataset family (renamed from `docclass-merged`,
2026-09-02 — "docclass" was a placeholder) is published through the CENTRALIZED
helpers in `packages/mailroom-corpus-eda/src/mailroom_eda/` (`hf_interface`,
`dataset_export`, `docclass_uploader`, `intent_backfill`) — never ad-hoc
upload code. See `packages/mailroom-corpus-eda/AGENTS.md` and the
`huggingface` opencode skill for the full workflow (cast-safe metadata,
line-boundary-safe JSONL, sha256 verification, surgical card renders,
blind-config label guard, issue #5 intent hydration).

## Governance & task board

`governance/TASKS.md` is the monorepo's task board and the single source of
truth for cross-agent task state: what is assigned, in progress, needs
attention, and done. Read it FIRST every session, before any task. It is the
simplified counterpart of
`packages/llm-entity-extraction/governance/MESSAGE_BOARD.md` (same laws,
fewer steps); package-scoped work keeps its own board.

The four lanes: `assigned` (queued/claimed, nothing underway) →
`in_progress` (any work exists — label the card before the code, never after)
→ `needs_attention` (blocked / review / decision, tagged in Evidence) →
`done` (Archive, append-only; reopen instead of delete).

- **Claim before edit** — one owner per card; claim = lane + Owner name + date.
- **Update, don't duplicate** — work touching an existing card's scope updates
  that card; a discovered-but-undelivered item spawns its own card before the
  parent closes.
- **No silent completion** — `done` requires green suites for the touched
  packages, a clean `git status` for the card's scope, Evidence naming the
  commit(s), and (for synced cards) the GitHub issue closed in the same
  commit. An agent is NOT done until its card says so.
- **Commit discipline** — reference cards: `HUB-00N: <summary>`; stage
  targeted paths only (`git add <explicit paths>` — never `git add .`/`-A`
  or a bare directory). Shared checkout: re-check `git status --porcelain`
  before every commit and unstage files you don't own (HUB-024/HUB-027
  sweep incidents). **Detailed messages (human directive 2026-09-04):** every
  commit carries a fully detailed, explanatory message — subject line plus
  a body that names each file changed and describes what/why (reference the
  card, note test evidence and gates). A terse "Update X" without a body is
  a defect. Rewrites of pushed history are reserved for human-directed
  corrections (see the 2026-09-04 reword session note in TASKS.md).
- **Issue routing** — board-only for small/single-session/low-risk cards;
  critical or cross-package cards get an issue in the repo where the work
  lands (this monorepo for hub scope, the package repo for package scope).
  Synced issues use the *Board card (HUB-0NN)* template
  (`.github/ISSUE_TEMPLATE/hub_card.yml`), carry the `kanban` + lane labels
  (taxonomy: `.github/labels.json`, applied by `board_state.py sync-issues`),
  and are mirrored both ways: the card's Issue column links the issue, lane
  moves land as issue comments.

The board is computationally readable: `scripts/board_state.py` parses the
live file (open table + archive) into JSON, validates the board's own laws
(`check` — structural contradictions exit 1, hygiene drift is warned), and
mirrors lane state onto GitHub issues and an optional Projects v2 board.
Run `check` before closing any card that touches the board; the CI gate
(`.github/workflows/board-governance.yml`) enforces it on every change to
`governance/`, `scripts/`, or `.github/`.

### Served Kanban board (`board-site/`, Vercel)

The board also runs as a **live, issue-backed web site** on Vercel
(HUB-055) — a "dispatch board" any agent can view and edit in a browser
at **https://mailroom-dev.vercel.app**. The issues themselves are the
store, which is what makes the site auto-updating + shared. The full
operational doc (API contract, env secrets, redeploy, reconciliation) is
the wiki page `docs/wiki/Served-Board.md` (mirror to
<https://github.com/Exios66/mailroom-dev/wiki/Served-Board>):

- **Deploy root is `board-site/`** (Vercel project `mailroom-dev`, live
  production; project Root Directory = `board-site` so BOTH CLI and
  Git-integration deploys build the board site — never leave it unset, or a
  push-triggered Git deploy serves the repo root as a bare file listing and
  404s `/api/board` (observed 2026-09-09). The dir carries its own
  `board-site/vercel.json`). Serverless functions
  under `board-site/api/`; static `board-site/index.html` is the adapted
  `mailroom-dispatch-board.html` (drag/move/edit + archive UI, filters,
  stats). Project secret `GITHUB_TOKEN` (gh keyring token, repo scope:
  Issues read/write) powers the proxy; never commit it.
- **Read path:** `GET /api/board` lists every open + closed issue labeled
  `kanban` and normalizes it to a board card (id `HUB-0NN` from title/body,
  lane from `stage/*`, priority from `priority/*`, desc/evidence from the
  `### Task` / `### Evidence plan` body sections, archived = closed).
- **Agents = the `### Owner` body section (never GitHub assignees).** The
  board displays the actual agent/persona/harness conducting the work
  (e.g. `opencode (GLM-5.3-Flash)`, `lucius`, `human`, `unclaimed`) from the
  issue's `### Owner` section, synced from the TASKS.md Owner column — NOT
  the issue's GitHub assignee (the repo owner's profile would otherwise show
  on every card). `sync-issues` pushes `### Owner`/`### Task`/`### Evidence
  plan`/`### Card ID`/`### Lane` into each synced issue body, so the served
  board always reflects the real agent, description and evidence trace.
- **Always reads the most-recent state.** `GET /api/board` is served with
  `Cache-Control: no-store`, and the frontend auto-refreshes every 30s + on
  tab refocus, so the board never shows stale data. The served board is
  LIVE-ONLY: if the proxy is unreachable it shows an offline banner, never a
  snapshot. The canonical board stays `governance/TASKS.md` — `pull-issues`
  imports served-site moves back into TASKS.md, `sync-issues` pushes
  TASKS.md truth into the issues (labels + body sections).
- **Write-back:** the UI PATCHes `/api/board/HUB-0NN` on every move/save;
  the proxy swaps the `stage/*` label (+ posts a dated "Board lane move"
  comment for the board mirror law), swaps `priority/*`, rewrites the body
  sections (incl. `### Owner` for agent changes), and closes/reopens for
  archive/restore. It never sets GitHub assignees to agent names (those
  aren't repo users).
- **Config (Vercel env secrets):** `GITHUB_TOKEN` (or `MAILROOM_GH_TOKEN`)
  with repo `Exios66/mailroom-dev` Issues read/write; `MAILROOM_GITHUB_REPO`
  to override. Never commit these.
- **Canonical board reconciliation:** TASKS.md stays the source of truth.
  After edits made on the served site (which write issues, not TASKS.md),
  run `python scripts/board_state.py pull-issues` — it reports issue-side
  lane moves that haven't landed in TASKS.md yet, then `--apply` rewrites
  the Lane cells + appends a dated `pull-issues` Evidence note. `sync-issues`
  still pushes board → labels; `pull-issues` is the reverse leg.
- **Card↔issue law is now the norm:** because the site reads `kanban`
  issues, every board card must have a synced issue (one card = one issue,
  `kanban` + `stage/*` + `priority/*` + `domain/*` labels). Open a card's
  issue from the `hub_card.yml` template and fill the Issue column, or the
  card won't appear on the served board.

Test gates: run the surgically relevant suite for the package you touched by
default; run that package's FULL suite (and any dependent suites) for
significant changes (packaging/imports, cross-cutting refactors, scoring).
Suites run one package per pytest invocation — several packages ship a
top-level regular `tests` package and collide when batched. Docs currency:
when a change alters behavior described by `README.md`, `AGENTS.md`, or
`governance/TASKS.md`, update those files in the same commit.

## Sub-package sync

Every package mirrors an independent `Exios66/*` repo. `scripts/sync_packages.py`
(status / pull / push / snapshot, cursor in `scripts/packages_sync.json`)
reconciles the mirrors; the monorepo is the development source of truth.

**Release-train sweep (the HUB-005 propagation):** the all-packages one-liner
is `python scripts/sync_packages.py push --all --patch` — one command fetches
every upstream tip, lands the monorepo delta as a single fast-forward commit
per package, and re-baselines the cursors; follow with
`sync_packages.py status` (expect 10/10 in sync, 0 monorepo-ahead) and
commit the cursor file. **Race caveat (2026-09-04 incident):** `patch_push`
copies the package subtree from the WORKTREE while the clean-tree guard runs
only once at script start — never run a sweep while any `packages/*` file is
uncommitted in a parallel session (a mid-run save gets swept upstream);
hardening tracked as HUB-044.

## Workspace rules

- Member dependency lines keep their published git pins (release builds via
  plain `pip install .` depend on them). Dev redirection happens ONLY through
  `[tool.uv.sources]` tables — never delete a pin line to "fix" resolution.
- Bump a pin only when cutting a release of the pinned package (see
  `packages/llm-mailroom/src/scripts/bump_dojo_scoring.py`, release-time only).
- Hub releases (the monorepo itself) follow the release chain (HUB-024):
  accumulate changes under `CHANGELOG.md` `[Unreleased]`, then
  `python scripts/release_chain.py cut X.Y.Z --apply --tag` — it stamps the
  section with today's date, bumps the hub `pyproject.toml` version, and
  creates the annotated `vX.Y.Z` tag (`mailroom-hub vX.Y.Z` message).
  Committing and pushing stay with the caller; a GitHub Release is cut from
  the changelog section. `scripts/release_chain.py check` + the
  `release-governance.yml` gate enforce tag↔section parity and semver order.
- Heavy assets (docs demos/screenshots, example PDFs, report archives) are
  pruned from this repo — keep them out; reference the upstream repos.
  EXCEPTION: the mailroom-corpus-eda EDA deliverables (`reports/figures/`,
  `reports/figures_interactive/`, `reports/tables/`, `SUMMARY_REPORT.*`) are
  tracked in full per human directive (HUB-008) — never prune them. Second
  exception: the claims-data-eda real-sample PDFs under `docs/examples/`
  (8 small text PDFs, human directive 2026-09-04, HUB-046) — tracked in
  full, regenerate only via `scripts/render_samples.py`.
- Deploy configs (Dockerfile, nixpacks.toml, railway.json) inside each
  package are still standalone-repo aware; build images from the package
  directory as before.
