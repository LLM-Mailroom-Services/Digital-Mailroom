# SAND prefix cheat-sheet

```
SAND-NNN     → sandbox-isolated card on governance/TASKS.md
DMR-NNN      → family card on llm-entity-extraction MESSAGE_BOARD
```

When filing work:

1. Is it only meaningful inside `local-mailroom-sandbox`?
   → **`SAND-*`** here.
2. Does it change shared mailroom / dojo / entity contracts across repos?
   → **`DMR-*`** on the family MESSAGE_BOARD; optionally add a thin
   `SAND-*` tracker that cites `Related: DMR-NNN`.

Never reuse a DMR number as a SAND id (avoids “is SAND-078 the same as
DMR-078?” confusion). Sequence SAND independently from 001.
