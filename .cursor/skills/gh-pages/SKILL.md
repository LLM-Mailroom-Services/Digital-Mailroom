---
name: gh-pages
description: GitHub Pages snapshot for The-Mailroom (scripts/publish_pages.sh → gh-pages:/docs, deploy-from-branch, NO Actions). Use when publishing the static pixel SPA, snapshot exporter, ?api= CORS, or checking main vs gh-pages drift.
---

# GitHub Pages (static snapshot)

**When:** Publish the pixel SPA snapshot, `scripts/publish_pages.sh`,
`scripts/export_snapshot.py`, `?api=` against a local server, or Pages drift.  
**Not** the Observatory (`/live`) and **not** GitHub Actions (account cannot
rely on Actions).

## Deploy

```bash
scripts/publish_pages.sh           # build site/ + push gh-pages:/docs
scripts/publish_pages.sh --status  # exit 1 = stale vs main
git config core.hooksPath hooks    # once per clone: push main auto-republishes
```

Settings → Pages → branch `gh-pages` → folder `/docs`. Publisher runs only from
`main` — switch back if Desktop left another branch checked out.

`MAILROOM_STRICT_SYNC=1` blocks a push when the check fails.

## Snapshot rules

- Bundled `data/*.json` is the **Pages** fallback when no live API answers.
- Live display path still must not fabricate Langfuse rows.
- `?api=` (persisted) points the static SPA at a running Mailroom API; CORS via
  `MAILROOM_CORS_ORIGINS`.
- `?api=` empty clears a stale localhost base so Pages does not blank.

## Related

- Pixel SPA: [pixel-console](../pixel-console/SKILL.md)
- Observatory is a different surface: [observatory](../observatory/SKILL.md)
