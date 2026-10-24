# Contributing to Digital Mailroom

Thanks for helping. This page is the short path from "I cloned it" to "my PR
merged". [`AGENTS.md`](AGENTS.md) is the full rulebook and wins on any
conflict.

## 1. Know which repo your change belongs in

Digital Mailroom is an **integration hub**. The package code is authored
elsewhere:

| You want to change… | Do it in… | Then |
| :--- | :--- | :--- |
| Scoring or metrics (`llm-dojo-scoring`) | [`Exios66/llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring) | Import into the hub |
| The pipeline (`llm-mailroom`) | [`Exios66/llm-mailroom`](https://github.com/Exios66/llm-mailroom) | Import into the hub |
| The visualizer (`The-Mailroom`) | [`Exios66/The-Mailroom`](https://github.com/Exios66/The-Mailroom) | Import into the hub |
| The sandbox (`local-mailroom-sandbox`) | [`Exios66/local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox) | Import into the hub |
| Corpus EDA / HF uploads (`mailroom-corpus-eda`) | [`Exios66/Mailroom-Corpus-EDA`](https://github.com/Exios66/Mailroom-Corpus-EDA) | Import into the hub |
| Workspace wiring, `scripts/`, `board-site/`, `governance/`, `docs/`, `.github/` | **This repo** | Open a PR here |

**Never edit `packages/*` in this repo**, and never hand-edit
`packages/local-mailroom-sandbox/vendor/`. Package copies are integration
outputs. Author and test the change in the standalone checkout, commit it
there, then import it with `python scripts/sync_packages.py pull --package
<name> --squash` (see [Sub-Package Sync](docs/wiki/Sub-Package-Sync.md)).
Pushing hub copies back to a standalone repo is forbidden.

## 2. Set up

You need Python 3.11+, [`uv`](https://docs.astral.sh/uv/), and a current Node LTS (only
for the `board-site` tests; development uses Node 22).

```bash
git clone https://github.com/LLM-Mailroom-Services/Digital-Mailroom.git
cd Digital-Mailroom
uv sync                                                              # one workspace, one .venv
git config --local commit.template "$(git rev-parse --show-toplevel)/.gitmessage"   # once per clone
```

Credentials (HF, OpenRouter, Langfuse, Modal) go in a gitignored `.env`, never
in a commit. The suites are network-free by default.

## 3. The card workflow

All work is tracked on [`governance/TASKS.md`](governance/TASKS.md), also
served live at <https://digital-mailroom-theta.vercel.app>.

1. **Read the board first.** Look for a card that already covers your work.
   If one exists, update it. Don't open a parallel card.
2. **Claim it.** Move an `unassigned` card to `assigned` and set the Owner to
   your name and the date (UTC). The moment you make a first edit, branch or
   run, it becomes `in_progress`. Label the card *before* the code.
3. **No card yet?** Small, single-session, low-risk work can be board-only.
   Critical or cross-package work gets a GitHub issue from the
   [Board card template](.github/ISSUE_TEMPLATE/hub_card.yml); fill in the
   card's Issue column.
4. **Keep the card current**, with status and Evidence as you go. Blocked?
   Move it to `needs_attention` with a tagged note (`needs:`, `review:` or
   `decision:`). Anything discovered but not delivered gets its own card
   before yours closes.
5. **Close with proof.** `done` needs green suites for what you touched, a
   clean `git status` for the card's scope, and Evidence naming your commits.
   Then move the card to the Archive.

## 4. Make the change

```bash
git switch -c dmr-0NN-short-description
# …edit…
python scripts/board_state.py check       # if you touched the board, scripts or .github
```

Run the **surgically relevant** suite for what you touched, and the package's
full suite for significant changes. One package per `pytest` invocation:

```bash
uv run pytest packages/llm-dojo-scoring/tests
python3 -m unittest discover scripts/tests     # hub governance tooling
(cd board-site && node tests/api.test.js)      # served-board API proxy
```

> **CI does not run the package suites.** Your local run is the gate. Quote
> the exact pass/skip/fail counts in the card's Evidence and in the PR body.
> [`docs/TESTING.md`](docs/TESTING.md) has the tiers and a change-type →
> required-suite matrix.

### Testing rules in brief

- A bug fix ships **in the same PR** as a regression test that was red before
  the fix and green after.
- Hand-compute expected values, and never copy the implementation's formula.
- No tautological asserts. Don't mock the unit under test. Use honest
  doubles that can express real failures.
- Skips name their reason, and they are not a hiding place.

The full list is in [`AGENTS.md` § Test discipline](AGENTS.md#test-discipline).

### Docs currency

If your change alters behavior described in `README.md`, `AGENTS.md` or
`governance/TASKS.md`, update those files **in the same commit**. Changing
`docs/wiki/`? Run `./docs/wiki/sync-wiki.sh --check` to see wiki drift.

## 5. Commit

- Subject: `DMR-0NN: <verb> <concrete behavior>`. The DMR prefix is mandatory
  for anything touching the board, `scripts/`, `.github/` or `board-site/`.
  `HUB-0NN` prefixes are historical only.
- Body: name each changed file and say what and why, plus your test evidence.
  A terse "Update X" is a defect. See [`docs/COMMIT_MESSAGES.md`](docs/COMMIT_MESSAGES.md).
- Stage **explicit paths** (`git add path/a path/b`), never `git add .` or
  `-A`. Re-check `git status --porcelain` first, because checkouts get shared.
- Times in evidence and cards are **UTC** (`TZ=UTC git commit …`).

## 6. Open the pull request

Use the [PR template](.github/PULL_REQUEST_TEMPLATE/pull_request.yml): one PR
is one card's scope. Include the card ID, a summary, the exact test counts and
any skipped gates. Two things look scary but are known:

- Every PR to `main` reads `BLOCKED` on a phantom required `ci` status (DMR-080).
  That is not a test failure.
- `board-governance.yml` runs `board_state.py check` on changes to
  `governance/`, `scripts/` and `.github/`. Run it locally first.

## 7. Releases (maintainers)

Hub releases follow `release_chain.py cut X.Y.Z --apply`, then `uv lock`, then
merge, then tag the merged tip. Package releases happen in their standalone
repos. Details: [Releases](docs/wiki/Releases.md).

## Working with agents

This repo is built for human + AI-agent teams. Specialist personas
(`.opencode/agents/`, mirrored in `.devin/agents/`) cover docs, UI, data, prompts,
vLLM, Modal and audits. If an agent edits your checkout, the same card, commit
and evidence rules apply. See [Subagents](docs/wiki/Subagents.md).

## Stuck?

[Troubleshooting](docs/wiki/Troubleshooting.md) covers the common snags, the
[Glossary](docs/wiki/Glossary.md) decodes the jargon, and the
[FAQ](docs/wiki/FAQ.md) has the gotchas. For security problems see
[`SECURITY.md`](SECURITY.md).
