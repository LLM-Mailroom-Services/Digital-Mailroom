# Run ledger

Every paid run that passed the spend gate: who signed it (initials), when (UTC), the run and its
locked spec, and how it ended. Appended by `sandbox run start` / `sandbox run resume`; the result
cell is filled when the run reaches a terminal state (✓ done, ✗ failed; blank = still open).
Do not edit rows by hand. Parse with `mailroom_sandbox.job.ledger.rows()`.

| signed_utc | initials | action | run_id | config | spec | rows | api_cap_usd | result |
|---|---|---|---|---|---|---|---|---|
| 2026-11-01T08:42:40Z | JB | start | extraction-gate-specialist-insurance-claim-qwen | config/runs/extraction-gate-specialist-insurance-claim-qwen.yaml | 295e169d5f81 | 60 | 0.05 | ✓ |
| 2026-11-01T08:43:07Z | JB | start | extraction-gate-specialist-correspondence-qwen | config/runs/extraction-gate-specialist-correspondence-qwen.yaml | d31affa9a548 | 60 | 0.05 | ✓ |
| 2026-11-01T08:44:03Z | JB | start | extraction-gate-specialist-corporate-record-qwen | config/runs/extraction-gate-specialist-corporate-record-qwen.yaml | b7db57702771 | 40 | 0.1 | ✓ |
| 2026-11-01T08:44:34Z | JB | start | extraction-gate-specialist-contract-qwen | config/runs/extraction-gate-specialist-contract-qwen.yaml | b994376771b9 | 40 | 0.1 | ✓ |
| 2026-11-01T08:45:18Z | JB | start | extraction-gate-specialist-merger-agreement-qwen | config/runs/extraction-gate-specialist-merger-agreement-qwen.yaml | cf1410a4e705 | 20 | 0.2 | ✓ |
| 2026-11-01T08:47:51Z | JB | start | extraction-gate-luna-v1.0.0-baseline | config/runs/extraction-gate-luna-v1.0.0-baseline.yaml | b6cf7cc75817 | 220 | 0.35 | ✓ |
| 2026-11-01T09:21:06Z | JB | start | specialist-condensed-v1-insurance-claim-qwen-ab | config/runs/specialist-condensed-v1-insurance-claim-qwen-ab.yaml | f507ed9d3263 | 60 | 0.05 | ✓ |
| 2026-11-01T09:21:34Z | JB | start | specialist-condensed-v1-correspondence-qwen-ab | config/runs/specialist-condensed-v1-correspondence-qwen-ab.yaml | e47e16848120 | 60 | 0.05 | ✓ |
| 2026-11-01T09:21:54Z | JB | start | specialist-condensed-v1-corporate-record-qwen-ab | config/runs/specialist-condensed-v1-corporate-record-qwen-ab.yaml | 694f6d3c5b2c | 40 | 0.08 | ✓ |
| 2026-11-01T09:22:26Z | JB | start | extraction-gate-specialist-contract-qwen-r2 | config/runs/extraction-gate-specialist-contract-qwen-r2.yaml | 23ea98503707 | 40 | 0.1 | ✓ |
| 2026-11-01T09:23:09Z | JB | start | extraction-gate-specialist-merger-agreement-qwen-r2 | config/runs/extraction-gate-specialist-merger-agreement-qwen-r2.yaml | b97c5429d3e9 | 10 | 0.15 | ✓ |
| 2026-11-01T09:23:22Z | JB | start | specialist-condensed-v2-insurance-claim-qwen-ab | config/runs/specialist-condensed-v2-insurance-claim-qwen-ab.yaml | 2eda831fe1d6 | 60 | 0.05 | ✓ |
| 2026-11-01T09:23:49Z | JB | start | specialist-condensed-v2-correspondence-qwen-ab | config/runs/specialist-condensed-v2-correspondence-qwen-ab.yaml | f089112a0146 | 60 | 0.05 | ✓ |
| 2026-11-01T09:24:38Z | JB | start | extraction-gate-specialist-insurance-claim-qwen-r2 | config/runs/extraction-gate-specialist-insurance-claim-qwen-r2.yaml | 38df9f926989 | 240 | 0.1 | ✓ |
| 2026-11-01T09:26:08Z | JB | start | extraction-gate-specialist-correspondence-qwen-r2 | config/runs/extraction-gate-specialist-correspondence-qwen-r2.yaml | b4d8ca466d3d | 240 | 0.1 | ✓ |
| 2026-11-01T09:27:12Z | JB | start | extraction-gate-specialist-corporate-record-qwen-r2 | config/runs/extraction-gate-specialist-corporate-record-qwen-r2.yaml | c5660df14491 | 160 | 0.15 | ✓ |
| 2026-11-01T09:29:17Z | JB | start | specialist-condensed-v3-insurance-claim-qwen-ab | config/runs/specialist-condensed-v3-insurance-claim-qwen-ab.yaml | 0fc01e19c6c5 | 60 | 0.05 | ✓ |
| 2026-11-01T09:31:11Z | JB | start | extraction-gate-luna-v1.1.0-baseline | config/runs/extraction-gate-luna-v1.1.0-baseline.yaml | 9e0cf931bac9 | 220 | 0.5 | ✓ |
| 2026-11-01T09:31:33Z | JB | start | extraction-gate-luna-v1.1.0-r2 | config/runs/extraction-gate-luna-v1.1.0-r2.yaml | 49e01f82d137 | 690 | 0.6 | ✓ |
| 2026-11-01T09:47:34Z | JB | start | extraction-gate-specialist-insurance-claim-qwen-r3 | config/runs/extraction-gate-specialist-insurance-claim-qwen-r3.yaml | 93186912f7e4 | 686 | 0.3 | ✓ |
| 2026-11-01T09:47:34Z | JB | start | extraction-gate-luna-v1.2.0-rereview | config/runs/extraction-gate-luna-v1.2.0-rereview.yaml | 020ed35827a9 | 880 | 0.6 | ✓ |
| 2026-11-01T18:20:07Z | JB | start | extraction-gate-luna-v1.2.0-r3 | config/runs/extraction-gate-luna-v1.2.0-r3.yaml | 07da15f0519a | 686 | 0.35 | ✓ |
| 2026-11-01T18:27:18Z | JB | start | extraction-gate-luna-v1.3.0 | config/runs/extraction-gate-luna-v1.3.0.yaml | f6743d5a3496 | 1596 | 1.1 | ✓ |
| 2026-11-02T01:12:59Z | JB | start | reviewer-validation-qwen-flash-test | config/runs/reviewer-validation-qwen-flash-test.yaml | 8b72aee96e7a | 323 | 0.6 | ✓ |
| 2026-11-02T01:52:32Z | JB | start | reviewer-calibration-luna-decisions-v3.1.0-train-half | config/runs/reviewer-calibration-luna-decisions-v3.1.0-train-half.yaml | e8c4238bca96 | 1491 | 1.5 | ✓ |
