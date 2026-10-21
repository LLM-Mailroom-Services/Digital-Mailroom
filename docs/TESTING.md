# Test-run requirements log

Canonical reference for **which tests to run, when**, across the
Digital-Mailroom monorepo. Read this before running any suite — the goal is
to never run a 5-minute full suite for a one-line docs change, and never
skip the cross-package suite for a change that touches two packages.

Source of truth for the package list: `AGENTS.md` ("Per-package test
suites"). Test counts below were re-measured 2026-10-21 (DMR-085). Wall times are
measured wall-clock on a shared `.venv`, ±20% depending on machine load;
rows marked *cov* were timed under `--cov`, which is slower than a plain run.

## Four tiers

| Tier | What it covers | Typical wall time | When |
| --- | --- | --- | --- |
| **1 — surgical** | The single test file/module touched by a change | seconds | Every edit, before committing |
| **2 — package unit** | The full test suite of the one changed package | seconds–minutes | Every non-trivial change to a package |
| **3 — cross-package** | The suites of every package a change touches, plus any package that imports the changed surface | 1–6 min | Cross-package refactors, shared-catalog changes (taxonomy, vendor, dojo), version bumps |
| **4 — full + governance** | All 7 package suites + `scripts/tests` + board-site JS + the governance gates | ~13.5 min suites + gates | Release cuts, CI gate verification, end-of-sprint sweeps |

## Per-package commands (measured)

Run from the repo root against the shared venv. Several packages ship a
top-level `tests` package and collide when batched — run **one package per
invocation**.

| Package | Command | Tests | Wall time |
| --- | --- | --- | --- |
| llm-dojo-scoring | `uv run pytest packages/llm-dojo-scoring/tests -q` | 1219 pass / 5 skip | ~28 s *cov* |
| llm-mailroom | `uv run pytest packages/llm-mailroom/src/tests -q` | 1864 pass / 37 skip / 2 fail* | ~9:40 *cov* |
| local-mailroom-sandbox | `uv run pytest packages/local-mailroom-sandbox/tests -q` | 1324 pass / 5 skip | ~1:50 *cov* |
| The-Mailroom | `uv run pytest packages/The-Mailroom/tests -q` | 421 pass | ~38 s *cov* |
| mailroom-corpus-eda | `uv run pytest packages/mailroom-corpus-eda/tests -q` | 186 pass / 17 skip | ~23 s |
| claims-data-eda | `uv run pytest packages/claims-data-eda/tests -q` | 40 pass | ~10 s |
| Enron-Evaluation-Environment | `uv run pytest packages/Enron-Evaluation-Environment/tests -q` | 87 pass | ~12 s |
| hub governance tooling | `python3 -m unittest discover scripts/tests` | 62 pass | ~9 s |
| board-site API | `(cd board-site && node tests/api.test.js)` | 23 checks | <1 s |

\* The two llm-mailroom failures (`test_audit_log.py::test_concurrent_appends_keep_chain_valid`,
`test_relations.py::test_concurrent_ledger_writers_do_not_fork_chain`) are a
real storage race (`storage/db.py` `ensure_schema` has no lock; `get_engine`
shares one async engine across event loops), not flakes — see AGENTS.md
§ Test discipline. Skips: llm-mailroom's 30 `docs/examples/samples/manifest.csv`
skips and corpus-eda's 17 `data/parquet` snapshot skips mean the real-sample /
real-corpus tests do not run in a fresh checkout.

**No CI workflow runs any of these suites** — the local run is the gate.

> llm-mailroom is the long pole (~5 min). Its sub-suites can be targeted for
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
| Release cut / sprint sweep | **4** | All 7 package suites + `scripts/tests` + board-site JS + all governance gates below |

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
