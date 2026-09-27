# Vendored: llm-mailroom (DMR-057 self-containment)

The `src/` tree below is a **tracked snapshot** of the pipeline/agents/prompts
code the sandbox imports at runtime (`pipeline.*`, `graph.*`, `agents.*`,
`llm.*`, `legalbench.*`, `observability.*`, `langchain_agents.*`, `schemas.*`,
`storage.*`, `api.*`, `scripts.*`). Shipping it in-repo makes the sandbox
fully operational offline — no `pip install mailroom@git...`, no
`sandbox fetch-deps` requirement.

- Upstream: https://github.com/Exios66/llm-mailroom
- Pin: **workspace snapshot** — tracks `packages/llm-mailroom` in the
  Digital-Mailroom monorepo (the source of truth; hub#62 doctrine, same as
  the llm-dojo-scoring snapshot below).
- Lineage: upstream tag `v0.7.1`
  (`2a212e76a62b98f6eba451ff6f3c5bc96039ae37`) was the last tagged pin; the
  five-class taxonomy removal (59c47401) landed upstream afterwards and this
  snapshot tracks the post-removal workspace. Standalone Phase-2 refresh
  (2026-09-24) copied `src/` minus `src/tests/` from
  `Exios66/llm-mailroom` PR #64 branch
  `cursor/merger-agreement-specialist-428f` at
  `4b93fc766a49498367b46f717f73cc32654cc382` because this checkout is not
  inside the Digital-Mailroom monorepo (`scripts/sync_vendor.py` expects
  `packages/llm-mailroom`). That SHA is the dedicated
  `merger_agreement_specialist` land (1:1 live-class map). The docclass-era
  compliance files (`agents/compliance_specialist.py`,
  `pipeline/docclass_mode.py`, `langchain_agents/prompts_docclass.py`,
  `langchain_agents/skills/compliance_specialist/`) are intentionally
  ABSENT — the monorepo guard
  (`scripts/tests/test_compliance_removal_guard.py`) keeps them out of the
  workspace, and the drift guard
  (`tests/test_vendor_drift.py`) keeps them out of here.
- Layout: upstream `src/` **minus `src/tests/`** (test-only files are never
  imported by the vendored modules); `scripts/` is kept — `legalbench.data`
  imports `scripts.fetch_full_cuad`.
- Refresh: `python scripts/sync_vendor.py` from the monorepo root — mirrors
  the workspace onto this tree carrying BOTH content updates AND deletions
  (a copy-only refresh is how the removed compliance files survived their
  upstream deletion; DMR-070). `sandbox fetch-deps` prefers the same
  workspace mirror when the monorepo layout is detected and falls back to a
  loud tag-based refresh for standalone clones.
- Snapshot tracks post-removal workspace lineage plus sandbox DMR-078
  merger specialist plumbing (agent module + MAUD skills + taxonomy
  `merger_agreement.specialist: merger_agreement_specialist` + graph
  extract dispatch). DMR-078 on main grafted that extract path onto the
  prior stable graph *without* `agents.bert_intake`. This standalone
  Phase-2 snapshot also copied llm-mailroom PR #64 tip (`4b93fc76`)
  wholesale, so `agents.bert_intake` and related graph/client/provider
  files **are** present after merging main. Vendor strategy for those
  extras is still an open merge question (see PR discussion).