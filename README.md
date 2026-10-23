<div align="center">

# 📬 Digital Mailroom

**LLM-Mailroom constellation monorepo — one checkout, five core packages, zero cross-repo import friction.**

Multi-agent legal-document pipeline · Deterministic scoring · Pixel-art visualizer · Local sandbox · Corpus EDA

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
Corpus feeds ────────────────> llm-mailroom (13-node pipeline)
                                     ▲             │
local-mailroom-sandbox ── executes ────┘             │ uses
  offline/local + Modal/vLLM GPU harness            ▼
  │                                         llm-dojo-scoring
  └────────────── uses scoring ─────────────> ALL engine + metrics

llm-mailroom ────────────────┐
local-mailroom-sandbox ──────┴── Langfuse / API ──> The-Mailroom
                                                  shared visualizer

Committed standalone sources ── import ──> Digital-Mailroom packages/
Imported workspace packages ── generate ─> sandbox vendor snapshots
Digital-Mailroom owns hub wiring, governance, board, and integration tooling.
```

## Repository Map

Five core packages are imported into `packages/` as git subtrees from authoritative standalone `Exios66/*` repositories: four built members and one virtual corpus-EDA member. Two core packages have GitHub Pages sites; the external Enron and claims feeds have their own sites.

> **Pruned in DMR-079:** `llm-entity-extraction` and `llm-mailroom-graph` left the monorepo (standalone `Exios66/*` repos only, no longer synced); `agent-mailroom` is preserved on the branch `feature/agent-mailroom`. Hub `v0.8.0` is the last release containing them (rollback point).

<div align="center">

| Layer | Repository | GitHub/Vercel Pages |
| :--- | :--- | :--- |
| **Hub** (integration) | [`LLM-Mailroom-Services/Digital-Mailroom`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) | [Dispatch Board](https://digital-mailroom-theta.vercel.app) |
| **Corpus EDA + HF** | [`Exios66/Mailroom-Corpus-EDA`](https://github.com/Exios66/Mailroom-Corpus-EDA) | [exios66.github.io/Mailroom-Corpus-EDA](https://exios66.github.io/Mailroom-Corpus-EDA/) |
| **Scoring engine** | [`Exios66/llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring) | — |
| **LangGraph pipeline** | [`Exios66/llm-mailroom`](https://github.com/Exios66/llm-mailroom) | — |
| **Pixel visualizer** | [`Exios66/The-Mailroom`](https://github.com/Exios66/The-Mailroom) | [exios66.github.io/The-Mailroom](https://exios66.github.io/The-Mailroom/) |
| **Local sandbox** | [`Exios66/local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox) | — |

</div>

## External corpus feeds and preserved checkouts

Enron and claims remain usable standalone feeds; their datasets, taxonomy and
published sites retain their identities. DMR-093 removes their local copies
from the active workspace after #162. Both preservation branches point to
`59c879d9fb4480084e53137e2e9fb25650933944`; PR162 must keep these package trees byte-identical.

| Layer | Repository | GitHub Pages |
| --- | --- | --- |
| **Corpus feed** | [`Exios66/Enron-Evaluation-Environment`](https://github.com/Exios66/Enron-Evaluation-Environment) | [exios66.github.io/Enron-Evaluation-Environment](https://exios66.github.io/Enron-Evaluation-Environment/) |
| **Corpus feed** | [`Exios66/claims-data-eda`](https://github.com/Exios66/claims-data-eda) | [exios66.github.io/claims-data-eda](https://exios66.github.io/claims-data-eda/) |

Browse [Enron's preserved package](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/enron-evaluation-environment/packages/Enron-Evaluation-Environment) or
[claims' preserved package](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/claims-data-eda/packages/claims-data-eda). Use a separate checkout of the
preservation branch for its original complete workspace (including the old
hub chart generator). To selectively restore a package, reconcile membership,
sync entries, dependencies and tests explicitly; keep current root metadata.
The earlier `feature/agent-mailroom` preservation branch remains unchanged.

## Package Details

<div align="center">

| Package | Role | Source |
| :--- | :--- | :--- |
| `llm-dojo-scoring` | ALL scoring engine logic and metrics; error-analysis and interpretation suite | [`Exios66/llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring) |
| `llm-mailroom` | LangGraph multi-agent legal-document pipeline (FastAPI producer) | [`Exios66/llm-mailroom`](https://github.com/Exios66/llm-mailroom) |
| `The-Mailroom` | Shared visualizer for BOTH llm-mailroom and local-mailroom-sandbox; hosted Observatory | [`Exios66/The-Mailroom`](https://github.com/Exios66/The-Mailroom) |
| `local-mailroom-sandbox` | Core offline/local and Modal/vLLM GPU testing interface for the llm-mailroom pipeline | [`Exios66/local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox) |
| `mailroom-corpus-eda` | mailroom-corpus corpus EDA (P0–P6) + centralized HF upload helpers | [`Exios66/Mailroom-Corpus-EDA`](https://github.com/Exios66/Mailroom-Corpus-EDA) |

</div>

> `mailroom-corpus-eda` is the sole virtual member (`package = false`): it has no build system and is not installed. Its EDA code and deliverables stay colocated with the four built members.

## Repository Structure

```
Digital-Mailroom/
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
│   ├── sync_packages.py   # standalone source → hub imports
│   ├── taxonomy_parity.py # taxonomy drift detector (CI gate)
│   ├── release_chain.py   # hub changelog ↔ semver tag ↔ version gate (HUB-024)
│   └── deploy_gh_pages.py # local GH Pages deploy (no Actions)
└── packages/              # five core packages (four built + one virtual)
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
uv run pytest packages/The-Mailroom/tests
uv run pytest packages/local-mailroom-sandbox/tests
uv run pytest packages/mailroom-corpus-eda/tests
```

Cross-package dependencies resolve to **workspace sources** during development (`[tool.uv.sources]` in each member pyproject); published git pins remain in dependency lines for release builds.

## Sub-Package Sync

Standalone `Exios66/*` repositories own package implementations. Author, test, and commit changes there; import committed sources here with `scripts/sync_packages.py`. Digital-Mailroom owns hub wiring, governance, board, and integration tooling. Workspace package copies and generated vendors are never implementation sources; never implement a package change here and push it back.

Commit messages follow the [shared template and examples](docs/COMMIT_MESSAGES.md): name the changed behavior, explain the affected files, and report validation and compatibility limits.

```bash
python scripts/sync_packages.py status                  # live status
python scripts/sync_packages.py pull --all              # sync from upstream
python scripts/sync_vendor.py                          # regenerate vendors from imported sources
python scripts/sync_vendor.py --check                  # verify vendor identity
python scripts/sync_packages.py snapshot                # cursor verification
```

## GitHub Governance Tooling

The board and GitHub surface are kept machine-readable and mutually consistent.
The live dispatch board is **<https://digital-mailroom-theta.vercel.app>** (issue-backed; see `board-site/` and `docs/wiki/Served-Board.md`):

```bash
python scripts/board_state.py status            # live board snapshot (--json for machines)
python scripts/board_state.py check             # board invariants; exit 1 on structural errors
python scripts/github_labels.py audit           # label taxonomy drift (CI gate)
python scripts/taxonomy_parity.py               # doc-class taxonomy drift (CI gate, HUB-019 §65A)
python scripts/release_chain.py status          # hub release chain: tags, changelog sections, hub version
python scripts/release_chain.py check           # chain invariants; exit 1 on structural errors
python scripts/release_chain.py cut X.Y.Z       # cut a hub release (dry run; --apply writes; tag after merge)
./docs/wiki/sync-wiki.sh                        # push docs/wiki/ source to the GitHub wiki (--check for drift)
```

See `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE/`, `.github/labels.json`, `scripts/board_state.py`, and `governance/TASKS.md` for the full governance contract.

## Wiki

The [GitHub wiki](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/wiki) is mirrored from `docs/wiki/`.

## Release Flow

Release packages from their authoritative standalone repositories and update consuming pins there at release time. Import committed sources into the hub, regenerate vendors, and verify integration suites. Hub releases version the integration workspace separately; commit the cut and `uv.lock`, merge the PR, then tag the merged main tip. See [Sub-Package Sync](docs/wiki/Sub-Package-Sync.md) and [Releases](docs/wiki/Releases.md). Legacy outbound package pushes are forbidden.

---

<div align="center">

**[llm-mailroom](https://github.com/Exios66/llm-mailroom)** ·
**[llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring)** ·
**[The-Mailroom](https://github.com/Exios66/The-Mailroom)**

<sub>Built by the governed evaluation family under <a href="https://github.com/LLM-Mailroom-Services">LLM-Mailroom-Services</a> (Exios66 · grantmooslin) · 2026</sub>

</div>
