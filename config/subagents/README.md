# Subagent roster

| File | Role |
| --- | --- |
| [`family-roster.yaml`](family-roster.yaml) | **Canonical family manifest** (packages, harnesses, all subagents) |
| [`roster.yaml`](roster.yaml) | Pointer for this checkout (`package: local-mailroom-sandbox`) |

Commands:

```bash
sandbox subagents packages
sandbox subagents list [--package llm-mailroom]
sandbox subagents show harness-doctor
sandbox subagents sync --harness all
sandbox subagents sync --harness opencode-global
sandbox subagents doctor
sandbox subagents doctor --apply-framework
sandbox subagents materialize --package digital-mailroom --root /path/to/Digital-Mailroom
sandbox subagents propagate
```

Monorepo workflow: [`docs/subagents-family-sync.md`](../../docs/subagents-family-sync.md).

Shared agent operating law: [`AGENT_FRAMEWORK.md`](AGENT_FRAMEWORK.md).

After editing an OpenCode prompt, run `sandbox subagents sync --harness all`.

Durable eve agent (machine-wide doctor UI/tools): `~/Downloads/agent-harness-doctor`.
