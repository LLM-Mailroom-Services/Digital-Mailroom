# SAND-042 master score & cost card — paired concurrency × fleet grid

**Conditions measured:** 5 of 5 · **Documents per condition:** 250 (5 specialists × n=50, one shared subclass-stratified draw) · **Model:** Qwen/Qwen3-8B-AWQ · L4 @ $0.80/GPU-hr · **Prompts:** v1 `*_simplified` only.

**Metric coverage:** verbatim /metrics 26/26 · GPU memory bandwidth 26/26 · mid-run KV/queue 25/26 · cold boot 5/5 cells. Every blank states its reason (no substitute values); the full matrix is in the master report.

5 conditions — {1×L4, 2×L4} × {client concurrency 8, 16} plus the 2×L4 C32 saturation point (16 per replica, the engine's `max_num_seqs` admission ceiling) — on the SAND-037 aligned spec.

All 5 cells score the **identical 250 documents** (5 specialists × 50 documents, one subclass-stratified draw per class), so every cell-to-cell delta below is **paired**: the unit of analysis is the per-document score difference. Intervals are 95% percentile bootstrap over documents; the last column is the paired n that Δ = 0.05 would need at 80% power.
Design, metric contract and acceptance rules: [`docs/SAND42-EXPERIMENT-DESIGN.md`](../../docs/SAND42-EXPERIMENT-DESIGN.md).

## Conditions

| Condition | Runbook | GPUs | Client concurrency | Per replica | min=max |
| --- | --- | ---: | ---: | ---: | --- |
| `1l4-c8` | `sandbox runbook show sand42-1l4-c8` | 1 | 8 | 8 | 1 |
| `1l4-c16` | `sandbox runbook show sand42-1l4-c16` | 1 | 16 | 16 | 1 |
| `2l4-c8` | `sandbox runbook show sand42-2l4-c8` | 2 | 8 | 4 | 2 |
| `2l4-c16` | `sandbox runbook show sand42-2l4-c16` | 2 | 16 | 8 | 2 |
| `2l4-c32` | `sandbox runbook show sand42-2l4-c32` | 2 | 32 | 16 | 2 |

**Matched per-replica-load pair:** `1l4-c8` vs `2l4-c16` (8 per replica each) isolates replica count. `1l4-c8` vs `1l4-c16` isolates concurrency at fixed GPUs. The 2×L4 cells are *not* a load twin of the 1×L4 cells.

## Quality (mean field score; contracts CUAD presence F1, merger MAUD accuracy)

| Metric | 1×L4 C8 | 1×L4 C16 | 2×L4 C8 | 2×L4 C16 | 2×L4 C32 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Correspondence | 0.388 | 0.379 | 0.376 | 0.390 | 0.373 |
| Insurance Claims | 0.671 | 0.667 | 0.665 | 0.670 | 0.666 |
| Corporate Records | 0.482 | 0.494 | 0.492 | 0.488 | 0.500 |
| Contracts | 0.599 | 0.604 | 0.624 | 0.604 | 0.622 |
| Merger Agreements | 0.027 | 0.028 | 0.028 | 0.025 | 0.021 |

## Serving efficiency (per condition, per specialist)

| Metric | 1×L4 C8 | 1×L4 C16 | 2×L4 C8 | 2×L4 C16 | 2×L4 C32 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Correspondence · documents/min/GPU | 49.41 | 63.47 | 29.42 | 36.80 | 38.41 |
| Correspondence · goodput docs/min/GPU | 49.41 | 63.47 | 29.42 | 36.80 | 38.41 |
| Correspondence · tokens/s/GPU | 2,262 | 2,903 | 1,346 | 1,684 | 1,757 |
| Correspondence · GPU util % (mean) | 87.2 | 61.8 | 65.0 | 64.5 | 49.1 |
| Correspondence · GPU mem used | 21,027 MiB (91.3% of 23,034) | 20,996 MiB (91.2% of 23,034) | 20,992 MiB (91.1% of 23,034) | 20,996 MiB (91.2% of 23,034) | 20,976 MiB (91.1% of 23,034) |
| Correspondence · GPU mem bandwidth | 59.0% mean | 44.1% mean | 57.8% mean | 62.3% mean | 42.0% mean |
| Correspondence · $/1k ok | $0.245320 | $0.214840 | $0.458920 | $0.378140 | $0.335500 |
| Correspondence · $/1k schema-valid | $0.245320 | $0.214840 | $0.458920 | $0.378140 | $0.335500 |
| Insurance Claims · documents/min/GPU | 20.31 | 27.95 | 12.53 | 16.76 | 19.77 |
| Insurance Claims · goodput docs/min/GPU | 20.31 | 27.95 | 12.53 | 16.76 | 19.77 |
| Insurance Claims · tokens/s/GPU | 1,258 | 1,738 | 777 | 1,038 | 1,225 |
| Insurance Claims · GPU util % (mean) | 93.2 | 91.6 | 85.6 | 67.4 | 74.8 |
| Insurance Claims · GPU mem used | 21,028 MiB (91.3% of 23,034) | 21,026 MiB (91.3% of 23,034) | 21,023 MiB (91.3% of 23,034) | 20,996 MiB (91.2% of 23,034) | 21,022 MiB (91.3% of 23,034) |
| Insurance Claims · GPU mem bandwidth | 82.6% mean | 80.0% mean | 83.0% mean | 61.8% mean | 71.1% mean |
| Insurance Claims · $/1k ok | $0.536240 | $0.477120 | $0.972480 | $0.787360 | $0.676280 |
| Insurance Claims · $/1k schema-valid | $1.675750 | $1.403294 | $3.473143 | $2.624533 | $2.254267 |
| Corporate Records · documents/min/GPU | 33.94 | 39.22 | 22.93 | 25.66 | 30.57 |
| Corporate Records · goodput docs/min/GPU | 33.94 | 39.22 | 22.93 | 25.66 | 30.57 |
| Corporate Records · tokens/s/GPU | 2,324 | 2,685 | 1,569 | 1,757 | 2,092 |
| Corporate Records · GPU util % (mean) | 84.6 | 82.4 | 82.4 | 81.2 | 63.7 |
| Corporate Records · GPU mem used | 21,028 MiB (91.3% of 23,034) | 21,026 MiB (91.3% of 23,034) | 21,023 MiB (91.3% of 23,034) | 20,996 MiB (91.2% of 23,034) | 21,023 MiB (91.3% of 23,034) |
| Corporate Records · GPU mem bandwidth | 69.6% mean | 53.2% mean | 76.2% mean | 65.1% mean | 46.6% mean |
| Corporate Records · $/1k ok | $0.370180 | $0.341420 | $0.586840 | $0.528320 | $0.433140 |
| Corporate Records · $/1k schema-valid | $0.385604 | $0.355646 | $0.611292 | $0.550333 | $0.451187 |
| Contracts · documents/min/GPU | 2.18 | 2.67 | 1.45 | 1.41 | 1.46 |
| Contracts · goodput docs/min/GPU | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Contracts · tokens/s/GPU | 688 | 858 | 449 | 436 | 451 |
| Contracts · GPU util % (mean) | 97.4 | 97.8 | 84.7 | 90.6 | 86.8 |
| Contracts · GPU mem used | 21,028 MiB (91.3% of 23,034) | 21,026 MiB (91.3% of 23,034) | 21,025 MiB (91.3% of 23,034) | 20,998 MiB (91.2% of 23,034) | 21,026 MiB (91.3% of 23,034) |
| Contracts · GPU mem bandwidth | 90.1% mean | 86.4% mean | 80.1% mean | 84.6% mean | 80.6% mean |
| Contracts · $/1k ok | $6.137540 | $4.500700 | $9.185660 | $6.744320 | $6.971020 |
| Contracts · $/1k schema-valid | $6.137540 | $4.500700 | $9.185660 | $6.744320 | $6.971020 |
| Merger Agreements · documents/min/GPU | 0.64 | 0.73 | 0.47 | 0.52 | 0.76 |
| Merger Agreements · goodput docs/min/GPU | 0.64 | 0.00 | 0.47 | 0.52 | 0.76 |
| Merger Agreements · tokens/s/GPU | 1,113 | 1,259 | 815 | 901 | 1,316 |
| Merger Agreements · GPU util % (mean) | 88.7 | 98.8 | 92.8 | 93.1 | 95.1 |
| Merger Agreements · GPU mem used | 21,028 MiB (91.3% of 23,034) | 21,025 MiB (91.3% of 23,034) | 21,027 MiB (91.3% of 23,034) | 21,001 MiB (91.2% of 23,034) | 21,026 MiB (91.3% of 23,034) |
| Merger Agreements · GPU mem bandwidth | 70.8% mean | 75.8% mean | 80.7% mean | 74.5% mean | 73.5% mean |
| Merger Agreements · $/1k ok | $19.927040 | $16.036420 | $25.681540 | $18.641200 | $17.237700 |
| Merger Agreements · $/1k schema-valid | $19.927040 | $16.036420 | $25.681540 | $18.641200 | $17.237700 |

## Paired deltas vs `1l4-c8`

Intervals are 95% percentile bootstrap over documents; a CI containing 0 is inside the noise floor. Full table: [`SAND42-CELL-COMPARISON.md`](SAND42-CELL-COMPARISON.md).

* `1l4-c16` vs `1l4-c8` · contracts_specialist: Δ +0.005 ([-0.024, 0.038], n=50, 22/17 better/worse)
* `1l4-c16` vs `1l4-c8` · corporate_records_specialist: Δ +0.012 ([-0.000, 0.028], n=50, 5/1 better/worse)
* `1l4-c16` vs `1l4-c8` · correspondence_specialist: Δ -0.009 ([-0.026, 0.001], n=50, 2/3 better/worse)
* `1l4-c16` vs `1l4-c8` · insurance_claims_specialist: Δ -0.004 ([-0.012, 0.003], n=50, 8/10 better/worse)
* `1l4-c16` vs `1l4-c8` · merger_agreement_specialist: Δ +0.000 ([-0.015, 0.015], n=50, 8/7 better/worse)
* `2l4-c8` vs `1l4-c8` · contracts_specialist: Δ +0.025 ([-0.011, 0.063], n=50, 21/22 better/worse)
* `2l4-c8` vs `1l4-c8` · corporate_records_specialist: Δ +0.010 ([-0.010, 0.033], n=50, 4/2 better/worse)
* `2l4-c8` vs `1l4-c8` · correspondence_specialist: Δ -0.012 ([-0.029, -0.000], n=50, 1/4 better/worse)
* `2l4-c8` vs `1l4-c8` · insurance_claims_specialist: Δ -0.005 ([-0.011, -0.001], n=50, 5/11 better/worse)
* `2l4-c8` vs `1l4-c8` · merger_agreement_specialist: Δ +0.001 ([-0.012, 0.014], n=50, 6/5 better/worse)
* `2l4-c16` vs `1l4-c8` · contracts_specialist: Δ +0.006 ([-0.025, 0.039], n=50, 21/20 better/worse)
* `2l4-c16` vs `1l4-c8` · corporate_records_specialist: Δ +0.006 ([0.000, 0.012], n=50, 5/1 better/worse)
* `2l4-c16` vs `1l4-c8` · correspondence_specialist: Δ +0.002 ([-0.021, 0.026], n=50, 3/4 better/worse)
* `2l4-c16` vs `1l4-c8` · insurance_claims_specialist: Δ -0.001 ([-0.007, 0.004], n=50, 11/6 better/worse)
* `2l4-c16` vs `1l4-c8` · merger_agreement_specialist: Δ -0.002 ([-0.016, 0.011], n=50, 8/8 better/worse)
* `2l4-c32` vs `1l4-c8` · contracts_specialist: Δ +0.023 ([-0.009, 0.055], n=50, 27/16 better/worse)
* `2l4-c32` vs `1l4-c8` · corporate_records_specialist: Δ +0.018 ([-0.007, 0.045], n=50, 7/1 better/worse)
* `2l4-c32` vs `1l4-c8` · correspondence_specialist: Δ -0.015 ([-0.037, 0.001], n=50, 1/4 better/worse)
* `2l4-c32` vs `1l4-c8` · insurance_claims_specialist: Δ -0.005 ([-0.010, -0.001], n=50, 7/12 better/worse)
* `2l4-c32` vs `1l4-c8` · merger_agreement_specialist: Δ -0.006 ([-0.019, 0.004], n=50, 4/6 better/worse)

## Findings

* 1l4-c16 vs 1l4-c8 · correspondence_specialist: +28% documents/min/GPU
* 1l4-c16 vs 1l4-c8 · insurance_claims_specialist: +38% documents/min/GPU
* 1l4-c16 vs 1l4-c8 · corporate_records_specialist: +16% documents/min/GPU
* 1l4-c16 vs 1l4-c8 · contracts_specialist: +23% documents/min/GPU
* 1l4-c16 vs 1l4-c8 · merger_agreement_specialist: +14% documents/min/GPU
* 2l4-c8 vs 1l4-c8 · correspondence_specialist: -40% documents/min/GPU
* 2l4-c8 vs 1l4-c8 · insurance_claims_specialist: -38% documents/min/GPU
* 2l4-c8 vs 1l4-c8 · corporate_records_specialist: -32% documents/min/GPU
* 2l4-c8 vs 1l4-c8 · contracts_specialist: -33% documents/min/GPU
* 2l4-c8 vs 1l4-c8 · merger_agreement_specialist: -27% documents/min/GPU
* 2l4-c16 vs 1l4-c8 · correspondence_specialist: -26% documents/min/GPU
* 2l4-c16 vs 1l4-c8 · insurance_claims_specialist: -17% documents/min/GPU
* 2l4-c16 vs 1l4-c8 · corporate_records_specialist: -24% documents/min/GPU
* 2l4-c16 vs 1l4-c8 · contracts_specialist: -35% documents/min/GPU
* 2l4-c16 vs 1l4-c8 · merger_agreement_specialist: -19% documents/min/GPU
* 2l4-c32 vs 1l4-c8 · correspondence_specialist: -22% documents/min/GPU
* 2l4-c32 vs 1l4-c8 · insurance_claims_specialist: -3% documents/min/GPU
* 2l4-c32 vs 1l4-c8 · corporate_records_specialist: -10% documents/min/GPU
* 2l4-c32 vs 1l4-c8 · contracts_specialist: -33% documents/min/GPU
* 2l4-c32 vs 1l4-c8 · merger_agreement_specialist: +18% documents/min/GPU

## Cost

| Session | Metered USD | Billed USD |
| --- | ---: | ---: |
| SAND-42 | 0.0 | 0.0 |

Per-condition detail and engine/GPU telemetry: [`SAND42-MASTER-REPORT.md`](SAND42-MASTER-REPORT.md).

_Generated 2026-10-13T04:33:18+00:00 by `sandbox run card --runbook sand42`._
