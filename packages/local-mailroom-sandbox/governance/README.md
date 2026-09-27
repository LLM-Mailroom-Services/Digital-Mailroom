# Sandbox governance (SAND)

Local board for **sandbox-isolated** work in
[`local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox).

## Prefix rule (binding)

| Prefix | Where it lives | Use for |
| --- | --- | --- |
| **`SAND-NNN`** | this repo — [`TASKS.md`](TASKS.md) | Sandbox harness, Modal runbooks, offline fixtures, vendor sync *as consumed by the sandbox*, job CLI, requirements mirrors, local docs |
| **`DMR-NNN`** | llm-entity-extraction **MESSAGE_BOARD** | Cross-family / mailroom-pipeline / dojo / entity work shared across the governed family |

**Do not** open `DMR-*` cards on this board. **Do not** invent a second
family MESSAGE_BOARD here (AGENTS.md / `docs/sister-repos.md`). When a
sandbox change is *driven by* a family DMR, cite the DMR in the SAND card
notes (`Related: DMR-078`) — the card ID stays `SAND-*`.

Legacy `SANDBOX-050-*` mission cards are archived under
[`archive/SANDBOX-050.md`](archive/SANDBOX-050.md) and mapped to `SAND-*`.

## Card ID format

```
SAND-<NNN>           # primary card (zero-padded, sequential)
SAND-<NNN>-<k>       # optional sub-card of a mission epic
```

Examples: `SAND-001`, `SAND-014-3`.

Lanes: `todo` → `in_progress` → `needs_attention` → `done` · Owner · UTC date.

## Files

| Path | Role |
| --- | --- |
| [`TASKS.md`](TASKS.md) | Active SAND task list (the local board) |
| [`archive/`](archive/) | Closed missions / superseded card schemes |
| [`PREFIX.md`](PREFIX.md) | Short cheat-sheet for agents / operators |

Next free ID: see the **Next ID** line at the top of `TASKS.md`.
