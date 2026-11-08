# Migration notes — GitBook → Tome (2026-11-08)

Source: `Exios66/mailroom-documentation`, `docs/` (92 Markdown files,
`SUMMARY.md`, `.gitbook.yaml`), the GitBook site at
<https://mailroom-inc.gitbook.io/the-digital-mailroom/>.
Tool: `tome migrate gitbook` (`@tomehq/cli` 0.9.0), run from
`~/workspace/digital-mailroom-docs`. Source repos were not modified.

## What transferred

- **91 pages migrated** (`tome migrate gitbook` dry-run and real run agree).
  41 became `.mdx` (they use converted components); the rest stayed `.md`.
- **Navigation** rebuilt from `docs/SUMMARY.md` — same 11 groups, same order,
  same titles. Two external GitHub links that sat in the sidebar (sandbox and
  eval-environment `reports/` folders) were dropped from the navigation; they
  are still linked from inside the experiment-reports pages.
- **Assets** copied from `docs/.gitbook/assets/` to `public/assets/`
  (`banner.png`, `fumi.gif`, `hoot-icon.png`, four chart SVGs). Image
  references in pages were rewritten from `.gitbook/assets/…` to `/assets/…`.
- **GitBook hint blocks** → Tome `<Callout>`; **tabs** → `<Tabs>`/`<Tab>`;
  **embeds** → plain Markdown links; **content-refs** → links.
- **Changelog feed** (`changelog/README.mdx`): the `{% updates %}` /
  `{% update %}` wrappers were stripped, keeping the dated entries as prose.
  The per-release pages keep their frontmatter and content unchanged.
- **API reference**: the 16 GitBook `{% openapi %}` blocks across the 7
  tag pages were replaced with pointers to Tome's generated `/api` reference.
  The checked-in spec (`docs/api-reference/mailroom-openapi.yaml`) was copied
  to `openapi.yaml` at the site root and wired in `tome.config.js`
  (`api.spec`, playground on). Spec itself is unchanged — still hand-written
  from `llm-mailroom` `c6476f7` (after v0.8.0, as of 2026-10-08).
- **Asset inventories** (`docs/assets/README.md`, `docs/assets/mascot/README.md`)
  moved to `notes/` — they describe the art, they are not site pages.
- **Config**: title/name "The Digital Mailroom", local search, API spec.
  The GitBook home frontmatter (`layout`, `icon`) is inert in Tome and was
  left in place rather than stripped.

## What was updated (2026-11-08)

Only the home page (`pages/README.md`): a migration note was added, and the
install-block version label moved from v0.8.0 (2026-10-07) to **v0.9.1**
(released 2026-11-03). Verified against `LLM-Mailroom-Services/Digital-Mailroom`
(`packages/llm-mailroom/CHANGELOG.md`, `[v0.9.1] - 2026-11-03`).

Current pins as of 2026-11-08:

| Fact | Current value | GitBook docs said (2026-10-07) |
| --- | --- | --- |
| llm-mailroom release | v0.9.1 (2026-11-03) | v0.8.0 |
| llm-dojo-scoring | v0.27.2 | v0.21.0 |
| Digital-Mailroom hub | v0.10.0 | — (not a GitBook pin) |
| Dataset code revision | v9.1 (`FULL_CORPUS_REVISION`) | v9.1 (code) / v9.2 (site) |
| Hub dataset | v9 · 3,302 rows | v9.2 |

## Still open — full freshness sweep

Page-level version claims elsewhere in the site still carry their original
2026-10-07 as-of dates (llm-mailroom v0.8.0, dojo v0.21.0, dataset v9.2).
A real sweep must follow the GitBook repo's own rule: verify each new value
upstream, then update **every** file in the fact's row in the same change and
re-date each sentence — a partial pin bump across 90 pages would leave the
site internally inconsistent. Open items for that sweep:

1. ~~llm-mailroom v0.8.0 → v0.9.1 everywhere (incl. the v0.9.1 extraction-gate
   hook and release tool — `docs/pipeline-reference-llm-mailroom/decision-reviewer.md`
   does not exist yet in this site).~~ — DONE 2026-11-08 (freshness sweep):
   pins moved to **v0.9.3** everywhere; `pages/pipeline-reference-llm-mailroom/decision-reviewer.md`
   created from the upstream v0.9.3 doc, extraction-gate section included.
2. ~~llm-dojo-scoring v0.21.0 → v0.27.2 everywhere.~~ — DONE 2026-11-08:
   pins moved to **v0.28.1** everywhere (the Nov 8 values had already moved past v0.27.2).
3. ~~Dataset pin: confirm whether the site pin is now v9.2 or has moved; the
   code revision is still v9.1.~~ — DONE 2026-11-08: site pin is **v9.3**
   (`ff4ca546`, 2026-11-06); code revision still **v9.1**.
4. The `maintaining.mdx` page still documents the GitBook workflow
   (Git Sync, `check_site.py`, GitBook Customize). It needs a Tome rewrite
   once this site has a deploy target.
5. The home page's card table still uses GitBook's `data-view="cards"` markup
   and Font Awesome icons; it renders as a plain table in Tome.

## Known conversion losses

- `{% embed %}` blocks became plain links — the interactive EDA dashboard
  embeds no longer render inline.
- GitBook's changelog feed sorting is gone; the changelog index is now a
  plain page in date order as written.
- Mermaid diagrams are fenced code blocks; they render only if Tome's theme
  handles Mermaid (verify on the first visual pass).

## Verification (2026-11-08)

- `npm run build` passes: 90 HTML pages in `out/` (89 source pages + shell),
  search index built, `llms.txt` / `llms-full.txt` / `mcp.json` generated.
  `out/` is gitignored; rebuild with `npm run build`.
- Home-page migration note and v0.9.1 label confirmed in the built bundles.
- Internal-link audit: 0 genuine broken links (the 6 flagged hits are
  code-span examples in the maintaining runbook, not links). 0 missing images.
- `tome lint` fails on this project AND on a fresh untouched `tome init`
  project with the same error (`Dynamic require of "fs" is not supported`) —
  a Tome 0.9.0 bug in this environment, not a content problem. Re-test after
  a Tome upgrade; the build is the verification until then.
- Two MDX fix-up passes were needed after migration: `fixup-migration.py`
  (openapi blocks, changelog wrappers, asset paths) and `fixup-mdx.py`
  (self-closing `<img>`/`<source>` void tags, escaping bare `<` in prose
  outside code spans). Both scripts are kept in the site root.

## Freshness sweep (2026-11-08)

All pins re-verified live before editing (git ls-remote tags, HF refs API,
raw files at tag v0.9.3 / v0.28.1, DMR main `d3520da` 2026-11-04). The Nov 8
values had already moved past the migration pins, so the sweep used the newest
verified values: llm-mailroom **v0.9.3** (2026-11-07), llm-dojo-scoring
**v0.28.1** (commit `00a2a7f`), hub **v0.10.0**, dataset code revision **v9.1**,
Hub dataset tag **v9.3** (`ff4ca546`, 2026-11-06; rows unchanged from v9.2).

Facts updated, every occurrence per fact:

- llm-mailroom v0.8.0 → v0.9.3; dojo v0.21.0 → v0.28.1 (pin `00a2a7f`);
  dataset site pin v9.2/`670e8bc6` → v9.3/`ff4ca546` (code pin stays v9.1).
- 13 nodes → **14 nodes** everywhere (new node `classification_arbiter`,
  added v0.9.1).
- Production sorter `sorter_v14` → **`sorter_condensed_v5`** (v0.9.3; sandbox
  condensed v1, bylaw rule reversed, ~3.7k-char prompt).
- `score_extraction` now applies per-type bands: the v0.21.0 caveat ("only the
  global `ambiguous_band` decides") is false under v0.28.1 — `score_extraction`
  calls `field_is_ambiguous` for every scored field.
- "Unreleased on `main`" labels removed everywhere: the features shipped in
  **v0.8.1** (2026-10-23) — free-quota breaker, triage result cache, durable
  Gmail echo outbox, Langfuse wiring (`langfuse>=4.9,<5`, trace redaction,
  prompt cache, score configs), experiment regression gate, Gmail sender
  auth/loop guards/DMARC/IDLE/ACKS/quarantine/staging. All verified against
  the v0.8.1 changelog.
- **Railway retired 2026-11-06** (The-Mailroom ADR-005): `railway.json` +
  `nixpacks.toml` deleted in v0.9.2; the hosted producer is the Hugging Face
  Docker Space. Deployment README's Railway section replaced with a retirement
  note; the Phoenix guard rewritten to `SPACE_ID`/`HF_SPACE_ID` (verified in
  `src/observability/tracing.py` at v0.9.3).
- Extraction schemas v2 (v0.9.3): `ContractExtraction` 17 fields,
  `MergerAgreementExtraction` 21 fields; v1 `merger_consideration` /
  `maud_clauses` are parse-compat only, never scored; v9 headlines read
  `partial` until dataset v10.
- mailroom-reloaded is no longer design-only: the repo now ships code
  (CrewAI-Flows pipeline, deterministic gates, SQLite hash-chained audit log);
  its dojo pin is v0.22.0 (vendored subset + parity pin, per its pyproject).
- Hub package copies (DMR main `d3520da`): llm-mailroom 0.9.1, dojo 0.27.2,
  The-Mailroom 0.5.1, hub 0.10.0.
- New page: `pages/pipeline-reference-llm-mailroom/decision-reviewer.md`,
  adapted from the upstream v0.9.3 doc (Decisions-API model
  `openai/gpt-6-luna-decisions`, calibration results, guards, extraction gate),
  added to `tome.config.js` navigation under Pipeline reference, after Agents.

Files changed: 37 content pages + 1 new page + `tome.config.js` + this file.
Nothing committed, pushed, deployed, or PR'd (per the sweep brief).

Verification: `npm run build` passes — **91 HTML pages** in `out/` (was 90;
the +1 is decision-reviewer), search index built. Home pins (v0.9.3),
`sorter_condensed_v5`, and `ff4ca546` confirmed in the built bundles.
Post-edit audit: no remaining `13-node`, `sorter_v14`, `v0.21.0` (except a
v0.21.0 release-history bullet in sister-repos.md), or `v9.2` pin claims
outside dated provenance notes.

Left stale on purpose (flagged, not verified):

- `openapi.yaml` `info.description` still cites `c6476f7` (after v0.8.0,
  2026-10-08); the spec has not been re-checked against the v0.9.2/v0.9.3 API
  changes (loopback tokenless serving, per-request token reads). The
  api-reference README callout repeats that provenance.
- The-Mailroom `main` "one unreleased fix" (`publish_pages.sh --skip-export`)
  in the-mailroom.md — about The-Mailroom, not llm-mailroom; not re-verified.
- Hugging Face Space status notes dated 2026-10-06 (producer Space not
  published, Observatory paused) — dated snapshots, not re-probed.
- eval-environment / mailroom-ml dataset pins (`ed7576b6`, v9.1 data commit)
  and the sandbox `FAMILY_HF_TAG` — other repos' pins, not re-checked.
- Dojo release-history bullets after v0.21.0 are not summarized on the
  sister-repos page; only the Latest/pin rows moved.
- "Honest gap (dojo v0.28.1)" labels moved with the pin; the underlying gap
  claims were checked against the dojo changelog (no new external benchmark
  announced in v0.22.0–v0.28.1) but not re-audited suite by suite.
- `pages/changelog/` untouched (generated history).
