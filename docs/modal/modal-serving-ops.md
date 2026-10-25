# Modal serving ops — warm-once, no-waste

**Owner:** SAND-028 · **Runbooks:** [`docs/runbooks/README.md`](../runbooks/README.md)
(generated from [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml)).
**Companion:** [`SAND-028-SERVING-SPEND-REVIEW.md`](../../governance/scheming/SAND-028-SERVING-SPEND-REVIEW.md).

Token-proxy cost is ~2.4% of GPU cost. The L4 wall-clock is ~98% of the price.
Optimize GPU *seconds*, not tokens.

```bash
sandbox runbook show l4-qwen3-8b           # singular 1×L4 / 1-container Qwen3-8B
sandbox runbook show improved-granite-fp8  # Granite Leg A swap-in
sandbox runbook check
```

## Rules (the money knobs)

These pins are `serving.baseline` in the catalog and must match
`deploy/modal_vllm.py` defaults (`sandbox runbook check` enforces that):

| Knob | Attended | Unattended/overnight |
| --- | --- | --- |
| `MODAL_VLLM_SCALEDOWN_SECONDS` | **120** | **600** |
| `MODAL_VLLM_MAX_CONTAINERS` | **1** | 1 (raise only after measured queueing; second L4 = `sandbox runbook show improved-second-l4`) |
| `MODAL_VLLM_MAX_NUM_SEQS` | **6** | 6 (scale-matrix short-doc cells override to 256) |
| `MODAL_VLLM_GPU` | **L4** | L4 |

- Pre-warm weights once (CPU-only, no GPU billed): `modal run deploy/modal_vllm.py::download_model`
- Never `modal deploy --strategy recreate` mid-matrix — a recreate re-pays image pull + weight load.
- Drive a track through `sandbox run suite` (or the catalog runbook script). Independent `sandbox run start` per class re-pays a boot.
- Teardown only after the last run: `./deploy/teardown_vllm.sh`

## Same-subset rule

Draw **one bucket per class** (the 100) and score 20/50 as prefixes of that locked set.
`corpus._draw_buckets` is **not** nested across independent draws (50⊂100 ~26% of seeds) — issue #38.

## Cost caps

`job.cost_cap_usd` + `job.max_wall_seconds` live in `specialist_posture.py` (rendered into the runbooks). After an N=20 probe, re-derive from measured wall. Prefer `MODAL_BILLED_GPU_SECONDS`.

## Evidence

- `reports/serving/*.serving.json` — 3 measured Modal runs ($0.5452 / 60 docs; boots 24% of spend).
- `reports/RUN-20-CONTRACTS-AWQ-C8-REPORT.md` — token-proxy = 2.44% of GPU cost.
- Anti-patterns table: [`docs/runbooks/README.md`](../runbooks/README.md).
