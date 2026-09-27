# Family subagent roster sync

One manifest drives OpenCode and Cursor across the mailroom family.

**Primary monorepo:** [LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom).
`Exios66/mailroom-dev` is legacy — use Digital-Mailroom for hub paths and
`scripts/sync_packages.py`.

## Canonical file

[`config/subagents/family-roster.yaml`](../config/subagents/family-roster.yaml) lists every
coding subagent, its **home package**, and which packages **materialize** it.

| Package | Typical path | Roster install path |
| --- | --- | --- |
| `local-mailroom-sandbox` | this repo / `packages/local-mailroom-sandbox` | `config/subagents/family-roster.yaml` |
| `digital-mailroom` | monorepo hub | `governance/subagents/family-roster.yaml` |
| `llm-mailroom` | `packages/llm-mailroom` | `config/subagents/family-roster.yaml` |
| `llm-entity-extraction` | `packages/llm-entity-extraction` | `config/subagents/family-roster.yaml` |
| `eval-environment` | eval runner repo | `config/subagents/family-roster.yaml` |

## Workflow

### One command (recommended)

From a sandbox checkout with sibling `Digital-Mailroom/` (or set
`DIGITAL_MAILROOM_ROOT` / `MONOREPO_ROOT`):

```bash
sandbox subagents propagate
```

Standalone **eval-environment** (sibling repo, not in `checkout-map.yaml`):

```bash
sandbox subagents materialize --package eval-environment --root ../eval-environment
sandbox subagents sync --harness all --package eval-environment --root ../eval-environment
```

This runs **materialize + sync** for every entry in
[`checkout-map.yaml`](../config/subagents/checkout-map.yaml).

### Monorepo automation

After a one-time hook in **Digital-Mailroom** `scripts/sync_packages.py` (see
[`scripts/monorepo/INTEGRATION.md`](../scripts/monorepo/INTEGRATION.md)), each
successful **`pull`** / **`push`** runs:

```bash
python3 packages/local-mailroom-sandbox/scripts/monorepo/after_packages_sync.py
```

### Manual per-checkout

```bash
sandbox subagents materialize --package llm-mailroom --root ../Digital-Mailroom/packages/llm-mailroom
sandbox subagents sync --harness all --package llm-mailroom --root ../Digital-Mailroom/packages/llm-mailroom
```

After editing prompts in `.opencode/agents/`, re-run **`propagate`** or sync for
the affected packages (`sandbox subagents list --package llm-mailroom`).

## Harness adapters

| Harness | Output | What sync does |
| --- | --- | --- |
| **OpenCode** | `.opencode/agents/<id>.md` | Merges roster frontmatter (`mode`, `title`, `tags`, `home_package`, `roster_id`) while preserving the prompt body |
| **Cursor** | `.cursor/agents/<id>.md` | Generates `name` + `description` stubs pointing at the OpenCode canonical prompt |
| **OpenCode global** | `~/.config/opencode/agents/<id>.md` | Same frontmatter merge for machine-wide profiles (`--harness opencode-global`) |

Default CLI sync target is **`--harness all`** (includes global).

Health: `sandbox subagents doctor` and optional `--also-root <checkout>`.
Framework v2: [`config/subagents/AGENT_FRAMEWORK.md`](../config/subagents/AGENT_FRAMEWORK.md).

## Environment

| Variable | Purpose |
| --- | --- |
| `DIGITAL_MAILROOM_ROOT` | Preferred path to the org monorepo checkout |
| `MONOREPO_ROOT` | Generic alias for the same |
| `MAILROOM_DEV_ROOT` | Legacy alias (still honored) |
| `SUBAGENT_PACKAGE` | Override default package filter for list/show/sync |

Default package filter for this standalone repo: `local-mailroom-sandbox`.
