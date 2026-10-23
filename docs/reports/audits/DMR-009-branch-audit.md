# DMR-009 — complete branch and superseded-PR audit

UTC snapshot: 2026-10-23T02:48:43Z. Scope: `LLM-Mailroom-Services/Digital-Mailroom` remote heads, local branches, open PRs and worktree occupancy. This audit does not delete branches in authoritative standalone repositories.

## Result

Closed **#154, #153 and #152** as superseded by **#162**, in that order so #154 was closed before deleting its #152 base. All three exact heads are ancestors of PR162 baseline `762402acac51edfb10ebd75a057b9ead7161ed61`; no unique commits remain outside that integration branch. PR162 is still open: these are superseded closures, not claims that their fixes shipped to main.

Deleted **five remote branches**, reducing the captured set **15 → 10**, and the one unoccupied, merged local release branch. Preserved **#156, #159 and #160** because their changes are absent from162. Refreshed existing **#157** as the audit/evidence PR rather than losing its earlier cleanup history. Kept the closed155 branch because it contains useful unique tests; a closed PR alone does not establish supersession.

The latest/upcoming five-package pruning PR belongs to **DMR093 / issue165**; no fixed PR number is assumed. Keep its occupied local `t3/surgical-hub-prune` branch and the Enron/claims preservation branches. PR162 and pruning work may advance concurrently; their later tips are not cleanup targets.

## Every remote branch

The table records **before** SHAs, so the deletion/retention decisions remain reproducible. Full dates, ancestry/divergence, after SHAs, action timestamps and PR head/base relations are in [the machine manifest](DMR-009-branch-manifest.json).

| Branch | Before SHA | Associated PR | Action | Evidence / continuing role |
|---|---|---|---|---|
| `claude/dmr-086-storage-race` | `a2695d480f95fcb4f775d57c625866754d9bca63` | #153 | DELETE | Deleted after closing #153; exact ancestor of PR162 (storage fix, documentation and regression tests). |
| `claude/dmr-087-dojo-length-guard` | `c0173ecee90e5f1e90ea8e734ff40de4b75d71f2` | #152 | DELETE | Deleted after closing #152 and dependent #154; exact ancestor of PR162 (dojo length guards). |
| `claude/dmr-090-local-ci` | `b4c7fa67b39d7ceac6506e689aa9a358949c12e3` | #156 | KEEP | Kept open #156: unique CI runner, pre-push hook and 53 tests absent from PR162; gate registry must follow five-package pruning. |
| `coderabbit/add-pull-request-tests/dfc5f5b1` | `f96552050b5caad4a150dd328af67ec8200b428a` | #160 | KEEP | Kept open #160: two unique governance test files absent from PR162; policy/doc changes in its broad title are already on main. |
| `coderabbit/document-pr-152-functions/541e0d1e` | `2250a55a43e4a57b4d236a0e42bed7c27e6ebe82` | #154 | DELETE | Deleted after closing #154 first; exact ancestor of PR162 (scorer documentation). |
| `coderabbit/pr149-comprehensive-tests/d720b152` | `387c386e23eec6797642f16c60a6690939b5e06d` | #155 | KEEP | Kept closed #155: unique negative CLI/validation tests absent from #160/#162; stale live-board assumptions need adaptation under DMR085 / issue148. |
| `codex/dmr-091-feeder-reconciliation` | `762402acac51edfb10ebd75a057b9ead7161ed61` | #162 | KEEP | Kept active #162 and its occupied root worktree. This branch can advance concurrently. |
| `codex/dmr-092-pre-integration-v091` | `fc282d87ac03f13af0de53cfc0c6e7decbeaa450` | #164 | DELETE | Deleted remote and unoccupied local branch after merged #164; exact ancestor of main. |
| `dmr-009-branch-prune` | `82a649b027e9bb984f430fd1c54fa229083af712` | #157 | KEEP | Kept/refreshed existing #157 as this audit vehicle; preserves its original 23-branch-prune history. |
| `feature/agent-mailroom` | `f5d97d98678773865d7f18af046b15ee47b1fd08` | — | KEEP | Kept intentional DMR079 package-preservation branch, including its additional regression-test commit. |
| `feature/claims-data-eda` | `59c879d9fb4480084e53137e2e9fb25650933944` | — | KEEP | Kept explicit DMR093 preservation branch for upcoming five-package pruning. |
| `feature/enron-evaluation-environment` | `59c879d9fb4480084e53137e2e9fb25650933944` | — | KEEP | Kept explicit DMR093 preservation branch for upcoming five-package pruning. |
| `main` | `f3c56ec56eb38cbb79c590a8f59ffa012a0efd04` | — | KEEP | Kept protected default/release branch. |
| `production-staging` | `2d1ff1c912046d5bd6c7db1fea89c2b2a9a7ccda` | — | DELETE | Deleted obsolete release-closeout snapshot; 0 commits ahead / 23 behind main; no open PR, worktree or observed configured deployment role. |
| `staging` | `30ae291cd1c7d59daf704d8f3ea90120c292b21f` | #159 | KEEP | Kept open #159: unique v9.2 consumer adoption/provenance tests; PR162 still uses pipeline v9.1. Must be reviewed source-first. |

## Local branches and worktrees

Initial inventory: four local heads and three worktrees. This session created an isolated cleanup worktree at `/private/tmp/dmr009-branch-audit`, adding local `dmr-009-branch-prune`, and removed only `codex/dmr-092-pre-integration-v091` at `fc282d87ac03f13af0de53cfc0c6e7decbeaa450` with `git branch -d` after confirming its containment in main.

Remaining local heads: `main`, `codex/dmr-091-feeder-reconciliation`, `dmr-009-branch-prune`, `t3/surgical-hub-prune`. The latter three are occupied. The detached `/private/tmp/dmr091-v091-release` worktree and all active worktrees were retained. No `develop` branch exists. Full occupancy and SHAs are captured in the manifest.

## Why the other PRs remain

- **156 / DMR090:** `scripts/ci.py`, `scripts/githooks/pre-push`, `scripts/tests/test_ci.py` are absent162. Five-package pruning must also update its seven-suite registry.
- **159:** adoption commits `20fa08d5`, `959219fa`, `30ae291c` change the pipeline corpus revision to v9.2 and add provenance/override tests. PR162 and the inspected authoritative pipeline main still use v9.1; newer producer data alone does not make consumer adoption obsolete. Review/adopt in the authoritative source first.
- **160 / DMR085:** its current diff consists of `scripts/tests/test_test_discipline_board.py` and `scripts/tests/test_testing_documentation.py`, both absent162/main. The old policy/docs title describes more than the current diff.
- **Closed155 / DMR085:** commit `387c386e` adds unique negative CLI/validation tests absent160/162. Hardcoded old owners, lanes and board-only assumptions prevent merging verbatim. Preserve the branch for targeted adaptation under the existing DMR085 / issue148 scope; no new implementation is part of this cleanup.
- **157 / DMR009:** its original `82a649b0` is the only committed record of the prior23-branch prune and reopened card. This session refreshed it without rewriting that history.

## Recovery and deletion guards

Before any closure or deletion, created `/Users/morningstar/.t3/backups/digital-mailroom-branches-20261023T024145Z/repository.bundle` with `git bundle create --all`, and captured `before.json` (all remote heads, local refs, PRs, worktrees and tag refs). `git bundle verify` confirms **complete history**. `SHA256SUMS` contains:

- `repository.bundle`: `f63dbf454559cbf790569063c4bf0d40ad77bcd9175586783ddc28bd6bc96f22`
- `before.json`: `fca1d56b214a9c61b029ec30e9233c76c45fa928ceee5f07614cce8bd51eb2ff`

`actions.json`, `after.json` and the tracked manifest record execution. Immediately before each deletion, re-read the live SHA, require its exact match, recheck open PR head/base dependencies and worktree occupancy, and prove ancestry in main or PR162. Delete using an explicit expected-SHA lease (`git push --force-with-lease=refs/heads/BRANCH:SHA origin :refs/heads/BRANCH`), then verify that remote ref is absent. No protected/default branch, preservation ref or release tag was deleted. `main`, all three preservation refs and the full remote tag listing match the before snapshot exactly.

To recover any removed branch, substitute a table name for BRANCH (the bundle stores origin tracking refs):

```sh
git fetch /Users/morningstar/.t3/backups/digital-mailroom-branches-20261023T024145Z/repository.bundle refs/remotes/origin/BRANCH:refs/heads/BRANCH
git push origin refs/heads/BRANCH:refs/heads/BRANCH
```

The earlier record names `~/.t3/backups/digital-mailroom-branches-20261021.bundle`, but that file is **absent on this machine**. Its prior verification is historical evidence only; this session does not claim it is currently available.

## Operational-role checks

Only main is default/protected; no repository rulesets were returned. GitHub Preview/Production environments have no branch-selection policy. Hub workflows and documented Vercel production follow main; no tracked configuration or open PR uses `production-staging`. Its exact tip is main's merged v0.9.0 closeout snapshot, 23 commits behind with zero unique commits. It was deleted on that evidence. The external Vercel project setting was not independently queried. `staging` was retained for its unique active159 work regardless of deployment naming.

## Prior deliveries retained

The board retains the September009 delivery (`da0ea35`: eight branch removals, Speed Insights lockfile residual, first14-page wiki publication) and the full historical October cleanup evidence committed in `82a649b0`:23 remote deletions (36 → 13), removal of11 merged local heads and the `t3/final-verify` worktree, earlier recovery bundle and recorded unique-history caveat. These are historical actions, not additions to today's five deletions.

## Historical agent-mailroom recovery and residual

The old cleanup caveat named orphan commit `d026bc51df6c710279dd9b53505c32afbce72ea8`. The original branch was already absent before this session. Preserved `feature/agent-mailroom` commit `f5d97d98` documents its substantially equivalent independent fixes and adds adapted regression tests for containment, WebSocket auth, review state, resume cleanup, wildcard IDs and timestamps.

One original behavior is **not** retained: `packages/agent-mailroom/src/agent_mailroom/pipeline/bins.py:214` still sorts `p.stat().st_mtime` without tolerating a disappearing file. This is tracked separately as **DMR-096 / [issue166](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/166)**; no retired source package is reintroduced or modified by this audit.

Recovered the **full original commit**, tree `83d153140fb1f4737076fadfd4435a7cf2a38b9a`, from GitHub into a temporary custom ref. Created and verified `historical-agent-fix.bundle`, saved its patch and API metadata in the same backup directory, then removed the temporary custom ref. Bundle SHA256: `c7d78bf70c5c381ff58abee6ec6a7e9196054628d56b7a4c6e509c25b7d0204e`. No new remote branch was created. Recovery command:

```sh
git fetch /Users/morningstar/.t3/backups/digital-mailroom-branches-20261023T024145Z/historical-agent-fix.bundle refs/archive/dmr009-agent-fix:refs/heads/recovered-agent-fix
```

## Post-PR162 cleanup of merged branches and retired worktrees

UTC window: 2026-10-23T14:40:37Z (snapshot) to 2026-10-23T14:51:32Z (verification). Baseline `origin/main` = `9e65790fda51afa1078be6211fe78b0355cc47c9` (PR162 merged at 2026-10-23T13:47:24Z; PR167 merged into it first). The earlier audit deliberately retained branches whose unique work was absent from the then-unmerged PR162. Once PR162 landed, that holding condition expired for the branches it carried, so this pass re-ran the decision against merged `main` instead of against an open integration branch.

Three remote heads were merged-PR heads whose exact tips are ancestors of `main`, so each was deleted under an explicit expected-SHA lease:

| Branch | Before SHA | PR | Evidence |
|---|---|---|---|
| `codex/dmr-091-feeder-reconciliation` | `0689b008ce0d311c1876b9a029be4e816c319c91` | #162 MERGED | Exact PR head; merge commit is `main` tip. |
| `t3/surgical-hub-prune` | `001f0958f36ac17999f146003bba033cfd9db4a8` | #167 MERGED | Merged into the PR162 head `0689b008`, which is now on `main`. |
| `coderabbit/add-pull-request-tests/dfc5f5b1` | `f96552050b5caad4a150dd328af67ec8200b428a` | #160 MERGED | Merge commit `8ee9d622` is a parent of `main` tip `9e65790f`. |

Local worktree and branch state was also reconciled:

- Local `main` was 57 commits behind and the primary checkout was parked on the merged `codex/dmr-091-feeder-reconciliation` head. `main` was fast-forwarded `f3c56ec5` -> `9e65790f` and the primary checkout returned to it.
- 47 `t3/*` scratch worktrees under `~/.t3/worktrees/Digital-Mailroom/` (8.2 GB) were removed. Every one had an empty `git status --porcelain`, no stash entry, no submodule, and zero unique commits against `origin/main`; none required `--force`.
- The 47 corresponding local `t3/*` branches and local `codex/dmr-091-feeder-reconciliation` were deleted with `git branch -d` (never `-D`), after the worktrees were removed.
- Detached worktree `/private/tmp/dmr091-v091-release` at `f3c56ec5` was removed; that commit is contained in `main` and equals the pre-merge local `main` tip, so no ref was lost.

Retained, with the reason each is not stale:

| Ref | SHA | Reason |
|---|---|---|
| `claude/dmr-090-local-ci` | `8d7e9e82` | Open #156; CI runner and tests absent from `main`. |
| `dmr-009-branch-prune` | `ae765ae9` | Open #157; this audit vehicle, checked out at `/private/tmp/dmr009-branch-audit`. |
| `staging` | `30ae291c` | Open #159; v9.2 consumer adoption absent from `main`. |
| `claude/readme-architecture-map` | `42ce73f4` | Open draft #171, created 2026-10-23T14:44:06Z, after this window's snapshot; untouched. |
| `coderabbit/pr149-comprehensive-tests/d720b152` | `387c386e` | Closed-unmerged #155; unique negative validation tests still absent from `main`. |
| `feature/agent-mailroom` | `f5d97d98` | DMR-079 preservation ref. |
| `feature/claims-data-eda` | `59c879d9` | DMR-093 preservation ref. |
| `feature/enron-evaluation-environment` | `59c879d9` | DMR-093 preservation ref. |

`feature/claims-data-eda` and `feature/enron-evaluation-environment` are ancestors of `main` yet remain by explicit rule. Containment alone is never sufficient grounds to delete a preservation ref.

Non-`main` remote heads moved 10 -> 8 across the window: three deletions, plus draft #171's head appearing during it. No tag, preservation ref or `main` changed. Remote deletions used `git push --force-with-lease=refs/heads/<branch>:<expected-sha> origin --delete <branch>` and each absent ref was re-verified with `git ls-remote`.

Snapshot and recovery: `/Users/morningstar/.t3/backups/digital-mailroom-branches-20261023T144037Z` holds a complete-history bundle (`git bundle verify`: complete history), `before.txt`, and `SHA256SUMS`. Bundle SHA256 `36b64083f7f464093639160e8d1e83d5f9638cdfa950e8b5dcc5b98600264f76`; snapshot SHA256 `81972f8d7bfbe132c67d394972ab14931762007936bb92d9291174b0a7bad616`. Recovery for a deleted ref:

```sh
git fetch /Users/morningstar/.t3/backups/digital-mailroom-branches-20261023T144037Z/repository.bundle refs/remotes/origin/BRANCH:refs/heads/BRANCH
git push origin refs/heads/BRANCH:refs/heads/BRANCH
```

Independent `archivist-file-organizer` audit returned SAFE for all three groups and flagged two ordering constraints that were honored: fast-forward `main` before any `-d`, and remove worktrees before branches. Post-verification: `git worktree list` shows only the primary checkout and `/private/tmp/dmr009-branch-audit`; local `t3/*` count is 0; `git worktree prune --dry-run -v` is empty; the three deleted remote refs return nothing from `git ls-remote`; all release tags and preservation refs match the pre-cleanup snapshot.

## Specialist evidence and validation

The `orchestrator-governor` report established DMR009/issue13 ownership and preservation of prior evidence. `code-analyst` verified every open PR and exact integration ancestry; `archivist-file-organizer` audited all15 remote heads, locals, worktrees and unique changes. The caller executed all changes. Final independent `board-evidence-auditor` review: **PASS**, after checking live closures/refs, exact ancestry, both complete-history bundle hashes, all15 original heads in the fresh bundle, protected refs/tags, the recovered historical tree and DMR096/issue166 evidence. No remaining publication corrections.

Validation completed for this documentation/governance change:

- `python3 -m unittest discover scripts/tests`: **62 tests OK** (22.909s).
- `python3 scripts/github_labels.py audit`: **33 manifest labels in sync**.
- `git diff --check`: clean.
- `python3 scripts/board_state.py check --json`: five pre-existing `phantom-card-reference` errors (DMR120/176/182/188/191), two pre-existing warnings (DMR078 not archived, DMR063 stale). **Zero new errors**; the check honestly remains exit1. The complete output is retained in the fresh backup as `board-check.json`.
- All three superseded PRs verified closed; all five deleted remote refs verified absent; preservation/default refs and full remote tag listing verified unchanged.

No package implementation changed relative to main; package suites were not required for the board/report-only diff. PR157 remains the publication/review vehicle for this completed external cleanup; DMR009 closes with committed audit evidence and issue13 closure.
