# Getting started

## Workspace setup

One checkout, one virtualenv — never import across separate repositories:

```bash
git clone https://github.com/LLM-Mailroom-Services/Digital-Mailroom.git
cd Digital-Mailroom
uv sync        # install every workspace member editable into .venv
```

Cross-package dependencies resolve to **workspace sources** during
development (`[tool.uv.sources]` in each member pyproject). The published
git pins stay in the dependency lines so plain `pip install .` inside a
package directory (Docker, Railway, Spaces) keeps working for release
builds. Never delete a pin line to "fix" resolution — bump pins only when
cutting a release of the pinned package (see [[Releases]]).

## Per-package test suites

Run one package per pytest invocation — several packages ship a top-level
regular `tests` package and collide when batched:

```bash
uv run pytest packages/llm-dojo-scoring/tests
uv run pytest packages/llm-mailroom/src/tests
uv run pytest packages/llm-entity-extraction/tests
uv run pytest packages/The-Mailroom/tests
uv run pytest packages/agent-mailroom/tests
uv run pytest packages/local-mailroom-sandbox/tests
uv run pytest packages/claims-data-eda/tests
uv run pytest packages/Enron-Evaluation-Environment/tests
```

`llm-mailroom-graph` and `mailroom-corpus-eda` ship no test suite — the
graph site is a static build and the corpus EDA is verified behaviorally via
`packages/mailroom-corpus-eda/run_all.py` (P0–P6).

Surgical by default; run a package's FULL suite only for significant
changes (packaging/imports, cross-cutting refactors, scoring) and always
before a release.

## Offline sandbox quickstart

```bash
cd packages/local-mailroom-sandbox
pip install -e ".[dev]"
cp config/.env.example .env
sandbox profiles                     # list provider profiles
sandbox up                           # langfuse + ollama compose profiles
sandbox pull-models                  # ollama pull qwen3:8b
sandbox health
sandbox eval pipeline --mock         # connected graph scores, no LLM
```

Live local-LLM tests need `SANDBOX_LOCAL_LLM=1`. See [[Offline-Sandbox]].

## Read the board before any task

[[Board-Governance]] is not optional: every agent (and human) reads
`governance/TASKS.md` FIRST every session, claims cards before edits, and
closes them with proof.

The board is also served live at https://digital-mailroom-theta.vercel.app — view and
edit cards in a browser (issue-backed, auto-updating). Site edits write
issues, not TASKS.md: run `python scripts/board_state.py pull-issues
--apply` afterward to pull lane moves back into the canonical board
([[Served-Board]]).

## Specialist subagents

Every specialty has a dedicated subagent (data/HF, prompts, docs/board, UI,
systems, vLLM, Modal) — invoke it through the Task tool rather than
improvising outside your expertise. The roster, the project agent files
under `.opencode/agents/`, and the rules (one specialist per concern, brief
like a card, the caller owns the work) are in [[Subagents]].
