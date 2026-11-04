---
name: vendor-sync
description: Refresh the sandbox's tracked vendor/ snapshots of llm-mailroom and llm-dojo-scoring from their reviewed standalone refs, then run the drift guards. Use only when the user asks to refresh, update or bump vendored code.
disable-model-invocation: true
---

# vendor-sync

`vendor/` holds **tracked, byte-checked snapshots** of `llm-mailroom` and
`llm-dojo-scoring` (`tests/test_vendor_drift.py`). Never edit them by hand — a hook
blocks it. This skill is the one sanctioned way to change them.

## 0. Preconditions

- The change must already be **committed and merged in the owning repo**
  (`llm-mailroom` for pipeline, `llm-dojo-scoring` for scoring). Never patch the
  snapshot to "fix it here first".
- `git status` is clean. Ask the user which package(s) and which target revision.

## 1. Set the target pin

Pins live in `_VENDOR_PINS` in `src/mailroom_sandbox/cli.py` as
`(name, ref, url, sha)`. The `sha` is the integrity check: a ref that has moved is
**rejected before any tracked file is replaced**.

```bash
# <url> and <ref> are the package and ref you are pinning; the printed commit must equal
# the `sha` you write into _VENDOR_PINS.
git ls-remote https://github.com/Exios66/<llm-dojo-scoring|llm-mailroom>.git <ref>
```

For a release tag, `ls-remote` prints the tag object and, for annotated tags, a `^{}` line
with the commit; use the `^{}` commit. Edit `ref` and `sha` together. Dojo pins a release
tag plus its commit; llm-mailroom pins a reviewed commit SHA (ref and sha are then the same).

## 2. Refresh

`sandbox fetch-deps` has **no package filter**: it refreshes every `_VENDOR_PINS` entry.
It does not prompt by itself (Claude Code asks because the command is on the `ask` list).

- **Monorepo** (`../../packages/<name>` exists): `fetch-deps` and
  `python scripts/sync_vendor.py [<name>]` copy the workspace tree (minus the shared vendor
  exclusions: top-level `tests/`/`test/`, `__pycache__`, `*.pyc`, `*.egg-info`,
  `legalbench/reports`) and do **not** compare it with the pin. First check out or import the pinned revision in
  `../../packages/<name>` (`git -C ../../packages/<name> rev-parse HEAD` must equal the
  pin's `sha`) — otherwise the snapshot will not match the provenance you record in step 3.
  To refresh one package only, use `python scripts/sync_vendor.py <name>`.
- **Standalone** (no workspace): `fetch-deps` clones each pinned ref and rejects a SHA
  mismatch before replacing tracked files. Because it refreshes both packages, run it only
  when the other package's pin is already what is vendored, then confirm with
  `git status vendor/` that only the intended package changed; revert anything else with
  `git checkout -- vendor/<other>`.

```bash
sandbox fetch-deps                          # standalone: both packages, SHA-checked
python scripts/sync_vendor.py <name>        # monorepo: one package, workspace must be at the pin
```

## 3. Update provenance

Make `vendor/README.md` (pin table) and `vendor/<name>/VENDOR.md` (source ref, exact
commit, version, date) match the new pin. Open both and check — do not assume the
refresh rewrote them.

## 4. Verify (show the output, do not summarize from memory)

```bash
.venv/bin/python -m pytest tests/test_vendor.py tests/test_vendor_drift.py \
  tests/test_vendor_refresh_git.py tests/test_vendor_sync_script.py -q
.venv/bin/python -m pytest -q -m "not local_llm"
ruff check src tests scripts deploy reports
```

Expected: both pytest runs exit 0 with no failures (skips are fine; any failure blocks the
commit), and `ruff check` prints `All checks passed!`.

`test_vendor_drift.py` also compares against **sibling checkouts** (`../llm-dojo-scoring`,
`../llm-mailroom/src`) when they exist. When the pinned commit exists in the sibling repo it
compares against `git archive` of that commit, so the sibling's checked-out branch does not
matter. When `git archive` of the pinned commit fails for any reason (most often the
commit is missing there — fetch it) it falls back to the working tree, and then a sibling
on a different revision fails the test even though the
vendor refresh is correct — say which sibling is stale rather than "fixing" vendor.

## 5. Commit

One commit titled `vendor: <package> -> <ref> (<short sha>)`, body listing old and new
pins and the diffstat. Do not push unless asked.
