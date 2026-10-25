# Project Agent Skills

Committed Cursor skills for **The-Mailroom**. Agents should discover these under
`.cursor/skills/*/SKILL.md` and prefer them over inventing a second trace
source, a Node toolchain, or a live LLM client inside this visualizer.

Companion to [`local-mailroom-sandbox` skills](https://github.com/Exios66/local-mailroom-sandbox/tree/main/.cursor/skills)
([PR #4](https://github.com/Exios66/local-mailroom-sandbox/pull/4)): same family
names (Langfuse / Phoenix / Braintrust / Ollama / Modal / Hugging Face),
rewritten for **this** repo’s job — rendering `document-pipeline` traces.

| Skill | Use for |
| --- | --- |
| [mailroom-tool-router](mailroom-tool-router/SKILL.md) | **Start here** — pick the right tool |
| [langfuse](langfuse/SKILL.md) | Default (and document-display) source |
| [apache-phoenix](apache-phoenix/SKILL.md) | Optional `MAILROOM_SOURCE=phoenix\|both` |
| [braintrust](braintrust/SKILL.md) | Not a display source — do not add one |
| [huggingface](huggingface/SKILL.md) | Hub eval / pilot scripts; copied catalogs |
| [ollama](ollama/SKILL.md) | Local LLM lives in sandbox/pipeline, not here |
| [modal](modal/SKILL.md) | Remote GPU lives in sandbox/pipeline, not here |
| [pixel-console](pixel-console/SKILL.md) | Vanilla `web/` SPA |
| [observatory](observatory/SKILL.md) | Hosted `/live` desk |
| [live-floor](live-floor/SKILL.md) | Poller, WS, watcher/inbox lamp |
| [pipeline-schema-sync](pipeline-schema-sync/SKILL.md) | Mirror `llm-mailroom` topology |
| [gh-pages](gh-pages/SKILL.md) | Deploy-from-branch snapshot |
| [tui](tui/SKILL.md) | `mailroom-tui` |
| [operator-desk](operator-desk/SKILL.md) | JWT auth, archive, ops, bin observer (`operator_desk/`) |
| [optional-ui](optional-ui/SKILL.md) | Optional React desk (`ui/`, `/desk`) — never the pixel CRT |

Also see root [`AGENTS.md`](../../AGENTS.md).
