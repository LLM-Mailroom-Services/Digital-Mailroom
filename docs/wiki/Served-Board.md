# The served dispatch board (`board-site/`, Vercel)

Since HUB-055 (predecessor monorepo) the Kanban board also runs as a **live,
issue-backed web site** — a dispatch board any agent (or the human) can view
and edit in a browser at **https://digital-mailroom-theta.vercel.app**
(standalone deployment: DMR-002, Vercel project `digital-mailroom`). The
GitHub issues are the
store, which is what makes the site auto-updating + shared: every change
is written straight through to a synced issue, so no deploy of content is
ever needed — only a deploy of the code that reads/writes it.

The issues are the single source for the site's cards, but **the board
remains canonical**: `governance/TASKS.md` is still the truth, and the two
are reconciled by the `board_state.py` legs (see below).

## What you see

- **Live cards** across the five lanes (unassigned → assigned → in-progress →
  needs-attention → done/archive), plus priority, agents, and date, fetched
  from every issue labeled `kanban` (open + closed). Unclaimed work lands in
  the **Unassigned** triage column.
- A **LIVE / OFFLINE badge** reflecting whether the board API is reachable.
- A **cross-board switcher** (`board-tabs`, DMR-005): the `DMR Board` chip is
  active and `HUB Board ↗` links to the predecessor's served board
  (https://mailroom-dev.vercel.app) — the HUB board carries the mirrored
  `DMR Board ↗` link back.
- **Drag/move + edit + new-card + archive UI**, filters and stats, and a
  delete → close (archive) interaction.
- Local storage is demoted to **preferences + operator identity** — the
  card data always comes from GitHub.

## Deploy root and layout

The deploy root is **`board-site/`** (Vercel project `digital-mailroom`;
project Root Directory = `board-site` so both CLI and Git-integration
deploys build the board site, which carries its own
`board-site/vercel.json`; the repo-root `.vercelignore` keeps CLI deploys
from the repo root limited to `board-site/`):

```
board-site/
├── index.html          static single-page dispatch board (fetches /api/board)
├── vercel.json         clean URLs + api maxDuration
├── api/
│   ├── board.js        GET  live cards (labels=kanban) · POST new card
│   └── board/[id].js   PATCH write-back for one card
└── lib/
    └── gh.js           zero-dependency tokenized GitHub REST proxy
```

The serverless functions are zero-dependency (Node 18+ `fetch` only); no
build step, no framework.

## The API contract

### Read — `GET /api/board`

Lists every open + closed issue labeled `kanban` and normalizes each to a
board card:

- `id` — `DMR-0NN` matched from the issue title/body
- `lane` — from the `stage/*` label (`stage/in-progress` → `in-progress`);
  closed issues read as `done`
- `priority` — from the `priority/*` label
- `desc` / `evidence` — from the `### Task` / `### Evidence plan` body
  sections
- `agents` — **the `### Owner` body section** (the agent/persona/harness
  doing the work, e.g. `opencode (GLM-5.3-Flash)`, `lucius`, `human`,
  `unclaimed`), falling back to GitHub assignees only when absent — never a
  blanket GitHub profile
- `archived` — true when the issue is closed
- Plus issue number, timestamps, and the issue's HTML URL.

### Write-back — `PATCH /api/board/DMR-0NN`

The UI PATCHes on every move/save. Only the changed keys need to be sent:

- `lane` → swaps the `stage/*` label **and posts a dated "Board lane move"
  comment** (the board mirror law); `priority` swaps the `priority/*` label.
- `desc` / `evidence` / `title` → rewrites the corresponding body sections
  (Lane/Priority cells are preserved) + the issue title.
- `agents` → rewrites the `### Owner` body section. It never sets GitHub
  assignees (agent names aren't repo users and GitHub rejects them with
  422).
- `archived: true` → **closes** the issue (lands in the archive);
  `archived: false` → **reopens** it.
- Any other HTTP method → `405`; malformed card ids → `400`; missing token –
  `500`.

Operator identity rides the `X-Mailroom-Actor` header (bounded to 60 chars)
and is recorded on lane-move comments.

### Create — `POST /api/board`

Creates a new card as a `kanban` issue (title + body sections + labels), so
the site can spawn a card without leaving the board. The write path is proven
end-to-end: DMR-007 was created through `POST /api/board`, landed as a kanban
issue in this repo, displayed live, and its lane was corrected through the
PATCH leg.

## Body sections are the data store

The served board renders **only** from the issue's body sections (never a
snapshot). The `### Owner`, `### Task`, `### Evidence plan`, `### Card ID`,
`### Lane`, `### Priority` and `### Domain` sections are what the read path
displays. `sync-issues` pushes these from `governance/TASKS.md` (the source
of truth) into every synced issue, so the board shows the real agent,
description and evidence trace:

```bash
python scripts/board_state.py sync-issues --apply   # labels + body sections
```

The section parser/writer is glue-proof (headings are never joined onto a
section's content) and recovers bodies previously corrupted by an old bug.

## Config / env (Vercel secrets — never commit)

| Secret | Purpose |
| --- | --- |
| `GITHUB_TOKEN` (or `MAILROOM_GH_TOKEN`) | GitHub token with `LLM-Mailroom-Services/Digital-Mailroom` Issues read/write (`stage/*`, `priority/*`, `kanban`, body, comments, assignees). The deployed production secret uses the gh-keyring token scoped to the repo. |
| `MAILROOM_GITHUB_REPO` | Optional override of the repo the board reads/writes (default `LLM-Mailroom-Services/Digital-Mailroom`). |

## Deploy / redeploy

**Git integration (live since DMR-004, 2026-09-09):** a push to `main` builds
`board-site/` automatically — the Vercel GitHub App is installed on the
`LLM-Mailroom-Services` org and project `digital-mailroom` is Git-linked
(production branch `main`, Root Directory `board-site`). CLI deploys remain
the fallback: run them from the **repo root** — the project Root Directory
`board-site` is applied to the uploaded tree, and the repo-root
`.vercelignore` limits the upload to `board-site/`:

```bash
vercel link --project digital-mailroom --cwd board-site   # once: link the checkout
vercel --prod --cwd .                                     # repo root: ships board-site/ only
```

Deploying from inside `board-site/` **with the Root Directory set** fails
("The specified Root Directory 'board-site' does not exist") because the
setting is applied on top of the uploaded tree — deploy from the repo root
(above) instead.

**Only two Vercel projects back the boards (DMR-007):** `digital-mailroom`
(this repo's board) and `mailroom-dev` (the predecessor's board). The
duplicate `board-site` project (`board-site-gamma.vercel.app`, linked to the
predecessor with Root Directory unset) was deleted — do not recreate it;
this repo's deploy root is the `board-site/` directory inside
`digital-mailroom`.

**Pin the production alias after every deploy.** The HUB-059 lesson (a
parallel `--prod` deploy hijacking the shared alias) still applies; the
standalone project owns `digital-mailroom-theta.vercel.app`, so a normal
`--prod` deploy moves that domain to the verified build. After an
out-of-band deploy, re-assert it:

```bash
vercel alias set <your-deployment-url> digital-mailroom-theta.vercel.app --token "$VERCEL_TOKEN"
```

**The project's Root Directory must be `board-site`.** With it unset, every
push-triggered Git-integration deploy builds the REPO ROOT — the live site
becomes a bare directory listing and `/api/board` 404s (observed 2026-09-09,
recovered by re-setting the Root Directory via the API + redeploying). Set /
repair it via the API, then deploy from the repo root:

```bash
curl -X PATCH -H "Authorization: Bearer $VERCEL_TOKEN" -H "Content-Type: application/json" \
  -d '{"rootDirectory": "board-site"}' https://api.vercel.com/v9/projects/digital-mailroom
```

Then verify against the alias:

```bash
curl https://digital-mailroom-theta.vercel.app/api/board        # 200 + JSON cards
curl -i https://digital-mailroom-theta.vercel.app/api/board/DMR-001   # 405 (PATCH only)
```

A `PATCH` smoke move (e.g. lane → same lane, or a round-trip that restores
it) exercises the write-back against a real issue without churn; a no-op
patch produces zero label/comment churn.

## Reconciliation with the canonical board

The served board writes **issues**, not `governance/TASKS.md`:

- **site → board:** after edits made on the served site, run
  `python scripts/board_state.py pull-issues` — it reports issue-side lane
  moves that haven't landed in TASKS.md yet, then `--apply` rewrites the
  Lane cells + appends a dated `pull-issues` Evidence note.
- **board → site:** `python scripts/board_state.py sync-issues --apply` is
  the reverse leg — it pushes board-derived `stage/*` / `priority/*` /
  `attention/*` / `domain/*` / `kanban` labels **and the `### Owner` /
  `### Task` / `### Evidence plan` / `### Card ID` / `### Lane` body
  sections** onto the synced issues, so the served board reflects the real
  agent, description and evidence trace from TASKS.md.
- **The card↔issue law is the norm:** the site only shows `kanban` issues,
  so every board card needs a synced issue (one card = one issue, opened
  from the `.github/ISSUE_TEMPLATE/hub_card.yml` template) with the full
  link in the card's Issue column — otherwise the card won't appear on the
  served board. Lane moves on the board are mirrored as issue comments, and
  the issue is closed in the same commit that archives the card.

## Always read the most-recent state

The board is **live-only** and never shows stale data:

- `GET /api/board` is served with `Cache-Control: no-store`.
- The frontend auto-refreshes every 30s and on tab refocus
  (`visibilitychange`), and shows a 🕒 freshness badge for the last read.
- If the proxy is unreachable it shows an explicit offline banner — it never
  falls back to a baked-in snapshot.

An agent keeping the board honest runs `sync-issues --apply` after editing
`governance/TASKS.md` (pushes the new agent/desc/evidence/labels into the
issues the served board reads) and `pull-issues --apply` after editing on the
served site (pulls lane moves back into TASKS.md).

## UX / interactions (agent + human)

- **Live agent filters:** the Agent filter chips are derived from the agents
  actually present on the live cards — no hardcoded roster. Any agent/persona/
  harness name (e.g. `opencode (GLM-5.3-Flash)`) becomes a one-click filter
  with a live count. The agent input in the card editor offers datalist
  suggestions from the same set.
- **Manual refresh + context:** the ⟳ button (or the `r` key) re-reads the
  live board on demand, and a `⎇ repo` badge shows the backing repository.
  `n` opens a new card, `a` toggles the archive, `/` focuses search.
- **GitHub trace:** every card carries a `↗` link straight to its synced issue,
  and the edit modal shows `created`/`updated` timestamps + the issue link —
  evidence cross-referencing without leaving the board.
- **Import is read-only + gated:** the live-only doctrine (HUB-059) means a
  JSON import only previews a snapshot in the local tab — it never writes to
  GitHub — and now confirms intent before applying.
- **Archived history pointer:** the archive footer notes that the full
  append-only history lives in `governance/TASKS.md` (the served archive only
  shows issue-backed cards).

The `board-governance.yml` CI gate runs `board_state.py check` (+ the label
audit + taxonomy parity) on every change to `governance/`, `scripts/`, or
`.github/`.