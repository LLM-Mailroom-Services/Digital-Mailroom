# Run Cost Derivation — how any Granite wave is priced from real data

**Purpose.** Every spend figure in `governance/SAND-027-MISSION-PLAN.md` is derived here from
measured per-document records, not from an estimate. The method answers two questions:

1. What does the **full contract split of the corpus** cost to run via API (Leg B)?
2. What does the same split cost on Modal vLLM (Leg A), and what is the safe cap for each wave?

**Priority classes.** Contracts and correspondence are the first-and-foremost comparison targets;
the derivation below is anchored on the contracts run (the only class with a full per-document
table). Correspondence is cheaper by construction (shorter documents) and is measured separately.

**Status: method complete, inputs partial.** Formulas + a worked contracts example + a
validated Modal model are DONE. Three of five classes have no Granite measurement yet, so their
numbers are extrapolated and must be re-derived after the N=20 probe (SAND-028-4 / F5).

---

## 1 · Data sources (what the harness already captures)

`src/mailroom_sandbox/eval/runners.py` records **per document**, per run:

| Field | Line | Meaning |
|---|---|---|
| `prompt_tokens` | 307–309 | input tokens billed by the provider |
| `completion_tokens` | 307–309 | output + thinking tokens billed |
| `latency_ms` | 223 | end-to-end per-doc latency |
| JSON `ok` / error | per item | whether the doc produced a scored output |

Aggregate fields (`cost_per_document`, `gpu_cost_per_document`, `total_tokens`) are
*means over n* — good for reporting, but **insufficient for projection**, because a projection
needs the distribution. The per-item rows are the projection input, which is why this method reads
`reports/*-REPORT.md` per-document tables rather than the summary line.

**Gap (must be closed by the probe):** documents that hit `LengthFinish` produce **no token counts**
in the record, yet they still consumed GPU time. In the contracts run **3 of 20 documents** did this.
Any per-doc projection from token records alone therefore *understates* cost. Fix = F1 fail-fast
(SAND-028-2), after which every billed document yields tokens.

## 2 · Leg B (OpenRouter) — exact, no model

API billing is token-based, so the projection is **exact** once token counts exist:

```
cost_api(N) = Σ_docs ( prompt_tokens × price_in + completion_tokens × price_out ) / 1e6
```

`price_in`/`price_out` come from `SANDBOX_TOKEN_PRICE_IN_PER_M` /
`SANDBOX_TOKEN_PRICE_OUT_PER_M` (`src/mailroom_sandbox/job/metrics.py:47`); for
`ibm-granite/granite-4.2-8b` that is **$0.06 / $0.25 per 1M**. No boot, no concurrency term, no
idle: **Leg B's cost per doc is a pure function of the documents themselves.**

## 3 · Leg A (Modal 1×L4) — container-time model

Modal bills the container, so cost tracks **occupied container-seconds**, not tokens:

```
container_seconds_per_doc = (latency_s / concurrency) + (cold_boot_s / N)
cost_modal(N) = [ Σ_docs (latency_s / concurrency) + cold_boot_s ] × rate_L4
rate_L4       = MODAL_GPU_USD_PER_HOUR / 3600      # $0.80/h for L4
```

`latency/concurrency` (not `latency × concurrency`): a document occupying `L` seconds of wall
time while `C` documents share the GPU consumes `L/C` container-seconds, because the container
is serving the other `C-1` documents for that same wall window.

**Validated against the measured contracts run** (concurrency 8, cold boot 161.1 s, L4 $0.80/h):

| | model | measured record | error |
|---|---|---|---|
| per-doc cost | **$0.01632** | **$0.01877** | 13 % |

The 13 % gap is the 3 LengthFinish documents' unrecorded container time — the model is
*conservative in the right direction* (it never over-projects). Re-validate after F1.

## 4 · Worked numbers — the contracts class (measured, 17 ok rows)

Per-document statistics from `reports/RUN-20-CONTRACTS-AWQ-C8-REPORT.md`:

| Metric | mean | p50 | p95 | min | max |
|---|---|---|---|---|---|
| prompt tokens | 11 434.6 | 12 131.0 | 13 349.0 | 7 991 | 13 485 |
| completion tokens | 1 506.7 | 1 364.0 | 2 875.4 | 386 | 3 029 |
| latency (s) | 523.1 | 627.6 | 809.3 | 29.3 | 817.6 |

**Per-document cost, both legs:**

| Leg | mean | p95 |
|---|---|---|
| B · OpenRouter @ $0.06/$0.25 | **$0.001063** | $0.001403 |
| B · OpenRouter @ $0.03/$0.13 (Qwen-flash, contrast) | $0.000539 | $0.000716 |
| A · Modal L4 | **$0.0188** (measured) | $0.0243 (model) |

**→ The API is ~18× cheaper per contract document than the Modal leg** at the current posture.
That asymmetry, not the cap, is the most decision-relevant number in this document.

## 5 · The full contract split, via API

`N` is the size of the contract split. Two rows differ in confidence:

- `N = 20 / 100` — the sizes this program actually runs (measured per-doc basis above).
- `N = 600` — the **full** contract split. A repo comment
  (`config/runs/run-20-contracts-specialist.yaml:47-48`, "600 available at the pin") gives this
  figure, but it is **UNVERIFIED** — see §7 to confirm it against the pinned corpus.

| N | API (mean tokens) | API (p95 tokens) | Modal (model) | Modal (measured-scaled) |
|---|---|---|---|---|
| 20 | **$0.021** | $0.028 | $0.33 | $0.38 |
| 100 | **$0.106** | $0.140 | $1.67 | $1.88 |
| 600 | **$0.64** | $0.84 | $9.83 | $11.26 |

**Answer to the standing question: the full 600-document contract split costs ≈ $0.64 via API**
(mean-token basis; ≈ $0.84 if every document behaved like the p95). On the Modal leg the same
split costs ≈ $10–11. Running the *entire* contract split through Leg B is ~$0.64 — cheap enough
that it should not be gated behind a per-wave approval; it is ~2 % of the $6 soft ceiling.

### Sensitivity — the one unknown that matters

`completion_tokens` is the term that can move, because Granite's thinking output is the part no
prompt can steer and OpenRouter cannot be told to suppress it:

| Scenario | per-doc | N=100 | N=600 |
|---|---|---|---|
| measured (mean) | $0.001063 | $0.106 | $0.64 |
| +50 % completion | $0.001251 | $0.125 | $0.75 |
| +100 % completion | $0.001439 | $0.144 | $0.86 |

Even a 2× completion-token blow-up keeps the full contract split under **$0.90**. The API
projection is robust; the Modal projection is the fragile one (it moves with latency, not tokens).

## 6 · Cap rules derived from this

- **W1 probe (N=20, 5 classes, both legs): hard cap $1.50**, expected ≈ $1.29.
- **Per-class escalation cap = 3× that class's measured N=20 both-leg cost.** Escalation is 5×
  the documents, so a 3× spend ceiling passes only if F1–F4 land. If the projection breaches it,
  **fix the run, do not raise the cap.**
- **Program ceiling $6 soft / $8 hard** — a safety bound, **not** an authorization. No wave is
  funded until its own gate passes; each later wave is re-priced from the probe and re-approved.
- Re-derive `sec_per_doc` and the caps from the **measured** probe before U8 (F5, SAND-028-4);
  the heuristics in `specialist_posture.py` are known to mis-size caps (a cap that aborts a
  correct run burns the whole warm window).

## 7 · Verifying N (open)

To confirm the contract-split size against the pinned corpus (`46a4d3c2…`), count
`expected_doc_class == "contract"` after the `ground_truth ⇆ default` join, or pull the class
column once:

```python
from huggingface_hub import HfApi, hf_hub_download
import pyarrow.parquet as pq
rev = "46a4d3c240a36671cde0182fff4960f6b8b73aca"
files = HfApi().list_repo_files("Lucius-Morningstar/mailroom-dataset", repo_type="dataset", revision=rev)
p = hf_hub_download("Lucius-Morningstar/mailroom-dataset",
                    sorted(f for f in files if f.startswith("parquet/default/") and f.endswith(".parquet"))[0],
                    repo_type="dataset", revision=rev)
t = pq.read_table(p)                     # inspect t.column_names for the class column first
```

Until that lands, treat `N = 600` as an unverified input and re-run §5 with the real `N` — the
method is unchanged, only the multiplier moves.

## 8 · Rules that keep these numbers honest

- **Slice, never re-draw (ops default).** 20 ⊂ 50 ⊂ 100 should come from one locked 100-draw per
  class; the sampler now supports nested strata draws (issue #38 — seeded shuffle + prefix), but
  matrix runs should still slice the locked set to avoid a second prepare pass.
- **Never fabricate rates.** If `MODAL_BILLED_GPU_SECONDS` is absent, the serving block stays
  absent — not zero (issues #36/#37). Every figure here is either measured or labelled
  extrapolated.
- **Re-derive, don't inherit.** These numbers expire when the serving posture changes
  (concurrency, decode contract, thinking policy). The probe supersedes §4 for Granite; the
  SAND-028 findings (2× on same 20 documents) already invalidated one earlier estimate.
