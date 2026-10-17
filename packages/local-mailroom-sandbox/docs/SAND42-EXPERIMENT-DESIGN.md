# SAND-042 — experimental design: paired concurrency × fleet grid

**Card:** SAND-042 · **Status:** preflight-ready, **not authorised to spend** ·
**Supersedes the design layer of:** SAND-037 (Experiments 1–4)
**Inputs:** `reports/SAND-37/` (SAND-37/39/40 cards + `SAND-37-MASTER-SCORE-COST-CARD.md`),
`docs/SPECIALIST-GRID-PLAN.md`, `docs/BENCHMARK-PROGRAM.md` (SAND-043),
the AmFam A100 cost cards, `config/runbooks/catalog.yaml`, `config/runs/sand42-*.yaml`.

This document is the *design and significance* layer. It states what each number means, what
denominator it uses, how many documents a comparison needs, and what has to be true before a
delta is called real. It does not move prompts (that is `prompt-engineer`) and it does not
interpret a finished run (that is `eval-judge`).

---

## 1. What SAND-037 Experiments 1–4 established, and what they got wrong

SAND-037's master card names four postures. Each ran five specialists on one warm fleet.

| Experiment | Posture | GPUs | Client concurrency | n / class | Cells |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | 1×L4 C8 n=20 | 1 | 8 | 20 | 5 of 5 |
| 2 | 1×L4 C8 n=50 (SAND-39 inverse leg) | 1 | 8 | 50 | 5 of 5 |
| 3 | 2×L4 C32 n=50 | 2 | 32 | 50 | 5 of 5 |
| 4 | 2×L4 C32 n=100 (merger 50 †) | 2 | 32 | 100 | 5 of 5 |

Established: 2×L4 at C32 lifted documents/min +99% at +0.4% cost/doc on the identical 250
documents (Exp. 2 → 3); larger runs cost less per document (−19% on the four unchanged
specialists, Exp. 3 → 4); the merger † settings moved MAUD accuracy 0.035 → 0.140 and coverage
23% → 69% on the same 50 agreements at 4.5× the cost.

The defects that SAND-042 must correct:

1. **GPU count and client concurrency moved together.** Exp. 2 → 3 changed replicas (1 → 2)
   *and* concurrency (8 → 32) at once, so +99% documents/min cannot be attributed to either.
   `docs/SPECIALIST-GRID-PLAN.md` says so outright: "Client concurrency still differs by design."
2. **C32 was the only 2×L4 concurrency ever run**, and C16 was never run on any fleet. The
   concurrency response curve has two points, both on different hardware.
3. **No GPU hardware telemetry on any L4 card.** `reports/SAND-37/SAND37_L4_cost_cards.md` line 7:
   "GPU hardware telemetry (utilization, power, temperature, memory) is not in any L4 card."
   The AmFam A100 cards *did* carry it (`gpu utilization % … src=serving-replica nvidia-smi`,
   peak util, power draw, temperature, mem used), and `reports/dashboard/gpu_report.py` line 800
   makes sampling it the top recommendation before the next spend.
4. **No interval on any delta.** Every comparison in the master card is a point estimate.
   SAND-043 §1.5: "Lead with the sample-size caveat when it applies."
5. **Contracts at T = 0.7 is as noisy run-to-run as between documents** (SD_diff 0.122 ≈
   between-doc SD 0.118), so contracts comparisons need 100+ paired documents or a contract.
6. **Length-capped loops** (contracts, merger) burned full decode budgets; fixed in the aligned
   spec by T = 0.7 plus the posture knobs, and recorded as a finding, not a rerun trigger.
7. **One cell silently serial.** `grid-50-contracts-specialist-awq-1l4` deployed with
   `MAX_INPUTS=0` and served one request at a time (no result). Deploy-env drift is now checked.
8. **A credential bug poisoned a whole leg.** SAND-038: `langchain_agents/base_agent.py:94`
   defaulted `api_key` to `OPENROUTER_API_KEY`, so every contracts/merger row 401'd on the first
   1×L4 contracts attempt. Fixed sandbox-side by `mailroom_sandbox.provider_credentials`.
9. **Replica imbalance at C32.** One replica held 16 running + 7 queued while the other ran 6;
   all 8 preemptions landed on the busy replica (SAND-040). Request counts still split 199/219,
   so it is bursty affinity, not a routing failure.
10. **Pooled numbers hid the long class.** The SAND-40 pooled column fell 20.7 → 11.9 docs/min
    only because merger † took 73% of busy time.

---

## 2. The claim SAND-042 tests

**Claim.** On the SAND-037 aligned spec (frozen L5 engine, v1 simplified prompts, one shared
subclass-stratified draw), *client concurrency* and *replica count* each have a measurable effect
on **document goodput**, **cost per usable record**, and **per-replica GPU utilization**, and
neither has a measurable effect on **quality**.

| Element | Value |
| --- | --- |
| **Metric** | Primary: per-class field score (mean over documents) with a bootstrap 95% CI. Secondary: documents/min/GPU at the class SLO, $/1k ok documents, $/1k **schema-valid** documents, GPU util % (mean/peak), preemptions, length-capped share. |
| **Denominator** | Quality: documents **attempted** (not documents ok). Reliability: documents attempted. Cost per usable record: documents **ok** and documents **schema-valid**. Goodput: documents attempted, per GPU, restricted to runs whose p95 document latency ≤ the class SLO. |
| **Population** | `Lucius-Morningstar/mailroom-dataset` @ `ed7576b6`, config `ground_truth`, `split: all` (train + test, both joined with the ground-truth config), seed 42. Five classes. One subclass-stratified 50-document draw per class, reused by every cell. |
| **Comparison** | Paired, per document, on the identical 250 documents. Five cells: {1×L4, 2×L4} × {client concurrency 8, 16} in the original grid, **plus** `2l4-c32` (2×L4 at the engine's admission ceiling) added by the SAND-047 amendment (§3.1, §3.6). |
| **Not tested** | Prompt quality (frozen v1 simplified stems, unchanged). Merger † chunked settings. Insurance-claims grammar-constrained schema. Model swaps. Anything about the test split as a benchmark set (that is `MB-v1`, SAND-043). |

**Contracts on every delta** (see §4): the interval must exclude 0, and the point estimate must
exceed the measured run-to-run noise floor for that class. Contracts and merger run at T = 0.7;
a contracts comparison at n = 50 is **underpowered for Δ = 0.05** (needs ~47 paired documents at
the SAND-037 floor — marginal) and **unpowered for Δ = 0.03** (needs ~131). Report contracts
deltas as intervals, never as rankings.

---

## 3. Design

### 3.1 The five cells

| Cell | Runbook | Replicas | Client concurrency | **Per replica** | min=max containers |
| --- | --- | ---: | ---: | ---: | --- |
| `1l4-c8` | `sandbox runbook show sand42-1l4-c8` | 1 | 8 | 8 | 1 |
| `1l4-c16` | `sandbox runbook show sand42-1l4-c16` | 1 | 16 | 16 | 1 |
| `2l4-c8` | `sandbox runbook show sand42-2l4-c8` | 2 | 8 | **4** | 2 |
| `2l4-c16` | `sandbox runbook show sand42-2l4-c16` | 2 | 16 | **8** | 2 |
| `2l4-c32` | `sandbox runbook show sand42-2l4-c32` | 2 | 32 | **16** | 2 |

Client concurrency is split **equally across replicas** (the operator rule): 2×L4 C8 → 4 per
replica, 2×L4 C16 → 8 per replica, 2×L4 C32 → 16 per replica.

**The SAND-047 amendment (`2l4-c32`).** The original grid pinned client concurrency to {8, 16}.
`2l4-c32` joins the 2×L4 arm only, because 32 total = **16 per replica = the engine's own
`max_num_seqs`** — the scheduler's admission ceiling, past which a request queues rather than
runs. That makes it the grid's saturation point, and it is exactly the per-replica load `1l4-c16`
already ran, so **1×L4 C16 vs 2×L4 C32 is a matched-load scale-out pair *at saturation*** — the
pair §3.2 said the original four cells could not supply. It also replicates SAND-037's 2×L4 C32
point (Experiment 3, §1) on this design's paired 250-document draw, which is what ties the grid
back to the only earlier C32 measurement. It is the grid's only concurrency above 16, and it
carries the 2-replica cost caps (caps are keyed by replicas, not concurrency).

### 3.2 The confound, stated honestly

The 2×L4 cells are **not** a per-replica-load twin of the 1×L4 cells. Two matched-load pairs
exist, and both isolate *replica count*:

> **1×L4 C8 (8/replica) vs 2×L4 C16 (8/replica)** — same per-replica load, double the GPUs.

> **1×L4 C16 (16/replica) vs 2×L4 C32 (16/replica)** — the same contrast *at saturation*, added by
> the SAND-047 amendment (§3.1). This is the sharper of the two: at the admission ceiling the
> client side offers exactly the same load as C16, so any throughput or latency difference is the
> second replica's scheduling — not more requests in flight.

The complementary pair that isolates *concurrency at fixed
GPUs* is **1×L4 C8 vs 1×L4 C16** (and, at two GPUs, 2×L4 C8 vs 2×L4 C16 — but there the load
changes from 4 to 8 per replica). Do not read `1l4-c16` vs `2l4-c8` as anything: both the GPU
count and the per-replica load differ.

### 3.3 Pairing

Every cell scores the **identical 250 documents** — five classes × 50, one draw. The dataset
block is byte-identical across the five cells' run YAMLs (same `strata`, same `sample_seed: 42`,
same revision), and the sampler is a per-stratum seeded prefix
(`corpus._draw_buckets` → `_seeded_prefix`), so the draw is reproducible and identical.

Pairing is the single largest variance saving: for corporate records an unpaired comparison needs
~390 documents per arm to see Δ = 0.05, a paired one needs 19
(`docs/BENCHMARK-PROGRAM.md` §3). Every SAND-042 delta is computed as the mean of per-document
score differences with a percentile bootstrap CI (`sand42_cards.paired_delta`).

### 3.4 Stratification

n = 50 per class, allocated **proportionally over every subclass of that class with a floor of 1
per subclass** (largest-remainder). Counts are the measured corpus distribution at the pinned
revision. This makes "properly stratified across all document types" literal: every sub-type is
represented, and the class score is not dominated by the largest sub-type.

| Class | Pool | Sub-types | Allocation (n = 50) |
| --- | ---: | ---: | --- |
| correspondence | 1,000 | 8 | email 24, memo 5, notice 5, demand 4, letter 4, press_release 4, meeting_request 3, attorney_demand 1 |
| insurance_claim | 1,100 | 6 | auto 13, property 9, carrier 7, inpatient 7, outpatient 7, pde 7 |
| corporate_record | 450 | 10 | charter_amendment 8, articles_of_incorporation 7, indenture 6, officer_certificate 6, subsidiary_list 6, rights_instrument 5, board_resolution 4, bylaws 4, powers_of_attorney 3, other 1 |
| contract | 600 | 26 | Consulting Agreements 3, License_Agreements 3, Supply 3, + 18 sub-types × 2, + 5 sub-types × 1 |
| merger_agreement | 152 | 5 | all_cash 18, other 18, all_stock 8, mixed_cash_stock 5, mixed_cash_stock_election 1 |

**Read this with the small-n caveat.** At n = 50 across 26 contract sub-types, per-sub-type n is
1–3, so per-sub-type scores are not inferable. Stratification here buys **representativeness of
the class score**, not per-sub-type ranking. The reported metric stays the class score.

`split: all` mixes train and test. That is deliberate: the test split does not hold 50 of each
sub-type (contract test n = 60 across 26 sub-types), and `split: all` is what SAND-37/39/40 used,
so the noise floor and every prior L4 number stay comparable. The consequence is that the
SAND-042 250 documents are a **development set**, not a frozen benchmark set; the clean
never-tuned test split belongs to `MB-v1` (SAND-043 §5.1) and must not be conflated with this.

### 3.5 One cold boot per cell

Each cell is a single `modal deploy` with `min_containers = max_containers = replicas`, and all
five specialists chained on that one warm fleet (runbook step order:
`env → activate_profile → check → prewarm → deploy → cutover → health → configs → teardown`).
Five specialist runs per cell, one cold boot per cell (per replica). The runner never
`modal deploy --strategy recreate` between classes — that is the catalog's own anti-pattern.

### 3.6 Alignment with issue #128 ("L4 Reruns")

[Issue #128](https://github.com/Exios66/local-mailroom-sandbox/issues/128) asks for a 2×2 on
**GPU count × per-replica load**, with the nvidia-smi sidecar as the reason for the rerun. All four
of its cells are now byte-identical to ours:

| #128 | R | per-replica | total C | ours |
| --- | ---: | ---: | ---: | --- |
| A | 1 | 8 | 8 | `1l4-c8` |
| B | 1 | 16 | 16 | `1l4-c16` |
| C | 2 | 8 | 16 | `2l4-c16` |
| D | 2 | 16 | 32 | `2l4-c32` |

**Where the original grid diverged, and how the SAND-047 amendment resolves it.** #128 pins
*per-replica load* to {8, 16} and lets total client concurrency reach 32; the four-cell grid pinned
**total client concurrency** to {8, 16} and split it across replicas (§3.1), because the instruction
that governs is "NOT the old 8/32" — C32 is SAND-037 Experiment 3, one of the postures this design
exists to correct. The amendment runs #128's D as well, as an **added fifth cell** rather than a
replacement, so both grids are now fully covered. Consequences, stated rather than papered over:

- The GPU-count-at-fixed-load contrast is **preserved**: `1l4-c8` vs `2l4-c16` (8/replica each) is
  exactly #128's A→C.
- #128's B→D (per-replica 16 at 1 vs 2 GPUs) is now measured as `1l4-c16` vs `2l4-c32`, so that
  contrast — and the A→D decomposition of SAND-037's +99 % along the 8→16 per-replica load axis —
  **is available**, where the four-cell grid could not supply it.
- `2l4-c8` (4/replica) is *not* in #128's grid at all: it is the 2×L4 half of the fixed-GPU
  concurrency contrast (2×L4 C8 vs 2×L4 C16), so it stays.
- #128's run order (C, then B, then A/D) is a budget-cutoff hedge, not a design constraint; this
  grid records no order, and `1l4-c8` ran first.

**Two telemetry requirements adopted from #128** (additive — they conflict with nothing):
`p95` utilization alongside the mean, and **`sampling_coverage_pct`, rejecting a cell below 90 %**
(`container_telemetry._coverage_pct`). Coverage is not `observed ÷ expected`: the sampler's cadence
is bimodal (a fixed sleep plus `nvidia-smi`'s own runtime), so a gap longer than twice the normal
cadence is counted as uncovered time instead.

### 3.7 Whole-document input (contracts), and why the cap was wrong

`max_input_chars` was sized by `specialist_posture._input_chars_for` as
`min(window fit, 1.25 × assumed prompt_tokens × 2.4)`. The `1.25 × assumed prompt` clamp exists so
short classes do not over-prefill into empty context — correct for correspondence, **wrong for
long-document classes**, because it sizes the cap from a *guess at the prompt* rather than from the
documents. Measured on the frozen draw:

| class | p50 chars | max chars | cap | docs over cap | text dropped |
| --- | ---: | ---: | ---: | ---: | ---: |
| contracts | 26,115 | 300,768 | 24,000 | 26/50 | **62 %** |
| merger | 349,823 | 505,699 | 30,000 | **50/50** | **93 %** |

`base_agent.truncate_input` keeps a head+tail window, so the omitted span is the **middle** — where
the operative clauses live. A contracts score computed on 38 % of the document is not a contracts
score.

**Contracts now runs the pipeline's own chunked pass** (`_SAND42_CHUNKED` → `chunk_chars` 43,000 /
`overlap_chars` 6,000, `max_input_chars` 49,000). Windows are paragraph-aware with a trailing
overlap, and the merge is the completeness guarantee: list fields union with normalized dedupe,
scalars keep the first non-null value, confidence takes the max. `extract_chunked` falls through to
plain single-pass `extract` when a document fits one window, so **small-document output is
unchanged** and only the 17 over-cap contracts change path. Measured: 50 → 85 calls, 1.09M input
tokens (2.8×), ≈ $0.26 and ≈ 18 min — inside the existing $0.90 / 4800 s cap.

Sizing rule (the same one SAND-040 used): every request must fit the 32K window because
`extract_chunked` skips a failed chunk **silently**, so the context-fit guard (2.4 chars/token +
4,000 system tokens) allows 49,382 chars beside the 8,192 output cap, and `chunk_window` holds each
window to `budget − overlap` so a chunk plus its overlap tail still fits.

**Merger runs the same way, with the SAND-040 optimised posture.** Its defect is far worse —
50/50 documents over cap, 93 % of text dropped, 7 % of each agreement seen — and the pre-fix
1L4-c8 run measured the result: MAUD accuracy 0.0 (0–1 of 13–17 questions answered), extraction F1 0.0,
degenerate `No-Shop: Yes` × 22 repetition, and 3/50 (6 %) `LengthFinishReasonError` failures. It
now takes the most efficient whole-document method this repo has, verbatim from
`sand40-50-merger-specialist-awq-2l4`: windows 47,000 / overlap 6,500, `max_tokens` 6,144,
temperature 0.7 / top_p 0.8 / top_k 20 / presence 1.0, and **one length re-sample**. Fits the 32K
window exactly (`54000/2.4 + 6144 + 4000 = 32644`). Cost is now **measured**, not extrapolated: the
5-document merger probe (2026-10-12, 1×L4, C8) ran 1,702,602 chars in **438 s** warm, so the
18,160,427-char draw is `438 × 10.66 ≈ 4,671 s ≈ 1.30 h ≈ $1.04` of GPU. That is an upper bound —
`extract_chunked` walks a document's chunks sequentially, so 5 documents keep only 5 requests in
flight while the 50-document run fills C8. The abort guard is `$1.70 / 7200 s` (2×L4 $2.55), i.e.
the measured figure plus ~55 % headroom; the pre-probe `$1.25 / 5400 s` guard would have aborted a
legitimate run. Same probe raised MAUD coverage from 0–1 of 13–17 questions to 17/17, 12/15, 9/13,
7/15 with 0 errors.

---

## 4. Noise floor and sample size

### 4.1 The prior, from SAND-037/39

SAND-39 (1×L4 C8) and SAND-37 2×L4 C32 scored the **identical 250 documents** with identical
settings, so the spread of the per-document differences is pure run-to-run noise
(`docs/BENCHMARK-PROGRAM.md` §3):

| Class | n paired | Between-doc SD | **SD of the difference** | Paired n for Δ = 0.05 | Paired n for Δ = 0.03 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Insurance claims (T 0.1) | 50 | 0.069 | 0.027 | 3 | 7 |
| Corporate records (T 0.1) | 50 | 0.249 | 0.077 | 19 | 53 |
| Correspondence (T 0.1) | 50 | 0.218 | 0.082 | 22 | 59 |
| Merger (T 0.7) | 42 | 0.049 | 0.052 | 9 | 24 |
| **Contracts (T 0.7)** | 38 | 0.118 | **0.122** | **47** | **131** |

n ≈ (2.8 × SD_diff / Δ)², 80% power, two-sided 5%, paired.

### 4.2 The SAND-042 re-measure

That floor was measured on the **SAND-037 draw**. SAND-042 uses a different (subclass-stratified)
draw, so the floor is a prior, not a measurement for these documents. `sand42-noise-floor`
re-runs the correspondence cell on the identical 50 documents at identical settings and reports
the paired SD_diff, Δ mean (which should be ≈ 0), and the n it implies
(`sand42_cards.write_noise_floor`). It is **blocked pending spend approval** — the preflight,
benchmark-check and runbook-check all pass today, only the spend flag is closed.

**Until that leg runs, quote no SAND-042 delta smaller than the §4.1 floor, and state that the
floor came from a different draw.**

### 4.3 Contracts and merger contracts

* Contracts and merger run at **T = 0.7** (Qwen3's documented non-thinking setting; T = 0.1 loops
  to every cap). At T = 0.7 contracts is as noisy run-to-run as between documents, so:
  **report contracts as an interval, or average k ≥ 3 samples per document.** n = 50 paired is
  marginal for Δ = 0.05 and unpowered for Δ = 0.03.
* Merger is the class with the smallest corpus (152 rows, 17 test) and the largest per-agreement
  cost. Its deltas are reported with intervals and never pooled into a fleet-level number.

---

## 5. Metric contract

A number is only meaningful with its definition, denominator, sample size and population. The
card carries the field set below; the machine-readable card is the contract
(`reports/SAND42/<shape>/<specialist>/<run_id>.card.json`).

### 5.1 What the AmFam A100 cards carried (the requested baseline)

Every field below appeared on the A100 cost cards, sampled from the serving replica:

`run_id · task · profile · model · gpu × replicas + rate source · documents +
dataset_fingerprint · billed window = cold boot + warm span · warm span · cold boot +
cold-boot $ · warm GPU $ · TOTAL GPU $ · run-span lower bound · boot $ / idle $ (enriched) ·
prompt / completion / total tokens · cost per total token · cost per document ·
**gpu utilization % (min/max/n, src = serving-replica nvidia-smi) · peak util % · power draw (W) ·
temperature (C) · mem used (MiB)** · throughput tok/s · mean e2e latency · mean TTFT
(src = vLLM /metrics histogram) · mean time-to-first-byte (proxy-measured, **not** TTFT) ·
score (exact_match, n) · aggregate bucket`.

### 5.2 What SAND-042 adds, and where each field comes from

| Group | Field | Source |
| --- | --- | --- |
| Quality | per-class score mean, bootstrap 95% CI, SD, scoring method, CUAD presence F1 / MAUD accuracy + coverage | run store → `grid_cards.collect_card`; CI from `sand42_cards.bootstrap_mean_ci` |
| Reliability | ok rate + **Wilson** interval, schema-valid rate, parse errors, length-capped share, error kinds | `sand42_cards._reliability` |
| Throughput | documents/min, **documents/min/GPU**, tokens/s/GPU, **goodput at the class SLO** | `sand42_cards._goodput` (SLO: 60 s short classes, 300 s contracts, 1800 s merger) |
| Cost | busy-window GPU $, $/doc, $/ok doc, **$/1k ok**, **$/1k schema-valid**, $/1M tokens, cold-boot $, idle $ | `grid_cards` + `sand42_cards._cost_per_usable` |
| Engine | TTFT p50/mean, prefix-cache hit rate, preemptions, length finishes, KV-cache use % — per replica, as before/after deltas | `vllm_metrics.scrape` → `grid_cards._engine_block`; the **full** exporter output (all ~120 families: queue depth, e2e/inter-token latency, prefill/decode time) is preserved verbatim as `vllm_metrics_<label>.txt` beside the summarized JSON |
| **GPU hardware (new)** | utilization % mean/**p95**/min/max/**peak**, **sampling coverage %**, power draw W, temperature C, memory used/total MiB — per replica, as a **time series** | **SAND-042 in-container nvidia-smi sampler → Modal Volume → `container_telemetry` → `grid_cards._container_telemetry`** |
| Conditions | engine, admission, fleet, dataset pin + draw, prompt stem, caps, temperature, retries | `grid_cards.collect_card` |

### 5.3 How the GPU telemetry is collected

Modal permits exactly one `@modal.web_server` per function — stacking a second raises
`Cannot set 'webhook_config' twice` (`modal/_partial_function.py:86`), so a `/telemetry` route on
a second port is not available. Instead:

1. `deploy/modal_vllm.py` mounts the `sandbox-vllm-telemetry` volume at `/telemetry` and, once
   vLLM is ready, starts a daemon thread that every `MODAL_VLLM_TELEMETRY_INTERVAL` (default 5 s)
   runs `nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,utilization.memory,power.limit,clocks.sm`
   (the memory-**bandwidth** utilisation, power cap and SM clock are L4/A100-portable)
   and appends one JSON line to `/telemetry/<label>/<process_start_time_seconds>.jsonl`,
   committing every `MODAL_VLLM_TELEMETRY_COMMIT_EVERY` samples (default 2 → ~10 s).
   The replica filename is vLLM's own `process_start_time_seconds` as `str(float)` —
   byte-identical to `vllm_metrics.group_replicas`'s key, so the GPU rows join to the
   engine rows per replica. (Not the hostname: every Modal container reports
   `socket.gethostname() == "modal"`, so two replicas would collide in one file.)
2. The label is per **cell** (`sand42-1l4-c8`, …, derived by
   `specialist_posture.sand42_cell_label`), so one deploy produces one series and the scraper
   finds it from any of the cell's five configs.
3. `sandbox run scrape-metrics --label before` records the window start;
   `--label after` pulls the volume, slices the series to `[before, now]`, and writes
   `container_telemetry_after.json` beside the vLLM scrape.
4. The card renders it under `engine_telemetry.gpu`, and the cell card reports util mean/peak,
   power and temperature.

Absent telemetry says "not captured" with a reason — never a fabricated zero. The volume is a
soft dependency: a missing SDK, a missing volume or an unauthorised CLI degrades to a warning and
never fails the scored run.

### 5.4 What is deliberately *not* claimed

* **TTFT is never inferred.** It comes from the vLLM `/metrics` histogram only
  (`vllm_metrics` docstring); the proxy-measured time-to-first-byte is reported separately and
  labelled as not-TTFT, exactly as the A100 cards did.
* **No composite score.** The decision rule is: a change ships if quality is non-inferior (the
  lower bound of the Δ interval is above −0.02) and it improves cost or goodput, or if it improves
  quality at a stated cost (`docs/BENCHMARK-PROGRAM.md` §5.2).
* **No pooled column without a per-class table.** Merger is excluded from any fleet-level
  throughput claim: on the frozen settings it is ~112k prompt tokens per agreement and dominates
  busy time.

---

## 6. Preflight and deployment readiness

Nothing below spends until an operator approves it. Run in this order.

```bash
# 0. Environment (repo checkout, Python >= 3.11)
pip install -e ".[dev]"
cp config/.env.example .env

# 1. Catalog + generated docs are consistent (no GPU, no network)
sandbox runbook check
sandbox runbook write          # only if the catalog changed; commit docs/runbooks/ with it

# 2. Static posture: engine pins, prompts, caps, walls, concurrency, dataset pin
sandbox run benchmark-check --config config/runs/sand42-50-correspondence-specialist-awq-1l4-c8.yaml
#    (repeat per config, or run it over the whole cell)

# 3. The draw is reproducible and identical across all five cells (needs the HF cache)
sandbox datasets pull
for cfg in config/runs/sand42-50-contracts-specialist-awq-*.yaml; do
  sandbox run preflight --config "$cfg" --live
done
#    compare the fingerprint/draw lines: they must be identical for the same class

# 4. Deploy knobs come from the run YAML, not a stale shell
set -a; eval "$(sandbox run deploy-env --config config/runs/sand42-50-contracts-specialist-awq-1l4-c8.yaml)"; set +a
#    MODAL_VLLM_TELEMETRY_LABEL=sand42-1l4-c8 must be in that block

# 5. Then, and only then, the runbook
sandbox runbook show sand42-1l4-c8
```

**`VLLM_BASE_URL` must end in `/v1`.** The profile's `base_url` is
`http://localhost:8000/v1` and the client appends only `/chat/completions`, so a bare
`https://<workspace>--sandbox-vllm-serve.modal.run` 404s every call while `/v1/models` still
answers. Use `https://<workspace>--sandbox-vllm-serve.modal.run/v1`. Found live on the
2026-10-11 corporate-records smoke; the runbook's cutover step now says so.

**Cold boot is measured, not assumed.** `preflight --live` records `cold_boot_seconds` on the
lock, so the card's cold-boot line is a measurement (0.41 s on a warm reuse, ~120 s on a cold
one) rather than an inference.

**Abort guards.** Each config carries `cost_cap_usd` and `max_wall_seconds` from the posture table
(`specialist_posture.SPECIALIST_POSTURE`); the five caps in a cell sum to **$3.70** on 1×L4 and
**$5.40** on 2×L4. Cost estimates (not invoices): ≈ 30–45 min warm on one L4 per cell
(SAND-37 measured ≈ 29 min for the same 250 documents at C8), ≈ 20–35 min on two.

**One cold boot per cell** is enforced by `min_containers = max_containers = replicas` plus a
single `modal deploy` per cell. Teardown (`./deploy/teardown_vllm.sh`) only after the fifth
specialist — two warm replicas bill two GPUs.

**Blocked until approved:** `sand42-noise-floor` (spend flag closed in the catalog;
`blocked_reason` is printed and the script exits non-zero).

---

## 7. Adversarial checks

| Risk | Check | Where |
| --- | --- | --- |
| **Leakage / tuning on the test split** | The five cells share one draw and no prompt is edited between cells; SAND-042 makes no quality-improvement claim. The never-tuned test split is reserved for `MB-v1` (SAND-043 §5.1) and is not this set. | §3.4, §2 "Not tested" |
| **Tuning on the scored documents** | Prompt stems are frozen v1 simplified for all five specialists, asserted at import (`specialist_posture._assert_sand42_prompts` rejects any non-`_simplified` stem). | `specialist_posture.py` |
| **Draws silently differ between cells** | The dataset block is identical across the five cells; `strata_guard` / `strata_draw_guard` hard-fail on an absent or dropped stratum instead of truncating; a test asserts the cells' strata blocks are equal. | `corpus.py`, `tests/test_sand42_grid.py` |
| **Small-n class (merger)** | Merger is reported per class with an interval, never pooled; its 17-agreement test split is explicitly out of scope. | §4.3 |
| **Pooling across classes** | No pooled column on the cell card; the comparison card is per class. | §5.4, `sand42_cards.render_cell_md` |
| **Replica imbalance / KV pressure** | Per-replica engine telemetry is scraped before/after and now includes GPU util and KV use per replica; preemptions and length finishes are reported per replica, so a C16/C8 imbalance is visible rather than averaged away. | §5.2, `grid_cards._engine_block` |
| **Silent serial cell** (`MAX_INPUTS=0`) | `env_drift` fails benchmark-check on any `MODAL_VLLM_*` shell value that disagrees with the run YAML. | `deploy_env.py` |
| **Wrong key to the endpoint** (SAND-038) | `mailroom_sandbox.provider_credentials` wraps `BaseAgent.__init__` at `runtime.activate()`. | SAND-038 |
| **A delta inside the noise floor** | Every cell-to-cell delta carries a bootstrap CI and better/worse counts; a CI containing 0 is reported as inside the floor. | `sand42_cards.paired_delta` |
| **Underpowered claim** | Each delta reports the paired n that Δ = 0.05 would need; contracts at n = 50 is flagged marginal. | §4.3 |

---

## 8. Evidence pack

Every SAND-042 number ships with:

* **Definition + denominator + population** — §2 and the card's `conditions` block.
* **n** — documents attempted, documents ok, documents schema-valid, paired documents.
* **SD_diff** — for each paired delta, and the noise-floor leg's own SD_diff.
* **Interval** — bootstrap Δ-CI (paired deltas), bootstrap CI (quality), Wilson (ok rate).
* **Manifest** — dataset repo + revision `ed7576b676343e0b402ec5412cded301e629bdee`, config
  `ground_truth`, `split: all`, `sample_seed: 42`, the per-class strata block, the run YAML path
  and the `spec_hash` recorded on the card.
* **Run card** — `reports/SAND42/<condition>/<specialist>/<run_id>.card.md` + `.card.json`
  (condition ∈ `1L4-c8`, `1L4-c16`, `2L4-c8`, `2L4-c16`).
* **Condition card** — `reports/SAND42/<condition>/SAND42-<SHAPE>-C<CONC>-SCORE-COST-CARD.md` + `.json`.
* **Comparison** — `reports/SAND42/SAND42-CELL-COMPARISON.md` + `.json`.
* **Noise floor** — `reports/SAND42/SAND42-NOISE-FLOOR.md`.
* **Master cost card** — `reports/SAND42/SAND42-MASTER-SCORE-COST-CARD.md` + `.json`.
* **Master full report** — `reports/SAND42/SAND42-MASTER-REPORT.md`.
* **Spend** — `reports/SAND42/metered-costs.json` (the teardown spend check, per study).

Report tree:

```
reports/SAND42/
├── README.md
├── SAND42-MASTER-SCORE-COST-CARD.md + .json   sandbox run card --runbook sand42
├── SAND42-MASTER-REPORT.md                    sandbox run card --runbook sand42
├── SAND42-CELL-COMPARISON.md + .json          sandbox run card --runbook sand42
├── SAND42-NOISE-FLOOR.md                      sandbox run card --runbook sand42-noise-floor
├── metered-costs.json                         sandbox run card --record-metered SAND-42 <m> <b>
├── 1L4-c8/                                    one folder per experimental condition
│   ├── SAND42-1L4-C8-SCORE-COST-CARD.md + .json    sandbox run card --runbook sand42-1l4-c8
│   └── <specialist>/<run_id>.card.md + .card.json  sandbox run card --config …
├── 1L4-c16/
│   ├── SAND42-1L4-C16-SCORE-COST-CARD.md + .json
│   └── <specialist>/<run_id>.card.md + .card.json
├── 2L4-c8/
│   ├── SAND42-2L4-C8-SCORE-COST-CARD.md + .json
│   └── <specialist>/<run_id>.card.md + .card.json
└── 2L4-c16/
    ├── SAND42-2L4-C16-SCORE-COST-CARD.md + .json
    └── <specialist>/<run_id>.card.md + .card.json
```

Specialist folders, in grid order: `correspondence`, `insurance_claims`, `corporate_records`,
`contracts`, `merger_agreement`.

---

## 9. Open items

1. **Noise-floor leg not yet run** (blocked pending spend) — §4.2.
2. **OTel *metrics* export from the container.** The new telemetry is an nvidia-smi series, not an
   OTLP metric stream. The vLLM image has no OTLP metrics exporter configured; enabling one is a
   separate change (add `OTEL_METRICS_EXPORTER`/`OTEL_EXPORTER_OTLP_ENDPOINT` to the vLLM
   subprocess env and point it at the Langfuse/Phoenix sink). No data is lost meanwhile: the
   vLLM Prometheus exporter is scraped before/after and its **entire** output is preserved
   verbatim (`vllm_metrics_<label>.txt`), so the OTLP *stream* would be a transport duplicate of
   an already-captured series, not a new source. Trace *spans* stay opt-in per `trace.sink`,
   which SAND-042 leaves at `none` as the SAND-037 grid did.
3. **`$ per 1M tokens` on Modal is a proxy**, not a bill — Modal bills container-seconds.
   The A100 cards carried both; the card keeps both and labels them.
4. **Insurance-claims schema-valid rate** is measured (0.23 on the SAND-037 grid) but not fixed
   here; grammar-constrained decoding is SAND-043 §5.5 item 3.
5. **Contracts power.** At n = 50 paired, contracts cannot resolve Δ = 0.03. If a contracts
   concurrency claim is needed, run contracts at k ≥ 3 samples per document or n = 150 paired.
6. **Merger whole-document processing — taken.** The `_input_chars_for` cap was sized from
   an *assumed* prompt length (`1.25 × prompt_tokens`), giving 30,000 chars for merger. All
   50 merger documents exceed it (270k–505k chars), so **93 % of merger text was dropped and
   a run saw 7 % of each agreement**. The 1L4-c8 cell measured the consequence: MAUD accuracy
   **0.0** with 0–1 of 13–17 questions answered, extraction F1 0.0, degenerate
   `No-Shop: Yes` × 22 repetition, and 3/50 (6 %) `LengthFinishReasonError` hard failures.
   Merger now runs the **SAND-040 optimised long-document posture** — our most efficient
   whole-document method and the one the A100-era merger cards converged on (95 % GPU util,
   ~$0.004/doc): chunked windows (47k / 6.5k overlap), Qwen3 non-thinking sampling
   (0.7 / top_p 0.8 / top_k 20 / presence 1.0), a 6144 output cap, and **one re-sample on
   `LengthFinishReasonError`**. The 1L4-c8 merger was re-run on this fixed posture (1×L4 C8):
   50/50 ok, 0 errors, `schema_valid` 1.00, MAUD **254/811 answered (31.3 %)** at 2.1 % micro
   accuracy — the numbers the master report now carries. Cost of the change is **measured, not extrapolated**: the 5-document
   merger probe (2026-10-12, 1×L4, C8) ran 1,702,602 chars in **438 s** warm, so the
   18,160,427-char draw is `438 × 10.66 ≈ 4,671 s ≈ 1.30 h ≈ $1.04` of GPU — an upper bound,
   because `extract_chunked` walks chunks sequentially and 5 documents keep only 5 requests in
   flight while the 50-document run fills C8. The abort guard moved from $1.25 / 5400 s to
   **$1.70 / 7200 s** (2×L4 $2.55) — the measured figure plus ~55 % headroom; the old guard would
   have aborted a legitimate run. The same probe moved MAUD coverage from 0–1 of 13–17 questions
   answered to 17/17, 12/15, 9/13, 7/15, with 0 errors and `schema_valid` 1.00. This is a
   deliberate deviation from #128's "what to drop: the † merger config in the factorial
   cells" — a truncated merger arm measures input coverage, not merger quality, so it cannot
   support the factorial claim either way. The 1L4-c8 merger re-run on the fixed posture is
   complete (above); the remaining SAND-042 cells run that same fixed posture.

---

## References

* `reports/SAND-37/SAND-37-MASTER-SCORE-COST-CARD.md`, `SAND-37-MASTER-APPENDIX.md`,
  `SAND37_L4_cost_cards.md`, `SAND37_L4_cost_record.md`
* `docs/SPECIALIST-GRID-PLAN.md` — the SAND-037 aligned spec and cell status
* `docs/BENCHMARK-PROGRAM.md` (SAND-043) — metric rules, corpus table, measured noise floor,
  scorecard schema, external references
* `config/runbooks/catalog.yaml` — `sand42-1l4-c8`, `sand42-1l4-c16`, `sand42-2l4-c8`,
  `sand42-2l4-c16`, `sand42-noise-floor`
* `config/runs/sand42-*.yaml` — the 20 cell configs + the noise-floor leg
* `deploy/modal_vllm.py` — the in-container telemetry sampler
* `src/mailroom_sandbox/job/container_telemetry.py`, `.../sand42_cards.py`,
  `.../specialist_posture.py`
