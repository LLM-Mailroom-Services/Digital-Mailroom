# Releases

The monorepo is the development source of truth; upstream repositories
remain the release vehicles for the deployed surfaces (HF Spaces, Railway).

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
  `pyproject.toml` version; `--apply` writes, `--tag` tags; never commits
  or pushes).
- Enforcement: `.github/workflows/release-governance.yml` runs `check` on
  every `v*` tag push; `board-governance.yml` runs it on hub-scope path
  changes.
- Cut a release:

  ```bash
  python scripts/release_chain.py cut X.Y.Z --apply --tag   # stamps section + bumps pyproject + tags
  git push origin main vX.Y.Z                               # the commit (with its DMR-0NN reference), then the tag
  python scripts/release_notes.py X.Y.Z --title "<epoch>" --out release-notes-vX.Y.Z.md
  gh release create vX.Y.Z --title "Mailroom Hub vX.Y.Z — <epoch>" --notes-file release-notes-vX.Y.Z.md
  ```

  The GitHub Release body is **generated** by `scripts/release_notes.py` from
  the freshly-stamped changelog section, so every release carries a summary
  of the changes, the highlights, the merged PRs, the key (HUB-card) commits,
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
- **Key commits** — the HUB-card-referenced commits in the window (the
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

## Release train (HUB-005 scope)

1. **Propagate monorepo work upstream**
   `python scripts/sync_packages.py push --package <name>` (a subtree push
   per package). If subtree ancestry can't fast-forward (snapshot-based
   cursors), publish as clean patch commits to the standalone repo and
   re-baseline the cursor with `snapshot` (see [[Sub-Package-Sync]]).
2. **Bump the consuming pins** — release-time only:
   `packages/llm-mailroom/src/scripts/bump_dojo_scoring.py` for the dojo
   pin. Never delete a pin line; bump only when cutting a release of the
   pinned package.
3. **Tag in the standalone repo** — one tag per release (`vX.Y.Z`), cut
   from the standalone repo the release ships from.
4. **Verify** — the touched packages' FULL suites green; `git status`
   clean; the board card closed with Evidence naming the commits.

## Current family pins

| Package | Pin | Consumed by |
| --- | --- | --- |
| llm-mailroom | v0.6.0 | sandbox `fetch-deps` / `[pipeline]` extra |
| llm-dojo-scoring | v0.12.2 | llm-mailroom, llm-entity-extraction, sandbox |
| llm-entity-extraction | v0.20.0 | sandbox `[evals]` extra |

## Deploy surfaces

- Deploy configs inside each package (`Dockerfile`, `nixpacks.toml`,
  `railway.json`) stay standalone-repo aware — build images from the
  package directory as before.
- GitHub Pages sites: [llm-entity-extraction](https://exios66.github.io/llm-entity-extraction/),
  [The-Mailroom](https://exios66.github.io/The-Mailroom/) (pixel console
  root; the new [terminal console](https://exios66.github.io/The-Mailroom/docs/terminal/)
  lives under `/docs/terminal/`),
  [llm-mailroom-graph](https://exios66.github.io/llm-mailroom-graph/).
- **The served Kanban board — Vercel:** https://digital-mailroom-theta.vercel.app
  (project `digital-mailroom`, deploy root `board-site/`). It is its own deploy
  surface with its own `vercel.json`, a `GITHUB_TOKEN` production secret,
  and the redeploy workflow documented in [[Served-Board]].
