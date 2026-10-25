# L4 Specialist Grid (Experiments 1–4) — SCORE & COST CARDS (one block per cell)

**Source:** the 20 per-cell grid cards (`*.card.json`, schema `sandbox.grid-card/v1`, generated 2026-10-01 06:44 UTC) under `reports/SAND-37/1L4/<specialist>/` and `reports/SAND-37/2L4/<specialist>/`. Each card holds the run conditions, per-document records, vLLM `/metrics` deltas per replica and cost. Every value below is read from those files, or computed from their per-document records where marked `=`.
**Model** `Qwen/Qwen3-8B-AWQ` · **vLLM** `v0.29.0` · **GPU** NVIDIA L4 @ **$0.80/GPU-hr** · **Data** `Lucius-Morningstar/mailroom-dataset` ground_truth @ `ed7576b6`, seed 42 (n=20 ⊂ n=50 ⊂ n=100).

**Checks:** busy GPU $ = wall × replicas × $0.80 ÷ 3,600 in all 20 cards. Field-score means and MAUD accuracies match the master card to 3 dp.
**GPU hardware telemetry (utilization, power, temperature, memory) is not in any L4 card.** The Modal vLLM path scrapes only vLLM `/metrics` and does not sample nvidia-smi. Record: [`SAND37_L4_cost_record.md`](./SAND37_L4_cost_record.md).

---

## Experiment 1 · 1×L4 C8 n=20

```
== SCORE & COST CARD — grid-20-insurance-claims-specialist-awq-1l4 ==
    experiment / posture        : Experiment 1 / 1×L4 C8 n=20  (1L4/insurance_claims/grid-20-insurance-claims-specialist-awq-1l4.card.json)
    task / prompt               : insurance_claims_specialist / insurance_claims_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 6c72fe4bf896)
    input / output cap          : 13,500 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : b52b9ad6e910d3c1…
    -- reliability ---------------------------------------------
    documents ok / n            : 20 / 20   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 0.30
    -- quality -------------------------------------------------
    score (sd)                  : 0.684 (0.054)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.599 / 0.627 / 0.686 / 0.757 / 0.806  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.285  (warm container; boot billed at session level)
    busy wall (s)               : 37.793
    GPU-seconds                 : 38.078
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.008462
    busy GPU $                  : $0.008398  (includes time used by failed docs)
    idle slot time / $          : 4.2 s / $0.000930  (11% of wall)
    cost per ok document        : $0.000420  ($0.420 per 1,000)
    cost per attempted doc      : $0.000420
    cost per 1M tokens          : $0.1225
    ok docs per GPU-hour        : 1,891  =
    -- throughput ----------------------------------------------
    documents per minute        : 31.75
    tokens per second           : 1,813.5  (per GPU 1,813.5)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 60,771 / 7,765 / 68,536  (completion share 11.3%)
    tokens per ok doc           : 3,426.8
    completion p95 / max        : 496 / 968
    per doc: instr / doc / output: 2,695 / 344 / 388  (method fit, 4.24 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 13.44 / 13.18
    p95 / p99 / max (s)         : 18.97 / 23.70 = / 24.81
    min (s)                     : 9.25  =
    mean TTFT (s)               : 1.063  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 7.11  vs client concurrency 8
    occupancy                   : 0.889
    slot utilization            : 0.8893
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 20
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 61.5 %
    replica 1                   : requests 20 · TTFT 1.06 s · prefix hit 61.5% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-20-contracts-specialist-awq-1l4 ==
    experiment / posture        : Experiment 1 / 1×L4 C8 n=20  (1L4/contracts/grid-20-contracts-specialist-awq-1l4.card.json)
    task / prompt               : contracts_specialist / contracts_specialist_v33_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 704bac6c015d)
    input / output cap          : 24,000 chars / 8,192 tokens
    sampling / retries          : temp 0.7 / 2
    spec_hash                   : bab8851282caa60d…
    -- reliability ---------------------------------------------
    documents ok / n            : 19 / 20   error rate 5.0 %
    error kinds                 : LengthFinishReasonError ×1
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.631 (0.143)  metric=CUAD clause-presence F1 (labeled-doc mean)
    per-doc min / p10 / p50 / p90 / max: 0.462 / 0.485 / 0.588 / 0.792 / 1.000  =
    CUAD labeled docs           : 16 of 19 ok
    CUAD P / R / micro F1       : 0.657 / 0.548 / 0.597
    clause value accuracy       : 32/44 (73%)
    -- time ----------------------------------------------------
    cold boot (s)               : 0.421  (warm container; boot billed at session level)
    busy wall (s)               : 299.295
    GPU-seconds                 : 299.716
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.066604
    busy GPU $                  : $0.066510  (includes time used by failed docs)
    idle slot time / $          : 138.0 s / $0.030657  (46% of wall)
    cost per ok document        : $0.003501  ($3.501 per 1,000)
    cost per attempted doc      : $0.003326
    cost per 1M tokens          : $0.4289
    ok docs per GPU-hour        : 228  =
    -- throughput ----------------------------------------------
    documents per minute        : 4.01
    tokens per second           : 518.1  (per GPU 518.1)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 123,139 / 31,915 / 155,054  (completion share 20.6%)
    tokens per ok doc           : 8,160.7
    completion p95 / max        : 2,442 / 4,860
    per doc: instr / doc / output: 2,867 / 3,614 / 1,680  (method fit, 4.57 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 67.93 / 65.78
    p95 / p99 / max (s)         : 104.92 / 172.92 = / 187.84
    min (s)                     : 26.49  =
    mean TTFT (s)               : 3.137  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 5.07  vs client concurrency 8
    occupancy                   : 0.634
    slot utilization            : 0.5391
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 20
    length-capped / preemptions : 1 / 0
    prefix-cache hit rate       : 42.5 %
    replica 1                   : requests 20 · TTFT 3.14 s · prefix hit 42.5% · length 1 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-20-corporate-records-specialist-awq-1l4 ==
    experiment / posture        : Experiment 1 / 1×L4 C8 n=20  (1L4/corporate_records/grid-20-corporate-records-specialist-awq-1l4.card.json)
    task / prompt               : corporate_records_specialist / corporate_records_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 49db8ebd55c5)
    input / output cap          : 15,000 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : c13d7e794b017dd5…
    -- reliability ---------------------------------------------
    documents ok / n            : 20 / 20   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 0.95
    -- quality -------------------------------------------------
    score (sd)                  : 0.459 (0.245)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.081 / 0.154 / 0.438 / 0.808 / 0.889  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.299  (warm container; boot billed at session level)
    busy wall (s)               : 23.359
    GPU-seconds                 : 23.658
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.005257
    busy GPU $                  : $0.005191  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000260  ($0.260 per 1,000)
    cost per attempted doc      : $0.000260
    cost per 1M tokens          : $0.0515
    ok docs per GPU-hour        : 3,043  =
    -- throughput ----------------------------------------------
    documents per minute        : 51.37
    tokens per second           : 4,314.9  (per GPU 4,314.9)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 97,183 / 3,608 / 100,791  (completion share 3.6%)
    tokens per ok doc           : 5,039.6
    completion p95 / max        : 239 / 247
    per doc: instr / doc / output: 2,158 / 2,701 / 180  (method fit, 4.37 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 14.23 / 14.40
    p95 / p99 / max (s)         : 20.53 / 20.68 = / 20.71
    min (s)                     : 5.86  =
    mean TTFT (s)               : 1.841  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 12.18  vs client concurrency 8
    occupancy                   : 1.523  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.5227
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 20
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 47.2 %
    replica 1                   : requests 20 · TTFT 1.84 s · prefix hit 47.2% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-20-correspondence-specialist-awq-1l4 ==
    experiment / posture        : Experiment 1 / 1×L4 C8 n=20  (1L4/correspondence/grid-20-correspondence-specialist-awq-1l4.card.json)
    task / prompt               : correspondence_specialist / correspondence_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 0ec3314ab111)
    input / output cap          : 12,000 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : db94f6be60731e68…
    -- reliability ---------------------------------------------
    documents ok / n            : 20 / 20   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.327 (0.241)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.000 / 0.044 / 0.333 / 0.668 / 0.784  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.334  (warm container; boot billed at session level)
    busy wall (s)               : 10.051
    GPU-seconds                 : 10.385
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.002308
    busy GPU $                  : $0.002234  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000112  ($0.112 per 1,000)
    cost per attempted doc      : $0.000112
    cost per 1M tokens          : $0.0442
    ok docs per GPU-hour        : 6,933  =
    -- throughput ----------------------------------------------
    documents per minute        : 119.39
    tokens per second           : 5,028.6  (per GPU 5,028.6)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 47,832 / 2,710 / 50,542  (completion share 5.4%)
    tokens per ok doc           : 2,527.1
    completion p95 / max        : 180 / 296
    per doc: instr / doc / output: 2,199 / 193 / 136  (method fit, 4.17 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 5.63 / 5.76
    p95 / p99 / max (s)         : 7.95 / 11.43 = / 12.24
    min (s)                     : 2.62  =
    mean TTFT (s)               : 0.960  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 11.21  vs client concurrency 8
    occupancy                   : 1.401  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.4014
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 20
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 66.7 %
    replica 1                   : requests 20 · TTFT 0.96 s · prefix hit 66.7% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-20-merger-specialist-awq-1l4-rerun ==
    experiment / posture        : Experiment 1 / 1×L4 C8 n=20  (1L4/merger_agreement/grid-20-merger-specialist-awq-1l4-rerun.card.json)
    task / prompt               : merger_agreement_specialist / merger_agreement_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 7e2b12cc13df)
    input / output cap          : 30,000 chars / 8,192 tokens
    sampling / retries          : temp 0.7 / 2
    spec_hash                   : 42a52cdf5f234f07…
    -- reliability ---------------------------------------------
    documents ok / n            : 18 / 20   error rate 10.0 %
    error kinds                 : LengthFinishReasonError ×2
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.014 (0.024)  metric=MAUD micro-accuracy
    MAUD questions / answered   : 289 / 39 (coverage 13%)
    correct / precision ans.    : 4 / 0.103
    GPU $ per correct answer    : $0.0176  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.535  (warm container; boot billed at session level)
    busy wall (s)               : 316.142
    GPU-seconds                 : 316.677
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.070373
    busy GPU $                  : $0.070254  (includes time used by failed docs)
    idle slot time / $          : 194.3 s / $0.043172  (61% of wall)
    cost per ok document        : $0.003903  ($3.903 per 1,000)
    cost per attempted doc      : $0.003513
    cost per 1M tokens          : $0.3846
    ok docs per GPU-hour        : 205  =
    -- throughput ----------------------------------------------
    documents per minute        : 3.80
    tokens per second           : 577.8  (per GPU 577.8)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 167,210 / 15,448 / 182,658  (completion share 8.5%)
    tokens per ok doc           : 10,147.7
    completion p95 / max        : 1,279 / 1,661
    per doc: instr / doc / output: 2,623 / 6,667 / 858  (method fallback, 4.50 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 54.16 / 50.46
    p95 / p99 / max (s)         : 66.15 / 105.29 = / 113.31
    min (s)                     : 35.06  =
    mean TTFT (s)               : 4.890  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 4.92  vs client concurrency 8
    occupancy                   : 0.614
    slot utilization            : 0.3855
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 20
    length-capped / preemptions : 2 / 0
    prefix-cache hit rate       : 30.6 %
    replica 1                   : requests 20 · TTFT 4.89 s · prefix hit 30.6% · length 2 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

---

## Experiment 2 · 1×L4 C8 n=50

```
== SCORE & COST CARD — grid-50-insurance-claims-specialist-awq-1l4 ==
    experiment / posture        : Experiment 2 / 1×L4 C8 n=50  (1L4/insurance_claims/grid-50-insurance-claims-specialist-awq-1l4.card.json)
    task / prompt               : insurance_claims_specialist / insurance_claims_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint b53ba23fea0a)
    input / output cap          : 13,500 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : 01f8863ba2d59587…
    -- reliability ---------------------------------------------
    documents ok / n            : 50 / 50   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 0.20
    -- quality -------------------------------------------------
    score (sd)                  : 0.684 (0.069)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.581 / 0.605 / 0.682 / 0.793 / 0.806  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.322  (warm container; boot billed at session level)
    busy wall (s)               : 87.417
    GPU-seconds                 : 87.739
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.019498
    busy GPU $                  : $0.019426  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000389  ($0.389 per 1,000)
    cost per attempted doc      : $0.000389
    cost per 1M tokens          : $0.1065
    ok docs per GPU-hour        : 2,052  =
    -- throughput ----------------------------------------------
    documents per minute        : 34.32
    tokens per second           : 2,086.6  (per GPU 2,086.6)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 162,525 / 19,876 / 182,401  (completion share 10.9%)
    tokens per ok doc           : 3,648.0
    completion p95 / max        : 624 / 956
    per doc: instr / doc / output: 2,707 / 543 / 398  (method fit, 4.58 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 15.12 / 13.96
    p95 / p99 / max (s)         : 26.71 / 32.34 = / 36.73
    min (s)                     : 8.49  =
    mean TTFT (s)               : 0.997  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 8.65  vs client concurrency 8
    occupancy                   : 1.081  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.0808
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 57.9 %
    replica 1                   : requests 50 · TTFT 1.00 s · prefix hit 57.9% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-50-contracts-specialist-awq-1l4 ==
    experiment / posture        : Experiment 2 / 1×L4 C8 n=50  (1L4/contracts/grid-50-contracts-specialist-awq-1l4.card.json)
    task / prompt               : contracts_specialist / contracts_specialist_v33_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint c29633d769b5)
    input / output cap          : 24,000 chars / 8,192 tokens
    sampling / retries          : temp 0.7 / 2
    spec_hash                   : 663799cfa33002af…
    -- reliability ---------------------------------------------
    documents ok / n            : 47 / 50   error rate 6.0 %
    error kinds                 : LengthFinishReasonError ×3
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.602 (0.118)  metric=CUAD clause-presence F1 (labeled-doc mean)
    per-doc min / p10 / p50 / p90 / max: 0.343 / 0.417 / 0.615 / 0.743 / 0.800  =
    CUAD labeled docs           : 39 of 47 ok
    CUAD P / R / micro F1       : 0.624 / 0.559 / 0.590
    clause value accuracy       : 71/110 (65%)
    -- time ----------------------------------------------------
    cold boot (s)               : 0.445  (warm container; boot billed at session level)
    busy wall (s)               : 655.158
    GPU-seconds                 : 655.603
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.145690
    busy GPU $                  : $0.145591  (includes time used by failed docs)
    idle slot time / $          : 242.4 s / $0.053876  (37% of wall)
    cost per ok document        : $0.003098  ($3.098 per 1,000)
    cost per attempted doc      : $0.002912
    cost per 1M tokens          : $0.3493
    ok docs per GPU-hour        : 258  =
    -- throughput ----------------------------------------------
    documents per minute        : 4.58
    tokens per second           : 636.2  (per GPU 636.2)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 342,770 / 74,037 / 416,807  (completion share 17.8%)
    tokens per ok doc           : 8,868.2
    completion p95 / max        : 2,829 / 3,391
    per doc: instr / doc / output: 2,835 / 4,458 / 1,575  (method fit, 4.39 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 70.25 / 68.15
    p95 / p99 / max (s)         : 108.92 / 131.65 = / 134.23
    min (s)                     : 22.35  =
    mean TTFT (s)               : 1.776  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 6.52  vs client concurrency 8
    occupancy                   : 0.815
    slot utilization            : 0.6300
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 3 / 0
    prefix-cache hit rate       : 44.2 %
    replica 1                   : requests 50 · TTFT 1.78 s · prefix hit 44.2% · length 3 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-50-corporate-records-specialist-awq-1l4 ==
    experiment / posture        : Experiment 2 / 1×L4 C8 n=50  (1L4/corporate_records/grid-50-corporate-records-specialist-awq-1l4.card.json)
    task / prompt               : corporate_records_specialist / corporate_records_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint d3139c5e07c1)
    input / output cap          : 15,000 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : 95c64a5863b63278…
    -- reliability ---------------------------------------------
    documents ok / n            : 50 / 50   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 0.94
    -- quality -------------------------------------------------
    score (sd)                  : 0.449 (0.249)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.058 / 0.131 / 0.442 / 0.789 / 0.889  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.285  (warm container; boot billed at session level)
    busy wall (s)               : 71.152
    GPU-seconds                 : 71.437
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.015875
    busy GPU $                  : $0.015812  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000316  ($0.316 per 1,000)
    cost per attempted doc      : $0.000316
    cost per 1M tokens          : $0.0683
    ok docs per GPU-hour        : 2,520  =
    -- throughput ----------------------------------------------
    documents per minute        : 42.16
    tokens per second           : 3,253.9  (per GPU 3,253.9)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 223,160 / 8,360 / 231,520  (completion share 3.6%)
    tokens per ok doc           : 4,630.4
    completion p95 / max        : 237 / 247
    per doc: instr / doc / output: 2,125 / 2,338 / 167  (method fit, 4.35 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 13.12 / 13.19
    p95 / p99 / max (s)         : 19.80 / 22.09 = / 22.25
    min (s)                     : 6.23  =
    mean TTFT (s)               : 1.425  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 9.22  vs client concurrency 8
    occupancy                   : 1.152  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.1524
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 48.2 %
    replica 1                   : requests 50 · TTFT 1.42 s · prefix hit 48.2% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-50-correspondence-specialist-awq-1l4 ==
    experiment / posture        : Experiment 2 / 1×L4 C8 n=50  (1L4/correspondence/grid-50-correspondence-specialist-awq-1l4.card.json)
    task / prompt               : correspondence_specialist / correspondence_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 8e4572ae7fba)
    input / output cap          : 12,000 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : c20ff843a924966e…
    -- reliability ---------------------------------------------
    documents ok / n            : 50 / 50   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.345 (0.218)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.000 / 0.083 / 0.333 / 0.675 / 0.821  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.333  (warm container; boot billed at session level)
    busy wall (s)               : 40.559
    GPU-seconds                 : 40.892
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.009087
    busy GPU $                  : $0.009013  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000180  ($0.180 per 1,000)
    cost per attempted doc      : $0.000180
    cost per 1M tokens          : $0.0631
    ok docs per GPU-hour        : 4,402  =
    -- throughput ----------------------------------------------
    documents per minute        : 73.97
    tokens per second           : 3,522.8  (per GPU 3,522.8)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 134,797 / 8,084 / 142,881  (completion share 5.7%)
    tokens per ok doc           : 2,857.6
    completion p95 / max        : 298 / 463
    per doc: instr / doc / output: 2,181 / 515 / 162  (method fit, 3.75 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 7.28 / 6.60
    p95 / p99 / max (s)         : 11.71 / 18.72 = / 19.76
    min (s)                     : 2.98  =
    mean TTFT (s)               : 0.813  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 8.98  vs client concurrency 8
    occupancy                   : 1.122  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.1225
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 61.1 %
    replica 1                   : requests 50 · TTFT 0.81 s · prefix hit 61.1% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-50-merger-specialist-awq-1l4 ==
    experiment / posture        : Experiment 2 / 1×L4 C8 n=50  (1L4/merger_agreement/grid-50-merger-specialist-awq-1l4.card.json)
    task / prompt               : merger_agreement_specialist / merger_agreement_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 1  ($0.80/GPU-hr) · client concurrency 8
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 23c90708536e)
    input / output cap          : 30,000 chars / 8,192 tokens
    sampling / retries          : temp 0.7 / 2
    spec_hash                   : 318540cd982a6f34…
    -- reliability ---------------------------------------------
    documents ok / n            : 46 / 50   error rate 8.0 %
    error kinds                 : LengthFinishReasonError ×4
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.048 (0.049)  metric=MAUD micro-accuracy
    MAUD questions / answered   : 751 / 179 (coverage 24%)
    correct / precision ans.    : 36 / 0.201
    GPU $ per correct answer    : $0.0036  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.994  (warm container; boot billed at session level)
    busy wall (s)               : 588.411
    GPU-seconds                 : 589.405
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.130979
    busy GPU $                  : $0.130758  (includes time used by failed docs)
    idle slot time / $          : 255.6 s / $0.056809  (43% of wall)
    cost per ok document        : $0.002843  ($2.843 per 1,000)
    cost per attempted doc      : $0.002615
    cost per 1M tokens          : $0.2768
    ok docs per GPU-hour        : 281  =
    -- throughput ----------------------------------------------
    documents per minute        : 5.10
    tokens per second           : 802.8  (per GPU 802.8)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 428,281 / 44,106 / 472,387  (completion share 9.3%)
    tokens per ok doc           : 10,269.3
    completion p95 / max        : 1,798 / 2,535
    per doc: instr / doc / output: 2,644 / 6,667 / 959  (method fallback, 4.50 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 57.87 / 51.26
    p95 / p99 / max (s)         : 109.72 / 135.42 = / 146.06
    min (s)                     : 30.88  =
    mean TTFT (s)               : 2.351  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 7.27  vs client concurrency 8
    occupancy                   : 0.909
    slot utilization            : 0.5655
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 1 of 1; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 4 / 0
    prefix-cache hit rate       : 36.9 %
    replica 1                   : requests 50 · TTFT 2.35 s · prefix hit 36.9% · length 4 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

---

## Experiment 3 · 2×L4 C32 n=50

```
== SCORE & COST CARD — grid-50-insurance-claims-specialist-awq-2l4 ==
    experiment / posture        : Experiment 3 / 2×L4 C32 n=50  (2L4/insurance_claims/grid-50-insurance-claims-specialist-awq-2l4.card.json)
    task / prompt               : insurance_claims_specialist / insurance_claims_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint b53ba23fea0a)
    input / output cap          : 13,500 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : cc07eba27c6af19a…
    -- reliability ---------------------------------------------
    documents ok / n            : 50 / 50   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 0.24
    -- quality -------------------------------------------------
    score (sd)                  : 0.686 (0.068)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.542 / 0.599 / 0.687 / 0.794 / 0.806  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.326  (warm container; boot billed at session level)
    busy wall (s)               : 35.600
    GPU-seconds                 : 35.926
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.015967
    busy GPU $                  : $0.015822  (includes time used by failed docs)
    idle slot time / $          : 2.9 s / $0.001286  (8% of wall)
    cost per ok document        : $0.000316  ($0.316 per 1,000)
    cost per attempted doc      : $0.000316
    cost per 1M tokens          : $0.0867
    ok docs per GPU-hour        : 5,010  =
    -- throughput ----------------------------------------------
    documents per minute        : 84.27
    tokens per second           : 5,127.5  (per GPU 2,563.8)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 162,525 / 20,014 / 182,539  (completion share 11.0%)
    tokens per ok doc           : 3,650.8
    completion p95 / max        : 709 / 956
    per doc: instr / doc / output: 2,707 / 543 / 400  (method fit, 4.58 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 20.93 / 19.64
    p95 / p99 / max (s)         : 32.63 / 33.26 = / 33.37
    min (s)                     : 15.31  =
    mean TTFT (s)               : 3.033  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 29.40  vs client concurrency 32
    occupancy                   : 0.919
    slot utilization            : 0.9187
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 56.8 %
    replica 1                   : requests 24 · TTFT 2.41 s · prefix hit 55.1% · length 0 · preempt 0
    replica 2                   : requests 26 · TTFT 3.61 s · prefix hit 58.3% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-50-contracts-specialist-awq-2l4-rerun ==
    experiment / posture        : Experiment 3 / 2×L4 C32 n=50  (2L4/contracts/grid-50-contracts-specialist-awq-2l4-rerun.card.json)
    task / prompt               : contracts_specialist / contracts_specialist_v33_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint c29633d769b5)
    input / output cap          : 24,000 chars / 8,192 tokens
    sampling / retries          : temp 0.7 / 2
    spec_hash                   : 3b6ca5ace37de710…
    -- reliability ---------------------------------------------
    documents ok / n            : 49 / 50   error rate 2.0 %
    error kinds                 : LengthFinishReasonError ×1
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.615 (0.127)  metric=CUAD clause-presence F1 (labeled-doc mean)
    per-doc min / p10 / p50 / p90 / max: 0.273 / 0.456 / 0.628 / 0.771 / 0.857  =
    CUAD labeled docs           : 40 of 49 ok
    CUAD P / R / micro F1       : 0.703 / 0.531 / 0.605
    clause value accuracy       : 77/113 (68%)
    -- time ----------------------------------------------------
    cold boot (s)               : 0.289  (warm container; boot billed at session level)
    busy wall (s)               : 312.765
    GPU-seconds                 : 313.054
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.139135
    busy GPU $                  : $0.139007  (includes time used by failed docs)
    idle slot time / $          : 153.0 s / $0.067994  (49% of wall)
    cost per ok document        : $0.002837  ($2.837 per 1,000)
    cost per attempted doc      : $0.002780
    cost per 1M tokens          : $0.3181
    ok docs per GPU-hour        : 563  =
    -- throughput ----------------------------------------------
    documents per minute        : 9.59
    tokens per second           : 1,397.0  (per GPU 698.5)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 360,560 / 76,386 / 436,946  (completion share 17.5%)
    tokens per ok doc           : 8,917.3
    completion p95 / max        : 2,688 / 2,915
    per doc: instr / doc / output: 2,853 / 4,506 / 1,559  (method fit, 4.40 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 104.34 / 103.35
    p95 / p99 / max (s)         : 156.58 / 186.75 = / 213.62
    min (s)                     : 36.45  =
    mean TTFT (s)               : 6.938  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 17.11  vs client concurrency 32
    occupancy                   : 0.535
    slot utilization            : 0.5109
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 1 / 0
    prefix-cache hit rate       : 43.3 %
    replica 1                   : requests 27 · TTFT 8.76 s · prefix hit 42.1% · length 0 · preempt 0
    replica 2                   : requests 23 · TTFT 4.79 s · prefix hit 44.6% · length 1 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-50-corporate-records-specialist-awq-2l4 ==
    experiment / posture        : Experiment 3 / 2×L4 C32 n=50  (2L4/corporate_records/grid-50-corporate-records-specialist-awq-2l4.card.json)
    task / prompt               : corporate_records_specialist / corporate_records_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint d3139c5e07c1)
    input / output cap          : 15,000 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : ae7a4401dc43ff2f…
    -- reliability ---------------------------------------------
    documents ok / n            : 50 / 50   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 0.94
    -- quality -------------------------------------------------
    score (sd)                  : 0.452 (0.235)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.081 / 0.141 / 0.441 / 0.759 / 0.889  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.308  (warm container; boot billed at session level)
    busy wall (s)               : 21.173
    GPU-seconds                 : 21.481
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.009547
    busy GPU $                  : $0.009410  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000188  ($0.188 per 1,000)
    cost per attempted doc      : $0.000188
    cost per 1M tokens          : $0.0406
    ok docs per GPU-hour        : 8,379  =
    -- throughput ----------------------------------------------
    documents per minute        : 141.69
    tokens per second           : 10,934.4  (per GPU 5,467.2)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 223,160 / 8,354 / 231,514  (completion share 3.6%)
    tokens per ok doc           : 4,630.3
    completion p95 / max        : 233 / 247
    per doc: instr / doc / output: 2,125 / 2,338 / 167  (method fit, 4.35 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 22.44 / 24.07
    p95 / p99 / max (s)         : 34.64 / 36.09 = / 36.48
    min (s)                     : 8.30  =
    mean TTFT (s)               : 3.954  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 52.98  vs client concurrency 32
    occupancy                   : 1.656  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.6557
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 47.2 %
    replica 1                   : requests 24 · TTFT 3.68 s · prefix hit 45.5% · length 0 · preempt 0
    replica 2                   : requests 26 · TTFT 4.20 s · prefix hit 48.8% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-50-correspondence-specialist-awq-2l4 ==
    experiment / posture        : Experiment 3 / 2×L4 C32 n=50  (2L4/correspondence/grid-50-correspondence-specialist-awq-2l4.card.json)
    task / prompt               : correspondence_specialist / correspondence_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 8e4572ae7fba)
    input / output cap          : 12,000 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : a6e93f6358b9f97b…
    -- reliability ---------------------------------------------
    documents ok / n            : 50 / 50   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.334 (0.203)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.000 / 0.083 / 0.333 / 0.546 / 0.863  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.297  (warm container; boot billed at session level)
    busy wall (s)               : 13.956
    GPU-seconds                 : 14.253
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.006335
    busy GPU $                  : $0.006203  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000124  ($0.124 per 1,000)
    cost per attempted doc      : $0.000124
    cost per 1M tokens          : $0.0434
    ok docs per GPU-hour        : 12,629  =
    -- throughput ----------------------------------------------
    documents per minute        : 214.96
    tokens per second           : 10,239.5  (per GPU 5,119.8)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 134,797 / 8,106 / 142,903  (completion share 5.7%)
    tokens per ok doc           : 2,858.1
    completion p95 / max        : 296 / 443
    per doc: instr / doc / output: 2,181 / 515 / 162  (method fit, 3.75 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 11.13 / 10.73
    p95 / p99 / max (s)         : 18.46 / 22.18 = / 22.28
    min (s)                     : 3.55  =
    mean TTFT (s)               : 2.654  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 39.89  vs client concurrency 32
    occupancy                   : 1.247  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.2466
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 59.9 %
    replica 1                   : requests 24 · TTFT 2.32 s · prefix hit 57.0% · length 0 · preempt 0
    replica 2                   : requests 26 · TTFT 2.96 s · prefix hit 62.6% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — grid-50-merger-specialist-awq-2l4 ==
    experiment / posture        : Experiment 3 / 2×L4 C32 n=50  (2L4/merger_agreement/grid-50-merger-specialist-awq-2l4.card.json)
    task / prompt               : merger_agreement_specialist / merger_agreement_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 23c90708536e)
    input / output cap          : 30,000 chars / 8,192 tokens
    sampling / retries          : temp 0.7 / 2
    spec_hash                   : 0d3c431fb803d3ed…
    -- reliability ---------------------------------------------
    documents ok / n            : 46 / 50   error rate 8.0 %
    error kinds                 : LengthFinishReasonError ×4
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.035 (0.041)  metric=MAUD micro-accuracy
    MAUD questions / answered   : 747 / 174 (coverage 23%)
    correct / precision ans.    : 26 / 0.149
    GPU $ per correct answer    : $0.0058  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.407  (warm container; boot billed at session level)
    busy wall (s)               : 340.849
    GPU-seconds                 : 341.256
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.151669
    busy GPU $                  : $0.151488  (includes time used by failed docs)
    idle slot time / $          : 196.9 s / $0.087496  (58% of wall)
    cost per ok document        : $0.003293  ($3.293 per 1,000)
    cost per attempted doc      : $0.003030
    cost per 1M tokens          : $0.3196
    ok docs per GPU-hour        : 485  =
    -- throughput ----------------------------------------------
    documents per minute        : 8.80
    tokens per second           : 1,390.5  (per GPU 695.2)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 429,708 / 44,229 / 473,937  (completion share 9.3%)
    tokens per ok doc           : 10,303.0
    completion p95 / max        : 1,543 / 2,852
    per doc: instr / doc / output: 2,675 / 6,667 / 962  (method fallback, 4.50 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 100.16 / 92.49
    p95 / p99 / max (s)         : 167.23 / 192.06 = / 211.57
    min (s)                     : 40.97  =
    mean TTFT (s)               : 9.394  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 17.14  vs client concurrency 32
    occupancy                   : 0.536
    slot utilization            : 0.4224
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 50
    length-capped / preemptions : 4 / 0
    prefix-cache hit rate       : 36.1 %
    replica 1                   : requests 24 · TTFT 9.74 s · prefix hit 35.6% · length 1 · preempt 0
    replica 2                   : requests 26 · TTFT 9.07 s · prefix hit 36.6% · length 3 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

---

## Experiment 4 · 2×L4 C32 n=100

```
== SCORE & COST CARD — sand40-100-insurance-claims-specialist-awq-2l4 ==
    experiment / posture        : Experiment 4 / 2×L4 C32 n=100  (2L4/insurance_claims/sand40-100-insurance-claims-specialist-awq-2l4.card.json)
    task / prompt               : insurance_claims_specialist / insurance_claims_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint d78a97b685ab)
    input / output cap          : 13,500 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : a21e118a35b8a790…
    -- reliability ---------------------------------------------
    documents ok / n            : 100 / 100   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 0.23
    -- quality -------------------------------------------------
    score (sd)                  : 0.672 (0.064)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.580 / 0.601 / 0.649 / 0.791 / 0.806  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.289  (warm container; boot billed at session level)
    busy wall (s)               : 81.502
    GPU-seconds                 : 81.791
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.036352
    busy GPU $                  : $0.036223  (includes time used by failed docs)
    idle slot time / $          : 12.6 s / $0.005584  (15% of wall)
    cost per ok document        : $0.000362  ($0.362 per 1,000)
    cost per attempted doc      : $0.000362
    cost per 1M tokens          : $0.0982
    ok docs per GPU-hour        : 4,401  =
    -- throughput ----------------------------------------------
    documents per minute        : 73.62
    tokens per second           : 4,525.6  (per GPU 2,262.8)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 327,213 / 41,631 / 368,844  (completion share 11.3%)
    tokens per ok doc           : 3,688.4
    completion p95 / max        : 697 / 1,683
    per doc: instr / doc / output: 2,702 / 570 / 416  (method fit, 4.46 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 22.06 / 20.42
    p95 / p99 / max (s)         : 38.45 / 55.07 = / 58.46
    min (s)                     : 12.10  =
    mean TTFT (s)               : 2.757  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 27.07  vs client concurrency 32
    occupancy                   : 0.846
    slot utilization            : 0.8458
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 100
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 40.4 %
    replica 1                   : requests 48 · TTFT 2.25 s · prefix hit 40.2% · length 0 · preempt 0
    replica 2                   : requests 52 · TTFT 3.23 s · prefix hit 40.6% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — sand40-100-contracts-specialist-awq-2l4 ==
    experiment / posture        : Experiment 4 / 2×L4 C32 n=100  (2L4/contracts/sand40-100-contracts-specialist-awq-2l4.card.json)
    task / prompt               : contracts_specialist / contracts_specialist_v33_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 6d82d7d13fa4)
    input / output cap          : 24,000 chars / 8,192 tokens
    sampling / retries          : temp 0.7 / 2
    spec_hash                   : 1ce35cb08739b9a3…
    -- reliability ---------------------------------------------
    documents ok / n            : 99 / 100   error rate 1.0 %
    error kinds                 : LengthFinishReasonError ×1
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.612 (0.127)  metric=CUAD clause-presence F1 (labeled-doc mean)
    per-doc min / p10 / p50 / p90 / max: 0.240 / 0.444 / 0.618 / 0.800 / 0.889  =
    CUAD labeled docs           : 82 of 99 ok
    CUAD P / R / micro F1       : 0.684 / 0.548 / 0.608
    clause value accuracy       : 156/237 (66%)
    -- time ----------------------------------------------------
    cold boot (s)               : 0.300  (warm container; boot billed at session level)
    busy wall (s)               : 460.624
    GPU-seconds                 : 460.924
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.204855
    busy GPU $                  : $0.204722  (includes time used by failed docs)
    idle slot time / $          : 148.3 s / $0.065905  (32% of wall)
    cost per ok document        : $0.002068  ($2.068 per 1,000)
    cost per attempted doc      : $0.002047
    cost per 1M tokens          : $0.2397
    ok docs per GPU-hour        : 773  =
    -- throughput ----------------------------------------------
    documents per minute        : 13.03
    tokens per second           : 1,853.9  (per GPU 927.0)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 707,289 / 146,665 / 853,954  (completion share 17.2%)
    tokens per ok doc           : 8,625.8
    completion p95 / max        : 2,226 / 3,235
    per doc: instr / doc / output: 2,916 / 4,229 / 1,481  (method fit, 4.58 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 100.96 / 96.14
    p95 / p99 / max (s)         : 159.27 / 197.77 = / 203.95
    min (s)                     : 40.59  =
    mean TTFT (s)               : 4.425  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 22.25  vs client concurrency 32
    occupancy                   : 0.695
    slot utilization            : 0.6781
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 100
    length-capped / preemptions : 1 / 0
    prefix-cache hit rate       : 39.6 %
    replica 1                   : requests 47 · TTFT 3.22 s · prefix hit 38.9% · length 0 · preempt 0
    replica 2                   : requests 53 · TTFT 5.49 s · prefix hit 40.3% · length 1 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — sand40-100-corporate-records-specialist-awq-2l4 ==
    experiment / posture        : Experiment 4 / 2×L4 C32 n=100  (2L4/corporate_records/sand40-100-corporate-records-specialist-awq-2l4.card.json)
    task / prompt               : corporate_records_specialist / corporate_records_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 76d8a17658f7)
    input / output cap          : 15,000 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : 770b562a3fd86f6c…
    -- reliability ---------------------------------------------
    documents ok / n            : 100 / 100   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 0.97
    -- quality -------------------------------------------------
    score (sd)                  : 0.475 (0.246)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.081 / 0.145 / 0.462 / 0.795 / 0.889  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.333  (warm container; boot billed at session level)
    busy wall (s)               : 48.108
    GPU-seconds                 : 48.441
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.021529
    busy GPU $                  : $0.021381  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000214  ($0.214 per 1,000)
    cost per attempted doc      : $0.000214
    cost per 1M tokens          : $0.0488
    ok docs per GPU-hour        : 7,432  =
    -- throughput ----------------------------------------------
    documents per minute        : 124.72
    tokens per second           : 9,098.8  (per GPU 4,549.4)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 421,101 / 16,622 / 437,723  (completion share 3.8%)
    tokens per ok doc           : 4,377.2
    completion p95 / max        : 233 / 250
    per doc: instr / doc / output: 2,110 / 2,101 / 166  (method fit, 4.40 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 20.52 / 19.92
    p95 / p99 / max (s)         : 31.77 / 36.26 = / 40.40
    min (s)                     : 7.41  =
    mean TTFT (s)               : 3.148  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 42.65  vs client concurrency 32
    occupancy                   : 1.333  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.3327
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 100
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 39.6 %
    replica 1                   : requests 49 · TTFT 2.59 s · prefix hit 39.2% · length 0 · preempt 0
    replica 2                   : requests 51 · TTFT 3.68 s · prefix hit 39.9% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — sand40-100-correspondence-specialist-awq-2l4 ==
    experiment / posture        : Experiment 4 / 2×L4 C32 n=100  (2L4/correspondence/sand40-100-correspondence-specialist-awq-2l4.card.json)
    task / prompt               : correspondence_specialist / correspondence_specialist_simplified
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 046a2c9bfc4e)
    input / output cap          : 12,000 chars / 8,192 tokens
    sampling / retries          : temp 0.1 / 2
    spec_hash                   : 9aabe1bcab7b2cf3…
    -- reliability ---------------------------------------------
    documents ok / n            : 100 / 100   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.341 (0.188)  metric=field extraction score vs ground truth
    per-doc min / p10 / p50 / p90 / max: 0.000 / 0.083 / 0.333 / 0.543 / 0.815  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.631  (warm container; boot billed at session level)
    busy wall (s)               : 27.519
    GPU-seconds                 : 28.150
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.012511
    busy GPU $                  : $0.012231  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.000122  ($0.122 per 1,000)
    cost per attempted doc      : $0.000122
    cost per 1M tokens          : $0.0416
    ok docs per GPU-hour        : 12,789  =
    -- throughput ----------------------------------------------
    documents per minute        : 218.03
    tokens per second           : 10,686.3  (per GPU 5,343.1)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 277,062 / 17,014 / 294,076  (completion share 5.8%)
    tokens per ok doc           : 2,940.8
    completion p95 / max        : 269 / 621
    per doc: instr / doc / output: 2,193 / 578 / 170  (method fit, 3.89 chars/token)
    model calls per ok doc      : 1.00  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 11.52 / 10.30
    p95 / p99 / max (s)         : 20.29 / 31.59 = / 37.86
    min (s)                     : 4.49  =
    mean TTFT (s)               : 2.648  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 41.88  vs client concurrency 32
    occupancy                   : 1.309  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.3086
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 100
    length-capped / preemptions : 0 / 0
    prefix-cache hit rate       : 34.8 %
    replica 1                   : requests 52 · TTFT 2.80 s · prefix hit 34.5% · length 0 · preempt 0
    replica 2                   : requests 48 · TTFT 2.49 s · prefix hit 35.1% · length 0 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

```
== SCORE & COST CARD — sand40-50-merger-specialist-awq-2l4 † ==
    experiment / posture        : Experiment 4 / 2×L4 C32 n=100 (merger cell n=50, same agreements as Experiment 3)  (2L4/merger_agreement/sand40-50-merger-specialist-awq-2l4.card.json)
    task / prompt               : merger_agreement_specialist / merger_agreement_specialist_maud_v1
    model / image               : Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · modal app sandbox-vllm
    gpu / replicas              : L4 x 2  ($0.80/GPU-hr) · client concurrency 32
    engine                      : awq_marlin · kv fp8 · max_num_seqs 16 · max_model_len 32,768 · CUDA graphs True · prefix cache True · thinking False
    dataset                     : Lucius-Morningstar/mailroom-dataset/ground_truth @ ed7576b6, seed 42  (fingerprint 23c90708536e)
    input / output cap          : 54,000 chars / 6,144 tokens
    sampling / retries          : temp 0.7, top_p 0.8, top_k 20, presence_penalty 1.0; chunk 47,000 + overlap 6,500 chars; length re-samples 1 / 2
    spec_hash                   : 9200d91b723c264b…
    -- reliability ---------------------------------------------
    documents ok / n            : 50 / 50   error rate 0.0 %
    error kinds                 : none
    parse errors                : 0
    schema-valid rate           : 1.00
    -- quality -------------------------------------------------
    score (sd)                  : 0.140 (0.090)  metric=MAUD micro-accuracy
    MAUD questions / answered   : 817 / 561 (coverage 69%)
    correct / precision ans.    : 114 / 0.203
    GPU $ per correct answer    : $0.0065  =
    -- time ----------------------------------------------------
    cold boot (s)               : 0.345  (warm container; boot billed at session level)
    busy wall (s)               : 1,658.838
    GPU-seconds                 : 1,659.183
    -- cost ----------------------------------------------------
    billed GPU $ (wall + boot)  : $0.737415
    busy GPU $                  : $0.737261  (includes time used by failed docs)
    idle slot time / $          : 0.0 s / $0  (0% of wall)
    cost per ok document        : $0.014745  ($14.745 per 1,000)
    cost per attempted doc      : $0.014745
    cost per 1M tokens          : $0.1313
    ok docs per GPU-hour        : 108  =
    -- throughput ----------------------------------------------
    documents per minute        : 1.81
    tokens per second           : 3,383.7  (per GPU 1,691.8)
    -- tokens (ok docs) ----------------------------------------
    prompt / completion / total : 5,334,445 / 278,545 / 5,612,990  (completion share 5.0%)
    tokens per ok doc           : 112,259.8
    completion p95 / max        : 8,012 / 13,241
    per doc: instr / doc / output: 19,669 / 87,019 / 5,571  (method fallback, 4.50 chars/token)
    model calls per ok doc      : 7.92  =
    -- latency (ok docs, e2e) ----------------------------------
    mean / p50 (s)              : 1,120.40 / 1,044.40
    p95 / p99 / max (s)         : 2,067.44 / 2,194.20 = / 2,264.44
    min (s)                     : 309.80  =
    mean TTFT (s)               : 10.815  (vLLM /metrics, request-weighted over replicas)
    -- concurrency ---------------------------------------------
    parallelism (Σlatency/wall) : 33.77  vs client concurrency 32
    occupancy                   : 1.055  (>1: summed per-doc latency exceeds client slots; see record §7)
    slot utilization            : 1.0553
    -- engine telemetry (vLLM /metrics delta) ------------------
    coverage                    : replicas observed: 2 of 2; scrape errors 0
    requests (Σ replicas)       : 418  (8.36 per doc)
    length-capped / preemptions : 23 / 8
    prefix-cache hit rate       : 28.2 %
    replica 1                   : requests 199 · TTFT 12.72 s · prefix hit 27.6% · length 14 · preempt 8
    replica 2                   : requests 219 · TTFT 9.09 s · prefix hit 28.8% · length 9 · preempt 0
    -- not captured on the L4 path -----------------------------
    GPU hardware                : utilization, power draw, temperature, memory used (nvidia-smi not sampled)
    kv_cache_usage_perc         : 0.0 (gauge read after the run drains; not a utilization figure)
    TTFT percentiles            : only the mean (histogram sum/count) is kept
```

---
