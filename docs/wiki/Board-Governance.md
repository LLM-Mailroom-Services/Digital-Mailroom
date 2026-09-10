# Board governance

`governance/TASKS.md` is the monorepo's task board and the **single source
of truth** for cross-agent task state. Read it FIRST every session, before
any task. Package-scoped work keeps its own board (e.g.
`packages/llm-entity-extraction/governance/MESSAGE_BOARD.md`).

## The four lanes

| Lane | Meaning |
| --- | --- |
| `assigned` | Queued or claimed, nothing underway — no draft, no diff, no branch |
| `in_progress` | ANY work exists and an owner holds it — label the card before the code, never after |
| `needs_attention` | Blocked / review / decision — the Evidence note says which (`needs:` / `review:` / `decision:`) |
| `done` | Finished, verified, evidenced — moved to the Archive (append-only; reopen instead of delete) |

## The laws

- **Claim before edit** — one owner per card; claim = lane + Owner name + date.
- **Update, don't duplicate** — work touching an existing card's scope updates that card; discovered-but-undelivered work spawns its own card before the parent closes.
- **No silent completion** — `done` requires green suites for touched packages, clean `git status` for the card's scope, Evidence naming the commit(s), and (for synced cards) the GitHub issue closed in the same commit. An agent is NOT done until its card says so.
- **Commit discipline** — reference cards: `HUB-0NN: <summary>` (or `HUB-0NN claimed/reopened` in the body). **Targeted staging (HUB-029):** `git add <explicit paths>` only — never `git add .` / `-A` / a bare directory; this is a shared checkout, so re-check `git status --porcelain` before every commit and unstage anything you don't own (HUB-024/HUB-027 sweep incidents).
- **Issues vs board** — small/single-session/low-risk cards are board-only; critical or cross-package cards get an issue via the *Board card (HUB-0NN)* template, linked both ways, lane moves mirrored as issue comments, closed in the same commit that archives the card.

## The tracker (machine-readable board state)

`scripts/board_state.py` parses the live board into JSON, validates the
board's own laws, and mirrors lane state onto GitHub:

```bash
python scripts/board_state.py status                # snapshot (--json for machines)
python scripts/board_state.py card HUB-014          # one card + commits referencing it
python scripts/board_state.py check                 # invariants; exit 1 on structural errors
python scripts/board_state.py check --with-issues   # + verify synced issues/labels via gh
python scripts/board_state.py sync-issues --apply   # push board-derived labels onto issues
python scripts/board_state.py pull-issues --apply   # reverse-sync served-board lane moves into TASKS.md
python scripts/board_state.py project-init          # one-time Projects v2 mirror setup
python scripts/board_state.py project-sync --apply  # mirror the open table into the project
```

## The served dispatch board (`board-site/`, Vercel)

> Full operational doc: [[Served-Board]] (layout, API contract, env secrets,
> redeploy workflow).

Since HUB-055 the board also runs as a **live, issue-backed web site** — a
dispatch board any agent can view and edit in a browser at
**https://digital-mailroom-theta.vercel.app**, deployed from the monorepo to Vercel
(project `digital-mailroom`; deploy root = `board-site/`). The GitHub issues
are the store, which makes the site auto-updating + shared:

- **Read:** `GET /api/board` lists every open + closed issue labeled
  `kanban` and normalizes each to a board card (id from title/body, lane
  from `stage/*`, priority from `priority/*`, desc/evidence from the
  `### Task` / `### Evidence plan` body sections, archived = closed).
- **Write:** the UI PATCHes `/api/board/HUB-0NN` on every move/save. Lane
  moves swap the `stage/*` label and post a dated "Board lane move"
  comment (the mirror law); priority swaps, body-section rewrites, and
  assignee changes PATCH the issue; archive = close, restore = reopen.
- **Config (Vercel env secrets):** `GITHUB_TOKEN` (or `MAILROOM_GH_TOKEN`)
  with Issues read/write on `LLM-Mailroom-Services/Digital-Mailroom`; `MAILROOM_GITHUB_REPO` to
  override. Never commit these.
- **Reconciliation:** TASKS.md stays canonical. After served-site edits
  (which write issues, not TASKS.md), run `board_state.py pull-issues` to
  see issue-side lane moves that haven't landed, then `--apply` to rewrite
  the Lane cells + append a dated Evidence note. `sync-issues` is the
  board → labels leg; `pull-issues` is the reverse.
- **Card↔issue law is now the norm:** the site only shows `kanban` issues,
  so every board card needs a synced issue (one card = one issue, `kanban`
  + `stage/*` + `priority/*` + `domain/*` labels) opened from the
  `hub_card.yml` template, or it won't appear on the served board.

`check` **errors** are structural contradictions (duplicate IDs, invalid
lanes, malformed issue links, missing attention tags, phantom commit
references); **warnings** are hygiene drift (pending-archive rows,
unclaimed cards with commits, stale `in_progress`). `--strict` fails on
warnings too. The CI gate
[`.github/workflows/board-governance.yml`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/.github/workflows/board-governance.yml)
runs `check` + the label audit + the doc-class taxonomy parity gate
(`scripts/taxonomy_parity.py`, HUB-019 §65A — fails when the canonical
five-class surfaces disagree; also triggered by changes to the taxonomy
surfaces themselves) on every change to `governance/`, `scripts/`, or
`.github/`.

The Projects v2 mirror (the *mailroom-hub board* project with
Lane/Owner/Card fields) needs a one-time interactive scope grant:
`gh auth refresh -s read:project`, then `project-init` + `project-sync`.

## Label taxonomy (issue flair)

`.github/labels.json` is the declarative source of truth —
`scripts/github_labels.py sync` creates/updates repo labels, `audit`
reports drift (CI-gated). Groups:

| Group | Labels |
| --- | --- |
| Stage (lane mirrors) | `stage/assigned` · `stage/in-progress` · `stage/needs-attention` · `stage/done` |
| Attention tags | `attention/blocked` · `attention/review` · `attention/decision` |
| Type | `type/bug` · `type/feature` · `type/task` · `type/docs` · `type/governance` · `type/release` · `type/sync` |
| Priority | `priority/critical` · `priority/high` · `priority/medium` · `priority/low` |
| Domain | `domain/hub` · `domain/governance` · `domain/tooling` · `domain/<package>` × 10 |
| Sync marker | `kanban` (this issue mirrors a HUB-0NN card) |

Issue forms live in `.github/ISSUE_TEMPLATE/` (board card, bug, feature,
task/TODO); the PR form (`.github/PULL_REQUEST_TEMPLATE/pull_request.yml`)
enforces the board discipline.
