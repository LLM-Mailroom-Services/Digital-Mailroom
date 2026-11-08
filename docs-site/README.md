# digital-mailroom-docs

The Digital Mailroom documentation site, built with [Tome](https://github.com/tomehq/tome).

Migrated 2026-11-08 from the GitBook site at
<https://mailroom-inc.gitbook.io/the-digital-mailroom/> (source:
[`Exios66/mailroom-documentation`](https://github.com/Exios66/mailroom-documentation),
`docs/`). See `MIGRATION-NOTES.md` for what was converted, what was changed,
and what is still stale.

## Run it

```bash
npm install
npm run dev     # local preview
npm run build   # static build into out/
npm run lint    # Tome's linter (broken links, missing pages, bad frontmatter)
```

## Do not deploy yet

There is no deploy target wired up. `tome deploy` / `tome login` / any
`domains:*` command needs Jack's explicit go-ahead for that site, per the
standing Tome rules. Local dev/build/lint only.

## Layout

| Path | What it is |
| --- | --- |
| `pages/` | The site content (89 pages, migrated from GitBook `docs/`) |
| `public/assets/` | Site art: banner, Fumi, Hermes icon, generated chart SVGs |
| `openapi.yaml` | Mailroom Producer API spec — powers the `/api` reference |
| `tome.config.js` | Site config: title, navigation (from GitBook `SUMMARY.md`), local search, API |
| `notes/` | Asset inventories moved out of `pages/` (not published) |
| `fixup-migration.py` | The deterministic fix-up pass run after `tome migrate` |
| `MIGRATION-NOTES.md` | Migration record + open freshness sweep |
