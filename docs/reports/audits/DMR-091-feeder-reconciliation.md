# DMR-091: upstream-first feeder reconciliation

> **Historical snapshot, superseded during DMR-091 source-first review.**
> The statements and counts below describe the initial reconciliation recorded
> at `46b24929` and its earlier manifest, not the current PR162 state. Subsequent
> audits found additional defects; fixes now land in standalone repositories
> before exact main imports. Current intermediate import evidence is
> [DMR-091-source-main-imports.md](DMR-091-source-main-imports.md).
> Final source/vendor verification remains pending; the historical zero-drift
> and no-source-write statements below must not be read as current claims.


Checked 2026-10-23 UTC. Draft reconciliation: [PR #162](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/162). Tracking issue: [#161](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/161).

All seven standalone `main` tips were fetched and compared with their recorded sync cursors and complete package trees. All current upstream paths are present. The four feeders with new work were imported **into this branch**; no standalone repository was pushed or modified. This report does not claim the reconciliation has merged into hub `main`.

## Imported sources and retained differences

| Package | Current feeder main | Missing paths | Modified paths | Additional hub paths |
| --- | --- | ---: | ---: | ---: |
| Enron-Evaluation-Environment | `160d9077cca6` | 0 | 11 | 1 |
| The-Mailroom | `d5358650e42d` | 0 | 21 | 3 |
| claims-data-eda | `a3fbca3c9c76` | 0 | 5 | 0 |
| llm-dojo-scoring | `377d00bdef11` | 0 | 5 | 1 |
| llm-mailroom | `cb960a2c1ab3` | 0 | 7 | 1 |
| local-mailroom-sandbox | `6d605cc184f1` | 0 | 54 | 1 |
| mailroom-corpus-eda | `524d90a9a8bc` | 0 | 6 | 1 |

The complete path inventory is [DMR-091-feeder-manifest.json](DMR-091-feeder-manifest.json). Cursor alignment means imported upstream state with explicit hub differences; it does not mean byte-identical packages or permission to push the hub over the feeders.

- **Dojo:** 22 newer commits imported, including corporate subclass schemas/relabeling, audit export, strict malformed-GT handling, prompt lineage, Python minimum, dependency and documentation work. The five modified scorer modules and additional length-guard tests are the existing PR #152/#154 residuals, retained after confirming they are absent upstream.
- **Mailroom:** 14 newer commits imported, including relations fixes, prompt lineage, pin-bump tooling and contract tests. The remaining differences include PR #153's existing storage concurrency fix/test, the explicit Modal dependency alignment, and the tested live/evaluation prompt-family compatibility repair described below.
- **Sandbox:** 21 newer commits imported, including corporate v7 subclass prompts/defaults, scoring wiring, SHA-verified fallback pins, and dependency updates. The DMR-088 refresh-every-vendor fix/test remains necessary and now uses upstream's four-part pins. Generated requirements and the Modal test assertion were aligned with upstream declarations. Both vendor trees were regenerated from current workspace sources. Its prompt-sync helper explicitly preserves the feeder-approved corporate evaluation v7 head independently of mailroom live v6.
- **Corpus EDA:** 26 newer commits imported, including v9.3 corporate-presence staging tools, relabel/conformance tests, export/presence fixes and upstream routing corrections. The completed merger-specialist routing work was taken from upstream. Existing hub workflow/report-link/requirements normalization and surface-parity coverage were retained. Dojo provenance hashes were updated only after AST comparison confirmed identical mirrored registries; the EDA parser already implements dojo's newer rejection of falsey malformed GT values.
- **The-Mailroom, Enron and claims:** upstream tips are unchanged. Their existing hub changes were preserved, including the Enron publish-verification fix already merged in #150.

Sandbox corporate prompt bytes were independently preserved against its feeder: historical simplified v6 `fe13501f…`, current subclass-v2 and production v7 `253559fc…`. No prompt regeneration or blanket replacement of frozen stems was performed. Corpus reports were imported as upstream bytes; no Plotly figures or datasets were regenerated/published. The root `uv.lock` is the active workspace lock; tracked standalone lock artifacts remain upstream provenance.

## Compatibility repair: preserve separate prompt families

The imported dojo intentionally serves corporate v6 (`fe13501f…`) in its live `production` family and corporate v7 (`253559fc…`) in its evaluation `production_prompts` family. Mailroom's pre-existing loader selected the latter despite its frozen lineage requiring v6. Three existing full-suite/focused parity tests reproduced the failure. The consumer now selects `production` for all five live specialists, whose bytes exactly match all existing frozen hashes and lengths. The updated tests pin both corporate family hashes and retain cross-family equality for the other four roles; all 11 focused tests pass.

Sandbox deliberately promoted its own evaluation default to v7 upstream. Its sync helper formerly inherited mailroom's loader transitively, which would now reset that completed promotion to v6. The helper now explicitly selects the corporate evaluation family, with a new exact-hash/existing-file regression test. Its existing repo-pin check was shown red before this fix and seven focused script checks pass afterward. No prompt text or frozen hash was changed in either repository.

## Every open hub PR

| PR | Finding and disposition |
| --- | --- |
| [#152](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/152) | Length guards are absent in current dojo main. Original commits merged into this reconciliation branch. The one scorer conflict retains both upstream documentation and the guard. MAUD span-list exemption preserved. New upstream docstring coverage required docstrings on the existing regression tests. |
| [#154](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/154) | Dependent documentation partly overlaps feeder docstrings. Original commits merged and overlap reconciled once. Its Raises text was corrected to distinguish MAUD spans from document batches. A three-way merge preserves the MAUD exemption; comparing stale branch heads alone would have falsely suggested behavior loss. |
| [#153](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/153) | Storage fix is absent upstream (feeder storage file matched hub baseline). Original commits merged, then vendor regenerated. |
| [#159](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/159) | Still-needed pipeline adoption of dataset v9.2. Kept separate: importing corpus producer code does not silently change consumer dataset revisions. The source remains on v9.1 pending this PR. Its changelog entry will need combining with imported upstream entries; keep both. Imported v9.3 producer code is staged, not a new published dataset. |
| [#156](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/156) | Hub CI work, no feeder package overwrite. Its AGENTS/board conflicts already reproduce against pre-reconciliation origin/main; it must retain current release-tagging guidance when updated. |
| [#157](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/157) | Hub board-only branch hygiene, no feeder overlap. New DMR-091 row placed away from its insertion to avoid an unnecessary board conflict. |
| [#160](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/160) | Hub governance/tests only, no feeder overwrite; clean merge-tree against reconciliation before final evidence edits. |

The original PRs remain open for their existing review history. After this reconciliation lands with merge ancestry preserved, #152/#153/#154 are already integrated and should be retired rather than reapplied. Do not squash away the preserved ancestry when consolidating this branch.

## Import and verification evidence

Dojo and mailroom used the sync driver's squash pull. Corpus's historical subtree merge produced 22 conflicts and was aborted cleanly; its recorded-cursor binary three-way delta reduced that to five actual overlapping files. Sandbox used its recorded-cursor delta and had one actual CLI conflict. No blanket `ours` resolution was used. Unforced `snapshot` accepted the sandbox/corpus import baselines after confirming zero missing upstream paths; all deliberate modifications are enumerated in the JSON.

A concurrent reader briefly replaced shared `FETCH_HEAD` and made status report the hub tree as the sandbox head. Direct GitHub API and remote reads proved sandbox main is valid `6d605cc1`; no feeder corruption occurred. The new root/wiki rule requires serialized shared-checkout fetches or dedicated refs with `--no-write-fetch-head`.

Validation results are recorded below. No claims of full green or delivery to main should be inferred while a listed blocker remains.

- Dojo: **1534 passed, 5 skipped** (full suite after integrating #152/#154).
- Corpus EDA: **278 passed, 19 skipped** (full suite; snapshot-dependent skips retained honestly).
- Sandbox: **1338 passed, 12 skipped, 1 failed**. Sole remaining failure: `test_modernbert_feeder_resolves_sibling`; this machine discovers external `/Users/morningstar/Desktop/Cold_Storage/mailroom-ml` with a model bundle but no `training/eval_modernbert.py`, so its status is correctly not ready. The seven imported packages do not include mailroom-ml. Integration-specific refresh, requirements, Modal and vendor checks: **85 passed**.
- Mailroom: **2031 passed, 37 skipped** (full suite, including notebook execution, after preserving live/evaluation prompt-family separation). Use the workspace kernel: `.venv/bin/python -m ipykernel install --prefix /tmp/dmr091-kernel --name python3`, then `JUPYTER_PATH=/tmp/dmr091-kernel/share/jupyter uv run --frozen pytest packages/llm-mailroom/src/tests -q`. The global kernel previously produced environment failures.
- The-Mailroom: **421 passed**.
- Enron: **91 passed**.
- Claims: **40 passed**.
- Hub scripts: **62 tests OK**; board API: **23 checks passed**.
- Vendor: **zero drift**, 205 mailroom and 95 dojo source/vendor file hashes agree using the driver's exclusions. Taxonomy parity, reference audit, label audit, release-chain check and `uv lock --check` pass.
- Board check has **five pre-existing phantom historical card references** (DMR-120/176/182/188/191), plus existing hygiene warnings. DMR-091 adds no structural error. Keep these visible rather than editing unrelated historical evidence.

## Continued upstream-first work

Root AGENTS and the sync wiki now require current feeder comparison before package edits, PR reviews or publishing; import completed standalone changes first, preserve justified residuals through a cursor-based merge, then refresh vendors. Do not run the release-train push merely because status reports local-ahead files: the retained differences above need their own reviewed propagation decision.
