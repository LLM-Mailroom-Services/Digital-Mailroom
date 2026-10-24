# DMR-110 — constellation label clearance

UTC date: 2026-10-24. Documentation artwork only.

## Reported defect and regression

The six source maps used an 88px current-location pill with 80.36px of glyphs: about 3.82px padding per side. Mobile pinned-pull glyphs reached x635 in a 640-unit canvas; the interrupted draft pushed its halo beyond the edge. The desktop legend overlapped the dojo card, mobile visualizer text had 1px bottom padding, and particles were painted above connector captions. Mobile stat values/captions had only 1–1.5px separation.

A browser regression against the unchanged source SVGs found **312 failures across 12 map variants**, plus the stat-caption failures. The shipped checker uses actual glyph bounds transformed into SVG coordinates, padded containers, owned-node checks, badge/text separation, footer clearance and paint order. Mutation checks prove it rejects a node title moved out of its card and a current badge moved down into that title.

## Correction and visual review

- Opaque, padded connector captions are painted after paths, particles and node cards.
- 136×34 current-location pill, 12px text, measured 94.03px glyph width: approximately **21px horizontal padding**.
- Mobile outer callout occupies x594–626 in a width640 canvas, preserving **14px minimum canvas clearance** and clearance from node edges.
- Node cards are 96px high, footer is outside the last node row, and mobile stat captions have at least 10px glyph separation.
- The hub map retains all nine original connections, including **both sandbox and pipeline traces into Langfuse**. Its separate generator/checker are committed beside the SVG.

Hazel reviewed current maps at 320px/375px and animation times 0, 0.7, 1.5 and 3 seconds, and checked the reduced-motion static presentation. Atom verified unchanged root README content/anchors, identical six source kits/checkers, and preserved data-flow labels. The shipped source regression pages plus hub passed **58 map-frame/stat cases**, with zero findings after the final checker corrections.

## Source deliveries

| Source | Merged PR | Source merge SHA |
| --- | --- | --- |
| llm-dojo-scoring | [#86](https://github.com/Exios66/llm-dojo-scoring/pull/86) | `f53f2a3301d3bb7e42b00c475f253605286fd14f` |
| llm-mailroom | [#125](https://github.com/Exios66/llm-mailroom/pull/125) | `4eaa01eab381f6f60df1488bb5fa84e34f8301cd` |
| Mailroom-Corpus-EDA | [#36](https://github.com/Exios66/Mailroom-Corpus-EDA/pull/36) | `5f2252c8887169b5d8967ff0e1338ec1b3f706c4` |
| The-Mailroom | [#50](https://github.com/Exios66/The-Mailroom/pull/50) | `dd94b96adb11c92a46bc6a5f15b77bf1f402b511` |
| mailroom-ml | [#62](https://github.com/LLM-Mailroom-Services/mailroom-ml/pull/62) | `01c2272f7ee6625b9196c25095346812d39d42ff` |
| local-mailroom-sandbox | [#164](https://github.com/Exios66/local-mailroom-sandbox/pull/164) | `5ae07c2c05ae6de680837f1134ffaf64c214e40e` |

Local source checks: Dojo documentation/docstrings 157 passed; pipeline landing/inventories 24 passed; The-Mailroom gallery/release 6 passed; sandbox documentation paths 3 passed. All six generators pass --check; XML, internal references and diff checks pass. ML GitHub lint-and-test passed before merge. No root README, runtime, dependency, model, corpus, release or vendor change.

## Hub imports and gates

All five merged sources were imported with `sync_packages.py pull --squash --verify-suite`; no force cursor or package implementation edits were used. Subtree merge metadata is retained.

| Imported package | Import merge | Verified cursor commit | Full package gate |
| --- | --- | --- | --- |
| llm-dojo-scoring | `1522c75f7` | `2cd8d3717` | Passed (driver recorded green; exact count not retained) |
| llm-mailroom | `65fa0eb4c` | `22bb15820` | 2,173 passed, 37 skipped |
| mailroom-corpus-eda | `78c2e3fdc` | `5dfc1e796` | 337 passed, 19 skipped |
| The-Mailroom | `f931f44ae` | `cb87f5a1e` | 507 passed, 2 skipped |
| local-mailroom-sandbox | `2e3d86b45` | `cd1a78218` | 1,514 passed, 12 skipped |

The supported `SYNC_VERIFY_CMD` override selected the shared project interpreter, with imported sources explicitly on `PYTHONPATH`, without changing the environment, lockfile or dependency specifications. The first sandbox attempt stopped at `test_launcher_passes_beacon_and_board_through` because its shell launcher selected system Python without `dotenv` (43 passed before the failure). Rerunning the same full gate with the launcher's documented `SANDBOX_PY` override selected the shared interpreter and passed; only then did the driver advance the cursor.

Final checks: all five manifest cursors match the reviewed source merge SHAs; live sync status is 5/5 in sync. Source artwork trees are byte-identical to those source objects. All six source kits/checkers are identical, and the hub shares the browser checker. All five imported generators and the hub generator pass `--check`; `git diff --check` passes. The hermetic hub scripts suite passes **81 tests**.

`sync_vendor.py --check` reports zero drift for both snapshots. The vendor tree remains `7661e257f2f9b356d941656685a84dfa04fa8e76`. The-Mailroom heavy-media exclusions remain pruned; its pre-existing hub-only `operator_desk/credentials.py` retains SHA256 `1cd48ed4abd64c77fe9c4ef7ba66faad654a6f308af07a7cd9e8959cca1fbce9`. Independent general import review verified all package changes are confined to README artwork assets and confirmed these integration exceptions. No runtime, dependency, version, lockfile or vendor diff.

`board_state.py check` remains at its pre-existing baseline: five phantom-card errors (DMR-120/176/182/188/191) and one stale DMR-063 warning, tracked under DMR-103. This gate is **not green**. The phantom required `ci` context remains the separately tracked DMR-080 branch-policy defect; the branch protection was not changed. The v0.10.0 minor release was already delivered under DMR-106; this documentation correction stays in Unreleased.
