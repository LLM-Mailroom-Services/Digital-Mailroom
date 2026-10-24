# Test-run requirements log

Canonical reference for **which tests to run, when**, across the
Digital-Mailroom monorepo. Read this before running any suite — the goal is
to never run a 5-minute full suite for a one-line docs change, and never
skip the cross-package suite for a change that touches two packages.

Source of truth for the package list: `AGENTS.md` ("Per-package test
suites"). Test counts below were re-measured 2026-10-23 on the five-core
workspace (after #162/#167), with plain runs (no `--cov`). Wall times are
measured wall-clock on a shared `.venv`, ±20% depending on machine load.

## Four tiers

| Tier | What it covers | Typical wall time | When |
| --- | --- | --- | --- |
| **1 — surgical** | The single test file/module touched by a change | seconds | Every edit, before committing |
| **2 — package unit** | The full test suite of the one changed package | seconds–minutes | Every non-trivial change to a package |
| **3 — cross-package** | The suites of every package a change touches, plus any package that imports the changed surface | 1–6 min | Cross-package refactors, shared-catalog changes (taxonomy, vendor, dojo), version bumps |
| **4 — full + governance** | All 5 core package suites + `scripts/tests` + board-site JS + the governance gates | ~7 min + gates | Release cuts, CI gate verification, end-of-sprint sweeps |

## Per-package commands (measured)

Run from the repo root against the shared venv. Several packages ship a
top-level `tests` package and collide when batched — run **one package per
invocation**.

| Package | Command | Tests | Wall time |
| --- | --- | --- | --- |
| llm-dojo-scoring | `uv run pytest packages/llm-dojo-scoring/tests -q` | 1936 pass / 5 skip | ~36 s |
| llm-mailroom | `uv run pytest packages/llm-mailroom/src/tests -q` | 2173 pass / 37 skip | ~3:35 |
| local-mailroom-sandbox | `uv run pytest packages/local-mailroom-sandbox/tests -q` | 1512 pass / 12 skip / 1 fail† | ~1:45 |
| The-Mailroom | `uv run pytest packages/The-Mailroom/tests -q` | 468 pass / 2 skip / 38 fail* | ~22 s |
| mailroom-corpus-eda | `uv run pytest packages/mailroom-corpus-eda/tests -q` | 337 pass / 19 skip | ~10 s |
| hub governance tooling | `python3 -m unittest discover scripts/tests` | 80 pass | ~33 s |
| board-site API | `(cd board-site && node tests/api.test.js)` | 23 checks | <1 s |

\* The-Mailroom's 38 failures on 2026-10-23 are a real package defect, not
flakes: 37 raise `AttributeError: 'PipelineRun' object has no attribute
'intake_bert'` (`server/poller.py` and `hosted/js/bert_panels.js` read a field
that `mailroom_ui/models.py` `PipelineRun` does not declare), plus
`test_trace_cache.py::test_live_traces_still_hit_langfuse`. They reproduce on
clean `main`; the fix belongs in the standalone `Exios66/The-Mailroom` source,
then a hub import. † The sandbox failure
(`test_modernbert_feeder.py::test_modernbert_feeder_resolves_sibling`) depends
on a local `mailroom-ml` sibling checkout: it skips when the sibling is absent
and fails when a present sibling's `feeder_status()` is not ok. The 2026-10-21
llm-mailroom storage-race failures (`test_audit_log.py`, `test_relations.py`)
did not reproduce in this run. Skips: llm-mailroom's
`docs/examples/samples/manifest.csv` skips and corpus-eda's `data/parquet`
snapshot skips mean the real-sample / real-corpus tests do not run in a fresh
checkout.

**No CI workflow runs any of these suites** — the local run is the gate.

## Historical seven-member measurements (2026-10-21, before DMR-093)

The two feeder rows below were measured in the seven-member checkout on
2026-10-21, before DMR-093 pruned the feeds (#167, merged 2026-10-23). The
seven-member four-tier sweep then took ~13.5 minutes plus gates under `--cov`.

| Preserved package | Historical command | Tests | Wall time |
| --- | --- | --- | --- |
| claims-data-eda | `uv run pytest packages/claims-data-eda/tests -q` | 40 pass | ~10 s |
| Enron-Evaluation-Environment | `uv run pytest packages/Enron-Evaluation-Environment/tests -q` | 87 pass | ~12 s |

Run these commands only in a separate checkout of the complete preserved
workspace: [Enron](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/enron-evaluation-environment/packages/Enron-Evaluation-Environment), [claims](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/claims-data-eda/packages/claims-data-eda), commit `59c879d9fb4480084e53137e2e9fb25650933944`.
#162 left both package trees byte-identical before #167 removed them. Keep the package-local ignores and tracked
sample PDFs when restoring. Do not overlay the old root pyproject, lock or
sync manifest onto current main; reconcile those contracts explicitly.



> llm-mailroom is the long pole (~3.5 min). Its sub-suites can be targeted for
> faster surgical feedback: `src/tests/test_observability.py`,
> `src/tests/test_agents/`, `src/tests/test_doc_inventories.py`, etc.

## Change-type → required-suite matrix

| Change type | Tier | Which suites |
| --- | --- | --- |
| Docs/markdown/`.gitignore`/comment only | **1** | None required (surgical if the file has a test) |
| Single-function fix in one package | **2** | That package's full suite |
| New test file | **1** | The new file itself + the package it tests |
| Prompt/template text change (prompts.py, `*.docclass.md`, docclass_prompts.py) | **3** | llm-dojo-scoring + The-Mailroom (both carry prompt surfaces) + llm-mailroom if `doc_inventories`/guards are affected |
| Taxonomy/catalog change (corpus.py, sorter_agent.py, taxonomy.yaml, `taxonomy_parity.py`) | **3** | llm-dojo-scoring + llm-mailroom + The-Mailroom + **`python scripts/taxonomy_parity.py`** (CI gate) |
| Shared-package change (llm-dojo-scoring, vendor/ snapshots) | **3** | The changed package + every dependant (llm-mailroom, sandbox) + sandbox `test_vendor_drift.py` |
| Version bump / pin change | **3** | All packages referencing the pin + `docs/wiki/Releases.md` + `release_chain.py check` |
| Board/tooling change (scripts/, board-site/) | **2–3** | `scripts/board_state.py check`, `board-site/tests/api.test.js`, relevant script tests |
| Multi-package refactor | **3** | Every touched package's full suite |
| Release cut / sprint sweep | **4** | All 5 core package suites + `scripts/tests` + board-site JS + all governance gates below |

## Governance gates (always run on governance/tooling changes and at tier 4)

```bash
python scripts/board_state.py check          # board invariants; 0 errors/0 warnings expected
python scripts/github_labels.py audit        # label taxonomy (CI gate)
python scripts/audit_references.py           # no stale Exios66/mailroom-dev references
python scripts/taxonomy_parity.py            # doc-class + subclass taxonomy (CI gate)
python scripts/release_chain.py check        # hub release-chain invariants (CI gate)
```

## Notes

- **Network-free by default.** The suites use local fixtures and the local HF
  cache; only explicit `--live` / integration flags touch the network.
- **Vendor drift:** if you touch `packages/llm-mailroom` or
  `packages/llm-dojo-scoring`, the sandbox vendor tree MUST be refreshed in
  the same commit (`cd packages/local-mailroom-sandbox && python
  scripts/sync_vendor.py`) or `test_vendor_drift.py` fails.
- **Cross-repo:** the standalone `LLM-Mailroom-Services/eval-environment`
  repo (144 tests) has its own gate; run `uv run pytest` there after a dojo
  change that alters its wiring.
- **Timestamps in evidence:** board cards and commit messages use UTC
  (ISO-8601, `%Y-%m-%dT%H:%M:%SZ`).
