# The-Mailroom Wiki

> This wiki mirrors `docs/` in the repository. **Edit both together** — the
> `wiki/` directory is pushed to the GitHub wiki by `wiki/sync-wiki.sh`.
> Architecture and process authority: `AGENTS.md` in the repo root.

## The governed constellation

The-Mailroom is one node of a governed family sharing one kanban board and one
trace contract: **[llm-mailroom](https://github.com/Exios66/llm-mailroom)** is
the upstream pipeline whose Langfuse project is this visualizer's sole data
source; **[llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction)**
is the prompt-experiment loop that breeds its sorter/specialist prompts (and
hosts the shared governance board); **[llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring)**
is the pinned scoring engine behind both (`@v0.11.0`); **llm-mailroom** itself
is pinned here as dist `mailroom` `@2a212e76a62b` / **v0.7.1** (optional extra `[pipeline]`); **[Enron-Evaluation-Environment](https://github.com/Exios66/Enron-Evaluation-Environment)**
and **[claims-data-eda](https://github.com/Exios66/claims-data-eda)** feed its
corpus classes; **[atticus-investigation](https://github.com/Exios66/atticus-investigation)**
is the LegalBench eval sibling. Full map:
[`llm-mailroom/docs/sister-repos.md`](https://github.com/Exios66/llm-mailroom/blob/main/docs/sister-repos.md).

## Surfaces

- **Pixel console** (`mailroom-web`) — local CRT / conveyor (FLOOR · REVIEW ·
  SESSIONS · HISTORY · METRICS · CONSOLE)
- **Observatory** (`/live`, `mailroom-hosted`) — public modern accessible desk
  (Pipeline · Review · History · Matters · Metrics · Debug;
  `GET /api/debug/bundle`). Hugging Face Space: Docker + port 7860
  (`scripts/publish_space.py`, `hosted/SPACE_README.md`). Railway /
  Fly / Render: see [Deployment](Deployment) (`.railway/railway.py` IaC,
  platform `PORT` preferred over image `MAILROOM_PORT`)
- **TUI** (`mailroom-tui`) — terminal (floor · review · sessions · metrics ·
  inspect · debug)
- **GitHub Pages** — static snapshot of the pixel SPA (not the Observatory)
- **Operator desk** (`operator_desk/`) — JWT auth, local archive, Langfuse-backed
  ops, `/ws/pipeline` (not a display source)
- **Optional React desk** (`ui/`) — `/desk` when built; Node never required for
  `mailroom-web`

## Agent skills

Committed under `.cursor/skills/`. Start with `mailroom-tool-router`. Family
stacks match
[local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox/tree/main/.cursor/skills)
(Langfuse default; Phoenix optional; Braintrust/Ollama/Modal are not this
visualizer). Extra skills cover pixel console, Observatory, live floor, schema
sync, Pages, TUI, and operator desk. Index: repo `.cursor/skills/README.md`.

## Pages

- [Home](Home) — overview, quick start, sister-repo pointer
- [Architecture](Architecture) — how traces become pixels
- [Demos](Demos) — stills of every desk, the live Hugging Face Space
  walkthrough, and the PR recordings
- [Releases](Releases) — semantic versioning, changelog, tagging process
- [Operator Desk](Operator-Desk) — JWT / archive / ops / bin observer
