<div align="center">

# 🎨 Observatory CSS

**Stylesheets for the Mailroom Observatory (hosted edition).**

</div>

---

## Files

| File | Purpose |
|:---|:---|
| `observatory.css` | Main Observatory styles |
| `variables.css` | CSS custom properties (tokens) |

## Design Tokens

The Observatory uses CSS custom properties for consistent theming:
- `--focus` — Focus ring color (3px dedicated ring)
- `--color-scheme` — Light/dark mode support
- `--cream` / `--ink` — Base palette

## Accessibility

- Focus rings are 3px and use a dedicated `--focus` token
- Contrast sized for text on cream/ink
- `prefers-reduced-motion: reduce` disables animations

## Related Files

- `../hosted/` — Observatory HTML/JS
- `../web/` — Pixel console styles
