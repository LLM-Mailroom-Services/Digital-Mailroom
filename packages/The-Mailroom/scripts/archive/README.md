# Archived Scripts

**Status: FROZEN / PROVENANCE-ONLY.** Everything under this tree is
preserved for lineage and reproducibility — none of it is part of the live
workflow.

| Bucket | Contents | Status |
|:---|:---|:---|
| `render_tui_shots.py` | One-off TUI frame renderer for README screenshots (requires a running Mailroom API at `MAILROOM_API_URL`) | One-time; screenshots it produced are baked into the READMEs |

## Why archive instead of delete

- The renderer is a dev-time artifact generator: it produced the TUI SVG
  frames shown in the README, but it is not part of any release, test,
  hook, or skill workflow. The frames it generated are committed assets and
  remain current; only the generator itself is retired from the live
  `scripts/` surface.
- If a future release needs fresh TUI frames, restore this file or re-render
  from the archived copy — the `MAILROOM_API_URL` contract is preserved in
  its docstring.

## Running archived scripts

```bash
.venv/bin/python scripts/archive/render_tui_shots.py --help
```

## Audit trail

Archived 2026-09-14 in the scripts organization pass (mailroom-issues #17
monorepo sweep). Live workflow confirmed intact: every other script in
`scripts/` is referenced by tests, skills, hooks, or sibling scripts per the
reference audit.