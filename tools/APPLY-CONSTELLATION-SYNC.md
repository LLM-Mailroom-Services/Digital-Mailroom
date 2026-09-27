# Constellation feeder sync (one-shot)

This PR adds a **git bundle** of the verified monorepo sync (211 paths vs `main`):

- `llm-dojo-scoring` v0.16.0
- `local-mailroom-sandbox` @ upstream `116d219` + vendor refresh
- `mailroom-corpus-eda` v9.1 revision
- Pin bumps on mailroom / entity-extraction / agent-mailroom
- Updated `scripts/packages_sync.json` cursors

Local verification (same tree as bundle tip `352363a7`):

- `pytest packages/llm-dojo-scoring/tests/test_consumer_compat.py` — 7 passed
- `pytest packages/llm-mailroom/src/tests/test_dojo_v012.py` — 11 passed
- `pytest packages/local-mailroom-sandbox/tests/test_vendor*.py` — 22 passed

## Apply to `main`

1. **Merge this PR** (adds workflow + bundle parts only).
2. **Run workflow:** Actions → **Apply constellation sync bundle** → **Run workflow**.
3. Workflow fast-forwards `main` to the bundled commit (full feeder sync).

No per-file MCP or subtree pull required.
