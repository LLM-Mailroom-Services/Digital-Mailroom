# QWEN-flash OpenRouter cost report (SAND-027-9)

Reproducible from a clean checkout via the tracked ledger
`reports/qwen-flash-cost-source.json` — no dependency on the gitignored
`reports/experiment_log.jsonl`.

Regenerate the machine report (markdown/json under `api-evals/reports/`):

```bash
python api-evals/run_api_evals.py report --from-ledger --prices 0.03 0.13
```

(`--prices` avoids a live OpenRouter `/models` fetch in offline CI; omit it to
refresh list prices and surface pin mismatches.)

## Price basis

| Field | Value |
| --- | --- |
| Model | `qwen/qwen3.7-flash` |
| List price (pin) | **$0.03 / 1M prompt** · **$0.13 / 1M completion** |
| Pin source | OpenRouter `/models`, verified 2026-09-25 (`api_evals.registry.DEFAULT_LIST_PRICES`) |
| Real API $ formula | `prompt_tokens × in/1M + completion_tokens × out/1M` |

## Per-run ledger (three records, 41 documents)

| record | n | prompt tok | completion tok | **real API $** | logged `estimated_gpu_cost_usd` (L4 proxy, **not** OpenRouter) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `api-smoke-1` | 1 | 12,158 | 997 | **$0.000494** | 0.001854 |
| `sandbox_contracts_specialist_api-contracts-20` (22:04Z) | 20 | 123,829 | 16,629 | **$0.005877** | 0.008428 |
| `sandbox_contracts_specialist_api-contracts-20` (22:08Z) | 20 | 123,829 | 15,310 | **$0.005705** | 0.008276 |
| **total** | **41** | | | **≈ $0.0121** | ≈ $0.0186 |

`estimated_gpu_cost_usd` is wall/busy GPU-seconds × Modal L4 $/hr — a **sandbox
comparison proxy** for local/Modal legs. It is **never** the OpenRouter invoice.

## Caveats (required in any published summary)

1. All three runs used `prompt_version: mailroom-default` — pinned simplified
   prompt stems were not recorded; these figures are **cost-only**, not
   prompt-fixed quality claims.
2. The two `contracts-20` rows logged `overall_extraction_score: 0.0` with zero
   errors — measurement status is **UNPROVEN** (issue #41); do not treat 0.0 as
   validated accuracy.
3. Dataset fingerprint `9c87afb3c10c` on the contracts rows matches the Modal
   `run-20-contracts-*` draw (draw parity); Modal baseline costs live in
   `reports/archive/MODAL-RUNS-REPORT.md`.

## Related docs

- Ledger schema + raw fields: `reports/qwen-flash-cost-source.json`
- Mission plan §2.7: `governance/SAND-027-MISSION-PLAN.md`
- GPU vs API cost honesty: `src/mailroom_sandbox/job/metrics.py` (module docstring)
