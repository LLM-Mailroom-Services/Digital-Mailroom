# The-Mailroom Wiki

> This wiki mirrors `docs/` in the repository. **Edit both together** — the
> `wiki/` directory is pushed to the GitHub wiki by `wiki/sync-wiki.sh`.
> Architecture and process authority: `AGENTS.md` in the repo root.

## The governed constellation

The-Mailroom is the shared visualizer for the
[llm-mailroom pipeline](https://github.com/Exios66/llm-mailroom) and its
[offline/local and Modal/vLLM sandbox](https://github.com/Exios66/local-mailroom-sandbox).
[Dojo](https://github.com/Exios66/llm-dojo-scoring) owns scoring and metrics;
[corpus EDA](https://github.com/Exios66/Mailroom-Corpus-EDA) owns corpus tooling.
These five source repositories are integrated by
[Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom).
The visualizer reads their Langfuse traces.

Optional `[eval]` and `[pipeline]` installs share published Dojo `v0.24.2` at immutable commit `4740d768`.
The producer code pin is dist `mailroom` at `60cd5fad0c7a616ec575857841bb9897b9e8c3ed` (0.8.1).
Enron and claims remain external data feeders, with their historical hub copies
on dedicated preservation branches; they are not active core workspace packages.
The standalone extraction and LegalBench repositories retain their own workflows.
Full source map: [pipeline sister repositories](https://github.com/Exios66/llm-mailroom/blob/main/docs/sister-repos.md).

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
