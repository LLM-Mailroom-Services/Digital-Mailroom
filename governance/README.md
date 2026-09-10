<div align="center">

# 🏛️ Governance

**Task board, card tracking, and cross-agent coordination for the Digital-Mailroom monorepo.**

</div>

---

## What This Directory Contains

| File | Description |
|:---|:---|
| `TASKS.md` | The monorepo's task board and single source of truth for cross-agent task state |

## Board Laws

The four lanes: `assigned` → `in_progress` → `needs_attention` → `done`

- **Claim before edit** — one owner per card
- **Update, don't duplicate** — work touching an existing card's scope updates that card
- **No silent completion** — `done` requires green suites, clean git status, and Evidence commits

## Board Machine-Readability

```bash
python scripts/board_state.py status    # live board snapshot
python scripts/board_state.py check     # structural invariant check (exit 1 on errors)
```

## Related Files

| Path | Purpose |
|:---|:---|
| `scripts/board_state.py` | Parses and validates the board |
| `scripts/github_labels.py` | Label taxonomy audit (CI gate) |
| `scripts/taxonomy_parity.py` | Doc-class taxonomy drift (CI gate) |
| `.github/workflows/board-governance.yml` | CI enforcement |
| `.github/ISSUE_TEMPLATE/hub_card.yml` | Synced card template |
| `.github/labels.json` | Label taxonomy |

## Issue Routing

- **Board-only**: small/single-session/low-risk cards
- **GitHub Issue**: critical or cross-package cards (repo where work lands)
- **Synced cards**: carry `kanban` + lane labels, mirrored both ways
