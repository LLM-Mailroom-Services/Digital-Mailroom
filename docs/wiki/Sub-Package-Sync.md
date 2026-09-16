# Sub-package sync

Every package under `packages/` mirrors an independent `Exios66/*`
repository (git subtree). **The monorepo is the development source of
truth**; the standalone repos remain standalone and operational.

## The doctrine (HUB-004, human-confirmed)

- **Current-only pulls** — only import upstream code that is current; stale
  code never regresses the monorepo (the sync driver has no rewind path —
  it only reports *forward* drift).
- **Monorepo truth wins** — on conflict, monorepo-side fixes win unless
  upstream genuinely supersedes them.
- **No merge tangles** — pulls are squashed; if subtree ancestry can't
  fast-forward (snapshot-based cursors), publish monorepo fixes upstream as
  clean patch commits instead of forcing grafts.
- **No silent drift** — `status` always recomputes real drift against live
  upstreams, so a stale manifest is visible at a glance.

## The driver

```bash
python scripts/sync_packages.py status                       # drift report (fetches upstreams; --json for machines)
python scripts/sync_packages.py pull  --package <name> --squash   # import upstream commits
python scripts/sync_packages.py push  --package <name>       # publish monorepo commits upstream
python scripts/sync_packages.py push  --package <name> --patch    # non-fast-forward fallback (HUB-012)
python scripts/sync_packages.py snapshot [--package <name>] [--force]  # re-baseline cursors (content-verified)
```

- `pull`/`push` refuse to run on a dirty worktree (`--allow-dirty` overrides).
- `pull --squash` keeps upstream history out of the monorepo log.
- Per-package cursors live in `scripts/packages_sync.json`.
- **Content-verified cursors (HUB-021)** — `snapshot` refuses to advance a
  cursor past upstream content the package tree doesn't actually contain
  (blob-level containment; gitignored prunes are exempt). The HUB-018
  incident (snapshot-advance without a merge → next squash pull re-imported
  the whole range) is now structurally impossible without `--force`.
- `pull` skips the subtree merge when the upstream tip is already contained
  in the package (the re-import loop killer).
- `push --patch` is the scripted HUB-012 workaround: it rebuilds the
  package's tracked files on top of the real upstream tip and lands ONE
  fast-forward commit upstream, then re-baselines the cursor (`--dry-run`
  prints the plan first).
- `status` shows per-package `CURSOR GAP` flags and the monorepo-ahead file
  count — the unpushed delta, i.e. the release-train payload (HUB-005).
- **The release-train sweep (HUB-005 propagation):** the all-packages
  one-liner is `python scripts/sync_packages.py push --all --patch` — one
  command fetches every upstream tip, lands the monorepo delta as a single
  fast-forward commit per package, and re-baselines the cursors. Follow with
  `sync_packages.py status` (expect 10/10 in sync, 0 monorepo-ahead) and
  commit the cursor file. `patch_push` extracts committed blobs (`git ls-tree
  -r HEAD` + `git cat-file blob`) — uncommitted work never propagates
  (DMR-028).
- After a pull, **re-apply monorepo-side prunes** the merge may resurrect
  (e.g. `packages/llm-entity-extraction/docs/{data,posit,posit-src}/` are
  gitignored-heavy-asset paths; gitignore does not apply to tracked files,
  so `git rm -r --cached` + tree removal is the fix — HUB-004).

## The push-leg decision tree (DMR-070)

Pick the push leg by WHAT the monorepo delta contains — the wrong leg is a
doom loop:

| Delta contains | Leg | Why |
| --- | --- | --- |
| Additions/modifications only | `push --package <name> --patch` (or full subtree push) | Content pushes carry everything; `--patch` lands one fast-forward commit. |
| Deletions of tracked upstream paths | `push --package <name>` (full subtree push, NO `--patch`) | `patch_push` rebuilds monorepo blobs on top of the tip — upstream-only paths would silently survive. The deletion guard now REFUSES (`exit 5`, `deleted_paths`) instead of letting that happen (the v0.6.0 compliance-removal trap). |
| Either, before pushing | add `--verify-suite` | Runs the touched package's pytest suite first (`SYNC_VERIFY_CMD` overrides); a red suite refuses push AND cursor advance. |

Post-import (DMR-070a): `pull --open-pr` blob-compares every ladder-resolved
path against BOTH merge sides; a resolution matching neither side is
resolution-introduced content — reported on stderr, in
`resolution_divergences` (JSON), and in the PR body. Exit codes:
0 ok / 1 network / 2 dirty / 3 conflict-aborted / 4 git-internal /
**5 verification refused**.

## Vendor snapshots (sandbox self-containment)

`packages/local-mailroom-sandbox/vendor/` tracks the monorepo **workspace
packages**, not upstream tags (hub#62 doctrine; the drift guard
`packages/local-mailroom-sandbox/tests/test_vendor_drift.py` enforces
byte-identity).

```bash
python scripts/sync_vendor.py           # mirror workspace -> vendor (content AND deletions)
python scripts/sync_vendor.py --check   # CI-friendly no-op drift gate
```

`sandbox fetch-deps` mirrors the workspace when the monorepo layout is
detected and falls back to a loud tag-based refresh for standalone clones.
NEVER tag-refresh the vendored llm-mailroom from the monorepo: the v0.7.1
tag predates the five-class taxonomy removal (59c47401), so a tag-based
re-snapshot resurrects the deleted docclass-era files.

## Verification contract for a sync session

1. `status` → all packages in sync (or the drift is the work).
2. Post-pull: the pulled package's FULL suite green (a subtree pull is a
   significant change).
3. Monorepo-side guards/skip-fixes intact.
4. Cursor advanced; `git status` clean; board card closed with Evidence.
