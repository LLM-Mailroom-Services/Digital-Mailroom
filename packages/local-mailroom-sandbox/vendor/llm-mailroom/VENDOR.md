# Vendored: llm-mailroom (DMR-057 self-containment)

The `src/` tree below is a **tracked snapshot** of the pipeline/agents/prompts
code the sandbox imports at runtime (`pipeline.*`, `graph.*`, `agents.*`,
`llm.*`, `legalbench.*`, `observability.*`, `langchain_agents.*`, `schemas.*`,
`storage.*`, `api.*`, `scripts.*`). Shipping it in-repo makes the sandbox
fully operational offline — no `pip install mailroom@git...`, no
`sandbox fetch-deps` requirement.

- Upstream: https://github.com/Exios66/llm-mailroom
- Pin: **v0.6.0** (annotated tag)
- Commit: `3cf9fb921f0048a10d9a15760e2b4d825831a344`
- Layout: upstream `src/` **minus `src/tests/`** (test-only files are never
  imported by the vendored modules); `scripts/` is kept — `legalbench.data`
  imports `scripts.fetch_full_cuad`.
- Refresh: `sandbox fetch-deps` re-snapshots from the pinned tag into this
  tracked tree (no `.git`, no upstream docs/notebooks/deploy).
- The sandbox prepends `vendor/llm-mailroom/src` to `sys.path` on package
  import (`mailroom_sandbox/__init__.py`), so imports resolve here before any
  installed `mailroom` wheel.