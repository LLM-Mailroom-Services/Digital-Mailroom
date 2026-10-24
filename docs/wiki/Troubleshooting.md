# Troubleshooting

Symptoms we have actually hit, with the fix. Cross-check [[FAQ]] for the
policy questions.

## Environment and tests

**`zsh: no matches found: --include=*.md`**
zsh expands unquoted globs. Quote them (`--include='*.md'`) or pass the
directory instead.

**`uv run` rewrote `uv.lock` and I didn't change any dependency.**
The committed lock disagrees with a `pyproject.toml` (often a version bump
without `uv lock`). Don't fold the diff into unrelated work. Fix it as its own
carded commit (`uv lock`, verify with `uv lock --check`). Use
`uv run --frozen …` for read-only runs that must not touch the lock.

**Tests collide or import the wrong package when I run two suites together.**
Several packages ship a top-level `tests` package. Run **one package per
pytest invocation** ([[Getting-Started]]).

**A suite fails and I did not touch that package.**
Reproduce it on clean `main` (`git stash`, rerun) before you start debugging.
The package may carry a real defect that belongs in its standalone repo. The
2026-10-23 measurements in `docs/TESTING.md` record the known failures (for
example The-Mailroom's `intake_bert` errors). Report the difference, don't
paper over it.

**`test_modernbert_feeder_resolves_sibling` skips or fails.**
It depends on a local `mailroom-ml` sibling checkout. It skips when the
sibling is missing and fails when a present sibling's `feeder_status()` is not
ok. That is a machine-local condition, not a hub regression.

**Many `docs/examples/samples` or `data/parquet` tests are skipped.**
The real-sample and real-corpus fixtures are not in a fresh checkout. Those
behaviors are untested in your environment. Say so in your card's Evidence.

**CI is green but I never ran the package tests.**
That's expected, since CI doesn't run them. Your local run is the gate.

## Sync and vendors

**`sync_packages.py pull` refuses to run: dirty worktree (exit 2).**
Commit or stash first. `--allow-dirty` exists but is an explicit recovery
option, not a default.

**Pull ended with exit 3 (conflict-aborted).**
The pull was rolled back to its pre-pull state. Resolve by source ownership:
the standalone commit wins; never take a blanket ours/theirs. Review any
`resolution_divergences` printed on stderr against the source commits.

**`sync_packages.py status` says "N file(s) monorepo-ahead".**
The hub copy differs from the cursor's upstream snapshot. That is a signal,
not a to-do. Don't push hub copies back; if a change is wanted, author it in
the standalone repo first and import it.

**`sync_vendor.py --check` fails, or `test_vendor_drift.py` fails.**
You (or an import) changed `llm-mailroom` or `llm-dojo-scoring` without
refreshing the sandbox vendor snapshots. Run `python scripts/sync_vendor.py`
and commit the regenerated tree with the import. Never hand-edit
`packages/local-mailroom-sandbox/vendor/`.

**Parallel fetches clobber each other.**
The sync driver uses the shared `FETCH_HEAD`. Serialize fetches or use
dedicated refs with `--no-write-fetch-head`.

## Board and GitHub

**`board_state.py check` fails on a card I didn't touch.**
Run `check` on clean `main` first; the board can carry pre-existing errors
(phantom card references, stale cards). Fix only what your change introduced,
and open a card for the rest.

**Every PR shows `BLOCKED` with a required `ci` check that never reports.**
A phantom required status context (DMR-080). It is not a test failure, so
don't chase it in your code.

**I edited a card on the served board and TASKS.md didn't change.**
The site writes GitHub issues, not TASKS.md. Run
`python scripts/board_state.py pull-issues` (then `--apply`) to bring lane
moves back ([[Served-Board]]).

**A card doesn't appear on the served board.**
Every card needs a synced issue with `kanban` + `stage/*` + `priority/*`
labels. Open one from the `hub_card.yml` template and fill the card's Issue
column ([[Board-Governance]]).

**`project-*` says the token lacks `read:project`.**
One-time: `gh auth refresh -s read:project`.

## Commits

**My commit picked up files I didn't write.**
The checkout is shared. Stage explicit paths only, and run
`git status --porcelain` before every commit; unstage what you don't own.

**`git commit -m "DMR-0NN: …"` skipped the template.**
`-m` and `-F` bypass the editor. The message still needs the full body; see
[`docs/COMMIT_MESSAGES.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/COMMIT_MESSAGES.md).
