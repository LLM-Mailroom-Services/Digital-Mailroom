# Apply HUB-064 board update

> **HISTORICAL** — archived per mailroom-issues#50. This is a HUB-era
> one-shot for the predecessor `Exios66/mailroom-dev` board; the DMR board
> never used the HUB namespace (DMR-001 lineage law) and this script's
> hard-coded HUB-064/HUB-043 rows would corrupt `governance/TASKS.md` if
> followed. `scripts/archive/apply_hub064_board.py` is retained as history.
> The DMR-era successor board work was DMR-012..DMR-018 (mailroom-issues#15).
>
> ---

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
