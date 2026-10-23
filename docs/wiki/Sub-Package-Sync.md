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
The prune PR depends on #162, whose two feeder trees must match that commit.
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
