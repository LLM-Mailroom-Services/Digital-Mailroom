# Releases

**Current:** [v0.4.0](https://github.com/Exios66/The-Mailroom/releases/tag/v0.4.0)
(2026-09-04) — terminal TUI + terminal GH Pages site.
Demos: [Demos](Demos).

The-Mailroom follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`) with the
version living in `pyproject.toml` and the release record in `CHANGELOG.md`.

## Version rules

- **MAJOR** — breaking change to the API responses, the data contract (trace
  interpretation), or the visual design.
- **MINOR** — new feature: new screen, new metrics, milestone delivery
  (each M2/M3/M4/M5 delivery is a MINOR).
- **PATCH** — bug fixes, docs fixes, tests-only changes.

## Release steps (in the release commit)

1. Run the full test suite: `python -m pytest tests/ -q`.
2. Move `## [Unreleased]` entries in `CHANGELOG.md` under
   `## [X.Y.Z] - YYYY-MM-DD`.
3. Bump the version in `pyproject.toml`.
4. Update `README.md` if commands/config/screens changed.
5. Update `wiki/` + `docs/` if architecture/config/usage changed.
6. Commit everything in one change, then tag:

```bash
git tag -a vX.Y.Z -m "X.Y.Z — <one-line summary>"
git push && git push --tags
```

The tag must match the CHANGELOG header exactly and point at a commit that
has that entry. After a pushed major/minor release, publish the wiki:
`wiki/sync-wiki.sh`.

## Automation

`python scripts/release.py --bump <patch|minor|major> --note "<summary>"`
performs the mechanical steps (bump + changelog move) and prints the exact
commit/tag commands; it refuses to run on a dirty working tree.
`python scripts/release.py --check` validates repo state (tests pass,
changelog format, version/tag consistency) without changing anything.
