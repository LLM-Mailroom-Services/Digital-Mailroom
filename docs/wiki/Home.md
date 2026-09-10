# Digital-Mailroom — the LLM-Mailroom monorepo wiki

**Digital-Mailroom** is the central checkout of the LLM-Mailroom constellation:
one uv workspace, one lockfile, one virtualenv, ten packages under
[`packages/`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/main/packages) —
each mirroring an independent, standalone-operational `Exios66/*` repository.

The monorepo is the **development source of truth**; the standalone repos
remain the release vehicles for the deployed surfaces.

The board is also served live at **https://digital-mailroom-theta.vercel.app**
(issue-backed, auto-updating; see [[Served-Board]]).

## Start here

- [[Getting-Started]] — workspace setup, suites, offline sandbox quickstart
- [[Architecture]] — every repository, with direct links + GitHub Pages sites
- [[Board-Governance]] — the task board, its laws, and the tooling that keeps it honest
- [[Served-Board]] — the live Vercel dispatch-board site, its API + deploy
- [[Sub-Package-Sync]] — the current-only sync doctrine and the sync driver
- [[HF-Corpus]] — the mailroom-corpus corpus family and its EDA pipeline
- [[Offline-Sandbox]] — local providers, reduced agent profile, Docker
- [[Releases]] — release train, pins, upstream publish
- [[FAQ]] — gotchas and common questions

## Key facts

| Thing | Value |
| --- | --- |
| Hub repo | [LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) — latest hub release **v0.4.0** |
| Task board | [`governance/TASKS.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/governance/TASKS.md) — machine-readable via `scripts/board_state.py` |
| Served board | [digital-mailroom-theta.vercel.app](https://digital-mailroom-theta.vercel.app) — live, issue-backed ([[Served-Board]]) |
| Conventions | [`AGENTS.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/AGENTS.md) — read first, every session |
| Packages | 10 (6 built + 4 virtual members) |
| Python | 3.11+ (workspace `requires-python >= 3.11`) |
| Family pins | llm-mailroom **v0.6.0** · llm-dojo-scoring **v0.12.2** · llm-entity-extraction **v0.20.0** |
| HF corpus | [mailroom-corpus](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-corpus) — schema v8, 2,000 rows |
| CI gate | `.github/workflows/board-governance.yml` — board invariants + label drift |
