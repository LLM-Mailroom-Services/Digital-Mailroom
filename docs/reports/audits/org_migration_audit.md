<div align="center">

# 🔍 Org-Migration Reference Audit

**DMR-006 · 2026-09-09 — hub identity `Exios66/mailroom-dev` → `LLM-Mailroom-Services/Digital-Mailroom`**

</div>

---

## Scope & method

Every tracked file is scanned for the two stale hub identifiers —
`Exios66/mailroom-dev` (the predecessor repository path) and
`mailroom-dev.vercel.app` (the predecessor served-board URL). Findings are
classified into three tiers before remediation:

| Tier | Meaning | Action |
|:---|:---|:---|
| **Migrate** | Current-state hub references (templates, changelog footer, wiki, READMEs, scripts) | rewritten to `LLM-Mailroom-Services/Digital-Mailroom` |
| **Intentional package-mirror** | `Exios66/*` standalone package repos, upstream pins, sync driver, GH Pages | unchanged — the package mirrors did **not** move |
| **Historical** | HUB-era board archive, changelog history, lineage notes, the cross-board switcher | unchanged — they describe the predecessor accurately |

The audit is enforced by `scripts/audit_references.py`, wired into
`.github/workflows/board-governance.yml`; a non-allowlisted hit fails CI.
Machine-readable companion: [`org_migration_audit.json`](org_migration_audit.json).

## Verdict

- Gated patterns: `Exios66/mailroom-dev`, `mailroom-dev.vercel.app`
- Non-allowlisted findings after the sweep: **0**
- Gate command: `python scripts/audit_references.py` (`--json` for machines)

## Migrated (hub tier)

| File | Change |
|:---|:---|
| `.github/ISSUE_TEMPLATE/config.yml` | TASKS.md + AGENTS.md contact links → new repo |
| `CHANGELOG.md` | scope line → "Digital-Mailroom monorepo"; compare/release footer links → new repo |
| `README.md` | repository tree label → `Digital-Mailroom/`; footer → LLM-Mailroom-Services (Exios66 · grantmooslin) |
| `LICENSE` | copyright holder → LLM-Mailroom Services (Exios66, grantmooslin) |
| `docs/wiki/Home.md`, `_Sidebar.md`, `README.md` | wiki identity → Digital-Mailroom |
| `docs/wiki/Getting-Started.md` | clone checkout dir → `Digital-Mailroom` |
| `docs/wiki/FAQ.md` | redeploy answer → project `digital-mailroom`, Root Directory `board-site`, Git integration live (stale "Root Directory unset" corrected) |
| `docs/wiki/Board-Governance.md`, `Releases.md`, `Architecture.md` | served-board project name + repository tree |
| `docs/README.md`, `docs/assets/README.md`, `docs/reports/README.md`, `docs/reports/audits/README.md`, `reports/README.md`, `data/README.md`, `data/manifests/README.md`, `governance/README.md`, `scripts/README.md` | descriptive text → "Digital-Mailroom monorepo" |
| `docs/docclass-merged-plan.md` | repository header → new repo |
| `docs/assets/mailroom-pipeline.svg` | canonical-diagram caption → `Digital-Mailroom/...` |
| `.opencode/agents/prompt-engineer.md` | workspace naming → Digital-Mailroom |
| `.github/dependabot.yml` | scope comment → Digital-Mailroom |
| `scripts/sync_packages.py` | propagation commit message → `from Digital-Mailroom@<stamp>` |
| `scripts/audit_references.py`, `docs/reports/audits/org_migration_audit.*` | new audit gate + this report |

## Intentionally unchanged (allowlisted)

| Tier | Files | Why |
|:---|:---|:---|
| Package mirrors | `packages/**` (READMEs, sister-repos, wiki, The-Mailroom constellation manifest/TUI, `gmail_intake` echo links + tests, `intent_backfill` comments) | the ten standalone repos remain `Exios66/*` release vehicles; their docs name the original hub correctly |
| Mirror wiring | `scripts/sync_packages.py` (`ORIGIN`), `scripts/packages_sync.json`, package `pyproject.toml` git pins, `scripts/deploy_gh_pages.py`, GH Pages URLs | unchanged until/unless the package repos migrate to the org (separate migration) |
| Historical | `governance/TASKS.md` archive + lineage, `AGENTS.md` lineage note, HUB-era `CHANGELOG.md` entries, `scripts/apply_hub064_board.py` | predecessor history is append-only and accurate |
| Cross-board UI | `board-site/index.html` (`HUB Board ↗` link + "original mailroom-dev board" title) | the switcher deliberately links the original HUB board |

## Bare-name sweep

Beyond the gated URL patterns, bare `mailroom-dev` project-name references were
swept in the same pass (wiki titles/sidebar/checkout dir/FAQ/Releases/
Board-Governance/Architecture, README family, `.opencode` agent doc,
dependabot comment, sync propagation message, SVG caption). Remaining bare
mentions are historical (CHANGELOG HUB-era entries) or the deliberate
cross-board UI label.

## Live surfaces

| Surface | State |
|:---|:---|
| DMR board | https://digital-mailroom-theta.vercel.app — issue-backed, Git-integration deploys live |
| HUB board | https://mailroom-dev.vercel.app — original board, cross-linked both ways |
| Repo About | description + homepage link the DMR board; topics updated |
| Original repo | `Exios66/mailroom-dev` carries the HUB-067 successor pointer to this repo |

## Gate contract

```bash
python scripts/audit_references.py          # exit 1 on non-allowlisted stale hub references
python scripts/audit_references.py --json   # machine-readable
```

The allowlist lives in `scripts/audit_references.py`; extending it is a
deliberate, reviewable act — never silence a finding without classifying it
here or in this report.
