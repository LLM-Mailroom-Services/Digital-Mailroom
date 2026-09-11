# Sister repos

This sandbox is an **orchestrator**. Canonical code stays in the governed family;
the code it imports at runtime ships as tracked snapshots under `vendor/`:

| Repository | Role | Pin |
| --- | --- | --- |
| [llm-mailroom](https://github.com/Exios66/llm-mailroom) | LangGraph pipeline, agents, prompts, SQLite catalog | tracked snapshot `v0.6.0` under `vendor/` (DMR-057) |
| [llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring) | Deterministic scoring engine | tracked snapshot `v0.12.2` under `vendor/` (DMR-057) |
| [llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction) | Prompt experiment loop (separate repo; not imported by the sandbox) | `v0.20.0` |
| [The-Mailroom](https://github.com/Exios66/The-Mailroom) | Pixel-art visualizer (Langfuse-only) | observer |
| [Enron-Evaluation-Environment](https://github.com/Exios66/Enron-Evaluation-Environment) | Correspondence corpus feed | Hub datasets |

Umbrella map: [llm-mailroom/docs/sister-repos.md](https://github.com/Exios66/llm-mailroom/blob/main/docs/sister-repos.md).

Do not duplicate the 13-node graph here. Do not create a second kanban board;
cross-repo work stays on llm-entity-extraction's MESSAGE_BOARD.

Sandbox traces use the same Langfuse v4 contract as llm-mailroom
(`document-pipeline` chain, `NODE_OBSERVATION_TYPES`, `mailroom` tag) so
The-Mailroom can observe local evals. Clone it with `sandbox fetch-deps --visualizer`.
