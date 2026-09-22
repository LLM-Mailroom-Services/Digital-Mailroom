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

## Specialist subagents — call them, don't impersonate them

Every specialty has a dedicated subagent. Invoke it through the **Task tool**
(`subagent_type: <name>`) instead of improvising outside your expertise;
specialty work done inline is a defect even when it happens to be correct.
The subagent's returned report is the evidence for that slice of the card.
The project specialists (`vllm-specialist`, `modal-specialist`,
`prompt-engineer`, `board-evidence-auditor`) and the global team
(`lucius`, `archivist-file-organizer`, `code-analyst`,
`test-suite-auditor`, `orchestrator-governor`,
`athena-database-agent`, `atom`, `hazel-ui-software-master`,
`jarvis-systems-maximizer`) are `mode: all` — callable through the Task
tool as subagents **and** selectable directly as primary agents (restart
opencode after editing their agent files; verify with `opencode agent
list`).

### Roster

| # | Specialty | `subagent_type` | Call it for | Example invocations |
|---|---|---|---|---|
| 1 | **Data & databases** | `athena-database-agent` | Dataset selection & integration (HF/Kaggle/Braintrust), schema design, ingestion/transformation pipelines, data QA, ML data preparation, SQL/NoSQL optimization | "We need the Enron correspondence dataset loaded into a SQLite schema for the eval loop — design the schema and write the ingestion script." / "The claims-data-eda CSV has 140k rows with inconsistent date formats — build a transformation pipeline that normalizes dates and deduplicates." / "Run a data QA pass on the mailroom-dataset parquet files: check for missing fields, type violations, and duplicate row hashes." |
| 2 | **HuggingFace & data science** | `lucius` | HF downloads/uploads/edits, `datasets`/`transformers` pipelines, EDA, statistical analysis, model training/eval, database upkeep | "Download the `Lucius-Morningstar/mailroom-dataset` dataset v9 split and run an EDA: field coverage, class imbalance, doc-length distribution." / "Upload the new `mailroom-dataset` v9 dataset to HF Hub using the centralized helpers in mailroom-corpus-eda." / "Train a lightweight classifier on the docclass labels and report per-class F1 — use the braintrust experiment logger." |
| 3 | **Prompt engineering** | `prompt-engineer` (project, `.opencode/agents/prompt-engineer.md`) | Run-failure diagnosis, GEPA mutations, prompt A/Bs across the llm-entity-extraction + llm-mailroom surfaces; master diagnostic evaluator and prompt engineer | "v24 left a `term_length` containment dip — diagnose it and produce v25." / "We're stuck at 0.93 on the sorter — what should the next rule be?" / "Candidate v31 didn't beat v30 by much — check the delta against the noise floor and decide if it's plateau territory." / "The contracts specialist is hallucinating on `change_of_control` clauses — reflect on the failure traces and engineer a surgical fix." |
| 4 | **Docs & board** | `atom` | READMEs/wikis/changelogs, doc-drift detection, Kanban board upkeep, inter-agent coordination, repo restructuring | "The llm-mailroom README references a `deploy/` dir that no longer exists — fix the drift." / "Update the governance/TASKS.md board to reflect DMR-029 through DMR-037." / "The docs wiki page `Served-Board.md` is out of sync with the actual board-site API — reconcile and push." |
| 5 | **Software & UI** | `hazel-ui-software-master` | UI/UX, fullstack, HTML/JS/CSS, bug fixes, local network testing, app architecture | "The board-site index.html drag-and-drop broke on Safari — debug and patch." / "Build a local-network test harness for the visualizer so agents can preview pages before deploy." / "Redesign the mailroom-dispatch-board.html filter panel for mobile viewports." |
| 6 | **Systems & repo hygiene** | `jarvis-systems-maximizer` | Performance triage, memory/CPU hogs, disk usage, cache cleanup, repo bloat, process prioritization | "The repo is 4GB — identify the bloat and suggest what to prune." / "My laptop is sluggish during eval runs — profile the processes and recommend prioritization." / "The `.venv` cache is eating 1.2GB — clean it safely without breaking the workspace." |
| 7 | **vLLM serving** | `vllm-specialist` (project, `.opencode/agents/vllm-specialist.md`) | `vllm serve` configs, quantization, multi-LoRA, structured outputs, speculative decoding, tensor/data/expert/context parallelism, KV-cache/memory tuning, diagnosing OOMs and throughput regressions | "Set up `vllm serve` for Llama-3-8B on an A10G with AWQ quantization — I need the exact flags for v0.29.0." / "The Modal-hosted vLLM is OOMing on 4096-token prompts — tune the memory budget and `max-model-len`." / "Enable prefix caching and structured JSON output via xgrammar for the contracts extraction endpoint." / "Diagnose why throughput dropped 40% after upgrading from v0.28.0 to v0.29.0 — check if Model Runner V2 is the cause." |
| 8 | **Modal compute** | `modal-specialist` (project, `.opencode/agents/modal-specialist.md`) | Modal apps (`@app.function`/`@app.cls`/`@app.server`), container Images, Volumes, Secrets, Dicts/Queues, Sandboxes, GPU selection & cost control, scale-to-zero/cold-start tuning, `modal serve`/`deploy`/`run`/`endpoint`, debugging Modal-hosted services | "Deploy `deploy/modal_vllm.py` to Modal with an L4 GPU, `scaledown_window=15min`, and a persistent HF cache volume." / "The Sandbox v2 backend isn't working — check the SDK version and fix the opt-in config." / "Add a `modal.Secret` for `HF_TOKEN` and a `modal.Volume` for the vLLM model cache to the entity extraction deploy app." / "Why is cold-start taking 12 minutes? Tune `startup_timeout` and check if memory snapshots apply." |
| 9 | **Board & repo auditing** | `board-evidence-auditor` (project, `.opencode/agents/board-evidence-auditor.md`) | Verifying board card claims against shipped evidence, auditing modules for incomplete work/TODOs, opening issues and DMR cards for discrepancies, maintaining STATE.md audit trail | "Audit all DMR-011 through DMR-029 cards — verify each claim against actual code and open cards for anything missing." / "The board claims DMR-029 is done, but the deploy file still has `Secret.from_local` — verify and open a defect card." / "Run a repo-wide audit for TODO/FIXME markers in deploy files and document findings in STATE.md." / "Check if the evidence links on done cards actually point to merged PRs, not stale branches." |
| 10 | **File management & organization** | `archivist-file-organizer` (global, `~/.config/opencode/agents/`) | Repo-layout audits and restructures, directory/file grouping and renames, vendor/snapshot tree upkeep (drift refactors, VENDOR.md pins), symlink/workspace hygiene, duplicate-file detection, junk/orphan sweeps | "Audit the sandbox `vendor/` tree and propose a canonical snapshot layout with verified moves." / "Find and sweep `.orig`/`.rej`/editor-swap junk across the monorepo." / "Renaming `mailroom_ui/` internals — map every reference and prove the tree still resolves." |
| 11 | **Concise code analysis** | `code-analyst` (global, `~/.config/opencode/agents/`) | Fast structured verdicts on code you point it at: diff review, root-cause tracing, dead-code confirmation, risk maps of unfamiliar modules — output is verdict + file:line evidence, never a book | "Give me a concise risk map of the pipeline retry ladder before I touch the 429 handling." / "Review this diff for silent-behavior changes." / "Is `hf_rows_as_manifest` dead? Show the search proof." |
| 12 | **Test suite auditing** | `test-suite-auditor` (global, `~/.config/opencode/agents/`) | Auditing suites themselves: dead/weak tests, stub dishonesty (stubs that cannot express real failure modes), unpinned error paths, skip discipline, marker hygiene — the "loud = monitored" enforcement layer | "Which of these loud-error behaviors are actually pinned by tests, and where would a regression slip in green?" / "Audit the stub honesty of the modal-side test doubles." / "Why does deleting the vendor tree turn the drift guard into a skip?" |
| 13 | **Master governance orchestrator** | `orchestrator-governor` (global, `~/.config/opencode/agents/`, `mode: all`) | Planning + dispatch + governance: reads AGENTS.md + the board first, breaks missions into units, briefs specialists like cards, chains them (never impersonates), holds the card lifecycle, closes with evidence; run as PRIMARY (plan/drive a session) or SUBAGENT (any agent hands it a mission) | "Plan and orchestrate the sandbox sweep — route each specialty and keep the card honest." / "I need a dispatch plan for a data + prompts + deploy mission; which agents in what order?" / "Govern this card to done: dispatch, gates, evidence, close." |
| 14 | **Codebase exploration** | `explore` | Fast read-only searches ("where is X", "how does Y work") before you edit — never modifies code | "Where is the `vllm` provider wired into the mailroom pipeline?" / "How does the board_state.py sync-issues command map TASKS.md lanes to GitHub labels?" / "Find all files that import `modal` — I need to know what touches the Modal SDK." / "What's the contract between the entity extraction prompts and the mailroom pipeline prompts?" |
| 15 | **General multi-step** | `general` | Research/execution spanning several specialties with no single owner; tasks that cut across data + prompts + infra | "Build an end-to-end eval pipeline: pull the dataset from HF, run extraction, score with dojo-scoring, and upload results to Braintrust." / "Set up a new package in the monorepo: create the layout, pyproject.toml, AGENTS.md, CI config, and sync_packages.json entry." / "Investigate why the mailroom pipeline is misclassifying insurance claims — check the data, the prompts, and the scorer in sequence." |

> **Note:** `.opencode/agents/STATE.md` is **not** a callable subagent — it is the board-evidence-auditor's live audit state file. Read it before any audit session to avoid repeating past mistakes, but never invoke it via the Task tool.

Rules that make the roster work:

- **One specialist per concern.** Do not ask a subagent to do another
  specialty's job; chain them (e.g. `explore` → `vllm-specialist` →
  `modal-specialist` → `prompt-engineer`).
- **Brief the specialist like a card.** Pass the card ID, the exact scope,
  the files/seams involved, and the evidence contract (what must be green,
  what the report must name). A vague prompt returns a vague report.
- **The caller owns the work.** Subagent output is a report, not a merged
  change: the calling agent writes the files, runs the gates, updates
  `governance/TASKS.md`, and commits — the specialist is evidence, not an
  author of record.
- **Specialists verify current upstream docs** (vLLM stable, Modal SDK,
  HF Hub APIs, Langfuse) before writing configuration; a report that quotes
  a version without checking it is incomplete.
- **Skills are the second layer.** Load the `huggingface`, `langfuse`, or
  `customize-opencode` skill when a task matches its description, and the
  package-local `.cursor/skills/` (openrouter, ollama, modal, langfuse,
  apache-phoenix, braintrust, huggingface, langgraph, dojo-scoring,
  legalbench) for provider/sink depth inside a package. The monorepo-root
  `.opencode/skills/` aggregates the 20 opencode-native skills mirrored from
  mailroom-dev's package `.opencode/skills/` trees (langchain/langgraph,
  langfuse, graphify, eval-engineering, hf-dataset-publish, openrouter-*,
  braintrust) so agents at the repo root auto-discover them; package-level
  copies stay the canonical source for in-package edits.
- `PROMPT_ENGINEER_GEPA_PROVENANCE` is provenance documentation for the
  prompt-engineer agent — not a callable subagent.

New specialist agents live **globally first** (canonical file in
`~/.config/opencode/agents/<name>.md`, available in every worktree), with an
**identical committed mirror** under `.opencode/agents/` (the project copy
is a harmless no-op while identical — keep them byte-identical; drift is a
housekeeping defect, documented in `docs/wiki/Subagents.md`). Project-local
specialists (prompt-engineer, vllm/modal-specialists, board-evidence-auditor,
lucius) stay project files by design — their protocols are repo-specific.
Restart opencode after adding any agent so the Task tool picks it up.

### Devin (CLI) mirror of the roster — dispatch, don't impersonate

Devin agents use the SAME roster, mirrored one-file-per-persona under
`.devin/agents/<name>.md` (flat-file custom subagent profiles; names match
the `subagent_type` column 1:1, plus `explore` and `general` so the names
resolve). A Devin agent dispatches a specialist via the **`run_subagent`
tool** with `profile: <name>` — same dispatch law as opencode: one
specialist per concern, brief like a card, the caller owns the work, chain
never impersonate. The `.opencode/agents/*.md` files stay the canonical
persona source; when a persona changes, update the `.devin/agents/` mirror
in the same commit (same semantics, Devin frontmatter: `name`,
`description`, optional `allowed-tools`, `max-nesting`).

**Discovery location (verified 2026-09-22):** Devin discovers project
profiles from the `.devin/agents/` directory of its **project root** —
for Devin Desktop sessions the project root is the workspace folder the
session opened on, NOT this repo when it sits inside a parent workspace
(e.g. a session rooted at `monorepo_mailroom/` reads
`monorepo_mailroom/.devin/agents/`, not
`monorepo_mailroom/Digital-Mailroom/.devin/agents/`). The committed copy
here serves repos opened as their own root; a parent-rooted workspace
needs the same files mirrored to the parent's `.devin/agents/` (verified
with `devin doctor`, which reports the loaded profile count). Profiles
are read at session start — restart Devin after adding/changing them.

Devin-specific notes:

- **Read-only profiles** — `code-analyst`, `test-suite-auditor`, and
  `explore` carry `allowed-tools` restricted to read/analysis tools (no
  `edit`/`write`).
- **`orchestrator-governor`** carries `max-nesting: 2`, so it can dispatch
  roster specialists as its own children when run as a subagent (specialist
  grandchildren cannot spawn further).
- **Model**: profiles do not pin a `model:` — they run on the default
  subagent router (cheap tier). Pin a `model:` in a profile file only if a
  persona needs a stronger model at higher cost.
- **Monitoring**: the Devin subagent panel shows every dispatch — profile,
  title, status, elapsed time, tool-call count (press `↓` from the input,
  then `Enter`); the caller announces each dispatch inline (profile + card
  scope + expected evidence), and every `run_subagent` call is visible in
  the transcript. Background subagents can be foregrounded, cancelled, or
  resumed from the panel.

## Sync & release at a glance — read before touching any package

The file-and-package flow has **three moving surfaces**; know which one you
are on before you edit:

| Surface | What it is | How it moves |
|---|---|---|
| **Monorepo** (this repo) | Development source of truth | You edit + commit HERE |
| **Standalone mirrors** (`Exios66/<name>`) | Every `packages/*` subtree mirrors an independent repo | Only via `scripts/sync_packages.py` — never hand-edit a mirror |
| **Vendor snapshots** (`packages/local-mailroom-sandbox/vendor/`) | Byte-identical snapshots of the workspace packages | Only via `scripts/sync_vendor.py` |

**The five commands every agent must know:**

```bash
python scripts/sync_packages.py status                          # drift report (expect 10/10 in sync)
python scripts/sync_packages.py push --package <name> [--patch] # publish monorepo deltas upstream
python scripts/sync_packages.py push --all --patch              # the release-train sweep (HUB-005)
python scripts/sync_vendor.py                                   # refresh sandbox vendor snapshots (+ --check gate)
python scripts/release_chain.py cut X.Y.Z --apply --tag         # cut a hub release (dry run without --apply/--tag)
python scripts/release_notes.py X.Y.Z                           # render the GitHub Release body
```

**Two release paths — never conflate them:**

1. **Hub release** (this repo itself): `release_chain.py cut X.Y.Z --apply --tag`
   stamps `[Unreleased]` → section + bumps the hub version + tags; the
   GitHub Release body is generated by `release_notes.py X.Y.Z`.
2. **Standalone package release** (an `Exios66/<name>` repo): cut in that
   package via its own release tooling (e.g. `scripts/release.py --bump` in
   llm-entity-extraction / The-Mailroom, or an explicit annotated tag), then
   **propagate** monorepo-side deltas with `sync_packages.py push` and
   re-baseline the cursor. Bump a consuming pin ONLY at release time of the
   pinned package (`packages/llm-mailroom/src/scripts/bump_dojo_scoring.py`
   for the dojo pin) — never delete a pin line.

**Ownership (DMR-074):** sync & release planning/dispatch is a
`orchestrator-governor` unit-of-work; execution is a `general` mission. When
your card's deliverable must reach a standalone repo, that is a **sync unit
on the card** — chain it, never hand-edit the mirror. Full law: §
[Sub-package sync](#sub-package-sync) below, the runbooks
`docs/wiki/Sub-Package-Sync.md` + `docs/wiki/Releases.md`, and the test-tier
matrix in `docs/TESTING.md` (`--verify-suite` runs a package's suite before
any push).

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

The `mailroom-dataset` dataset family (canonical id
`Lucius-Morningstar/mailroom-dataset`, "Mailroom Dataset v1", v9, 3,302 rows,
pinned tip 46a4d3c2, GT-closure revision 2026-09-13) is the current corpus.
Its frozen
v8 baseline remains `Lucius-Morningstar/mailroom-corpus` (2,000 rows, pinned
eafe1ab4) — itself renamed from `docclass-merged` on 2026-09-02 ("docclass"
was a placeholder). Both are published through the CENTRALIZED helpers in
`packages/mailroom-corpus-eda/src/mailroom_eda/` (`hf_interface`,
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

**DMR namespace (DMR-001, 2026-09-09):** this repo is the standalone
Digital-Mailroom version, cloned from the original `Exios66/mailroom-dev`
monorepo. Its board was restarted fresh: cards use `DMR-00N` and never reuse
the predecessor `HUB-00N` numbers. HUB-era evidence lives in the original
repo and this repo's git history.

The five lanes: `unassigned` (queued and unclaimed — free for the next agent
or team to claim) → `assigned` (claimed, nothing underway) → `in_progress`
(any work exists — label the card before the code, never after) →
`needs_attention` (blocked / review / decision, tagged in Evidence) → `done`
(Archive, append-only; reopen instead of delete).

- **Claim before edit** — one owner per card; claim = lane + Owner name + date.
- **Update, don't duplicate** — work touching an existing card's scope updates
  that card; a discovered-but-undelivered item spawns its own card before the
  parent closes.
- **No silent completion** — `done` requires green suites for the touched
  packages, a clean `git status` for the card's scope, Evidence naming the
  commit(s), and (for synced cards) the GitHub issue closed in the same
  commit. An agent is NOT done until its card says so.
- **Commit discipline** — reference cards: `DMR-00N: <summary>`; stage
  targeted paths only (`git add <explicit paths>` — never `git add .`/`-A`
  or a bare directory). Shared checkout: re-check `git status --porcelain`
  before every commit and unstage files you don't own (HUB-024/HUB-027
  sweep incidents). **DMR prefix is the law for board commits (mailroom-issues
  directive 2026-09-14):** any commit that touches the board — `governance/
  TASKS.md`, `scripts/board_state.py` + board tooling, `.github/` templates/
  workflows that govern the board, `board-site/` — MUST lead with the `DMR-0NN:`
  card it affects (or `DMR-0NN claimed/reopened`). `HUB-0NN` prefixes belonged
  to the original `Exios66/mailroom-dev` board and are never used for NEW board
  work here (DMR-001 lineage law); HUB references may appear only as historical
  notes inside message bodies, never as the commit's routing prefix. **Detailed
  messages (human directive 2026-09-04):** every
  commit carries a fully detailed, explanatory message — subject line plus
  a body that names each file changed and describes what/why (reference the
  card, note test evidence and gates). A terse "Update X" without a body is
  a defect. Rewrites of pushed history are reserved for human-directed
  corrections (see the 2026-09-04 reword session note in TASKS.md). **UTC is
  the canonical timezone (hub#plan-Phase7):** timestamps in evidence, board
  cards, and messages are UTC (ISO-8601, `%Y-%m-%dT%H:%M:%SZ`). Author
  commits as UTC (`TZ=UTC git commit ...`); when reading a foreign timestamp
  use `git show --date=iso-strict` so the offset is explicit. Bare `YYYY-MM-DD`
  card dates are interpreted as UTC by convention (board_state.py flags
  Owner-cell dates for this reason).
- **Issue routing** — board-only for small/single-session/low-risk cards;
  critical or cross-package cards get an issue in the repo where the work
  lands (this monorepo for hub scope, the package repo for package scope).
  Synced issues use the *Board card (DMR-0NN)* template
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
(DMR-002) — a "dispatch board" any agent can view and edit in a browser
at **https://digital-mailroom-theta.vercel.app**. The issues themselves are the
store, which is what makes the site auto-updating + shared. The full
operational doc (API contract, env secrets, redeploy, reconciliation) is
the wiki page `docs/wiki/Served-Board.md` (mirror to
<https://github.com/LLM-Mailroom-Services/Digital-Mailroom/wiki/Served-Board>):

- **Deploy root is `board-site/`** (Vercel project `digital-mailroom`, live
  production; Git integration is live (DMR-004, 2026-09-09) — every push to
  `main` builds the board site. Project Root Directory = `board-site` so BOTH
  CLI and Git-integration deploys build the board site — never leave it unset,
  or a push-triggered Git deploy serves the repo root as a bare file listing
  and 404s `/api/board` (observed 2026-09-09). The dir carries its own
  `board-site/vercel.json`; the repo-root `.vercelignore` limits CLI deploys
  from the repo root to `board-site/`). Serverless functions
  under `board-site/api/`; static `board-site/index.html` is the adapted
  `mailroom-dispatch-board.html` (drag/move/edit + archive UI, filters,
  stats). Project secret `GITHUB_TOKEN` (gh keyring token, repo scope:
  Issues read/write) powers the proxy; never commit it.
- **Read path:** `GET /api/board` lists every open + closed issue labeled
  `kanban` and normalizes it to a board card (id `DMR-0NN` from title/body,
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
- **Write-back:** the UI PATCHes `/api/board/DMR-0NN` on every move/save;
  the proxy swaps the `stage/*` label (+ posts a dated "Board lane move"
  comment for the board mirror law), swaps `priority/*`, rewrites the body
  sections (incl. `### Owner` for agent changes), and closes/reopens for
  archive/restore. It never sets GitHub assignees to agent names (those
  aren't repo users).
- **Config (Vercel env secrets):** `GITHUB_TOKEN` (or `MAILROOM_GH_TOKEN`)
  with repo `LLM-Mailroom-Services/Digital-Mailroom` Issues read/write;
  `MAILROOM_GITHUB_REPO` to override. Never commit these.
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
top-level regular `tests` package and collide when batched. **Read
`docs/TESTING.md` for the tier model (surgical / package unit /
cross-package / full+governance), per-package commands with measured
durations, and the change-type → required-suite matrix.** Docs currency:
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
commit the cursor file. `patch_push` extracts committed blobs (`git ls-tree -r
HEAD` + `git cat-file blob`) — uncommitted work never propagates (DMR-028).

**Sync failures are diagnosed, never silent (DMR-064, hardened DMR-073):**
exit codes are
0 ok / 1 network / 2 dirty-at-entry (or conflicts left in place via
`--keep-conflicts`/`--allow-dirty`) / 3 merge conflict aborted cleanly /
4 other git/internal failure (multi-package runs return the max severity).
**A push is not trusted until its landing is proven (DMR-073):** `push
--patch` verifies with a post-push `ls-remote` probe that the remote tip now
equals the pushed worktree commit — an unchanged tip (the SILENT NO-OP class
that hid the DMR-071 deltas), an unreachable remote, or a foreign concurrent
tip refuses with exit 5/1 and leaves the cursor untouched; the success line
names the POST-push tip and the pushed commit (never the stale pre-push
probe). An empty staged diff is likewise cross-checked against the tree
(`local_ahead_paths`): "empty diff while the monorepo is ahead" is an
extraction-mismatch refusal (exit 5), not a trusted no-delta. Cursors
re-baseline only after a verified landing.
A conflicted `pull` is detected (MERGE_HEAD + `diff --diff-filter=U` +
`ls-files -u` classification: both-modified/add/add/modify-delete), the
worktree is **aborted back to its pre-pull state by default**, and a
structured summary with per-path remediation is printed. To import a
divergent upstream as a reviewable change instead of a local mess, use
`pull --open-pr [--resolve ours|theirs]` — it aborts, creates
`sync/<package>/import-<sha>` (main stays clean), imports upstream with the
chosen resolution strategy, pushes the branch, and opens a `gh` PR against
`main`; the sync cursor never advances until the PR merges. Entry-guard
recovery: a leftover `MERGE_HEAD` from an interrupted run is diagnosed with a
remediation hint instead of a dead "worktree is dirty" refusal.
`pull`/`push`/`snapshot` accept `--json` (JSON Lines, one record per package:
command, package, ok, exit_code, error_class, conflicted_paths, remediation,
cursor_updated, branch, pr_url) and the global `--manifest`/`--repo-root`
overrides for temp-state runs. Hermetic suite: `python3 -m unittest discover
scripts/tests`.

**Push-leg decision tree (DMR-070 — follow it; the wrong leg is a doom
loop):** pick the leg by WHAT the monorepo delta contains:
- **Content-only delta** (files added/modified, nothing deleted): either leg
  works — `push --package <name> --patch` (fast, one fast-forward commit) or
  the full `git subtree push` leg.
- **Deletion-bearing delta** (the monorepo removed tracked upstream paths —
  e.g. a retired agent): **only the full subtree-push leg carries
  deletions** — run `push --package <name>` WITHOUT `--patch`.
  `push --patch` REFUSES deletion-bearing packages (exit 5, error_class
  `verify`, `deleted_paths` in the record) because a content push would
  silently resurrect the deleted files upstream — the v0.6.0 compliance
  removal shipped exactly this trap. If a deletion-bearing push fails
  containment/non-fast-forward, fix the push (fetch upstream, graft), never
  re-add the deleted files.
- **Verify before pushing:** add `--verify-suite` to `push --patch` (and
  `pull`) to run the touched package's pytest suite before anything is
  pushed or any cursor advances (`SYNC_VERIFY_CMD` env overrides the
  default pytest invocation — used by the hermetic tests).

**Post-import verification (DMR-070):** after `pull --open-pr` resolves
conflicts, every ladder-resolved path is blob-compared against BOTH merge
sides; a resolution matching NEITHER side is resolution-introduced content
(the v0.6 `corpus.py` else-branch mangling class) — it is reported loudly on
stderr, carried as `resolution_divergences` in the JSON record, and appended
to the PR body. Exit codes now include **5 verification refused**
(`--verify-suite` failure, or the patch-push deletion guard); severity order
5 > 4 > 3 > 2 > 1 > 0.

**Vendor snapshots (sandbox self-containment, DMR-057/hub#62/DMR-070):**
`packages/local-mailroom-sandbox/vendor/` are TRACKED snapshots that track
the monorepo **workspace packages**, not upstream tags (the drift guard
`tests/test_vendor_drift.py` enforces byte-identity; both VENDOR.md files
document the doctrine). Refresh with `python scripts/sync_vendor.py`
(monorepo root) — it mirrors workspace → vendor carrying BOTH content AND
deletions, and `--check` is a CI-friendly no-op drift gate.
`sandbox fetch-deps` mirrors the workspace when the monorepo layout is
detected and falls back to a loud tag-based refresh for standalone clones.
NEVER tag-refresh the vendored llm-mailroom from the monorepo: the v0.7.1
tag predates the five-class taxonomy removal (59c47401), so a tag-based
re-snapshot resurrects the deleted docclass-era files (the exact revival
this tooling now refuses).

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
