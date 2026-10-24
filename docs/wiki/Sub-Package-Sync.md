# Sub-package sync

Standalone `Exios66/*` repositories are the authoritative package sources.
Digital-Mailroom imports committed sources into `packages/` (git subtrees)
and generates sandbox vendors. Hub-owned wiring, governance, board, and
integration tooling are implemented in the hub.

## Active package scope (DMR-093, 2026-10-23)

Sync and release integration now select five core packages: `llm-dojo-scoring`,
`llm-mailroom`, `local-mailroom-sandbox`, `The-Mailroom` and
`mailroom-corpus-eda` (the only virtual member). Enron and claims remain external
feeds, preserved as complete hub checkouts on
[`feature/enron-evaluation-environment`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/enron-evaluation-environment/packages/Enron-Evaluation-Environment) and
[`feature/claims-data-eda`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/claims-data-eda/packages/claims-data-eda) at `59c879d9fb4480084e53137e2e9fb25650933944`.
The prune landed as #167 on top of #162; `main` carries none of those trees.
Historical seven-member release/test evidence retains its original scope.
For restoration use a separate checkout; reconcile membership, sync, dependencies
and tests before any selective import, without replacing current root metadata.

## Source ownership (DMR-091, user-directed)

| Source repository | Owns |
| --- | --- |
| llm-dojo-scoring | ALL scoring engine logic and metrics |
| llm-mailroom | The document-processing pipeline |
| local-mailroom-sandbox | The core offline/local and Modal/vLLM GPU testing interface for that pipeline |
| The-Mailroom | The visualizer used by BOTH sandbox and llm-mailroom |
| Mailroom-Corpus-EDA | Core corpus EDA and centralized HF upload helpers |

The corpus repositories likewise own their package implementations. Read the
source repository's governance before edits. Implement, test, and commit in
that standalone checkout first; then import the committed source here. Never
implement a package change in the hub and push it back. Workspace and vendor
copies are integration artifacts, never competing implementation sources.

## Import doctrine

- Fetch current standalone main branches before an import or hub PR review.
  Compare source tips with `scripts/packages_sync.json` cursors and package
  trees; import completed source changes first. Serialize shared-checkout
  fetches or use dedicated refs with `--no-write-fetch-head` because the
  driver shares `FETCH_HEAD`.
- Review overlapping PR changes for work already shipped in the source.
  A remaining package fix belongs in its standalone source first. Do not
  silently retain hub-authored package behavior during conflict resolution.
- Record source SHAs, import commits, cursor verification, and test evidence.
  `status` recomputes drift against live upstreams; hub-ahead paths require
  explanation as integration outputs or correction through the source.
- Do not rewind current sources to stale snapshots. Review conflicts by
  ownership and source commits, not a blanket "monorepo truth wins" rule.

## The driver

```bash
python scripts/sync_packages.py status                              # live drift report; --json for machines
python scripts/sync_packages.py pull --package <name> --squash --verify-suite
python scripts/sync_packages.py snapshot --package <name>            # content-verified cursor re-baseline
```

`pull` refuses a dirty worktree by default. Squash imports keep source history
out of the hub log. The driver skips merges when the source tip is already
contained. `snapshot` refuses cursor advancement past missing source blobs
(gitignored prunes are exempt); do not use `--force` to bypass missing content.
After imports, preserve documented hub-only heavy-asset exclusions without
changing authoritative package behavior.

A conflicted pull aborts to its pre-pull state by default. Recovery options
`--keep-conflicts`/`--allow-dirty` are explicit; interrupted MERGE_HEAD state
gets remediation. `pull --open-pr` produces a reviewable import branch/PR;
the cursor advances only after merge. Resolve against authoritative source
commits, reviewing every ladder-resolved path. Content matching neither side
is reported as `resolution_divergences` on stderr, in JSON, and in the PR body.
`--verify-suite` runs the imported package's suite; `SYNC_VERIFY_CMD` overrides
the runner. Exit codes: 0 ok / 1 network / 2 dirty / 3 conflict-aborted /
4 git-internal / **5 verification refused** (severity 5 > 4 > 3 > 2 > 1 > 0).
Global `--manifest`/`--repo-root` support isolated state runs.

## Runbook: import a standalone change (step by step)

Written so a small model can follow it literally. Do the steps in order; if a
step's output does not match what is written, STOP at that step and use its
"If not" line. Never improvise a different command.

**Vocabulary.** *Source* = the standalone repo `Exios66/<name>` (the only place
package code is written). *Hub* = this repo. *Cursor* = the SHA recorded per
package in `scripts/packages_sync.json` (the last source commit imported).
*Import* = copying new source commits into `packages/<name>/`.

**Step 0 — use a clean, private worktree.** `pull` refuses a dirty tree, and
the shared checkout is often dirty with other agents' work. Never stash or
discard someone else's changes; make your own checkout instead:

```bash
git fetch origin main
git worktree add -b dmr-NNN-<slug> ../Digital-Mailroom-dmrNNN origin/main
cd ../Digital-Mailroom-dmrNNN
```

**Step 1 — see what is new.**

```bash
python3 scripts/sync_packages.py status
```

Each package prints `in sync` or `N new upstream commit(s)`. Only packages
that say `new upstream commit(s)` need an import. The `[N file(s)
monorepo-ahead]` suffix is normal explained drift, not an error.
If not: a package says `in sync` but you expected a change, the change is not in
the *source* yet (see "Where a dependency bump really lands" below). Stop.

**Step 2 — look at exactly what will come in.**

```bash
git fetch https://github.com/Exios66/<Repo>.git main:refs/remotes/src/<name> --no-write-fetch-head
git log --oneline <synced_sha>..refs/remotes/src/<name>
git diff --stat <synced_sha> refs/remotes/src/<name>
```

`<synced_sha>` is the package's `synced_sha` in `scripts/packages_sync.json`.
Write down the commit list; it goes in the PR body.

**Step 3 — try the plain pull.**

```bash
python3 scripts/sync_packages.py pull --package <name> --squash
echo "exit=$?"
```

| You see | Meaning | Do |
| --- | --- | --- |
| a squash commit and exit 0 | import done, cursor advanced | go to Step 5 |
| `refusing to pull: worktree is dirty`, exit 2 | you skipped Step 0 | do Step 0, retry |
| `CONFLICT ... The pull was ABORTED`, exit 3 | normal when hub files drifted from the source | Step 4 |
| exit 1 | network problem | retry once, then report |
| exit 4 | git/internal error | stop, paste the output into the card |

**Step 4 — on conflict, import through a PR branch.**

```bash
python3 scripts/sync_packages.py pull --package <name> --squash --open-pr --resolve ours
```

`ours` keeps the hub's copy of the conflicted files. That is correct when the
conflicted files are NOT in the upstream diff (check the Step 2 `git diff --stat`; the PR diff must contain only those files). If the upstream commits DO
touch a conflicted file, do not use `ours` blindly: ask the board owner.
The driver makes branch `sync/<name>/import-<sha12>`, merges, and, if the test
suite passes, pushes and opens a PR. It may print `could not return to main`
and leave you on the sync branch: that is expected in a worktree where `main`
is checked out elsewhere; just stay on the branch. Read stderr for `resolution_divergences`;
any entry there must be reviewed against the source commit before merge.

If it prints `verify-suite FAILED` and does not push, go to Step 4b.

**Step 4b — `--verify-suite` failed: is it the import or was it already red?**
The driver's gate is `pytest -x`, so any pre-existing failure blocks it. Run the
package's suite on the branch AND on the base commit and compare totals:

```bash
uv run --frozen pytest packages/<name>/tests -q | tail -3          # on the import branch
git checkout -q --detach origin/main
uv run --frozen pytest packages/<name>/tests -q | tail -3          # baseline
git checkout -q sync/<name>/import-<sha12>
```

(`llm-mailroom` uses `packages/llm-mailroom/src/tests`.) Identical pass/fail
counts mean the import changed nothing: push the branch yourself and open the
PR with `gh pr create`, putting BOTH count lines in the body. Different counts
mean the import broke something: do not push; report the new failing tests.
A red baseline is its own bug; open or update a board card for it.

**Step 5 — advance the cursor.** The PR flow never touches the cursor, so do
it once the tree really equals the source. Run `status` FIRST and check that
`upstream=` is the exact commit you imported: `snapshot` records the CURRENT
upstream tip, so if the source moved while you worked (it did on 2026-10-23:
The-Mailroom #44 landed an hour after #45) the cursor would claim commits you
never imported. If the tip moved, go back to Step 3 and import again. Then:

```bash
python3 scripts/sync_packages.py snapshot --package <name>
python3 scripts/sync_packages.py status      # that package must now say "in sync"
```

Commit the changed `scripts/packages_sync.json` (in the import PR, as its own commit) (card-prefixed message). If
`snapshot` refuses with missing content, the import is incomplete: do NOT pass
`--force`.

**Landing the import PR.** Merge it with a MERGE COMMIT (`gh pr merge <n>
--merge`), not a squash: git-subtree finds the previous import point by the
`Squashed 'packages/<name>/' changes from A..B` commit in main's history, and a
squash-merge discards it, so the next pull starts from an older base and
produces spurious conflicts (as happened with The-Mailroom on 2026-10-23).
Main reads BLOCKED on the phantom `ci` check (DMR-080); `--admin` is the
known workaround.

**Step 6 — verify vendors after a llm-dojo-scoring, llm-mailroom or sandbox import.**
The sandbox vendors the first two packages. A sandbox import can reintroduce
its standalone snapshots over newer hub-generated copies, even when the source
change only updates a lockfile. The-Mailroom and mailroom-corpus-eda are not
vendored; skip this step for them.

```bash
python3 scripts/sync_vendor.py --check
```

If that check reports drift, regenerate with the driver, then check again:

```bash
python3 scripts/sync_vendor.py
python3 scripts/sync_vendor.py --check
```

Never hand-edit vendor files. Review generated changes against the imported
workspace packages. If `pull --verify-suite` stopped before advancing its
cursor, it leaves the import merge in place: regenerate vendors, run the full
package suite on the corrected tree, confirm the upstream tip has not moved,
then use Step 5's content-verified `snapshot`. Preserve the subtree merge and
squash metadata when landing the PR.

**Step 7 — close out.** Run the package's full suite (`docs/TESTING.md`), then
record in the card: source SHA range, import PR, exact pass/fail/skip counts,
and any red baseline. `python3 scripts/board_state.py check` must not gain
new errors.

### Where a dependency bump really lands

- **Python lockfiles.** A package's own `uv.lock` (e.g.
  `packages/local-mailroom-sandbox/uv.lock`) is a SOURCE file: it only changes
  through the source repo + `pull`. The hub's own resolution is the ROOT
  `uv.lock`; it is hub-owned and is bumped here with
  `uv lock --upgrade-package <pkg>` (then `uv lock --check`), as its own card
  and commit. An import normally does not change the root lock (it can if the imported
  package changed its `pyproject.toml`; `uv lock --check` tells you).
- **npm lockfiles** (`packages/The-Mailroom/ui/package-lock.json`) are source
  files and arrive by `pull`.
- **Dependabot PRs must be merged in the source repo.** Dependabot also runs on
  forks. `LLM-Mailroom-Services/mailroom-sandbox` is a FORK of
  `Exios66/local-mailroom-sandbox` (verify with `gh repo view <repo> --json
  isFork,parent`); merging dependabot PRs there changes the fork only and the
  hub never sees them. Before merging any dependabot PR, run that check and
  merge only on the repo named in `scripts/packages_sync.json` (`url`).
- **Read the manifest diff of every dependabot PR, not the title.** A grouped
  security PR can carry an unannounced MAJOR (2026-10-23: The-Mailroom #43 moved
  `tailwindcss` 3 -> 4 under the title "4 updates" and broke `npm run build`).
  Before merging, in the PR's `package.json`/`pyproject.toml` diff look for any
  changed major version, then run the real build (`cd packages/The-Mailroom/ui
  && npm ci && npm run build && npm audit`) or the package suite. If a major
  sneaks in, fix it in the source repo first (an `overrides`/constraint PR),
  never in the hub, then re-run the import.
- A bump already present in the source lock (check the version in the package
  `uv.lock`) is obsolete: close the dependabot PR instead of merging.

## Legacy outbound tooling

`push`, `push --patch`, and `push --all --patch` are historical commands and
are forbidden for package delivery. The former HUB-005 release train and
DMR-070 push-leg decision tree do not authorize hub-to-source changes.
Existing deletion guards, post-push landing verification, and cursor safety
checks remain tooling safeguards, not permission to publish hub package copies.

## Vendor snapshots (sandbox self-containment)

`packages/local-mailroom-sandbox/vendor/` tracks imported workspace packages;
the sandbox drift guard enforces byte-identity. After importing committed
source changes, regenerate copies; never edit vendors by hand or push them
back as source.

```bash
python scripts/sync_vendor.py           # imported workspace -> vendor, content AND deletions
python scripts/sync_vendor.py --check   # no-op drift gate
```

`sandbox fetch-deps` mirrors the workspace in hub layout; standalone clones
use their configured tag-based refresh. Never tag-refresh hub vendors: stale
tags (such as llm-mailroom v0.7.1 before the taxonomy removal) resurrect removed
paths. Hub vendor regeneration is an integration output.

## Verification contract for an import session

1. Record current source tips, cursors, and explained integration drift.
2. Run the imported package's FULL suite and relevant dependent suites;
   a subtree pull is a significant change. Run packages separately.
3. Verify source-owned fixes came from committed standalone sources, and
   hub-only wiring and documented heavy-asset exclusions remain intact.
4. Regenerate vendors and run `sync_vendor.py --check` plus sandbox gates.
5. Verify cursors; finish with a clean card scope and board Evidence naming
   source/import commits and exact pass/skip/fail counts.
