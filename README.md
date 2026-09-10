<div align="center">

# 🏛️ LLM-Mailroom Constellation

**A governed monorepo housing the full LLM-Mailroom ecosystem — one checkout, one virtualenv, ten packages, zero cross-repo import friction.**

Multi-agent legal-document pipeline · Prompt-experiment loop · Deterministic scoring · Pixel-art visualizer · Walking-office-floor mailroom · Corpus EDA

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv workspace](https://img.shields.io/badge/uv-workspace-6C63FF)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/mailroom-processing-banner-dark.svg">
  <img src="docs/assets/mailroom-processing-banner.svg" alt="Mailroom processing pipeline — six stages from intake to routing, human-in-the-loop review, and every file committed to the auditable hash archive" width="880"/>
</picture>

</div>

---

> **Canonical architecture & taxonomy:** See the [canonical Mailroom pipeline](docs/assets/mailroom-pipeline.svg) and the [v7 taxonomy specification](docs/v7-taxonomy.md). These are the root-level sources of truth for the pipeline visualization and v7 terminology.

## Architecture

```
                    ┌── corpus feeds (colocated data) ─────────────────────┐
                    │  Enron-Evaluation-Environment   claims-data-eda      │
                    │  mailroom-corpus-eda   (mailroom-corpus, P0–P6 EDA)  │
                    └──────────────────────────┬───────────────────────────┘
                                               ▼
                    ┌── prompt-experiment loop ────────────────────────────┐
                    │  llm-entity-extraction        (GEPA prompt versions) │
                    └──────────────────────────┬───────────────────────────┘
                                               ▼
┌────────────────────────┐        ┌───────────────────────────────────────┐
│  llm-dojo-scoring      │◀───────│           llm-mailroom                │
│  shared scoring engine │ import │  LangGraph multi-agent pipeline       │
└────────────────────────┘        └──────────────────┬────────────────────┘
                                                     ▼
                    ┌── surfaces ──────────────────────────────────────────┐
                    │  The-Mailroom (visualizer)     agent-mailroom        │
                    │  local-mailroom-sandbox        llm-mailroom-graph    │
                    └──────────────────────────┬───────────────────────────┘
                                               ▼
                    ┌──────────────────────────────────────────────────────┐
                    │            Digital-Mailroom — this standalone repo     │
                    │        (central truth; every box lives in it)        │
                    └──────────────────────────────────────────────────────┘
```

## Repository Map

All ten packages live in `packages/` as git subtrees and mirror independent `Exios66/*` repositories. GitHub Pages sites exist for six of them.

<div align="center">

| Layer | Repository | GitHub Pages |
|:---|:---|:---|
| **Hub** (central truth) | [`LLM-Mailroom-Services/Digital-Mailroom`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) | — |
| **Corpus feed** | [`Exios66/Enron-Evaluation-Environment`](https://github.com/Exios66/Enron-Evaluation-Environment) | [exios66.github.io/Enron-Evaluation-Environment](https://exios66.github.io/Enron-Evaluation-Environment/) |
| **Corpus feed** | [`Exios66/claims-data-eda`](https://github.com/Exios66/claims-data-eda) | [exios66.github.io/claims-data-eda](https://exios66.github.io/claims-data-eda/) |
| **Corpus EDA + HF** | [`Exios66/Mailroom-Corpus-EDA`](https://github.com/Exios66/Mailroom-Corpus-EDA) | [exios66.github.io/Mailroom-Corpus-EDA](https://exios66.github.io/Mailroom-Corpus-EDA/) |
| **Prompt experiments** | [`Exios66/llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction) | [exios66.github.io/llm-entity-extraction](https://exios66.github.io/llm-entity-extraction/) |
| **Scoring engine** | [`Exios66/llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring) | — |
| **LangGraph pipeline** | [`Exios66/llm-mailroom`](https://github.com/Exios66/llm-mailroom) | — |
| **Pixel visualizer** | [`Exios66/The-Mailroom`](https://github.com/Exios66/The-Mailroom) | [exios66.github.io/The-Mailroom](https://exios66.github.io/The-Mailroom/) |
| **Walking floor** | [`Exios66/agent-mailroom`](https://github.com/Exios66/agent-mailroom) | — |
| **Local sandbox** | [`Exios66/local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox) | — |
| **Knowledge graph** | [`Exios66/llm-mailroom-graph`](https://github.com/Exios66/llm-mailroom-graph) | [exios66.github.io/llm-mailroom-graph](https://exios66.github.io/llm-mailroom-graph/) |

</div>

## Package Details

<div align="center">

| Package | Role | Source |
|:---|:---|:---|
| `llm-dojo-scoring` | Deterministic scoring, error-analysis, visualization & interpretation suite | [`Exios66/llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring) |
| `llm-mailroom` | LangGraph multi-agent legal-document pipeline (FastAPI producer) | [`Exios66/llm-mailroom`](https://github.com/Exios66/llm-mailroom) |
| `llm-entity-extraction` | Prompt-experiment loop: prompt versions × models over CUAD/LegalBench/MAUD | [`Exios66/llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction) |
| `The-Mailroom` | Pixel-art visualizer console + hosted Observatory (Langfuse as source of truth) | [`Exios66/The-Mailroom`](https://github.com/Exios66/The-Mailroom) |
| `agent-mailroom` | Self-contained mailroom: one state machine per document, specialist agents at desks | [`Exios66/agent-mailroom`](https://github.com/Exios66/agent-mailroom) |
| `local-mailroom-sandbox` | Local-first experiment sandbox (Ollama, vLLM, llama.cpp) | [`Exios66/local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox) |
| `Enron-Evaluation-Environment` | Enron corpus EDA → pipeline-ready correspondence dataset | [`Exios66/Enron-Evaluation-Environment`](https://github.com/Exios66/Enron-Evaluation-Environment) |
| `claims-data-eda` | CMS DE-SynPUF EDA → pipeline-ready insurance_claim dataset | [`Exios66/claims-data-eda`](https://github.com/Exios66/claims-data-eda) |
| `llm-mailroom-graph` | Derived knowledge-graph site of llm-mailroom | [`Exios66/llm-mailroom-graph`](https://github.com/Exios66/llm-mailroom-graph) |
| `mailroom-corpus-eda` | mailroom-corpus corpus EDA (P0–P6) + centralized HF upload helpers | [`Exios66/Mailroom-Corpus-EDA`](https://github.com/Exios66/Mailroom-Corpus-EDA) |

</div>

> Virtual members (`package = false`) have no build system and are not installed — they exist so their data/code stays colocated in the single checkout.

## Repository Structure

```
mailroom-dev/
├── AGENTS.md              # workspace rules & cross-package conventions
├── README.md              # this file — the canonical entry point
├── pyproject.toml         # uv workspace definition
├── uv.lock                # single lockfile for all packages
├── .gitignore
├── governance/            # task board (TASKS.md) & governance tooling
├── docs/
│   ├── v7-taxonomy.md     # canonical v7 corpus/live-taxonomy terminology
│   ├── assets/
│   │   └── mailroom-pipeline.svg
│   └── wiki/
├── scripts/
│   ├── board_state.py     # board machine-readable parser + CI gate
│   ├── sync_packages.py   # subtree ↔ standalone repo sync
│   ├── taxonomy_parity.py # taxonomy drift detector (CI gate)
│   ├── release_chain.py   # hub changelog ↔ semver tag ↔ version gate (HUB-024)
│   └── deploy_gh_pages.py # local GH Pages deploy (no Actions)
└── packages/              # all ten packages (subtree + virtual)
```

## Development

One workspace, one lockfile, one virtualenv:

```bash
uv sync                  # install workspace + dev group into .venv (editable)
uv run pytest ...        # run against the shared venv
```

Per-package test suites:

```bash
uv run pytest packages/llm-dojo-scoring/tests
uv run pytest packages/llm-mailroom/src/tests
uv run pytest packages/llm-entity-extraction/tests
uv run pytest packages/The-Mailroom/tests
uv run pytest packages/agent-mailroom/tests
uv run pytest packages/local-mailroom-sandbox/tests
uv run pytest packages/mailroom-corpus-eda/tests
```

Cross-package dependencies resolve to **workspace sources** during development (`[tool.uv.sources]` in each member pyproject); published git pins remain in dependency lines for release builds.

## Sub-Package Sync

Every package mirrors an independent `Exios66/*` repository. The monorepo is the development source of truth; `scripts/sync_packages.py` keeps the mirrors reconciled.

```bash
python scripts/sync_packages.py status                  # live status
python scripts/sync_packages.py pull --all              # sync from upstream
python scripts/sync_packages.py push --package llm-mailroom
python scripts/sync_packages.py push --package llm-mailroom --patch   # non-fast-forward fallback
python scripts/sync_packages.py snapshot                # cursor verification
```

## GitHub Governance Tooling

The board and GitHub surface are kept machine-readable and mutually consistent.
The live dispatch board is **https://digital-mailroom-theta.vercel.app** (issue-backed; see `board-site/` and `docs/wiki/Served-Board.md`):

```bash
python scripts/board_state.py status            # live board snapshot (--json for machines)
python scripts/board_state.py check             # board invariants; exit 1 on structural errors
python scripts/github_labels.py audit           # label taxonomy drift (CI gate)
python scripts/taxonomy_parity.py               # doc-class taxonomy drift (CI gate, HUB-019 §65A)
python scripts/release_chain.py status          # hub release chain: tags, changelog sections, hub version
python scripts/release_chain.py check           # chain invariants; exit 1 on structural errors
python scripts/release_chain.py cut X.Y.Z       # cut a hub release (dry run; --apply writes, --tag tags)
./docs/wiki/sync-wiki.sh                        # push docs/wiki/ source to the GitHub wiki (--check for drift)
```

See `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE/`, `.github/labels.json`, `scripts/board_state.py`, and `governance/TASKS.md` for the full governance contract.

## Wiki

The [GitHub wiki](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/wiki) is mirrored from `docs/wiki/`.

## Release Flow

The monorepo is the development source of truth. Upstream repositories remain the release vehicles for deployed surfaces; propagate package changes with `scripts/sync_packages.py push` when a release is cut, then bump published pins as required.

---

<div align="center">

**[llm-mailroom](https://github.com/Exios66/llm-mailroom)** ·
**[llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction)** ·
**[llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring)** ·
**[The-Mailroom](https://github.com/Exios66/The-Mailroom)** ·
**[agent-mailroom](https://github.com/Exios66/agent-mailroom)**

<sub>Built by the governed evaluation family under <a href="https://github.com/Exios66">@Exios66</a> · 2026</sub>

</div>
