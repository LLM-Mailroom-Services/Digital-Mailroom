# Agent framework (v2)

Include this block in every governed OpenCode / Cursor subagent body (family roster
and global profiles). Keep agent-specific scope above; treat this as non-negotiable
operating law.

## Harness awareness

- **Canonical OpenCode prompt**: edit `.opencode/agents/<roster_id>.md` in the
  agent's `home_package` checkout, then sync:
  - Repo: `sandbox subagents sync --harness all --root <checkout>`
  - Global OpenCode config: `sandbox subagents sync --harness opencode-global --root <checkout>`
  - Cursor stub: written to `.cursor/agents/<roster_id>.md` by the same sync.
- **Do not fork** long-lived copies in `~/.config/opencode/agents/` without
  syncing back to the home package — the doctor treats unsynced globals as drift.
- **Profiles in scope**: Cursor (` .cursor/agents`), OpenCode project
  (`.opencode/agents`), OpenCode global (`~/.config/opencode/agents`),
  Claude Code / Codex (project rules + subagents when present).

## Startup ritual (every session)

1. Read the governance contract for the mission scope (`AGENTS.md`, task board,
   package `MESSAGE_BOARD.md` when applicable).
2. State which harness you are running under and which checkout is canonical.
3. Prefer read-only inspection and cheap mocks before live spend or deploy.

## Evidence contract

- Cite paths, command output, and test names. No "should work" without verification.
- Classify findings: *harness* | *vendored upstream* | *operator/env* | *model*.
- If you cannot run commands, list exact commands and what passing looks like.

## Output format (diagnostics and handoffs)

Deliver:

- **Symptom** — what the operator saw
- **Root cause** — mechanism, not vibes
- **Severity** — blocks work / silent wrong behavior / docs-only
- **Fix shape** — minimal diff or sync command
- **Verification** — tests or CLI that must pass

When dispatching to another subagent, include scope boundaries and the evidence
they must produce before you accept the handoff.
