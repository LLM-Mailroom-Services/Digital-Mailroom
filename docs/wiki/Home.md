# Digital-Mailroom — the LLM-Mailroom monorepo wiki

**Digital-Mailroom** is the central checkout of the LLM-Mailroom constellation:
one uv workspace, one lockfile, one virtualenv, five core packages under
[`packages/`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/main/packages) —
each mirroring an independent, standalone-operational `Exios66/*` repository.

Standalone repositories own package implementations and releases. Implement
and test there first, then import committed sources here. Digital-Mailroom
owns workspace wiring, governance, the board and integration tooling.
Enron and claims are external feeds with complete preserved hub checkouts;
see [[Architecture]] for branch and source links.

The board is also served live at **https://digital-mailroom-theta.vercel.app**
(issue-backed, auto-updating; see [[Served-Board]]).

## Start here

- [[Getting-Started]] — workspace setup, suites, offline sandbox quickstart
- [[Architecture]] — every repository, with direct links + GitHub Pages sites
- [[Board-Governance]] — the task board, its laws, and the tooling that keeps it honest
- [[Subagents]] — the specialist roster (data, HF, prompts, docs, UI, systems, vLLM, Modal) and the rules that make it work
- [[Served-Board]] — the live Vercel dispatch-board site, its API + deploy
- [[Sub-Package-Sync]] — the current-only sync doctrine and the sync driver
- [[HF-Corpus]] — the mailroom-corpus corpus family and its EDA pipeline
- [[Offline-Sandbox]] — local providers, reduced agent profile, Docker
- [[Releases]] — release train, pins, upstream publish
- [[FAQ]] — gotchas and common questions
- [[Troubleshooting]] — symptoms we have hit (tests, sync, vendors, board, commits) and their fixes
- [[Glossary]] — workspace, board, pipeline and scoring terms
- Contributing? Read [`CONTRIBUTING.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/CONTRIBUTING.md) first; security reports: [`SECURITY.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/SECURITY.md)

## Key facts

| Thing | Value |
| --- | --- |
| Hub repo | [LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) — latest hub release **v0.9.1** (`pyproject.toml` 0.9.1) |
| Task board | [`governance/TASKS.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/governance/TASKS.md) — machine-readable via `scripts/board_state.py` |
| Served board | [digital-mailroom-theta.vercel.app](https://digital-mailroom-theta.vercel.app) — live, issue-backed ([[Served-Board]]) |
| Conventions | [`AGENTS.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/AGENTS.md) — read first, every session |
| Subagents | 15-agent roster ([[Subagents]]) — project + global agent files under `.opencode/agents/` (see DMR-062) |
| Packages | 5 (4 built + 1 virtual member: mailroom-corpus-eda) |
| Python | 3.11+ (workspace `requires-python >= 3.11`) |
| Imported package versions | llm-dojo-scoring **0.24.0** · llm-mailroom **0.8.1** · local-mailroom-sandbox **0.3.0** · The-Mailroom **0.5.1** · mailroom-corpus-eda **0.1.0** (see [[Releases]] for consuming pins) |
| HF corpus | [mailroom-dataset](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset) — schema v9, 3,302 rows (frozen v8 baseline: [mailroom-corpus](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-corpus)) |
| CI gates | `board-governance.yml` (board invariants + label drift) · `release-governance.yml` (changelog ↔ tag ↔ version). No workflow runs the package suites — the local run is the gate ([`docs/TESTING.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/docs/TESTING.md)) |
