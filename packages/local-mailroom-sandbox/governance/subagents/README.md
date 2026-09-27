# Family subagent roster (monorepo mirror)

The **canonical** manifest lives in the sandbox package at
[`config/subagents/family-roster.yaml`](../../config/subagents/family-roster.yaml)
and is copied to **`governance/subagents/family-roster.yaml`** on the org monorepo
**[LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)**
when you materialize the **`digital-mailroom`** hub:

```bash
# from local-mailroom-sandbox (standalone or monorepo package)
sandbox subagents materialize --package digital-mailroom --root /path/to/Digital-Mailroom
sandbox subagents sync --harness all --package digital-mailroom --root /path/to/Digital-Mailroom
```

Or use **`sandbox subagents propagate`** with `DIGITAL_MAILROOM_ROOT` set.

Sibling packages (`packages/llm-mailroom`, `packages/llm-entity-extraction`, …)
receive the same manifest under their own `config/subagents/` plus filtered
OpenCode/Cursor stubs for agents listed under that package in the family roster.
