# vendor/

Tracked, pinned snapshots of the family code the sandbox imports at runtime
(self-contained posture, DMR-057). **No `pip install ...@git...` is required —
the sandbox prepends these trees to `sys.path` on import.**

| Tree | Pin | Content |
| --- | --- | --- |
| `llm-mailroom/` | `a7d7bf0b1c1b` (reviewed `main` commit, after #141) | `src/` (minus tests) — `pipeline.*`, `graph.*`, `agents.*`, `llm.*`, `legalbench.*`, `observability.*`, `langchain_agents.*`, `scripts.*` |
| `llm-dojo-scoring/` | `2fea5ea7cff7` (0.26.0 release merge commit: reviewer scoring, rescore, CMS #93 mapping, five-class schema registry) | `src/llm_dojo_scoring/` — scoring engine (`serving`, `experiment`, `extraction_metrics`, incl. the per-subclass `corporate_record_schema`) |

Provenance + refresh details live in each tree's `VENDOR.md`. `sandbox fetch-deps`
re-snapshots both trees from their pinned refs (network, optional). The
installed `mailroom` wheel does not ship `scripts/` or `legalbench/`; the
vendored tree supplies `PYTHONPATH` for `sandbox pipeline watcher` /
`sandbox pipeline api`.