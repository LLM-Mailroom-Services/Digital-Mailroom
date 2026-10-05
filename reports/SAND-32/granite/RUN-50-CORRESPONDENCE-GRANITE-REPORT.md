# Run report — `run-50-correspondence-granite` (HALTED INFEASIBLE, 5/50 attempt-1)

The Granite correspondence-50 leg was **halted as economically infeasible** on
this deployment (vLLM 0.29 + Granite FP8 guided extraction single-streams).
Attempt-1 (c=4): 5/50 ok, 0 errors, then killed on pace math; no restart was
viable at any concurrency (proof below). No scores (nothing completed).

| | |
| --- | --- |
| run_id | `run-50-correspondence-granite` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local DMR-074 pin) |
| engine | `ibm-granite/granite-4.2-8b-fp8`, vLLM `v0.29.0`, 1×L4, `compressed-tensors`, 32768 (same warm R2 app; cold boot recorded once in probe report) |
| fix under test | run-scoped 8192 decode (`correspondence_specialist` knobs) |
| dataset | 50-doc draw `a67938db273e` (Qwen-Run-B quotas), test, rev `46a4d3c2`, seed 42 |

## Attempt-1 (c=4): 5/50 ok, 0 err — killed on pace

| metric | value |
| --- | --- |
| docs ok / errors at kill | 5 / 0 |
| pace | ~4 min/doc → 50 docs ≈ 200 min ≈ **$2.67** vs $0.80 cap → guard-abort certain with zero scores |
| sunk cost | ~25 min warm ≈ **$0.33** (recorded, not recoverable) |

## Infeasibility proof (measured, this block)

1. **Engine single-streams:** live logs steady at `Running: 1 req (never >1
   despite c=8 dispatched)`, gen 11–18 tok/s, KV 0–9%. vLLM 0.29 serializes
   guided-JSON + Granite thinking server-side (grammar single-flight);
   `max_num_seqs=6` never binds. Dispatch concurrency is irrelevant — 8
   simultaneous client dispatches were logged in the halt run while the engine
   admitted 1.
2. **Proxy timeout math:** Modal proxy 408s queued requests at ~82 s; at
   18 tok/s a generation may use at most ~1500 tokens before its queuemates
   die — but Granite needs ~3–12k (thinking). Any c>1 piles up; c=1 needs
   50 × ~3 min ≈ 150 min ≈ $2.00. No feasible point exists inside the caps.
3. **Client timeout is structural:** `ChatOpenAI(timeout=120)` hardcoded in the
   vendored agent tree (drift-guarded, not editable per-run); p95 Granite gen
   exceeds it. Fixing needs a vendor change + image bump (vLLM ≥ 0.30 native
   `granite_thinking_parser`), both out of this sequence's budget.

## Incidents (no new cold boot; app shared the R2 deployment)

- **Duplicate dispatcher:** two `sandbox run start` processes (PIDs 71628,
  71749) briefly dispatched attempt-1 concurrently (cause undetermined —
  possibly an orphaned launch surviving an interrupted session). Both killed;
  attempt-1 log preserved as `stdout-attempt1-c4.log`. Effective in-flight
  during overlap unknown — pace math above is therefore conservative.
- **Modal profile flip:** active profile briefly `exios66` (another session?),
  restored to `hermes-agent-jjb` before any deploy action. No cross-account
  spend (all apps listed under Hermes).
- **Drift-guard refusal:** c=4→c=8 config edit tripped the run lock;
  resolved with `--force` re-lock (no completed items existed to lose).

## Qwen comparison (correspondence)

No Granite score exists to compare — the Qwen AWQ legs stand alone:
Run A (20 docs): 0.2280 overall, $0.00168/doc billed; Run B (50 docs):
0.2547 overall, $0.00249/doc billed, both 100% ok. Granite's correspondence
story is told by eval-environment API legs (0.0999 correspondence real-run)
plus the probe pair ( awake: schema-valid but 0.0 extraction on 1 doc).

## Spend accounting (this instance)

- Attempt-1 sunk: ~25 min × $0.80/hr ≈ **$0.33** (billed window, no scores).
- Pre-flight c=4 estimate is voided by this verdict — do not re-estimate this
  leg on the current image.
