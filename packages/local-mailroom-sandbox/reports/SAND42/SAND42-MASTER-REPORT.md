# SAND-042 master report — full detail

Per-condition tables, engine and GPU telemetry, the paired comparison and the method. Executive summary: [`SAND42-MASTER-SCORE-COST-CARD.md`](SAND42-MASTER-SCORE-COST-CARD.md).

# SAND-042 · 1× L4 · client concurrency 8 · n=50 × 5 specialists

**Cells reported:** 5 of 5 · **Runbook:** `sand42-1l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · L4 @ $0.80/GPU-hr

## Shared conditions

| Condition | Value |
| --- | --- |
| Engine | Qwen/Qwen3-8B-AWQ · max_model_len 32768 · max_num_seqs 16/replica · max_inputs 32 |
| Fleet | 1 replica(s) · client concurrency 8 (8 per replica) |
| Dataset | `Lucius-Morningstar/mailroom-dataset` ground_truth @ ed7576b6, split=all, seed 42, one class bucket, 50 per class stratified over every subclass (min 1 per sub-type) |
| Prompt | v1 `*_simplified` stems only |
| Output cap | max_tokens 8,192 · temperature 0.7 contracts + merger, 0.1 elsewhere |
| GPU telemetry | in-container nvidia-smi series, label `sand42-1l4-c8` |

## Per specialist

| Metric | Correspondence | Insurance Claims | Corporate Records | Contracts | Merger Agreements |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quality (95% CI) | 0.388 [0.323, 0.451] | 0.671 [0.654, 0.688] | 0.482 [0.413, 0.555] | 0.599 [0.565, 0.632] | 0.027 [0.017, 0.040] |
| Scored documents | 50 | 50 | 50 | 50 | 50 |
| Quality SD | 0.238 | 0.062 | 0.248 | 0.120 | 0.041 |
| Scoring method | suite | suite | suite | suite+cuad | suite+maud |
| Clause metric | n/a (no clause scoring) | n/a (no clause scoring) | n/a (no clause scoring) | CUAD F1 0.593 · 50 labeled | MAUD acc 2.7% · 302/811 answered |
| Ok rate (Wilson) | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] |
| Schema-valid rate | 100.0% | 32.0% | 96.0% | 100.0% | 100.0% |
| Parse errors | 0 | 0 | 0 | 0 | 0 |
| Length-capped | 0 | 0 | 0 | 0 | 0 |
| Error kinds | none | none | none | none | none |
| p50 latency (s) | 6.2 | 13.4 | 10.8 | 114.2 | 547.4 |
| p95 latency (s) | 9.3 | 22.3 | 14.5 | 671.4 | 1,370.2 |
| SLO (s) · met | 60 · yes | 60 · yes | 60 · yes | 300 · no | 1,800 · yes |
| Documents/min | 49.41 | 20.31 | 33.94 | 2.18 | 0.64 |
| Documents/min/GPU | 49.41 | 20.31 | 33.94 | 2.18 | 0.64 |
| Goodput docs/min/GPU | 49.41 | 20.31 | 33.94 | 0.00 | 0.64 |
| Tokens/s/GPU | 2,261.7 | 1,258.3 | 2,324.3 | 688.5 | 1,113.4 |
| Mean TTFT (s) | 0.66 | 0.77 | 1.20 | 2.03 | 3.77 |
| Prefix-cache hit | 63.6% | 58.4% | 50.9% | 40.9% | 19.6% |
| Wall (s) | 60.7 | 147.7 | 88.4 | 1,378.0 | 4,657.5 |
| Billed GPU $ (run) | $0.0123 | $0.0268 | $0.0185 | $0.3069 | $0.9964 |
| $ / 1k ok docs | $0.245320 | $0.536240 | $0.370180 | $6.137540 | $19.927040 |
| $ / 1k schema-valid | $0.245320 | $1.675750 | $0.385604 | $6.137540 | $19.927040 |
| $ / doc | $0.000245 | $0.000536 | $0.000370 | $0.006138 | $0.019927 |
| $ / ok doc | $0.000245 | $0.000536 | $0.000370 | $0.006138 | $0.019927 |
| $ / 1M tokens | $0.089 | $0.144 | $0.090 | $0.323 | $0.192 |
| GPU util (mean/p95/min–max) | 87.2% mean / 100.0 p95 / 0.0–100.0% min–max (n=8) | 93.2% mean / 100.0 p95 / 0.0–100.0% min–max (n=18) | 84.6% mean / 100.0 p95 / 0.0–100.0% min–max (n=14) | 97.4% mean / 100.0 p95 / 0.0–100.0% min–max (n=231) | 88.7% mean / 100.0 p95 / 0.0–100.0% min–max (n=747) |
| GPU mem used (mean) | 21,027 MiB (91.3% of 23,034) | 21,028 MiB (91.3% of 23,034) | 21,028 MiB (91.3% of 23,034) | 21,028 MiB (91.3% of 23,034) | 21,028 MiB (91.3% of 23,034) |
| GPU mem bandwidth (mean) | 59.0% mean | 82.6% mean | 69.6% mean | 90.1% mean | 70.8% mean |
| Sampling coverage | 100.0% | 99.2% | 100.0% | 99.9% | 99.9% |
| GPU power (W, mean) | 64.6 | 70.2 | 64.7 | 71.3 | 67.5 |
| GPU temp (C, mean) | 53.0 | 63.8 | 69.4 | 75.1 | 73.9 |
| KV cache use, mid-run (max %) | 6.4% | 6.5% | 10.2% | 42.1% | 49.7% |
| Queue depth, mid-run (running/waiting) | 8 running / 0 waiting | 8 running / 0 waiting | 8 running / 0 waiting | 9 running / 0 waiting | 8 running / 2 waiting |
| Preemptions | 0 | 0 | 0 | 0 | 0 |
| Length finishes | 0 | 0 | 0 | 3 | 4 |

## Cost (computed from the session)

The fleet is pinned warm (`min_containers=1`) from deploy to teardown, so Modal meters the **whole window** — the cold boot and the idle between specialists included. This is computed from the session's own timestamps, not scraped from the billing CLI (whose figures are credits-based and workspace-wide).

| Fleet cost | Value |
| --- | ---: |
| Replicas × GPU | 1 × L4 @ $0.80/GPU-hr |
| Cold boot (deploy → ready) | 122.0 s |
| Fleet window (deploy → teardown) | 6,427.0 s |
| Fleet GPU-hours | 1.7853 |
| **Fleet GPU $** | **$1.4282** |
| Of which the five runs | 6,123.7 s (95.3%) |
| Boot + idle overhead | 303.3 s |

## Per-run cards

| Specialist | Run ID | Card |
| --- | --- | --- |
| Correspondence | `sand42-50-correspondence-specialist-awq-1l4-c8` | [sand42-50-correspondence-specialist-awq-1l4-c8.card.md](1L4-c8/correspondence/sand42-50-correspondence-specialist-awq-1l4-c8.card.md) |
| Insurance Claims | `sand42-50-insurance-claims-specialist-awq-1l4-c8` | [sand42-50-insurance-claims-specialist-awq-1l4-c8.card.md](1L4-c8/insurance_claims/sand42-50-insurance-claims-specialist-awq-1l4-c8.card.md) |
| Corporate Records | `sand42-50-corporate-records-specialist-awq-1l4-c8` | [sand42-50-corporate-records-specialist-awq-1l4-c8.card.md](1L4-c8/corporate_records/sand42-50-corporate-records-specialist-awq-1l4-c8.card.md) |
| Contracts | `sand42-50-contracts-specialist-awq-1l4-c8` | [sand42-50-contracts-specialist-awq-1l4-c8.card.md](1L4-c8/contracts/sand42-50-contracts-specialist-awq-1l4-c8.card.md) |
| Merger Agreements | `sand42-50-merger-specialist-awq-1l4-c8` | [sand42-50-merger-specialist-awq-1l4-c8.card.md](1L4-c8/merger_agreement/sand42-50-merger-specialist-awq-1l4-c8.card.md) |

_Merger dominates pooled throughput (≈ 112k prompt tokens per agreement on the frozen settings), so no pooled column is reported here — compare per class._

_Generated 2026-10-13T04:33:17+00:00 by `sandbox run card --runbook sand42-1l4-c8` from the committed per-run `*.card.json`._


---

# SAND-042 · 1× L4 · client concurrency 16 · n=50 × 5 specialists

**Cells reported:** 5 of 5 · **Runbook:** `sand42-1l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · L4 @ $0.80/GPU-hr

## Shared conditions

| Condition | Value |
| --- | --- |
| Engine | Qwen/Qwen3-8B-AWQ · max_model_len 32768 · max_num_seqs 16/replica · max_inputs 32 |
| Fleet | 1 replica(s) · client concurrency 16 (16 per replica) |
| Dataset | `Lucius-Morningstar/mailroom-dataset` ground_truth @ ed7576b6, split=all, seed 42, one class bucket, 50 per class stratified over every subclass (min 1 per sub-type) |
| Prompt | v1 `*_simplified` stems only |
| Output cap | max_tokens 8,192 · temperature 0.7 contracts + merger, 0.1 elsewhere |
| GPU telemetry | in-container nvidia-smi series, label `sand42-1l4-c16` |

## Per specialist

| Metric | Correspondence | Insurance Claims | Corporate Records | Contracts | Merger Agreements |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quality (95% CI) | 0.379 [0.313, 0.448] | 0.667 [0.649, 0.686] | 0.494 [0.428, 0.561] | 0.604 [0.566, 0.641] | 0.028 [0.017, 0.039] |
| Scored documents | 50 | 50 | 50 | 50 | 50 |
| Quality SD | 0.240 | 0.067 | 0.243 | 0.134 | 0.041 |
| Scoring method | suite | suite | suite | suite+cuad | suite+maud |
| Clause metric | n/a (no clause scoring) | n/a (no clause scoring) | n/a (no clause scoring) | CUAD F1 0.614 · 50 labeled | MAUD acc 2.8% · 286/811 answered |
| Ok rate (Wilson) | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] |
| Schema-valid rate | 100.0% | 34.0% | 96.0% | 100.0% | 100.0% |
| Parse errors | 0 | 0 | 0 | 0 | 0 |
| Length-capped | 0 | 0 | 0 | 0 | 0 |
| Error kinds | none | none | none | none | none |
| p50 latency (s) | 9.6 | 21.4 | 19.5 | 167.9 | 948.7 |
| p95 latency (s) | 14.4 | 31.9 | 27.3 | 791.9 | 1,917.9 |
| SLO (s) · met | 60 · yes | 60 · yes | 60 · yes | 300 · no | 1,800 · no |
| Documents/min | 63.47 | 27.95 | 39.22 | 2.67 | 0.73 |
| Documents/min/GPU | 63.47 | 27.95 | 39.22 | 2.67 | 0.73 |
| Goodput docs/min/GPU | 63.47 | 27.95 | 39.22 | 0.00 | 0.00 |
| Tokens/s/GPU | 2,903.2 | 1,737.9 | 2,685.3 | 857.9 | 1,258.8 |
| Mean TTFT (s) | 1.53 | 1.77 | 2.41 | 3.70 | 7.25 |
| Prefix-cache hit | 63.6% | 58.4% | 50.9% | 37.7% | 12.5% |
| Wall (s) | 47.3 | 107.3 | 76.5 | 1,124.4 | 4,098.5 |
| Billed GPU $ (run) | $0.0107 | $0.0239 | $0.0171 | $0.2250 | $0.8018 |
| $ / 1k ok docs | $0.214840 | $0.477120 | $0.341420 | $4.500700 | $16.036420 |
| $ / 1k schema-valid | $0.214840 | $1.403294 | $0.355646 | $4.500700 | $16.036420 |
| $ / doc | $0.000215 | $0.000477 | $0.000341 | $0.004501 | $0.016036 |
| $ / ok doc | $0.000215 | $0.000477 | $0.000341 | $0.004501 | $0.016036 |
| $ / 1M tokens | $0.078 | $0.128 | $0.083 | $0.233 | $0.155 |
| GPU util (mean/p95/min–max) | 61.8% mean / 100.0 p95 / 0.0–100.0% min–max (n=8) | 91.6% mean / 100.0 p95 / 0.0–100.0% min–max (n=16) | 82.4% mean / 100.0 p95 / 0.0–100.0% min–max (n=12) | 97.8% mean / 100.0 p95 / 0.0–100.0% min–max (n=166) | 98.8% mean / 100.0 p95 / 0.0–100.0% min–max (n=552) |
| GPU mem used (mean) | 20,996 MiB (91.2% of 23,034) | 21,026 MiB (91.3% of 23,034) | 21,026 MiB (91.3% of 23,034) | 21,026 MiB (91.3% of 23,034) | 21,025 MiB (91.3% of 23,034) |
| GPU mem bandwidth (mean) | 44.1% mean | 80.0% mean | 53.2% mean | 86.4% mean | 75.8% mean |
| Sampling coverage | 100.0% | 100.0% | 100.0% | 100.0% | 93.1% |
| GPU power (W, mean) | 59.0 | 69.9 | 65.2 | 71.6 | 71.8 |
| GPU temp (C, mean) | 68.5 | 76.9 | 77.2 | 76.6 | 73.9 |
| KV cache use, mid-run (max %) | 8.0% | 15.1% | 21.9% | 74.8% | 95.1% |
| Queue depth, mid-run (running/waiting) | 14 running / 0 waiting | 16 running / 0 waiting | 16 running / 0 waiting | 16 running / 6 waiting | 16 running / 14 waiting |
| Preemptions | 0 | 0 | 0 | 0 | 0 |
| Length finishes | 0 | 0 | 0 | 2 | 2 |

## Cost (computed from the session)

The fleet is pinned warm (`min_containers=1`) from deploy to teardown, so Modal meters the **whole window** — the cold boot and the idle between specialists included. This is computed from the session's own timestamps, not scraped from the billing CLI (whose figures are credits-based and workspace-wide).

| Fleet cost | Value |
| --- | ---: |
| Replicas × GPU | 1 × L4 @ $0.80/GPU-hr |
| Cold boot (deploy → ready) | 146.0 s |
| Fleet window (deploy → teardown) | 5,098.0 s |
| Fleet GPU-hours | 1.4161 |
| **Fleet GPU $** | **$1.1329** |
| Of which the five runs | 4,853.4 s (95.2%) |
| Boot + idle overhead | 244.6 s |

## Per-run cards

| Specialist | Run ID | Card |
| --- | --- | --- |
| Correspondence | `sand42-50-correspondence-specialist-awq-1l4-c16` | [sand42-50-correspondence-specialist-awq-1l4-c16.card.md](1L4-c16/correspondence/sand42-50-correspondence-specialist-awq-1l4-c16.card.md) |
| Insurance Claims | `sand42-50-insurance-claims-specialist-awq-1l4-c16` | [sand42-50-insurance-claims-specialist-awq-1l4-c16.card.md](1L4-c16/insurance_claims/sand42-50-insurance-claims-specialist-awq-1l4-c16.card.md) |
| Corporate Records | `sand42-50-corporate-records-specialist-awq-1l4-c16` | [sand42-50-corporate-records-specialist-awq-1l4-c16.card.md](1L4-c16/corporate_records/sand42-50-corporate-records-specialist-awq-1l4-c16.card.md) |
| Contracts | `sand42-50-contracts-specialist-awq-1l4-c16` | [sand42-50-contracts-specialist-awq-1l4-c16.card.md](1L4-c16/contracts/sand42-50-contracts-specialist-awq-1l4-c16.card.md) |
| Merger Agreements | `sand42-50-merger-specialist-awq-1l4-c16` | [sand42-50-merger-specialist-awq-1l4-c16.card.md](1L4-c16/merger_agreement/sand42-50-merger-specialist-awq-1l4-c16.card.md) |

_Merger dominates pooled throughput (≈ 112k prompt tokens per agreement on the frozen settings), so no pooled column is reported here — compare per class._

_Generated 2026-10-13T04:33:18+00:00 by `sandbox run card --runbook sand42-1l4-c16` from the committed per-run `*.card.json`._


---

# SAND-042 · 2× L4 · client concurrency 8 (4 per replica) · n=50 × 5 specialists

**Cells reported:** 5 of 5 · **Runbook:** `sand42-2l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · L4 @ $0.80/GPU-hr

## Shared conditions

| Condition | Value |
| --- | --- |
| Engine | Qwen/Qwen3-8B-AWQ · max_model_len 32768 · max_num_seqs 16/replica · max_inputs 32 |
| Fleet | 2 replica(s) · client concurrency 8 (4 per replica) |
| Dataset | `Lucius-Morningstar/mailroom-dataset` ground_truth @ ed7576b6, split=all, seed 42, one class bucket, 50 per class stratified over every subclass (min 1 per sub-type) |
| Prompt | v1 `*_simplified` stems only |
| Output cap | max_tokens 8,192 · temperature 0.7 contracts + merger, 0.1 elsewhere |
| GPU telemetry | in-container nvidia-smi series, label `sand42-2l4-c8` |

## Per specialist

| Metric | Correspondence | Insurance Claims | Corporate Records | Contracts | Merger Agreements |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quality (95% CI) | 0.376 [0.307, 0.444] | 0.665 [0.648, 0.683] | 0.492 [0.426, 0.558] | 0.624 [0.591, 0.657] | 0.028 [0.017, 0.041] |
| Scored documents | 50 | 50 | 50 | 50 | 50 |
| Quality SD | 0.242 | 0.064 | 0.239 | 0.116 | 0.043 |
| Scoring method | suite | suite | suite | suite+cuad | suite+maud |
| Clause metric | n/a (no clause scoring) | n/a (no clause scoring) | n/a (no clause scoring) | CUAD F1 0.637 · 50 labeled | MAUD acc 2.8% · 297/811 answered |
| Ok rate (Wilson) | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] |
| Schema-valid rate | 100.0% | 28.0% | 96.0% | 100.0% | 100.0% |
| Parse errors | 0 | 0 | 0 | 0 | 0 |
| Length-capped | 0 | 0 | 0 | 0 | 0 |
| Error kinds | none | none | none | none | none |
| p50 latency (s) | 5.3 | 11.6 | 7.6 | 75.6 | 359.1 |
| p95 latency (s) | 8.3 | 18.7 | 10.8 | 413.2 | 783.9 |
| SLO (s) · met | 60 · yes | 60 · yes | 60 · yes | 300 · no | 1,800 · yes |
| Documents/min | 58.84 | 25.06 | 45.86 | 2.90 | 0.94 |
| Documents/min/GPU | 29.42 | 12.53 | 22.93 | 1.45 | 0.47 |
| Goodput docs/min/GPU | 29.42 | 12.53 | 22.93 | 0.00 | 0.47 |
| Tokens/s/GPU | 1,346.5 | 777.5 | 1,568.6 | 449.0 | 814.5 |
| Mean TTFT (s) | 0.55 | 0.62 | 0.80 | 1.64 | 3.33 |
| Prefix-cache hit | 61.7% | 57.0% | 49.7% | 37.0% | 17.6% |
| Wall (s) | 51.0 | 119.7 | 65.4 | 1,032.8 | 3,186.0 |
| Billed GPU $ (run) | $0.0229 | $0.0486 | $0.0293 | $0.4593 | $1.2841 |
| $ / 1k ok docs | $0.458920 | $0.972480 | $0.586840 | $9.185660 | $25.681540 |
| $ / 1k schema-valid | $0.458920 | $3.473143 | $0.611292 | $9.185660 | $25.681540 |
| $ / doc | $0.000459 | $0.000972 | $0.000587 | $0.009186 | $0.025682 |
| $ / ok doc | $0.000459 | $0.000972 | $0.000587 | $0.009186 | $0.025682 |
| $ / 1M tokens | $0.167 | $0.261 | $0.143 | $0.495 | $0.247 |
| GPU util (mean/p95/min–max) | 65.0% mean / 99.0 p95 / 0.0–100.0% min–max (n=15) | 85.6% mean / 100.0 p95 / 0.0–100.0% min–max (n=32) | 82.4% mean / 100.0 p95 / 0.0–100.0% min–max (n=19) | 84.7% mean / 100.0 p95 / 0.0–100.0% min–max (n=330) | 92.8% mean / 100.0 p95 / 0.0–100.0% min–max (n=913) |
| GPU mem used (mean) | 20,992 MiB (91.1% of 23,034) | 21,023 MiB (91.3% of 23,034) | 21,023 MiB (91.3% of 23,034) | 21,025 MiB (91.3% of 23,034) | 21,027 MiB (91.3% of 23,034) |
| GPU mem bandwidth (mean) | 57.8% mean | 83.0% mean | 76.2% mean | 80.1% mean | 80.7% mean |
| Sampling coverage | 100.0% | 94.7% | 100.0% | 98.9% | 99.0% |
| GPU power (W, mean) | 59.8 | 67.0 | 65.6 | 66.4 | 69.9 |
| GPU temp (C, mean) | 62.9 | 69.6 | 72.5 | 75.2 | 76.3 |
| KV cache use, mid-run (max %) | 2.8% | 7.9% | 10.2% | 29.4% | 51.1% |
| Queue depth, mid-run (running/waiting) | 4 running / 0 waiting | 4 running / 0 waiting | 5 running / 3 waiting | 7 running / 5 waiting | 8 running / 1 waiting |
| Preemptions | 0 | 0 | 0 | 0 | 0 |
| Length finishes | 0 | 0 | 0 | 5 | 12 |

## Cost (computed from the session)

The fleet is pinned warm (`min_containers=1`) from deploy to teardown, so Modal meters the **whole window** — the cold boot and the idle between specialists included. This is computed from the session's own timestamps, not scraped from the billing CLI (whose figures are credits-based and workspace-wide).

| Fleet cost | Value |
| --- | ---: |
| Replicas × GPU | 2 × L4 @ $0.80/GPU-hr |
| Cold boot (deploy → ready) | 434.0 s |
| Fleet window (deploy → teardown) | 4,731.0 s |
| Fleet GPU-hours | 2.6283 |
| **Fleet GPU $** | **$2.1027** |
| Of which the five runs | 4,149.6 s (87.7%) |
| Boot + idle overhead | 581.4 s |

## Per-run cards

| Specialist | Run ID | Card |
| --- | --- | --- |
| Correspondence | `sand42-50-correspondence-specialist-awq-2l4-c8` | [sand42-50-correspondence-specialist-awq-2l4-c8.card.md](2L4-c8/correspondence/sand42-50-correspondence-specialist-awq-2l4-c8.card.md) |
| Insurance Claims | `sand42-50-insurance-claims-specialist-awq-2l4-c8` | [sand42-50-insurance-claims-specialist-awq-2l4-c8.card.md](2L4-c8/insurance_claims/sand42-50-insurance-claims-specialist-awq-2l4-c8.card.md) |
| Corporate Records | `sand42-50-corporate-records-specialist-awq-2l4-c8` | [sand42-50-corporate-records-specialist-awq-2l4-c8.card.md](2L4-c8/corporate_records/sand42-50-corporate-records-specialist-awq-2l4-c8.card.md) |
| Contracts | `sand42-50-contracts-specialist-awq-2l4-c8` | [sand42-50-contracts-specialist-awq-2l4-c8.card.md](2L4-c8/contracts/sand42-50-contracts-specialist-awq-2l4-c8.card.md) |
| Merger Agreements | `sand42-50-merger-specialist-awq-2l4-c8` | [sand42-50-merger-specialist-awq-2l4-c8.card.md](2L4-c8/merger_agreement/sand42-50-merger-specialist-awq-2l4-c8.card.md) |

_Merger dominates pooled throughput (≈ 112k prompt tokens per agreement on the frozen settings), so no pooled column is reported here — compare per class._

_Generated 2026-10-13T04:33:18+00:00 by `sandbox run card --runbook sand42-2l4-c8` from the committed per-run `*.card.json`._


---

# SAND-042 · 2× L4 · client concurrency 16 (8 per replica) · n=50 × 5 specialists

**Cells reported:** 5 of 5 · **Runbook:** `sand42-2l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · L4 @ $0.80/GPU-hr

## Shared conditions

| Condition | Value |
| --- | --- |
| Engine | Qwen/Qwen3-8B-AWQ · max_model_len 32768 · max_num_seqs 16/replica · max_inputs 32 |
| Fleet | 2 replica(s) · client concurrency 16 (8 per replica) |
| Dataset | `Lucius-Morningstar/mailroom-dataset` ground_truth @ ed7576b6, split=all, seed 42, one class bucket, 50 per class stratified over every subclass (min 1 per sub-type) |
| Prompt | v1 `*_simplified` stems only |
| Output cap | max_tokens 8,192 · temperature 0.7 contracts + merger, 0.1 elsewhere |
| GPU telemetry | in-container nvidia-smi series, label `sand42-2l4-c16` |

## Per specialist

| Metric | Correspondence | Insurance Claims | Corporate Records | Contracts | Merger Agreements |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quality (95% CI) | 0.390 [0.323, 0.459] | 0.670 [0.652, 0.688] | 0.488 [0.417, 0.557] | 0.604 [0.572, 0.637] | 0.025 [0.016, 0.035] |
| Scored documents | 50 | 50 | 50 | 50 | 50 |
| Quality SD | 0.249 | 0.065 | 0.250 | 0.117 | 0.033 |
| Scoring method | suite | suite | suite | suite+cuad | suite+maud |
| Clause metric | n/a (no clause scoring) | n/a (no clause scoring) | n/a (no clause scoring) | CUAD F1 0.612 · 50 labeled | MAUD acc 2.6% · 280/811 answered |
| Ok rate (Wilson) | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] |
| Schema-valid rate | 100.0% | 30.0% | 96.0% | 100.0% | 100.0% |
| Parse errors | 0 | 0 | 0 | 0 | 0 |
| Length-capped | 0 | 0 | 0 | 0 | 0 |
| Error kinds | none | none | none | none | none |
| p50 latency (s) | 6.9 | 16.2 | 12.5 | 102.8 | 579.4 |
| p95 latency (s) | 13.3 | 23.6 | 25.3 | 504.7 | 1,047.8 |
| SLO (s) · met | 60 · yes | 60 · yes | 60 · yes | 300 · no | 1,800 · yes |
| Documents/min | 73.60 | 33.52 | 51.33 | 2.82 | 1.05 |
| Documents/min/GPU | 36.80 | 16.76 | 25.66 | 1.41 | 0.52 |
| Goodput docs/min/GPU | 36.80 | 16.76 | 25.66 | 0.00 | 0.52 |
| Tokens/s/GPU | 1,684.1 | 1,037.8 | 1,756.6 | 435.7 | 901.2 |
| Mean TTFT (s) | 1.30 | 1.30 | 1.63 | 3.51 | 4.39 |
| Prefix-cache hit | 62.5% | 56.9% | 49.9% | 37.4% | 17.3% |
| Wall (s) | 40.8 | 89.5 | 58.4 | 1,063.4 | 2,866.6 |
| Billed GPU $ (run) | $0.0189 | $0.0394 | $0.0264 | $0.3372 | $0.9321 |
| $ / 1k ok docs | $0.378140 | $0.787360 | $0.528320 | $6.744320 | $18.641200 |
| $ / 1k schema-valid | $0.378140 | $2.624533 | $0.550333 | $6.744320 | $18.641200 |
| $ / doc | $0.000378 | $0.000787 | $0.000528 | $0.006744 | $0.018641 |
| $ / ok doc | $0.000378 | $0.000787 | $0.000528 | $0.006744 | $0.018641 |
| $ / 1M tokens | $0.138 | $0.212 | $0.129 | $0.364 | $0.180 |
| GPU util (mean/p95/min–max) | 64.5% mean / 98.0 p95 / 0.0–100.0% min–max (n=12) | 67.4% mean / 100.0 p95 / 0.0–100.0% min–max (n=26) | 81.2% mean / 100.0 p95 / 0.0–100.0% min–max (n=17) | 90.6% mean / 100.0 p95 / 0.0–100.0% min–max (n=242) | 93.1% mean / 100.0 p95 / 0.0–100.0% min–max (n=675) |
| GPU mem used (mean) | 20,996 MiB (91.2% of 23,034) | 20,996 MiB (91.2% of 23,034) | 20,996 MiB (91.2% of 23,034) | 20,998 MiB (91.2% of 23,034) | 21,001 MiB (91.2% of 23,034) |
| GPU mem bandwidth (mean) | 62.3% mean | 61.8% mean | 65.1% mean | 84.6% mean | 74.5% mean |
| Sampling coverage | 100.0% | 100.0% | 97.9% | 98.9% | 99.6% |
| GPU power (W, mean) | 58.1 | 61.1 | 64.6 | 68.8 | 69.6 |
| GPU temp (C, mean) | 58.7 | 71.0 | 77.0 | 76.1 | 75.6 |
| KV cache use, mid-run (max %) | 4.8% | 9.4% | 17.6% | 50.1% | 90.2% |
| Queue depth, mid-run (running/waiting) | 8 running / 0 waiting | 8 running / 0 waiting | 13 running / 0 waiting | 12 running / 3 waiting | 16 running / 7 waiting |
| Preemptions | 0 | 0 | 0 | 0 | 0 |
| Length finishes | 0 | 0 | 0 | 1 | 5 |

## Cost (computed from the session)

The fleet is pinned warm (`min_containers=1`) from deploy to teardown, so Modal meters the **whole window** — the cold boot and the idle between specialists included. This is computed from the session's own timestamps, not scraped from the billing CLI (whose figures are credits-based and workspace-wide).

| Fleet cost | Value |
| --- | ---: |
| Replicas × GPU | 2 × L4 @ $0.80/GPU-hr |
| Cold boot (deploy → ready) | 146.0 s |
| Fleet window (deploy → teardown) | 3,294.0 s |
| Fleet GPU-hours | 1.8300 |
| **Fleet GPU $** | **$1.4640** |
| Of which the five runs | 3,046.4 s (92.5%) |
| Boot + idle overhead | 247.6 s |

## Per-run cards

| Specialist | Run ID | Card |
| --- | --- | --- |
| Correspondence | `sand42-50-correspondence-specialist-awq-2l4-c16` | [sand42-50-correspondence-specialist-awq-2l4-c16.card.md](2L4-c16/correspondence/sand42-50-correspondence-specialist-awq-2l4-c16.card.md) |
| Insurance Claims | `sand42-50-insurance-claims-specialist-awq-2l4-c16` | [sand42-50-insurance-claims-specialist-awq-2l4-c16.card.md](2L4-c16/insurance_claims/sand42-50-insurance-claims-specialist-awq-2l4-c16.card.md) |
| Corporate Records | `sand42-50-corporate-records-specialist-awq-2l4-c16` | [sand42-50-corporate-records-specialist-awq-2l4-c16.card.md](2L4-c16/corporate_records/sand42-50-corporate-records-specialist-awq-2l4-c16.card.md) |
| Contracts | `sand42-50-contracts-specialist-awq-2l4-c16` | [sand42-50-contracts-specialist-awq-2l4-c16.card.md](2L4-c16/contracts/sand42-50-contracts-specialist-awq-2l4-c16.card.md) |
| Merger Agreements | `sand42-50-merger-specialist-awq-2l4-c16` | [sand42-50-merger-specialist-awq-2l4-c16.card.md](2L4-c16/merger_agreement/sand42-50-merger-specialist-awq-2l4-c16.card.md) |

_Merger dominates pooled throughput (≈ 112k prompt tokens per agreement on the frozen settings), so no pooled column is reported here — compare per class._

_Generated 2026-10-13T04:33:18+00:00 by `sandbox run card --runbook sand42-2l4-c16` from the committed per-run `*.card.json`._


---

# SAND-042 · 2× L4 · client concurrency 32 (16 per replica) · n=50 × 5 specialists

**Cells reported:** 5 of 5 · **Runbook:** `sand42-2l4-c32` · **Model:** Qwen/Qwen3-8B-AWQ · L4 @ $0.80/GPU-hr

## Shared conditions

| Condition | Value |
| --- | --- |
| Engine | Qwen/Qwen3-8B-AWQ · max_model_len 32768 · max_num_seqs 16/replica · max_inputs 32 |
| Fleet | 2 replica(s) · client concurrency 32 (16 per replica) |
| Dataset | `Lucius-Morningstar/mailroom-dataset` ground_truth @ ed7576b6, split=all, seed 42, one class bucket, 50 per class stratified over every subclass (min 1 per sub-type) |
| Prompt | v1 `*_simplified` stems only |
| Output cap | max_tokens 8,192 · temperature 0.7 contracts + merger, 0.1 elsewhere |
| GPU telemetry | in-container nvidia-smi series, label `sand42-2l4-c32` |

## Per specialist

| Metric | Correspondence | Insurance Claims | Corporate Records | Contracts | Merger Agreements |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quality (95% CI) | 0.373 [0.310, 0.438] | 0.666 [0.649, 0.683] | 0.500 [0.428, 0.570] | 0.622 [0.584, 0.659] | 0.021 [0.013, 0.029] |
| Scored documents | 50 | 50 | 50 | 50 | 50 |
| Quality SD | 0.237 | 0.062 | 0.252 | 0.133 | 0.029 |
| Scoring method | suite | suite | suite | suite+cuad | suite+maud |
| Clause metric | n/a (no clause scoring) | n/a (no clause scoring) | n/a (no clause scoring) | CUAD F1 0.636 · 50 labeled | MAUD acc 2.1% · 260/811 answered |
| Ok rate (Wilson) | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] | 50/50 100.0% [0.929, 1.000] |
| Schema-valid rate | 100.0% | 30.0% | 96.0% | 100.0% | 100.0% |
| Parse errors | 0 | 0 | 0 | 0 | 0 |
| Length-capped | 0 | 0 | 0 | 0 | 0 |
| Error kinds | none | none | none | none | none |
| p50 latency (s) | 10.7 | 24.0 | 16.8 | 171.4 | 935.5 |
| p95 latency (s) | 17.9 | 40.1 | 31.5 | 592.6 | 1,491.5 |
| SLO (s) · met | 60 · yes | 60 · yes | 60 · yes | 300 · no | 1,800 · yes |
| Documents/min | 76.82 | 39.53 | 61.14 | 2.92 | 1.52 |
| Documents/min/GPU | 38.41 | 19.77 | 30.57 | 1.46 | 0.76 |
| Goodput docs/min/GPU | 38.41 | 19.77 | 30.57 | 0.00 | 0.76 |
| Tokens/s/GPU | 1,756.7 | 1,224.9 | 2,092.1 | 451.3 | 1,316.0 |
| Mean TTFT (s) | 3.04 | 4.65 | 5.09 | 7.68 | 10.32 |
| Prefix-cache hit | 61.9% | 56.4% | 49.1% | 36.9% | 17.4% |
| Wall (s) | 39.1 | 75.9 | 49.1 | 1,026.4 | 1,972.3 |
| Billed GPU $ (run) | $0.0168 | $0.0338 | $0.0217 | $0.3486 | $0.8619 |
| $ / 1k ok docs | $0.335500 | $0.676280 | $0.433140 | $6.971020 | $17.237700 |
| $ / 1k schema-valid | $0.335500 | $2.254267 | $0.451187 | $6.971020 | $17.237700 |
| $ / doc | $0.000336 | $0.000676 | $0.000433 | $0.006971 | $0.017238 |
| $ / ok doc | $0.000336 | $0.000676 | $0.000433 | $0.006971 | $0.017238 |
| $ / 1M tokens | $0.122 | $0.182 | $0.105 | $0.376 | $0.166 |
| GPU util (mean/p95/min–max) | 49.1% mean / 100.0 p95 / 0.0–100.0% min–max (n=10) | 74.8% mean / 99.0 p95 / 0.0–100.0% min–max (n=21) | 63.7% mean / 100.0 p95 / 0.0–100.0% min–max (n=14) | 86.8% mean / 100.0 p95 / 0.0–100.0% min–max (n=235) | 95.1% mean / 100.0 p95 / 0.0–100.0% min–max (n=588) |
| GPU mem used (mean) | 20,976 MiB (91.1% of 23,034) | 21,022 MiB (91.3% of 23,034) | 21,023 MiB (91.3% of 23,034) | 21,026 MiB (91.3% of 23,034) | 21,026 MiB (91.3% of 23,034) |
| GPU mem bandwidth (mean) | 42.0% mean | 71.1% mean | 46.6% mean | 80.6% mean | 73.5% mean |
| Sampling coverage | 94.4% | 81.8% ⚠ below the 90% gate (issue #128) | 100.0% | 96.9% | 99.2% |
| GPU power (W, mean) | 52.9 | 62.8 | 56.1 | 67.5 | 70.1 |
| GPU temp (C, mean) | 60.3 | 68.1 | 70.8 | 75.3 | 75.9 |
| KV cache use, mid-run (max %) | 3.6% | 10.2% | 0.0% | 64.2% | 96.3% |
| Queue depth, mid-run (running/waiting) | 5 running / 0 waiting | 7 running / 0 waiting | 0 running / 0 waiting | 16 running / 5 waiting | 16 running / 4 waiting |
| Preemptions | 0 | 0 | 0 | 0 | 0 |
| Length finishes | 0 | 0 | 0 | 5 | 4 |

## Cost (computed from the session)

The fleet is pinned warm (`min_containers=1`) from deploy to teardown, so Modal meters the **whole window** — the cold boot and the idle between specialists included. This is computed from the session's own timestamps, not scraped from the billing CLI (whose figures are credits-based and workspace-wide).

| Fleet cost | Value |
| --- | ---: |
| Replicas × GPU | 2 × L4 @ $0.80/GPU-hr |
| Cold boot (deploy → ready) | 143.0 s |
| Fleet window (deploy → teardown) | 3,227.0 s |
| Fleet GPU-hours | 1.7928 |
| **Fleet GPU $** | **$1.4342** |
| Of which the five runs | 2,886.0 s (89.4%) |
| Boot + idle overhead | 341.0 s |

## Per-run cards

| Specialist | Run ID | Card |
| --- | --- | --- |
| Correspondence | `sand42-50-correspondence-specialist-awq-2l4-c32` | [sand42-50-correspondence-specialist-awq-2l4-c32.card.md](2L4-c32/correspondence/sand42-50-correspondence-specialist-awq-2l4-c32.card.md) |
| Insurance Claims | `sand42-50-insurance-claims-specialist-awq-2l4-c32` | [sand42-50-insurance-claims-specialist-awq-2l4-c32.card.md](2L4-c32/insurance_claims/sand42-50-insurance-claims-specialist-awq-2l4-c32.card.md) |
| Corporate Records | `sand42-50-corporate-records-specialist-awq-2l4-c32` | [sand42-50-corporate-records-specialist-awq-2l4-c32.card.md](2L4-c32/corporate_records/sand42-50-corporate-records-specialist-awq-2l4-c32.card.md) |
| Contracts | `sand42-50-contracts-specialist-awq-2l4-c32` | [sand42-50-contracts-specialist-awq-2l4-c32.card.md](2L4-c32/contracts/sand42-50-contracts-specialist-awq-2l4-c32.card.md) |
| Merger Agreements | `sand42-50-merger-specialist-awq-2l4-c32` | [sand42-50-merger-specialist-awq-2l4-c32.card.md](2L4-c32/merger_agreement/sand42-50-merger-specialist-awq-2l4-c32.card.md) |

_Merger dominates pooled throughput (≈ 112k prompt tokens per agreement on the frozen settings), so no pooled column is reported here — compare per class._

_Generated 2026-10-13T04:33:18+00:00 by `sandbox run card --runbook sand42-2l4-c32` from the committed per-run `*.card.json`._


---

# SAND-042 · paired comparison across the 5 cells

All 5 cells score the **identical 250 documents** (5 specialists × 50 documents, one subclass-stratified draw per class), so every cell-to-cell delta below is **paired**: the unit of analysis is the per-document score difference. Intervals are 95% percentile bootstrap over documents; the last column is the paired n that Δ = 0.05 would need at 80% power.

Reference cell: **1l4-c8** (1×L4, client concurrency 8).

## 1l4-c16 (1× L4 · C16) vs 1l4-c8

| Class | Paired n | Δ mean | 95% CI | SD_diff | better / worse / tie | n for Δ=0.05 |
| --- | ---: | ---: | --- | ---: | --- | ---: |
| Contracts | 50 | +0.005 | [-0.024, 0.038] | 0.111 | 22 / 17 / 11 | 39 |
| Corporate Records | 50 | +0.012 | [-0.000, 0.028] | 0.055 | 5 / 1 / 44 | 10 |
| Correspondence | 50 | -0.009 | [-0.026, 0.001] | 0.051 | 2 / 3 / 45 | 9 |
| Insurance Claims | 50 | -0.004 | [-0.012, 0.003] | 0.028 | 8 / 10 / 32 | 3 |
| Merger Agreements | 50 | +0.000 | [-0.015, 0.015] | 0.054 | 8 / 7 / 35 | 9 |

## 2l4-c8 (2× L4 · C8 · 4/replica) vs 1l4-c8

| Class | Paired n | Δ mean | 95% CI | SD_diff | better / worse / tie | n for Δ=0.05 |
| --- | ---: | ---: | --- | ---: | --- | ---: |
| Contracts | 50 | +0.025 | [-0.011, 0.063] | 0.134 | 21 / 22 / 7 | 57 |
| Corporate Records | 50 | +0.010 | [-0.010, 0.033] | 0.079 | 4 / 2 / 44 | 20 |
| Correspondence | 50 | -0.012 | [-0.029, -0.000] | 0.053 | 1 / 4 / 45 | 9 |
| Insurance Claims | 50 | -0.005 | [-0.011, -0.001] | 0.018 | 5 / 11 / 34 | 2 |
| Merger Agreements | 50 | +0.001 | [-0.012, 0.014] | 0.046 | 6 / 5 / 39 | 7 |

## 2l4-c16 (2× L4 · C16 · 8/replica) vs 1l4-c8

| Class | Paired n | Δ mean | 95% CI | SD_diff | better / worse / tie | n for Δ=0.05 |
| --- | ---: | ---: | --- | ---: | --- | ---: |
| Contracts | 50 | +0.006 | [-0.025, 0.039] | 0.117 | 21 / 20 / 9 | 44 |
| Corporate Records | 50 | +0.006 | [0.000, 0.012] | 0.023 | 5 / 1 / 44 | 2 |
| Correspondence | 50 | +0.002 | [-0.021, 0.026] | 0.086 | 3 / 4 / 43 | 24 |
| Insurance Claims | 50 | -0.001 | [-0.007, 0.004] | 0.019 | 11 / 6 / 33 | 2 |
| Merger Agreements | 50 | -0.002 | [-0.016, 0.011] | 0.047 | 8 / 8 / 34 | 7 |

## 2l4-c32 (2× L4 · C32 · 16/replica) vs 1l4-c8

| Class | Paired n | Δ mean | 95% CI | SD_diff | better / worse / tie | n for Δ=0.05 |
| --- | ---: | ---: | --- | ---: | --- | ---: |
| Contracts | 50 | +0.023 | [-0.009, 0.055] | 0.119 | 27 / 16 / 7 | 45 |
| Corporate Records | 50 | +0.018 | [-0.007, 0.045] | 0.095 | 7 / 1 / 42 | 29 |
| Correspondence | 50 | -0.015 | [-0.037, 0.001] | 0.068 | 1 / 4 / 45 | 15 |
| Insurance Claims | 50 | -0.005 | [-0.010, -0.001] | 0.016 | 7 / 12 / 31 | 1 |
| Merger Agreements | 50 | -0.006 | [-0.019, 0.004] | 0.041 | 4 / 6 / 40 | 6 |

## Noise floor (run-to-run, same 50 documents)

`sand42-noisefloor-correspondence-awq-1l4-c8` re-run against `sand42-50-correspondence-specialist-awq-1l4-c8` (identical settings, identical documents):

| Metric | Value |
| --- | ---: |
| Paired documents | 50 |
| Δ mean (should be ≈ 0) | -0.003 |
| 95% CI | [-0.022, 0.016] |
| SD of the difference | 0.066 |
| better / worse / tie | 1 / 2 / 47 |
| Paired n for Δ=0.05 | 14 |
| Paired n for Δ=0.03 | 39 |

**Quote no delta smaller than this floor.** Any cell-to-cell interval that contains 0 is inside the noise floor.

_Generated 2026-10-13T04:33:20+00:00 by `sandbox run card --runbook sand42`._


---

## Figures

![Quality](figures/cmp-quality.png)
![Cost](figures/cmp-cost.png)
![Latency](figures/cmp-latency.png)
![Throughput](figures/cmp-throughput.png)
![Gpu](figures/cmp-gpu.png)

---

## Method

* Engine, prompts, decode, dataset pin and draw are identical across the 5 conditions; only the replica count and the client concurrency differ (asserted in `tests/test_sand42_grid.py`).
* Client concurrency is split equally across replicas: 2×L4 C8 → 4 per replica, 2×L4 C16 → 8 per replica, 2×L4 C32 → 16 per replica (the engine's `max_num_seqs` ceiling).
* One warm fleet per condition (`min_containers = max_containers = replicas`), five specialists chained, teardown after the fifth: one cold boot per condition.
* Quality intervals are percentile bootstraps over per-document scores; deltas are paired on the shared 250 documents; ok rates use a Wilson interval.
* GPU hardware telemetry is sampled inside the serving replica (nvidia-smi util / power / temperature / memory) and recorded per condition; vLLM `/metrics` gives the engine side (TTFT, prefix-cache hit rate, preemptions, length finishes, KV use) per replica.
* Sample sizes, the noise floor and the contracts caveat: `docs/BENCHMARK-PROGRAM.md` §3 and `docs/SAND42-EXPERIMENT-DESIGN.md` §4.

## Metric completeness

Measured from the artifacts rather than asserted — `verbatim /metrics` is the full
exporter output preserved per replica; `bandwidth` is the in-container nvidia-smi
series carrying `utilization.memory`; `mid-run KV` is a sample taken while the run was
WORKING (the before/after scrapes bracket the run and read 0 by construction); `cold
boot` is the fleet window having recorded `ready_ts`.

| Cell | verbatim /metrics | GPU mem bandwidth | mid-run KV / queue | cold boot |
| --- | ---: | ---: | ---: | ---: |
| `1l4-c8` | all | all | all | yes |
| `1l4-c16` | all | all | all | yes |
| `2l4-c8` | all | all | all | yes |
| `2l4-c16` | all | all | all | yes |
| `2l4-c32` | all | all | 4/5 | yes |

**Open coverage.** Every blank above carries its reason; a gap is never rendered as a number, and none of these blanks is a failed capture:

* `2l4-c32` — mid-run KV / queue: 1 of 5 run(s) not sampled

*Mid-run KV / queue is diagnostic telemetry, not a primary endpoint — it explains a throughput result rather than producing one, and no headline number depends on it. The primary endpoints (per-class throughput, $/1k ok documents, quality with CIs) and the verbatim engine telemetry are complete for every cell. Per-class pairing ceilings (e.g. contracts) are explained in the comparison's pairing note.*

## Open items

* The noise-floor leg (`sand42-noise-floor`) runs with the 1L4-C8 re-run (spend approved 2026-10-12), so the deltas above carry this campaign's own run-to-run floor rather than the SAND-037/39 prior, which was measured on a different draw.
* Mid-run KV / queue is unsampled for `2l4-c8` and for four of the five `2l4-c32` runs. Both are re-runnable without changing the design; the completeness table above is generated from the run store, so it cannot go stale when they land.
* Contracts at n=50 paired is marginal for Δ=0.05 and unpowered for Δ=0.03 — report as an interval, never a ranking.
* OTel *metrics* export from the container is not wired (the telemetry is an nvidia-smi series); trace spans stay opt-in via `trace.sink`.
* This grid shows the second L4 does not pay per GPU, but not whether that is a property of the L4s or of the client feeding them. The controlled test — data-parallel with a per-request feed, tensor-parallel on one endpoint, and a raised admission ceiling — is designed in [`docs/SAND42-FOLLOWUP-DESIGN.md`](../../docs/SAND42-FOLLOWUP-DESIGN.md).

_Generated 2026-10-13T04:33:18+00:00 by `sandbox run card --runbook sand42`._
