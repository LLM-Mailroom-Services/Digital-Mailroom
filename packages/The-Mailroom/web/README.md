<div align="center">

# 🌐 The-Mailroom Web

**Pixel console (CRT/conveyor canvas) for The-Mailroom visualizer.**

</div>

---

## Purpose

The pixel console provides a CRT-style visual interface for the Mailroom pipeline, featuring:

- Conveyor canvas animation
- Agent status visualization
- Pipeline progress tracking

## Running

```bash
cd packages/The-Mailroom
pip install -e ".[dev]"
mailroom-web              # http://127.0.0.1:8001/
```

## Structure

| Path | Contents |
| :--- | :--- |
| [`css/`](css/) | Pixel console styles |
| [`js/`](js/) | Pixel console JavaScript |

## Related Files

- `hosted/` — Observatory (hosted edition)
- `ui/` — React operator desk
- `tui/` — Terminal user interface
