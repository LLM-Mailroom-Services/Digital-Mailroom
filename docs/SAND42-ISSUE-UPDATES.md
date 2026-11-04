# SAND-042 issue updates — paste-ready

This session has **no GitHub tooling** (`tools.github.*` is absent from the tool catalog), so these
are written here to be pasted into the issues. Each block is self-contained; the ledger in §1 is
generated from the repository by `sand42_cards.metric_completeness()` and reproduced in
`reports/SAND42/SAND42-MASTER-REPORT.md` § *Metric completeness*, so it cannot drift from the data.

---

## §1 → paste as a comment on issue **#129** (SAND-042 remaining runbook legs)

**Metric-coverage ledger — update 2026-10-12**

The 2L4-C32 saturation cell has **landed and is published** (`81d1b1c`): 5/5 specialists, 0 errors,
both replicas scraped, completion-watch `[21 ok / 1 note / 0 gaps]`, **0 tasks billing**, **$1.78
metered** against a $6.20 cap. It supplies the fifth master section and the fifth comparison column.

Its headline result, per class against its matched-load 1-GPU twin (`1l4-c16`, 16 per replica on one
L4): correspondence **−39.5 %**, insurance **−29.2 %**, corporate **−22.9 %**, contracts **−45.2 %**,
and merger **+3.9 %** — the merger is the only class where the second L4 pays, and the only class the
mid-run sample caught at **99.0 % KV with 16 running / 10 queued**. Fleet-total throughput always
rises (+10 %…+108 %); it is per-GPU efficiency that falls, because the second replica is starved by
the client (request share skews 78/22 toward the first-started replica).

**Coverage, by metric, measured from the artifact store:**

| Cell | verbatim /metrics | GPU mem bandwidth | mid-run KV / queue | cold boot |
| --- | ---: | ---: | ---: | ---: |
| `1l4-c8` | *in flight* | *in flight* | *in flight* | *in flight* |
| `1l4-c16` | *in flight* | complete | *in flight* | *in flight* |
| `2l4-c8` | complete | complete | **missing (5/5)** | **missing** |
| `2l4-c16` | complete | complete | *in flight* | *in flight* |
| `2l4-c32` | complete | complete | **partial (1 of 5)** | complete |

**Running now** (gated behind a metric-capture smoke that must pass before any live spend; it failed
once, correctly, and stopped the launch):

1. `1l4-c8` re-run + the **noise floor** riding its boot — restores the verbatim `/metrics` families
   *and* the missing `utilization.memory` (bandwidth) family *and* the cold-boot boundary.
2. `1l4-c16` re-run — restores the verbatim `/metrics` families.
3. `2l4-c16` re-run — mid-run KV / queue for all five runs.

All three now capture, per run: verbatim `/metrics` at **before / mid / after** per replica (~120
families), the **mid-run series** (`vllm_metrics_mid.series.jsonl`, from which the card reports the
run's maximum `kv_cache_usage_perc` / `num_requests_running` / `num_requests_waiting`), the
in-container nvidia-smi series including **memory bandwidth**, the run store, the fleet window with
`ready_ts`, and the per-run + cell + master reports. The mid-run sample is wired into the **runbook**
(`midrun_metrics` step, `MIDRUN_INTERVAL`, default 30 s), not left to an operator.

**Remaining, if time permits — the only gaps left after the three legs above:**

| Cell | What a re-run would add | Est. |
| --- | --- | --- |
| `2l4-c8` | mid-run KV / queue (5 runs) + `ready_ts` | ~75 min · ~$1.8 |
| `2l4-c32` | mid-run KV / queue for **4 of 5** runs (only the merger was sampled) | ~75 min · ~$1.8 |

Roughly **$3.6 and 2.5 h**. Neither changes a headline number: mid-run KV is diagnostic telemetry
(design §5.2, "GPU hardware"), and every blank in the master carries its reason rather than a
substitute value. They are listed so the coverage matrix can be made uniform if the budget allows.

**One correctness note worth recording.** The original grid's "the engine never backs up
(`num_requests_waiting = 0`)" observation came from the before/after scrapes, which fire at a run's
**drained edges** — where `kv_cache_usage_perc` and both queue gauges are 0 *by construction*. All 58
preserved KV readings in the tree are 0.0. At C32, sampled mid-run, the loaded replica actually sits
at **16 running / 8–10 waiting / KV 74–99 %**. The mid-run label is what makes that visible, and it
is now part of the capture contract.

---

## §2 → paste as a comment on issue **#128** ("L4 Reruns")

Follow-up to the earlier note: all four of #128's cells are now covered on the paired draw — A
(`1l4-c8`), B (`1l4-c16`), C (`2l4-c16`), and D (`2l4-c32`, added as the SAND-047 saturation cell,
which made the design doc's §3.6 map D to `2l4-c32` instead of "not run"). Both matched-load
contrasts (A→C at 8/replica, B→D at 16/replica) are measured, and A and B are being re-run now to
complete their verbatim `/metrics` coverage. This issue can close once those two legs land.

---

## §3 → paste as a new issue (or keep as the design record)

**Title:** SAND-042 follow-up: does a controlled feed restore per-GPU parity on 2×L4? (feed-controlled
scale-out experiment)

**Body:** see [`docs/SAND42-FOLLOWUP-DESIGN.md`](SAND42-FOLLOWUP-DESIGN.md). In one line: hold the
engine, draw, prompts and workload fixed and vary only **how work reaches two GPUs** — data-parallel
as-is (control), data-parallel with a per-request feed, **tensor-parallel on one endpoint**, and
data-parallel with a raised admission ceiling — to decide whether "the second L4 does not pay" is a
property of L4s or of this client. ≈$8 all-in, ~6 h, 4 arms, full metric coverage from the start.
