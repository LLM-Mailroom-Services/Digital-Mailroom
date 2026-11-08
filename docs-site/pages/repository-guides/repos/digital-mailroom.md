---
icon: warehouse
title: Digital-Mailroom
---

# Digital-Mailroom

**The monorepo: every constellation package in one checkout and one virtualenv.**

|            |                                                                                                          |
| ---------- | -------------------------------------------------------------------------------------------------------- |
| Repository | [LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)      |
| Role       | Hub; development source of truth for cross-repo work                                                     |
| Live board | [Dispatch Board](https://digital-mailroom-theta.vercel.app)                                              |
| Wiki       | [GitHub wiki](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/wiki), sourced from `docs/wiki/` |

## What it does

Digital-Mailroom holds all ten constellation packages under `packages/` as git subtrees, each with its own history, wired into a single `uv` workspace with one `uv.lock`. A contributor clones one repository, runs `uv sync`, and has every package installed editable with no cross-repo import juggling.

It also carries the governance tooling for the whole family: the cross-repo task board, the served Dispatch Board, label and taxonomy drift checks, and the hub release chain.

## Monorepo versus standalone repositories

The hub is the place to plan cross-repo work, but its package copies can trail the standalone repositories. As of 2026-11-08 (hub v0.10.0, last commit 2026-11-04):

| Package | In the hub | Standalone repository |
| ------- | ---------- | --------------------- |
| llm-mailroom | 0.9.1, pins llm-dojo-scoring at commit `a82843e8` | 0.9.3, pins v0.28.1 |
| llm-dojo-scoring | 0.27.2 | v0.28.1 |
| The-Mailroom | 0.5.1 | 0.5.0 |

Run `python scripts/sync_packages.py status` before you rely on a package copy. The standalone repositories remain the release vehicles for deployed surfaces. Do not quote a hub package version as the current release.

The hub's `[Unreleased]` changelog also records that `.github/workflows/ci.yml` was removed. The per-package pytest matrix was disabled yet still registered as a required check. Verification is local, per `docs/TESTING.md`. Governance gates stay in `board-governance.yml`.

## Quick start

```bash
git clone https://github.com/LLM-Mailroom-Services/Digital-Mailroom.git
cd Digital-Mailroom
uv sync
uv run pytest packages/llm-mailroom/src/tests   # one package per invocation
```

## Layout

```
Digital-Mailroom/
├── AGENTS.md            workspace rules and cross-package conventions
├── governance/          TASKS.md (the DMR board) and governance tooling
├── board-site/          the served Dispatch Board (Vercel)
├── docs/                v7 taxonomy contract, docclass contract, wiki source
├── scripts/             board_state, sync_packages, taxonomy_parity, release_chain, ...
└── packages/            the ten packages
```

| Package                                                                                                                 | Installed?                              |
| ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `llm-mailroom`, `llm-dojo-scoring`, `llm-entity-extraction`, `The-Mailroom`, `agent-mailroom`, `local-mailroom-sandbox` | Yes, editable                           |
| `Enron-Evaluation-Environment`, `claims-data-eda`, `llm-mailroom-graph`, `mailroom-corpus-eda`                          | No: virtual members (`package = false`) |

## Key tools

| Command                                                                | What it does                                               |
| ---------------------------------------------------------------------- | ---------------------------------------------------------- |
| `python scripts/sync_packages.py status`                               | Drift between each subtree and its `Exios66/*` upstream    |
| `python scripts/sync_packages.py pull --all` / `push --package <name>` | Bring upstream changes in, or publish monorepo changes out |
| `python scripts/board_state.py status` / `check`                       | Board snapshot and invariant check                         |
| `python scripts/taxonomy_parity.py`                                    | Document-class taxonomy drift gate                         |
| `python scripts/github_labels.py audit`                                | Label taxonomy drift gate                                  |
| `python scripts/release_chain.py status` / `cut X.Y.Z`                 | Hub release chain                                          |
| `python scripts/release_notes.py`                                      | Release-notes generator for the hub GitHub releases        |
| `python scripts/sync_vendor.py`                                        | Refresh the sandbox vendor snapshots from the workspace packages |
| `python scripts/audit_references.py`                                   | Org-migration reference audit (DMR-006)                    |
| `python scripts/gen_interactive_charts.py`                             | Plotly interactive charts for the EDA repositories         |
| `python scripts/deploy_gh_pages.py`                                    | Deploy EDA reports to GitHub Pages through a `gh-pages` branch |

## Rules worth knowing

* Member `pyproject.toml` files keep their published git pins. Workspace redirection happens only through `[tool.uv.sources]`, so `pip install .` inside a package still builds the release.
* Nested `.github/workflows/` inside packages do not run here.
* Heavy assets (example PDFs, screenshots, report archives) are pruned; tests that need them skip.
* Stage explicit paths only; never `git add .` in the shared checkout.

## Its documentation

* [README](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/README.md) — the hub manual
* [AGENTS.md](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/AGENTS.md) — workspace rules
* [docs/v7-taxonomy.md](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/v7-taxonomy.md) — canonical class and subclass terminology
* [docs/DOCCLASS\_CONTRACT.md](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/DOCCLASS_CONTRACT.md) — document-class contract
* [docs/TESTING.md](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/TESTING.md) — testing across the workspace
* Wiki source: [Getting Started](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Getting-Started.md), [Architecture](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Architecture.md), [Board Governance](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Board-Governance.md), [Served Board](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Served-Board.md), [Sub-Package Sync](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Sub-Package-Sync.md), [Releases](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Releases.md), [HF Corpus](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/HF-Corpus.md), [Offline Sandbox](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Offline-Sandbox.md), [Subagents](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Subagents.md), [FAQ](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/FAQ.md), [Sandbox Jobs](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Sandbox-Jobs.md), [Sandbox Modal](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/wiki/Sandbox-Modal.md)
* [docs/docclass-merged-plan.md](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/docclass-merged-plan.md) — the corpus plan behind the document-class contract
* [docs/reports/audits/](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/main/docs/reports/audits) — frozen baselines, coverage matrix, org-migration audit
