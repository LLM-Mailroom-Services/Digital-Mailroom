# SAND-032 Stage 10 — eval-environment v2 specialist prompts on Qwen3-8B-AWQ (n=75)

Prompts: `eval-environment@e5d8766` `prompts/*_specialist_v2.md` (GEPA v2, previously A/B'd at N=20 on
Qwen 3.7 Flash), copied to `config/prompts/*_v2_evalenv.txt`.

Serving: Qwen3-8B-AWQ, the frozen engine (awq_marlin, fp8 KV, thinking off, CUDA graphs, seqs16), 1×L4, c8.
Data: public HF `mailroom-dataset` @ `ed7576b` only, seed-42 single-class draws of 75. The first 50 are the
same docs as the Stage 3 production-prompt runs (nested draws), so the comparison below is **paired on 50 docs**.
Contracts are out of scope (already promoted); merger is out of scope (per user).

| class | v2 mean (75) | v2 (paired 50) | production (paired 50) | Δ paired | v2 better / worse docs | schema v2 / prod | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| correspondence | 0.3446 | 0.3419 | 0.3004 | **+0.0415** | 22 / 12 | 1.00 / 0.98 | **PROMOTE** |
| insurance_claim | 0.6675 | 0.6832 | 0.6881 | −0.0049 | 8 / 17 | 0.24 / 0.22 | HOLD |
| corporate_record | 0.4689 | 0.4479 | 0.4583 | −0.0104 | 6 / 8 | 0.94 / 0.94 | HOLD |

**Reading:**
- **Correspondence v2** is a real gain: ~10× the run-to-run noise (the Stage 3 repeat moved 0.004), better on
  22 docs and worse on 12 (sign test p ≈ 0.12), with no schema cost. It carries over from Qwen 3.7 Flash to
  Qwen3-8B-AWQ, so promote it.
- **Insurance v2** is flat on mean but loses more docs than it wins (8/17), and it does not fix the known
  schema-validity problem (0.24). Hold; the schema issue needs its own prompt fix.
- **Corporate v2** is within noise and slightly negative. Hold (no evidence of benefit on this model).

**Caveats:**
- The production-prompt baseline ran on 2×L4 c32 and v2 on 1×L4 c8. Serving topology does not change
  outputs beyond decode nondeterminism (thinking off), which the repeat run bounds at ~0.004.
- Runtime: 75 docs in 74 s (corr), 146 s (insurance), 133 s (corporate) on one L4 at c8.
  Ledger cost ≈ $0.14 for all three.

Per-run reports: `reports/{correspondence,insurance,corporate}/SAND032-S10-*-V2-REPORT.md`.
