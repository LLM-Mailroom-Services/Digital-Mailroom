# Vendored: llm-dojo-scoring (DMR-057 self-containment)

The `src/llm_dojo_scoring/` tree below is a **tracked snapshot** of the
deterministic scoring engine the sandbox imports at runtime
(`experiment`, `serving`, `extraction_metrics`, `mailroom`, `get_suite`,
`headline_metrics`, …). Shipping it in-repo removes the
`llm-dojo-scoring @ git+...` pip pin — the sandbox no longer needs the
network or an install to score runs.

- Upstream: https://github.com/Exios66/llm-dojo-scoring
- Pin: **workspace snapshot — see monorepo** (tracks `packages/llm-dojo-scoring`
  in the Digital-Mailroom monorepo — the development source of truth;
  hub#62 doctrine). Current snapshot: upstream dojo PR branch
  **`feat/corporate-record-subclass-schemas` @ `8e6566c` + lineage JSON @ `3b2eeb4`** —
  i.e. branch tip commit `8e6566c1d1c52efeb5ebbb57ddee90a94586f7da` (frozen sha,
  verified by `sandbox fetch-deps` after clone via `git rev-parse HEAD`; the
  branch stays the clone ref so a shallow clone still resolves) with the vendored
  `prompts/eval_environment_lineage.json` byte-equal to the dojo branch's own
  file at `3b2eeb4` (reviewer-verified).
  (draft #46, corporate-record per-subclass schema work: `corporate_record_schema.py`,
  `corporate_record_relabel.py`, `align_unlabeled` in `suites._score_extraction`,
  per-subclass `required_ftypes`/`unlabeled_fields`, the amended
  `corporate_records_specialist_v7` production template). This is the PR-branch
  tip re-vendored by hand (the monorepo workspace was not available at bump
  time) — it **supersedes the `v0.22.0` tag** (`a2862cec`, released 2026-10-16,
  one sync cycle behind: the tag lacks the per-subclass machinery entirely).
- Lineage: upstream tag `v0.15.0` (`9db1417b`) was the last tagged pin; the
  vendored tree mirrors the monorepo workspace snapshot, refreshed with the
  DMR-061 emitter counters on 2026-09-14, the SAND-042 schema-adherence
  line (v0.3.0), and the v0.22.0 fixes (strict `metric_id_for`,
  required emitter provenance, `identity_mixed` serving legs) and the
  eval-environment prompt lineage (`llm_dojo_scoring.prompts.lineage` +
  `prompts/eval_environment_lineage.json`) so the drift guard stays
  byte-identical. The prompt lineage JSON in THIS snapshot is regenerated —
  via the dojo's own `scripts/sync_eval_environment_lineage.py --eval-env`
  (deterministic; sha-verified) against the sibling
  `LLM-Mailroom-Services/eval-environment` checkout @ `22d217ab9f226f2674ace699a6ea41c121bbc26b`
  — so the vendored catalog carries 43 versions (5 archived / 15 frozen /
  23 mutations), including `corporate_records_specialist_v7` (sha256
  `253559fc…`) **and** the SAND-042 frozen successors
  `insurance_claims_specialist_v4` (`1ca6e83c…`) / `merger_agreement_specialist_v4`
  (`da316691…`). The dojo branch snapshot itself was synced at eval-environment
  `b449a79` (42 → 41 versions) and lacks those two `*_v4` keys; the sibling is
  already at #99's tip, so the regenerated file is the authoritative catalog.
  `source_commit` inside the JSON names `22d217ab…` for the same reason.
- Layout: upstream package dir relocated under `src/` (mirrors
  `vendor/llm-mailroom/src`); upstream `tests/`, `examples/`, `docs/` are not
  vendored.
- Refresh: `python scripts/sync_vendor.py` from the monorepo root — mirrors
  the workspace onto this tree carrying BOTH content updates AND deletions
  (DMR-070). `sandbox fetch-deps` prefers the same workspace mirror when the
  monorepo layout is detected and falls back to a loud tag-based refresh for
  standalone clones.
- The sandbox prepends `vendor/llm-dojo-scoring/src` to `sys.path` on package
  import (`mailroom_sandbox/__init__.py`), so the vendored engine shadows any
  installed `llm_dojo_scoring`.