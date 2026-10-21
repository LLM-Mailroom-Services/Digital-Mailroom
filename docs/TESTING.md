# Test-run requirements log

Canonical reference for **which tests to run, when**, across the
Digital-Mailroom monorepo. Read this before running any suite — the goal is
to never run a 5-minute full suite for a one-line docs change, and never
skip the cross-package suite for a change that touches two packages.

Source of truth for the package list: `AGENTS.md` ("Per-package test
suites"). All timings below are **measured wall-clock** (2026-09-14, shared
`.venv`), approximate ±20% depending on machine load.

## Four tiers

| Tier | What it covers | Typical wall time | When |
| --- | --- | --- | --- |
| **1 — surgical** | The single test file/module touched by a change | seconds | Every edit, before committing |
| **2 — package unit** | The full test suite of the one changed package | seconds–minutes | Every non-trivial change to a package |
| **3 — cross-package** | The suites of every package a change touches, plus any package that imports the changed surface | 1–6 min | Cross-package refactors, shared-catalog changes (taxonomy, vendor, dojo), version bumps |
| **4 — full + governance** | All 9 package suites + the governance gates | ~7 min suites + gates | Release cuts, CI gate verification, end-of-sprint sweeps |

## Per-package commands (measured)

Run from the repo root against the shared venv. Several packages ship a
top-level `tests` package and collide when batched — run **one package per
invocation**.

| Package | Command | Tests | Wall time |
| --- | --- | --- | --- |
| llm-dojo-scoring | `uv run pytest packages/llm-dojo-scoring/tests -q` | 369 pass / 5 skip | ~13 s |
| llm-mailroom | `uv run pytest packages/llm-mailroom/src/tests -q` | 995 pass / 36 skip | ~4:50 |
| local-mailroom-sandbox | `uv run pytest packages/local-mailroom-sandbox/tests -q` | 259 pass / 1 skip | ~12 s |
| The-Mailroom | `uv run pytest packages/The-Mailroom/tests -q` | 334 pass / 2 skip | ~12 s |
| claims-data-eda | `uv run pytest packages/claims-data-eda/tests -q` | 40 pass | ~6 s |
| Enron-Evaluation-Environment | `uv run pytest packages/Enron-Evaluation-Environment/tests -q` | 87 pass | ~5 s |

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
| Release cut / sprint sweep | **4** | All 9 suites + all governance gates below |

## Governance gates (always run on governance/tooling changes and at tier 4)

```bash
python scripts/board_state.py check          # board invariants; 0 errors/0 warnings expected
python scripts/github_labels.py audit        # label taxonomy (CI gate)
python scripts/audit_references.py           # no stale Exios66/mailroom-dev references
python scripts/taxonomy_parity.py            # doc-class + subclass taxonomy (CI gate)
python scripts/release_chain.py check        # hub release-chain invariants (CI gate)
```

## Local CI runner (`scripts/ci.py`, DMR-090)

GitHub Actions is unusable for this account, so CI runs locally. `scripts/ci.py`
(stdlib only) runs the same governance gates as the workflows plus the gates
they never ran: `uv lock --check`, `sync_vendor.py --check`, `scripts/tests`,
`board-site` JS tests and one `uv run --frozen pytest` per package.

```bash
python3 scripts/ci.py run                     # = --changed: gates mapped from the diff vs origin/main
python3 scripts/ci.py run --all               # every gate (tier 4)
python3 scripts/ci.py run --only scripts lock # named gates/groups (partial run)
python3 scripts/ci.py run --all --report-status   # + post the required `ci` commit status
python3 scripts/ci.py status                  # print the last run (.ci/last-run.json)
```

- Every run writes `.ci/last-run.json` and `.ci/last-run.md` (gitignored);
  paste the `.md` into the PR body as the test evidence.
- `--changed` mapping: `packages/<pkg>/**` -> that suite; `llm-dojo-scoring` /
  `llm-mailroom` also -> vendor + the sandbox suite; `scripts/`, `governance/`,
  `.github/` -> governance + scripts; `board-site/` -> board-site; any
  `pyproject.toml`/`uv.lock` -> lock + all suites; anything else (or an empty
  diff) -> governance only.
- `labels-audit` needs GitHub credentials; without them it is `skip (reason)`.
  A skip is reported, never counted as a pass.
- `--report-status` posts `ci` for HEAD to `LLM-Mailroom-Services/Digital-Mailroom`
  (override: `MAILROOM_GITHUB_REPO`; token: `GITHUB_TOKEN`, `MAILROOM_GH_TOKEN`,
  `gh auth token`). It refuses on a dirty tree, a HEAD that is not on a remote
  branch, or a partial run that would post `success` (partial runs may only post
  `failure`).
- Optional pre-push hook: `git config core.hooksPath scripts/githooks` runs
  `ci.py run --changed` before each push; `SKIP_CI=1` bypasses it loudly.

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
