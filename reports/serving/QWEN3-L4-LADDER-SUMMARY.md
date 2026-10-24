# SAND-032 — Qwen3-8B-AWQ on Modal L4: program summary

Public HF `Lucius-Morningstar/mailroom-dataset` @ `ed7576b` only — no partner or proprietary data;
there is no data-sharing agreement. vLLM v0.29.0, Modal profile `exios66`, app `sandbox-vllm-sand032`.
Measured Modal spend (fleet-window ledger estimate): **$2.80 of the $5.00 cap** at program close; the ledger
stood at $1.21 after stages 1–5. The fleet-window estimate under-counts Modal billing (section 7, finding 5):
reconcile against the Modal usage page.

## 1. Knob ladder (1×L4, correspondence n=20, c8, same 20 docs) — [SAND032-LADDER.md](SAND-32/SAND032-LADDER.md)

| rung | score | schema | wall s | tok/s | TTFT s | $/doc busy | gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L0 baseline AWQ | 0.2787 | 1.00 | 31.9 | 1261 | 3.07 | 0.000354 | PASS |
| L1 + thinking off | 0.2742 | 0.95 | 26.5 | 1524 | 2.51 | 0.000294 | PASS |
| L2 + awq_marlin | 0.2674 | 0.90 | 26.4 | 1526 | 2.65 | 0.000294 | REVERT (schema) |
| **L5 frozen** (+fp8 KV, seqs16, CUDA graphs) | **0.2841** | **1.00** | **18.0** | **2238** | **1.40** | **0.000200** | **PASS** |

Frozen config: AWQ-marlin, `kv_cache_dtype=fp8`, thinking off, `max_num_seqs=16`, CUDA graphs [1,2,4,8,16].
**−44% wall, −43% $/doc vs L0 at equal quality.** Cold boot rises to 216 s (graph capture), paid once per fleet.
L3/L4 were folded into L5 (user-directed); L2's schema dip did not reproduce in L5.

## 2. Scale-out (correspondence n=100, same docs)

| fleet | wall s | tok/s | p50 / p95 s | GPU $/doc | score |
| --- | --- | --- | --- | --- | --- |
| 1×L4, c8 | 95.0 | 2579 | 6.9 / 11.6 | 0.000212 | 0.2886 |
| 2×L4, c16 | **46.1** | **5308** | 5.7 / 14.4 | 0.000206 | 0.2966 |

**2.06× faster at flat $/doc** — the second replica buys latency for free. Load split 49/51, 0 preemptions.

## 3. Five-specialist sweep (2×L4, c32 = 16/replica, n=50)

| class | headline metric | value | wall s | tok/s | p50 / p95 s | GPU $/doc |
| --- | --- | --- | --- | --- | --- | --- |
| correspondence | overall extraction | 0.3004 (repeat 0.3043) | 16.0 | 7395 | 6.8 / 12.9 | 0.000144 |
| insurance_claim | overall extraction | 0.6881 (schema 0.22 — known prompt issue) | 60.7 | 3042 | 19.7 / 34.1 | 0.000541 |
| corporate_record | overall extraction | 0.4583 (schema 0.94) | 56.3 | 4692 | 28.9 / 55.1 | 0.000502 |
| contract | CUAD clause-detection F1 | 0.596 (38 labeled docs) | 234.3 | 1616 | 85.8 / 167.5 | 0.002218 |
| merger_agreement | MAUD answer accuracy | 4.0% (44/50 ok) | 342.4 | 1477 | 119.0 / 211.4 | 0.003460 |
| merger (MAUD v1 prompt) | MAUD answer accuracy | **8.5%** (clean subset 10.7%) | 442.5 | 1383 | 183.5 / 315.2 | 0.005461 |

*Correction (2026-09-28): the MAUD-prompt row's $/doc (0.005461) comes from the serving export, which also bills that run's 122.8 s cold boot; on the busy-window basis used by every other row it is **0.004275** ([run report](../SAND-32/merger/SAND032-S5-MERGER50-MAUD-REPORT.md)).*

c32 on 2×L4 cut correspondence GPU $/doc a further 30% vs c16 (0.000144 vs 0.000206).
Replica split under short bursts was uneven (35/15 on corr50) — Modal router, not vLLM.

## 4. bf16 quality arm (1×L4, 16k, correspondence n=20, same docs as the ladder)

bf16 `Qwen/Qwen3-8B` scored 0.2742 vs AWQ L5 0.2841 on the same 20 docs — **no quality case for dropping AWQ**.

## 5. Scoring fixes made during the program

- **merger_agreement:** Hub rows carry only `maud_clause_labels`; the suite field map never met them
  (F1 0 by construction). Now scored as MAUD per-question accuracy (`eval/maud_scoring.py`).
  Dataset defect: several MAUD sub-questions are collapsed under one name (e.g. No-Shop), so a clean
  single-sub-question subset is reported alongside. Fixing it belongs upstream in the dataset build.
- **contract:** Hub rows carry only `cuad_clause_labels`; now scored as CUAD category-presence F1 plus
  metadata value checks (`eval/cuad_scoring.py`). All runs were rescored offline with the current scorer.

## 6. Incident

`sand032-s6-sorter1000` (LLM sorter, 1000 train docs) was aborted at 146/1000: `run start` activated the
profile default `Qwen/Qwen3-8B` against the AWQ fleet (vLLM 404 on every request). Fleet stopped;
cost $0.083. Fix committed (activation uses the run YAML's `engine.model`); the `judge` agent remains
pinned to `Qwen/Qwen3-8B` and must be verified before any sorter rerun. Estimated rerun: ~6–9 min, ~$0.30.

## 7. Stages 6–9 (2026-09-28): sorter at scale, admission ×2, Modal routing

| run | fleet | wall s | tok/s | p50 / p95 s | quality |
| --- | --- | --- | --- | --- | --- |
| corr100 s2b | seqs16, max_inputs 32, c16 | 46.1 | 5308 | 5.7 / 14.4 | 0.2966 |
| corr100 s7 | seqs32, **max_inputs 64**, c64 | 149.4 | 1641 | 31.2 / 51.5 | — (97/100 requests on ONE replica) |
| corr100 s9 | seqs32, **max_inputs 32**, c64 | **39.0** | **6282** | 21.2 / 30.4 | 0.2872 (split 51/49) |
| insurance50 s3 → s9 | seqs16 c32 → seqs32 c64 bal. | 60.7 → 52.8 | 3042 → 3501 | 19.7 → 27.0 p50 | 0.688 → 0.682 |
| corporate50 s3 → s9 | " | 56.3 → 48.6 | 4692 → 5431 | 28.9 → 45.2 p50 | 0.458 → 0.439 |
| contracts50 s3 → s9 | " | 234.3 → 219.5 | 1616 → 1571 | 85.8 → 109.8 p50 | CUAD F1 0.596 → 0.570; 0 preemptions |
| sorter s6 (isolated) | seqs16, c32 | 1791 (458/1000 docs; own $0.80 cost guard) | 8475 | 37.0 / 530.5 | acc 0.895, macro-F1 0.864 |

**Runbook findings:**

1. **Set `max_inputs` = `max_num_seqs` per container.** Modal's router fills one container up to
   `max_inputs` before routing to the next. With max_inputs 64, it sent 97/100 requests to one L4 (3.2× slower).
   At 32 it split 51/49. This is the single largest serving lever found.
2. **Doubling admission (seqs 16→32, c32→c64) buys only 7–17% wall** on a balanced 2×L4 fleet, while p50
   latency rises (queuing). One L4 saturates at around 16 concurrent sequences for these prompts.
   - **Batch/offline:** seqs32 + max_inputs 32 + c64.
   - **Latency-sensitive:** seqs16 + max_inputs 16 + c32.
3. **fp8 KV holds 32 long contracts per replica with 0 preemptions.** KV is not the constraint on L4 at 32k.
4. **The vendored LLM sorter reads whole documents** (about a 5.4k-token prompt, long docs chunked; p50 8k, max 298k
   prompt tokens). Head-truncating sorter input is the main sorter cost lever. Errors: corporate→contract
   (recall 0.74), merger→contract (recall 0.44).
5. **The ledger (fleet-window estimate) under-counts Modal billing.** Reconcile against the usage page.

**Recommended production runbook (Qwen3-8B-AWQ, vLLM v0.29.0, Modal L4):**

- Engine: `awq_marlin`, `kv_cache_dtype=fp8`, thinking off (`enable_thinking=false`), CUDA graphs
  [1,2,4,8,16,(32)], `max_model_len` 32768, `gpu_memory_utilization` 0.90, prefix caching on.
- Fleet: 2 containers × 1 L4 (`min=max=2` while a batch runs), `max_inputs` = `max_num_seqs`, scaledown 120 s.
- Client: concurrency = replicas × `max_num_seqs`.

Ledger at close: $2.80 cumulative (fleet-window estimate).

<!-- sand032-program-figures -->
## Figures

![SAND-032 knob ladder small multiples](figures/sand032-ladder.svg)

![Correspondence n=100 wall time by fleet](figures/sand032-routing.svg)

![Wall time, seqs16 fleet vs seqs32 balanced fleet](figures/sand032-admission.svg)

![Production vs v2 prompt, paired](figures/sand032-v2-prompts.svg)

*Table views: sections 1, 2 and 7 above, and [SAND032-V2-PROMPT-PROMOTION.md](SAND-32/SAND032-V2-PROMPT-PROMOTION.md).*
