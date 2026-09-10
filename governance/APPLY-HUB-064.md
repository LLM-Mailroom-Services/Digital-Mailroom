# Apply HUB-064 board update

**Do not merge** `cos/hub-064-archive-043` (tip has placeholder `TASKS.md` from a failed MCP upload).

## Preferred (from repo root on `main`)

```bash
git fetch origin
git checkout -B cos/hub-064-archive-043 origin/main
python3 scripts/apply_hub064_board.py
python scripts/board_state.py check
git add governance/TASKS.md
git commit -m "HUB-064: spawn Gmail triage prod-readiness; archive HUB-043"
git push -u origin cos/hub-064-archive-043 --force-with-lease
```

Issue #29 already closed. Follow-up issue #43 exists. After merge, `python scripts/board_state.py sync-issues --apply`.
