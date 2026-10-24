# DMR-097 dependency residuals — 2026-10-24 UTC

## Scope and source ownership

The interrupted session left the authoritative sandbox lock uncommitted. Its
reported source drift (`5b571fbd`, then `2e4289ed`) had already been imported
by hub PR [#182](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/182),
commit `a25f676f9`, before this resume. Hub PR
[#176](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/176)
already delivered the earlier root lock refresh and sync runbook. Those
imports were preserved.

SAND-062 source PR [#162](https://github.com/Exios66/local-mailroom-sandbox/pull/162)
completes the lock and test harness repairs before an inbound hub import.
No package implementation is authored in the hub.

| Dependency | Authoritative sandbox result | Hub root result |
|---|---|---|
| nbconvert | 7.17.2 | 7.17.2, already adopted |
| OpenTelemetry API/SDK/exporters | 1.45.1 | 1.45.1, already adopted |
| OTEL semantic conventions/shared exporters | 0.66b1 | 0.66b1, already adopted |
| pypdf | 6.21.2 | 6.21.2, already adopted |
| filelock | 4.2.1 | 4.2.1 |
| certifi | 2026.10.19, already adopted | 2026.10.19 |

The OpenTelemetry resolution adds its required shared HTTP transport and OTLP
common distributions. No packages were removed and no dependency specs changed.

## New fork PRs merged during this resume

Each PR changed only its dependency artifacts in `uv.lock`, had successful
network-free CI, and was checked at its exact head before merge:

- [sandbox fork #9](https://github.com/LLM-Mailroom-Services/mailroom-sandbox/pull/9): pypdf 6.21.2, merge `ee431a78`.
- [sandbox fork #10](https://github.com/LLM-Mailroom-Services/mailroom-sandbox/pull/10): certifi 2026.10.19, merge `b433ef85`.
- [sandbox fork #11](https://github.com/LLM-Mailroom-Services/mailroom-sandbox/pull/11): filelock 4.2.1, merge `3fe65124`.

The source and hub resolutions explicitly adopt their missing versions rather
than assuming fork merges propagate to the authoritative source.

## Test repairs and independent review

`test_initial_cli_knobs_survive_cold_resume` failed on unchanged source main
with `ModuleNotFoundError: llm`: its fresh process patched vendored imports
before sandbox initialization. `SDK_SETUP` now imports `mailroom_sandbox`
first. Running the generation module independently also exposed 39 missing
`api_evals` imports that suite order masked. Its `source_root` fixture now uses
`monkeypatch.syspath_prepend` for the tracked API-evals package.

The existing real OpenAI transport substitution and model/token/temperature/
prompt assertions remain intact. There are no product code changes.
The repaired module passes all 45 tests. Code-analyst review approved the
bootstrap repairs and coordinated dependency changes, contingent on full gates.
The first complete source run, before adding the new pypdf/filelock bumps,
passed 1,512 tests with 14 skips. Final results are recorded below.

## Verification

Merged source: `5c6af57a18ff0c9393ab8472a042e16a2e4f09ca` (source PR #162;
implementation `4235b96`, source evidence `2c4dada`). Final source suite:
**1,512 passed / 14 skipped / 0 failed** on the complete dependency set.
Hub sandbox final suite: **1,514 passed / 12 skipped / 0 failed** (102.55 s).
The other four hub package gates are running sequentially. Hub import PR:
[#187](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/187).
Content-verified snapshot at `2026-10-24T03:58:05Z` records source
`5c6af57a18ff0c9393ab8472a042e16a2e4f09ca`; status reports zero new upstream
commits and zero cursor gaps. The other four cursor entries are unchanged.

The driver import recovered the old standalone vendor snapshots. Its initial
automatic gate was interrupted before claiming success; the cursor remained
unchanged. `scripts/sync_vendor.py` regenerated the reviewed workspace copies,
then `--check` passed. All **318** pre-import tracked vendor files were compared
byte-for-byte and remain unchanged. The net package diff contains only the four
expected source files and a recovered 15-line `data/cache/README.md`. That README
has the identical longstanding source blob at both `2e4289ed` and `5c6af57a`;
no cached dataset was imported. The sync runbook now covers this sandbox vendor
reconciliation before final suite/cursor verification.

Both locks pass `uv lock --check`; the source passes `uv pip check`. Offline
smokes exercise notebook HTML export, OTEL SDK span/exporter initialization,
PDF write/read, and real file-lock exclusion, reentrancy and reacquisition.
Source extras installed from its own changed lock: dev, notebooks, observability.
Hub verification uses a private virtualenv resolved from the hub root lock.

The first concurrent hub runs were interrupted after a systems specialist
confirmed heavy swapping on the 8 GiB host. Partial runs are not counted as
passing gates; final hub suites run one package at a time. Other agents'
processes and the shared checkout were left untouched.

## Existing hub gate failures and follow-ups

Independent test-suite-auditor verification at unchanged base `b719e75d3`
and this branch found **80 tests, 13 failures** in both runs, with identical
failing test/subtest identities. Two detect a real pre-existing ArchiveBrowser
taxonomy gap; eleven concern archived-board test expectations/metadata.
No dependency regression is observed by this comparison.

Other baseline gates:

- Board check: five phantom-card reference errors (`DMR-120`, `176`, `182`, `188`, `191`) and one stale-card warning (`DMR-063`).
- Reference audit: historical predecessor-repo mention in `docs/wiki/Glossary.md:27` is not allowlisted.
- Release chain: local lightweight `v0.0.1` has no matching changelog section (one error, one warning).
- Label audit passes; taxonomy parity passes; served-board API passes all 23 checks.

Follow-ups were opened before closing the dependency card:

- DMR-102 / [#185](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/185): deliberate source-owned Tailwind 4 migration. Source #45 currently keeps Tailwind 3.4.19 with its reviewed selector-parser override. No migration is implemented here.
- DMR-103: reconcile historical hub governance tests and gate findings without weakening them; preserve separate DMR-080/081 decisions.
- DMR-104 / [The-Mailroom #46](https://github.com/Exios66/The-Mailroom/issues/46): repair source ArchiveBrowser filters (missing merger_agreement, retired compliance_filing remains), then import.

The unrelated untracked source `data/provider_health.json` and `.lock` artifacts
are excluded from every commit. All source/import commits, full gate counts and
scoped status must be recorded before the parent card is archived.
