# Releases

Standalone repositories own package implementations and releases. Digital-Mailroom
imports their committed sources and generates vendor snapshots; it releases its
own integration workspace, wiring, governance, board, and tooling separately.
See [[Sub-Package-Sync]] for the five core packages and their source owners.

## Active package scope (DMR-093, 2026-10-23)

Sync and release integration now select five core packages: `llm-dojo-scoring`,
`llm-mailroom`, `local-mailroom-sandbox`, `The-Mailroom` and
`mailroom-corpus-eda` (the only virtual member). Enron and claims remain external
feeds, preserved as complete hub checkouts on
[`feature/enron-evaluation-environment`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/enron-evaluation-environment/packages/Enron-Evaluation-Environment) and
[`feature/claims-data-eda`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/claims-data-eda/packages/claims-data-eda) at `59c879d9fb4480084e53137e2e9fb25650933944`.
The prune landed as #167 on top of #162; `main` carries none of those trees.
Historical seven-member release/test evidence retains its original scope.
For restoration use a separate checkout; reconcile membership, sync, dependencies
and tests before any selective import, without replacing current root metadata.

## Hub release chain (HUB-024)

The hub (Digital-Mailroom) versions **itself** with a Keep a Changelog +
Semantic Versioning chain:

- `CHANGELOG.md` (root) accumulates work under `[Unreleased]` between
  releases; every hub release is an annotated git tag `vX.Y.Z`
  (`mailroom-hub vX.Y.Z` message) mirrored as a GitHub Release cut from the
  matching changelog section. While the hub is `0.x`, a MINOR bump may carry
  breaking workspace changes; PATCH is fixes-only.
- `scripts/release_chain.py` is the chain governor: `status` (snapshot),
  `check` (invariants — a version tag must never exist without its
  changelog section, sections must be semver + strictly descending, the hub
  pyproject version must never sit behind the newest tag), and `cut X.Y.Z`
  (stamps `[Unreleased]` into a dated section, bumps the hub
  `pyproject.toml` version; `--apply` writes; never commits or pushes).
  Do not use `--tag`: it tags the pre-cut HEAD before the cut is committed.
- Enforcement: `.github/workflows/release-governance.yml` runs `check` on
  every `v*` tag push; `board-governance.yml` runs it on hub-scope path
  changes.
- Cut a release:

  ```bash
  TZ=UTC python scripts/release_chain.py cut X.Y.Z --apply
  uv lock
  # Commit CHANGELOG.md, pyproject.toml, and uv.lock together under the DMR card.
  # Merge the PR; update this checkout to the merged main tip before tagging.
  git tag -a vX.Y.Z -m "mailroom-hub vX.Y.Z"
  git push origin vX.Y.Z
  python scripts/release_notes.py X.Y.Z --title "<epoch>" --out release-notes-vX.Y.Z.md
  gh release create vX.Y.Z --title "Mailroom Hub vX.Y.Z — <epoch>" --notes-file release-notes-vX.Y.Z.md
  ```

  The GitHub Release body is **generated** by `scripts/release_notes.py` from
  the freshly-stamped changelog section, so every release carries a summary
  of the changes, the highlights, the merged PRs, the key card-referenced commits,
  and references to the changelog + compare. Mirror the section title
  (`Mailroom Hub vX.Y.Z — <epoch>`) as the release name.

## Release-notes template (`.github/RELEASE_TEMPLATE.md`)

All hub GitHub Releases use the `scripts/release_notes.py` generator, which
renders the `.github/RELEASE_TEMPLATE.md` template with real data from the
release window:

- **Highlights** — one line per landed card, derived from the changelog
  section's bolded headlines.
- **Changes** — the full `## [X.Y.Z]` changelog section body (the detailed
  per-card record).
- **Pull requests merged** — every PR whose merge commit landed in
  `v<previous>..v<X.Y.Z>` (resolved via `gh`; the offline fallback lists the
  merge commits from git only).
- **Key commits** — the card-referenced commits in the window (the
  critical evidence), then the non-card commits to complete the trace.
- **Verify + reference** — the changelog link, the `v<prev>...v<ver>` compare
  URL, and the board note pointing to each card's Evidence.

Usage:

```bash
python scripts/release_notes.py X.Y.Z                # print the notes body
python scripts/release_notes.py X.Y.Z --out notes.md # write the --notes-file
python scripts/release_notes.py X.Y.Z --title "visualizer epoch"
python scripts/release_notes.py X.Y.Z --no-net       # offline (git-only PRs)
python scripts/release_notes.py X.Y.Z --json         # machine-readable
```

The template placeholders mirror the generated sections; edit the template to
change what every release carries, never hand-type a release body.

- Package versions at a hub release are recorded in that release's
  changelog section (see the `[0.1.0]` section for the baseline).

## Package release and hub import

1. **Author and verify in the standalone source** — implement package changes
   in that repository, with its regression tests, governance, and release
   tooling. Never implement in `packages/*` and push back to the source.
2. **Release from the standalone repository** — cut its release/tag from the
   committed source using its own tooling. Bump consuming pins in the consuming
   standalone repository only at release time of the pinned package (for the
   dojo pin, llm-mailroom `src/scripts/bump_dojo_scoring.py`). Never delete a pin.
3. **Import committed sources into Digital-Mailroom** — fetch current tips,
   compare cursors, and use `sync_packages.py pull --package <name> --squash`.
   Review imports and cursor updates; regenerate vendors with `sync_vendor.py`.
4. **Verify the integration** — imported packages' FULL suites and relevant
   dependents green, vendor drift absent, card scope clean, and Evidence naming
   standalone source/release and hub import commits plus exact test counts.

The legacy HUB-005 outbound train (`sync_packages.py push`, including
`push --all --patch`) is forbidden for package delivery. A hub release never
publishes package implementation back into authoritative standalone sources.

## Ownership

- **Planning & dispatch** — `orchestrator-governor` scopes standalone source
  work, source releases, hub imports, and hub releases as distinct card units.
- **Execution** — `general` missions execute source work in authoritative
  standalone checkouts and run imports/vendor generation in the hub.
- **Hub ownership** — hub wiring, board, governance, and integration tooling
  stay hub-owned. Imported `packages/*` and vendors are never implementation
  sources. Vendors are generated only, never edited by hand.

## Current family pins

Current pins as committed in the imported sources (2026-10-25, hub v0.10.0 line):

| Pin | Value | Declared in |
| --- | --- | --- |
| llm-dojo-scoring | `4740d768` (v0.24.2 release commit) | llm-mailroom dependency line; The-Mailroom `eval` extra |
| llm-mailroom (producer/vendored) | `60cd5fa` (current reviewed main tip) | The-Mailroom `[pipeline]` extra; local-mailroom-sandbox `_VENDOR_PINS` |
| The-Mailroom (sandbox fetch) | `98ae227` (current reviewed main tip) | local-mailroom-sandbox `_VISUALIZER_PIN` |

Imported source versions match the pins: llm-dojo-scoring 0.24.2, llm-mailroom
0.8.1, local-mailroom-sandbox 0.3.0, The-Mailroom 0.5.1 and
mailroom-corpus-eda 0.1.0. Dojo is pinned by its release commit rather than the
movable tag; pipeline and visualizer pins name reviewed standalone commits.
Consuming pins move only when the pinned package releases, in the consuming
standalone repo. Check `python scripts/sync_packages.py status` for current
cursors.

### Hub tag namespace

Only annotated hub releases `v0.1.0`–`v0.10.0` and the
`pre-pr162-2026-10-23` rollback snapshot are kept in this repository.
Standalone package tags stay in their authoritative repositories. A label
without a `CHANGELOG.md` section is not a hub release: DMR-112 removed the
leaked standalone tags (`v0.1.1`–`v0.24.0` subjects) and the pre-chain
`v0.0.1` label after DMR-106's earlier cleanup, restoring a clean
`release_chain.py check`. If an artifact tag genuinely must live here, make it
annotated, add its CHANGELOG section and list it in this table.

## Deploy surfaces

- Deploy configs inside each package (`Dockerfile`, `nixpacks.toml`,
  `railway.json`) stay standalone-repo aware — build images from the
  package directory as before.
- GitHub Pages sites: [The-Mailroom](https://exios66.github.io/The-Mailroom/) (pixel console
  root; the terminal console will live under `/docs/terminal/` once
  `publish_pages.sh` lands — that URL **404s today**; track [DMR-013](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/18)).
- **The served Kanban board — Vercel:** https://digital-mailroom-theta.vercel.app
  (project `digital-mailroom`, deploy root `board-site/`). It is its own deploy
  surface with its own `vercel.json`, a `GITHUB_TOKEN` production secret,
  and the redeploy workflow documented in [[Served-Board]].
