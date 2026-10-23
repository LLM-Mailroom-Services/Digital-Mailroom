# DMR-091 source-main imports — intermediate evidence

2026-10-23 UTC. PR162 remains under review; final vendor composition and
additional Dojo ownership adoption are pending. This is not final completion.

- Dojo source PR59 merged at `1d7fac8e510b834977e452b25a761c66945ad464`;
  all 198 tracked source paths/modes imported exactly. Reviewed candidate tree
  `89fc3acaf68e5486974716a26daac14020948a17` equals merged main.
- Corpus source PR31 merged at `4735ee0208f14c224154aba8f09653b590d7a405`;
  reviewed tree `b0acc31e0b4d9030acf3817c4dc8e330da2fb181` equals merged main.
  All 178 non-overlay source paths match. Five existing hub overlays remain:
  `.github/workflows/ci.yml`, `.github/workflows/dependabot-auto-merge.yml`,
  `README.md`, `reports/SUMMARY_REPORT.md`, `requirements.txt`; the existing
  extra `tests/test_surface_parity.py` remains. No runtime fix was discarded.
- Sync cursors advance to these actual source-main commits, never an
  uncommitted or consumer-authored implementation.

Source suites: Dojo1595 passed/5 skipped; Corpus337 passed/16 skipped.
Independent xhigh postfix review approved both, including a separate24-case
final review of the corpus temporal alignment fix. Hub import suites:
Dojo1595 passed/5 skipped; Corpus337 passed/19 skipped (additional local
snapshot/surface-dependent skips). Full source and hub XML was parsed.

Both new `test_full_source_audit_regressions.py` files are explicitly tracked.
The transient full mode/blob inventory is `/tmp/dmr091-source-main-import-evidence.json`.
Sandbox vendor drift is intentionally still visible pending its upstream-first
refresh and final source-main import. No hub patch was exported upstream.
