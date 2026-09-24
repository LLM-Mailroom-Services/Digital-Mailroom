<div align="center">

# 🔌 Agent Mailroom API

**HTTP surface for the agent-mailroom package (`agent_mailroom.api.app`).**

</div>

---

## Endpoints

Routes mount at `/` and `/v1` (see the package `README.md` “Full endpoint list” for
the live table). Common paths include `/health`, `/upload`, `/lookup`,
`/review/queue`, `/metrics`, `/hive/board`, and `/console`.

## Usage

```bash
cd packages/agent-mailroom
uv run uvicorn agent_mailroom.api.app:app --host 127.0.0.1 --port 8080
```

## Related Files

- `../agents/` — Agent implementations
- `../pipeline/` — Pipeline logic
- `../storage/` — Storage backend
