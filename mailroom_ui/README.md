<div align="center">

# 🐍 Mailroom UI

**Python backend for The-Mailroom visualizer package.**

</div>

---

## Purpose

The `mailroom_ui` package provides the Python backend for The-Mailroom visualizer, including:

- API endpoints for the visualizer
- Data transformation and aggregation
- WebSocket event handling
- Intake normalization utilities

## Key Modules

| Module | Purpose |
|:---|:---|
| `intake_normalize.py` | Deterministic text normalization (mirrors `agents/intake.py`) |

## Usage

```python
from mailroom_ui.intake_normalize import deterministic_normalize, looks_messy
```

## Related Files

- `server/` — Server implementation
- `hosted/` — Observatory (hosted edition)
- `web/` — Pixel console
- `ui/` — React operator desk
