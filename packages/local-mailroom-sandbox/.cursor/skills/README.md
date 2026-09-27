# Project Agent Skills

Committed Cursor skills for **local-mailroom-sandbox**. Agents should discover these under `.cursor/skills/*/SKILL.md` and prefer them over inventing parallel stacks.

| Skill | Use for |
| --- | --- |
| [sandbox-tool-router](sandbox-tool-router/SKILL.md) | **Start here** — pick the right tool |
| [ollama](ollama/SKILL.md) | Default local LLM |
| [modal](modal/SKILL.md) | Remote Modal vLLM |
| [langfuse](langfuse/SKILL.md) | Default tracing / The-Mailroom |
| [apache-phoenix](apache-phoenix/SKILL.md) | Optional Phoenix sidecar |
| [braintrust](braintrust/SKILL.md) | Opt-in hosted Braintrust |
| [huggingface](huggingface/SKILL.md) | Hub pulls / weights (offline-first) |

Coding **subagents** (GEPA prompt engineer, trace analyst, harness doctor,
adversarial reviewer): roster in [`config/subagents/`](../../config/subagents/),
prompts in [`.opencode/agents/`](../../.opencode/agents/) — sync Cursor stubs
with `sandbox subagents sync --harness cursor`.

Also see root [`AGENTS.md`](../../AGENTS.md) and [`docs/docker-offline.md`](../../docs/docker-offline.md).
