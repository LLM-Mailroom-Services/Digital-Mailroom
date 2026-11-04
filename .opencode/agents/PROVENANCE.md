# OpenCode agent provenance

Family agents were copied from upstream snapshots (byte-stable prompts). Refresh
by re-downloading from the cited refs and updating `config/subagents/roster.yaml`
`family_source` fields.

| Agent | Upstream repo | Ref |
| --- | --- | --- |
| prompt-engineer | Exios66/llm-entity-extraction | `42c54929` |
| eval-judge | Exios66/llm-entity-extraction | `42c54929` |
| experiment-log-sync | Exios66/llm-entity-extraction | `42c54929` |
| trace-log-analyst | Exios66/llm-mailroom | `28cb4be8` |
| mailroom-arch-optimizer | Exios66/llm-mailroom | `28cb4be8` |
| legal-changelog-auditor | Exios66/llm-mailroom | `28cb4be8` |
| harness-doctor | sandbox-native | SAND-017 |
| adversarial-reviewer | sandbox-native | SAND-017 |

Cursor stubs under `.cursor/agents/` are generated — run:

```bash
sandbox subagents sync --harness cursor
```
