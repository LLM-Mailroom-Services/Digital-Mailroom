<div align="center">

# 🖥️ The-Mailroom Server

**Backend server implementation for The-Mailroom visualizer.**

</div>

---

## Purpose

The server provides the backend API for The-Mailroom visualizer, including:

- Langfuse/Phoenix data aggregation
- WebSocket event streaming
- Review queue management
- Pipeline status endpoints

## Running

```bash
cd packages/The-Mailroom
pip install -e ".[dev]"
mailroom-web              # Pixel console on http://127.0.0.1:8001/
mailroom-hosted           # Observatory on http://127.0.0.1:8001/live
```

## API Endpoints

| Endpoint | Purpose |
| :--- | :--- |
| `/api/traces` | Pipeline trace data |
| `/api/review-queue` | Human review queue |
| `/api/review/resolve` | Resolve review items |
| `/api/debug/bundle` | Debug bundle |
| `/ws/pipeline` | WebSocket pipeline events |

## Related Files

- `hosted/` — Observatory (hosted edition)
- `web/` — Pixel console
- `ui/` — React operator desk
