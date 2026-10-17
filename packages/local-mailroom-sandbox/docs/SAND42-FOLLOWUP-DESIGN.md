# SAND-042 follow-up — the feed-controlled scale-out experiment (proposed: SAND-048)

The five-cell grid answered *whether* the second L4 pays. It did not answer **why not**, beyond
showing the mechanism is client-side. This design turns that diagnosis into a controlled test: hold
the engine, the draw, the prompts and the workload fixed and vary **only how work reaches two GPUs**.

Everything here assumes the capture contract the grid ended with — verbatim vLLM `/metrics` at
**before / mid / after** per replica, the mid-run series, the in-container nvidia-smi series
(including memory bandwidth), the run store, the fleet window with `ready_ts`, and the cards that
report them. The mid-run label is the load-bearing addition: without it the primary response
variable of this experiment is structurally zero (see §4).

---

## 1. What the grid left unanswered

| # | Question | What we measured | What is still unknown |
| --- | --- | --- | --- |
| Q1 | Scaling out rotates *fleet total* up (+10 %…+108 %) but *per-GPU* down (−23 %…−45 %, except the merger at +3.9 %). Is that the hardware, or the feed? | The loaded replica sits at 16 running (the `max_num_seqs` ceiling) with 8–10 queued while the other runs 6–8 with 0 waiting, KV ≈ 35 %. The second GPU is idle *because work does not reach it*. | Whether a controlled feed restores per-GPU parity — i.e. whether "the second L4 does not pay" is a property of L4s or of this client. |
| Q2 | At C32, is the ceiling admission or the client? | 32 total = 16/replica = exactly `max_num_seqs`, and the engine queues (10 waiting). | Whether raising `max_num_seqs` at the same total concurrency moves throughput — the admission-vs-feed discriminator. |
| Q3 | The merger is the only class where the second GPU pays, and the only class that hit KV 99 %. Is its gain compute/bandwidth, or KV capacity? | +3.9 % per GPU, KV max 99.0 %, 16 running / 10 queued. | DP gives 2× KV capacity but one GPU per request; TP gives both GPUs' compute + bandwidth to every request but a sharded (similar total) cache. The two hypotheses predict *opposite* winners. |
| Q4 | Is the 1L4-vs-2L4 matched-load contrast complete? | Yes — 1L4-C8 vs 2L4-C16 (8/replica) and 1L4-C16 vs 2L4-C32 (16/replica). | Nothing. This is the grid's strongest result and needs no follow-up. |
| Q5 | Why is the *routing* sticky at all? | The skew always favours the earlier-started replica, and grows with concurrency (C8 ≈ 50/50 → C32 78/22). | Whether it is connection reuse (the OpenAI SDK's default httpx pool, no `http_client` override) or Modal's own routing. Arms B and C separate these. |

## 2. Design

One draw (the same subclass-stratified 250 documents), the SAND-037 aligned engine, v1 `*_simplified`
stems, n = 50 per class, five specialists chained on one warm fleet per arm. **The only thing that
varies is the path from client to GPU(s).**

| Arm | Posture | GPUs | Containers | Client concurrency | Isolates |
| --- | --- | --- | --- | --- | --- |
| **A** | 2×L4 data-parallel, single endpoint, keep-alive client | 2 | 2 × 1 | 32 | **Control** — reproduces `2l4-c32`; provides this campaign's own run-to-run reference |
| **B** | as A, but one connection per request (`Connection: close`, or a least-connections proxy in front) | 2 | 2 × 1 | 32 | **Routing** (Q1, Q5) |
| **C** | 2×L4 **tensor-parallel**, one container spanning both GPUs | 2 | 1 × 2 | 32 | **No distribution at all** (Q1, Q3) |
| **D** | as A, but `max_num_seqs = 32`/replica | 2 | 2 × 1 | 32 **and** 64 | **Admission** (Q2) |

Arm C is a one-variable change from A: `MODAL_VLLM_GPU=L4:2` makes `deploy/modal_vllm.py` derive
`TP_SIZE=2` (`deploy/modal_vllm.py:151`), with `min_containers = max_containers = 1`.

Arm B's connection change belongs in the vendored client (`vendor/llm-mailroom/src/llm/client.py`
builds `OpenAI(**kwargs)` with no `http_client`, so the SDK's default pooled keep-alive applies) and
therefore travels through the family repo + `scripts/sync_vendor.py`, never as a vendor-tree edit
(DMR-074). A proxy-fronted variant avoids the dependency: point the client at a least-connections
proxy (the sandbox already ships a gateway, `sandbox pipeline api`) and leave the client untouched.

## 3. Pre-registered hypotheses and decisions

| # | Hypothesis | Falsified if |
| --- | --- | --- |
| H1 | B and/or C restore per-GPU throughput to **≥ 0.85 ×** the 1-GPU twin at the same per-replica load — i.e. the second GPU starts to pay | either arm stays below **0.70 ×** |
| H2 | If the residual deficit is routing, **B ≈ C**; if it is engine-side, **C > B** | — (this is a discriminator, not a bet) |
| H3 | For the merger: **C > B** ⇒ its gain is compute/memory-bandwidth; **B > C** ⇒ it is KV capacity | both within the noise floor ⇒ neither explains it |
| H4 | **D(32/replica) − C32** exceeds the measured noise floor ⇒ admission was binding at C32 | the difference sits inside the noise floor ⇒ the client was binding |

H1 is the one that matters for the paper: it decides whether "the second L4 does not pay below C32"
is a statement about **L4s** or about **this client's feed**. As it stands the grid cannot tell them
apart, and a reviewer is entitled to say so.

## 4. Measurement contract (why full coverage is a precondition, not a nicety)

Every arm runs the runbook's `midrun_metrics` step, so each run carries:

- `vllm_metrics_{before,mid,after}.{json,txt}` — the verbatim exporter output per replica; the mid
  pass is the only one that sees live gauges;
- `vllm_metrics_mid.series.jsonl` — every mid sample, from which the card reports the run's maximum
  (`kv_cache_usage_perc`, `num_requests_running`, `num_requests_waiting`);
- `container_telemetry_{after,mid}.json` — nvidia-smi util / memory / temperature / power /
  **memory bandwidth** / SM clock, per replica;
- the run store, the fleet window (`ready_ts`), the per-run + cell cards and the master.

The primary response variable is the **per-replica `num_requests_running` split over the run**, which
is exactly the quantity that was 0 by construction in every before/after scrape of the original grid.
Getting the split wrong is how the original campaign concluded "the engine never backs up" while the
engine was in fact queueing.

## 5. Cost, wall clock, and guards

| | |
| --- | --- |
| Arms | 4 (A–D), one warm fleet each, five specialists chained |
| Wall | ~80–95 min per arm ⇒ **~6 h** sequential |
| Measured anchor | `2l4-c32` cost **$1.78 metered** for the full cell (5 runs, 2 GPUs) |
| Estimate | **≈ $8 all-in** (D's second load level adds one extra pass) |
| Guards | per-run `cost_cap_usd` (2-replica row, $6.20/arm ceiling), `max_wall_seconds`, the completion-watch winddown, one app name at a time |

Run order: **A first** (the control, and the campaign's own noise reference), then B, C, D. If spend
must be cut, drop D: H1 (the paper-relevant claim) is decided by A vs B vs C alone.

## 6. What this buys

- A yes/no on whether scale-out *can* pay on two L4s, which the current grid can only answer as
  "not with this client".
- A prescription rather than a diagnosis for anyone running DP behind a single Modal endpoint.
- For the merger — the one profitable class — a mechanism (compute vs capacity) instead of a number.
- Every finding measured under the full capture contract, so no column needs a "not measured"
  caveat in its own report.
