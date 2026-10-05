# SAND-032 Stage 1 — 1×L4 knob ladder (correspondence n=20, c8, same 20 docs every rung)

Gate per rung (paired on identical doc ids): ok 20/20 · mean score ≥ L0 − 0.02 · schema_valid ≥ L0 − 0.05 · $/doc (busy) not worse than the previous kept rung. L3 (fp8 KV) is pinned for 2×L4 regardless.

| rung | change | ok | score | Δ vs L0 (paired) | schema | wall s | p50 s | p95 s | tok/s | TTFT s | prefix % | boot→ready s | $/doc busy | gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l0-baseline | baseline (current AWQ posture) | 20/20 | 0.2787 | 0.0000 | 1.00 | 31.9 | 10.29 | 14.57 | 1261 | 3.07 | 59.0 | — | 0.000354 | **PASS** |
| l1-nothink | + Qwen3 thinking off | 20/20 | 0.2742 | -0.0045 | 0.95 | 26.5 | 8.03 | 11.70 | 1524 | 2.51 | 58.8 | 123 | 0.000294 | **PASS** |
| l2-marlin | + awq_marlin kernel | 20/20 | 0.2674 | -0.0112 | 0.90 | 26.4 | 8.06 | 12.74 | 1526 | 2.65 | 58.8 | 120 | 0.000294 | **REVERT** |
| l5-graphs | + CUDA graphs (eager off) | 20/20 | 0.2841 | 0.0054 | 1.00 | 18.0 | 6.41 | 10.15 | 2238 | 1.40 | 58.8 | 216 | 0.000200 | **PASS** |

![SAND-032 ladder small multiples](../figures/sand032-ladder.svg)

_The table above is the figure's table view._
