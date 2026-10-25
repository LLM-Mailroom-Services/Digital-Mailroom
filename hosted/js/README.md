<div align="center">

# 📜 Observatory JavaScript

**JavaScript modules for the Mailroom Observatory (hosted edition).**

</div>

---

## Modules

| Module | Purpose |
|:---|:---|
| `debug.js` | Debug suite with ring buffer, dump, export, and verbose modes |
| `pipeline.js` | Pipeline tray updates and WebSocket handling |
| `review.js` | Human review queue management |
| `replay.js` | History replay with `prefers-reduced-motion` support |
| `inspect.js` | Native `<dialog>` for spans, generations, scores |

## Debug Suite

Silent UI failures are recorded in a ring buffer:
```javascript
window.__OBSERVATORY_DEBUG__.dump()
window.__OBSERVATORY_DEBUG__.export()
window.__OBSERVATORY_DEBUG__.explain(event)
window.__OBSERVATORY_DEBUG__.setVerbose(true)
```

## Related Files

- `../hosted/css/` — Observatory styles
- `../hosted/` — Observatory HTML
- `../web/js/` — Pixel console JavaScript
