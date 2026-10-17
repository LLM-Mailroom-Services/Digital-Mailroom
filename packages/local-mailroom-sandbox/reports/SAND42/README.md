# SAND-042 — paired concurrency × fleet grid

Four cells = **{1×L4, 2×L4} × {client concurrency 8, 16}**. Each cell is one warm fleet
(one cold boot per cell), five specialists chained at **n = 50** each, all five on the
**same subclass-stratified 50-document draw**, so every cell scores the identical 250
documents and every cell-to-cell delta is paired.

**Design, metric contract, sample-size maths and acceptance rules:**
[`docs/SAND42-EXPERIMENT-DESIGN.md`](../../docs/SAND42-EXPERIMENT-DESIGN.md).

## Cells

| Cell | Runbook | Replicas | Client concurrency | Per replica | min=max containers |
| --- | --- | ---: | ---: | ---: | --- |
| `1l4-c8` | `sandbox runbook show sand42-1l4-c8` | 1 | 8 | 8 | 1 |
| `1l4-c16` | `sandbox runbook show sand42-1l4-c16` | 1 | 16 | 16 | 1 |
| `2l4-c8` | `sandbox runbook show sand42-2l4-c8` | 2 | 8 | 4 | 2 |
| `2l4-c16` | `sandbox runbook show sand42-2l4-c16` | 2 | 16 | 8 | 2 |

Client concurrency is split equally across replicas. The one **matched per-replica-load**
pair is `1l4-c8` vs `2l4-c16` (8 per replica each) — that pair isolates replica count.
`1l4-c8` vs `1l4-c16` isolates concurrency at fixed GPUs.

## What each cell runs

Five specialists, `n = 50` each, on the SAND-037 aligned spec unchanged — frozen L5 engine
(awq_marlin, fp8 KV, CUDA graphs, `max_num_seqs` 16/replica, thinking off, `max_inputs` 32),
**v1 `*_simplified` prompts only**, decode 8192, temperature 0.7 on contracts and merger
(JSON-schema grammar) and 0.1 elsewhere.

The draw is one class bucket per specialist, stratified over **every subclass** of that class
(proportional, minimum 1 per sub-type): correspondence 8 sub-types, insurance claims 6,
corporate records 10, contracts 26, merger agreements 5.

## GPU + engine telemetry

Every run carries:

* the **vLLM `/metrics`** before/after deltas (TTFT, prefix-cache hit rate, preemptions,
  length finishes, KV-cache use) — per replica;
* the **SAND-042 in-container nvidia-smi series** (utilization mean/min/max/peak, power draw,
  temperature, memory used) — sampled inside the serving replica every 5 s for the whole cell,
  written to the `sandbox-vllm-telemetry` Modal volume under the cell label, pulled by
  `sandbox run scrape-metrics`, and recorded on the card as `engine_telemetry.gpu`.

Modal allows exactly one `@modal.web_server` per function, so this is a volume series rather
than a second HTTP port. Absent telemetry says "not captured" with a reason, never a zero.

## Reports

One folder per **experimental condition**, each with one folder per **specialist**; master
cost card and master full report at the root.

```
reports/SAND42/
├── SAND42-MASTER-SCORE-COST-CARD.md + .json     master cost card    (sandbox run card --runbook sand42)
├── SAND42-MASTER-REPORT.md                      master full report  (same command)
├── SAND42-CELL-COMPARISON.md + .json            paired Δ + bootstrap CI across the four conditions
├── SAND42-NOISE-FLOOR.md                        run-to-run floor memo
├── metered-costs.json                           --record-metered SAND-42 <metered> <billed>
├── 1L4-c8/
│   ├── SAND42-1L4-C8-SCORE-COST-CARD.md + .json      condition card  (--runbook sand42-1l4-c8)
│   └── <specialist>/<run_id>.card.md + .card.json    per-run card    (--config <cfg>)
├── 1L4-c16/ … 2L4-c8/ … 2L4-c16/                     same shape per condition
```

Specialist folders: `correspondence`, `insurance_claims`, `corporate_records`, `contracts`,
`merger_agreement`. SAND-042 writes its own tree; the SAND-37/39/40 tree is untouched.

The condition card carries the scorecard groups from `docs/BENCHMARK-PROGRAM.md` §5.2: quality with
a bootstrap 95% CI, reliability (Wilson ok rate, schema-valid rate, length-capped share),
document goodput at the class SLO, `$`/1k ok documents and `$`/1k **schema-valid** documents,
engine + GPU telemetry.

## Before you spend

```bash
sandbox runbook check
sandbox run benchmark-check --config config/runs/sand42-50-correspondence-specialist-awq-1l4-c8.yaml
sandbox datasets pull
sandbox run preflight --config config/runs/sand42-50-contracts-specialist-awq-1l4-c8.yaml --live
set -a; eval "$(sandbox run deploy-env --config config/runs/sand42-50-contracts-specialist-awq-1l4-c8.yaml)"; set +a
```

Cost caps per cell sum to **$3.70** on 1×L4 and **$5.40** on 2×L4 — abort guards, not
estimates. Estimates: ≈ 30–45 min warm on one L4 per cell, ≈ 20–35 min on two.

`sand42-noise-floor` is **blocked** until spend is approved separately: it only measures the
run-to-run noise floor, and until it runs the SAND-037/39 floor in
`docs/BENCHMARK-PROGRAM.md` §3 is a prior measured on a *different* draw.

**No SAND-042 delta is real until it clears the noise floor and its interval excludes 0.**
