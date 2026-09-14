# Vendored: llm-dojo-scoring (DMR-057 self-containment)

The `src/llm_dojo_scoring/` tree below is a **tracked snapshot** of the
deterministic scoring engine the sandbox imports at runtime
(`experiment`, `serving`, `extraction_metrics`, `mailroom`, `get_suite`,
`headline_metrics`, …). Shipping it in-repo removes the
`llm-dojo-scoring @ git+...` pip pin — the sandbox no longer needs the
network or an install to score runs.

- Upstream: https://github.com/Exios66/llm-dojo-scoring
- Pin: **v0.15.0** (annotated tag; llm-mailroom v0.7.1's own pin)
- Commit: `9db1417b` (v0.15.0 tag; the vendored tree mirrors the monorepo
  workspace snapshot, refreshed with the DMR-061 emitter counters on
  2026-09-14 so the drift guard stays byte-identical)
- Layout: upstream package dir relocated under `src/` (mirrors
  `vendor/llm-mailroom/src`); upstream `tests/`, `examples/`, `docs/` are not
  vendored.
- Refresh: `sandbox fetch-deps` re-snapshots from the pinned tag into this
  tracked tree (no `.git`).
- The sandbox prepends `vendor/llm-dojo-scoring/src` to `sys.path` on package
  import (`mailroom_sandbox/__init__.py`), so the vendored engine shadows any
  installed `llm_dojo_scoring`.