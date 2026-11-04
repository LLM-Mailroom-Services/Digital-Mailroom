# Monorepo `sync_packages.py` hook

Primary monorepo: **[LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)**.
`Exios66/mailroom-dev` is a legacy HUB artifact — do not target it for new work.

After `pull` or `push` refreshes `packages/local-mailroom-sandbox`, propagate
the family subagent roster into every mapped checkout (OpenCode + Cursor).

## One-time wiring (Digital-Mailroom)

Apply [`sync_packages.patch`](sync_packages.patch) or add manually near
`require_subtree()` in `scripts/sync_packages.py`:

```python
def run_subagents_post_sync() -> None:
    """Refresh family coding subagents after sandbox package sync (SAND-017)."""
    hook = REPO_ROOT / "packages/local-mailroom-sandbox/scripts/monorepo/after_packages_sync.py"
    if not hook.is_file():
        return
    run(
        [sys.executable, str(hook), "--monorepo-root", str(REPO_ROOT)],
        capture=False,
    )
```

Call **`run_subagents_post_sync()`** at the end of `cmd_pull` and `cmd_push`
immediately before each command returns success (`return 0`), after
`save_manifest(manifest)`.

## Manual run

From the **Digital-Mailroom** monorepo root:

```bash
python3 packages/local-mailroom-sandbox/scripts/monorepo/after_packages_sync.py
```

From a standalone sandbox checkout (sibling `Digital-Mailroom/` clone):

```bash
sandbox subagents propagate
# or
DIGITAL_MAILROOM_ROOT=../Digital-Mailroom sandbox subagents propagate
```

Legacy env `MAILROOM_DEV_ROOT` is still accepted as a fallback alias.
