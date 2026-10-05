# Training report — ModernBERT run-3

## LIVE — SSH training session (2026-09-27)

| | |
| --- | --- |
| status | **IN PROGRESS** (operator SSH tunnel to CHTC GPU) |
| host | `rogers-gpu-1.discovery.wisc.edu` (Cursor remote / SOCKS tunnel) |
| action | **Do not** start Modal jobs, sandbox GPU evals, or second training processes on that host until this session exits |

When training completes, capture:

1. New `run_id` and `/checkpoints/runs/<run_id>/summary.json`
2. `training/eval_modernbert.py --json` export
3. Update this report’s archived section below and
   [RUN-03-MODERNBERT-HELDOUT-TEST-REPORT.md](./RUN-03-MODERNBERT-HELDOUT-TEST-REPORT.md)

---

## Archived completed leg — Modal run (2026-09-21)

Prior run-3 training finished on Modal L4; local weights under
`mailroom-ml/artifacts/pytorch/model/`. Narrative source:
`mailroom-ml/reports/RUN3-REPORT-20260921.md`.

| | |
| --- | --- |
| run_id (trainer) | `20260921-093211` |
| checkpoint archive | `/checkpoints/runs/20260921-132753` |
| Modal app | `ap-KVX4EVKG4MI2XJ71r6Hkow` |
| data build | `mailroom-finetune @ 19720ceb` → training Hub set (leak-audited, 8-key correspondence) |
| budget gate | est. $4.11 vs ceiling $4.32 (passed) |

### Hyperparameters (approved plan)

epochs=2, batch=4, grad-accum=8, lr=2e-5, seed=42, max_length=8192,
label-smoothing=0.05, loss-lambda-dt=0.65, **weight-mode=sqrt-inverse**,
weight-cap=10, warmup-frac=0.06, mlp-heads, early-stop-patience=2, eval-test on.

### Validation vs run-2 published (observed macro-F1)

| metric | run-2 published (e2) | run-3 e1 (selected) | run-3 e2 |
| --- | --- | --- | --- |
| doc_type macro-F1 (observed) | 0.8524 | **0.9245** | 0.9227 |
| doc_type doc acc | 0.8859 | **0.9164** | 0.9164 |
| doc_type ECE calibrated | 0.0201 | **0.0228** | 0.0154 |
| contract macro-F1 (obs.) | 0.101 | 0.0395 | 0.0367 |
| correspondence macro-F1 (obs.) | 0.098 | 0.0845 | 0.0845 |
| insurance_claim macro-F1 (obs.) | 0.7714 | 0.7677 | **0.8954** |
| corporate_record macro-F1 (obs.) | 0.238 | 0.2156 | **0.2669** |
| merger_agreement macro-F1 (obs.) | 0.1951 | 0.1951 | **0.2180** |

**Selection (shipped artifact):** epoch **1** — best val doc_type macro-F1 with
calibrated doc_type ECE ≤ 0.05 (`gate_met: true`). Note: post-run selection code
(`1718358`) would have preferred epoch 2 on subclass objective; that rule is **not**
reflected in the archived `summary.json` (documented in `governance/M9a-HANDOFF.md`).

### Trainer-integrated held-out test (323 docs)

From `artifacts/pytorch/model/summary.json`:

| metric | value |
| --- | --- |
| doc_type accuracy | 0.9288 (300 / 323) |
| subclass accuracy conditional | 0.5733 (172 / 300) |

### Serving validation (same session)

- ONNX fp32 parity vs PyTorch: **PASS** (max |Δ| ≤ 4.25e-06 per head).
- int8 default: **rejected** (argmax agreement failures on gate samples).
- Tokenizer padding/truncation bug fixed (`06842ba`) — CPU warm path ~30 ms/doc short docs.

### Verdict vs #107 / M9a goals (archived leg)

- doc_type + calibration: improved vs run-2 published gate story; GPU harness doc_type
  0.8947 (see held-out report).
- insurance_claim subclass: strong epoch-2 val macro-F1 (0.8954) but shipped epoch-1 checkpoint.
- contract + correspondence: **not improved**; remain sub-Verify; fast-path exclusion for
  high-ECE heads.

Held-out interpretation:
[RUN-03-MODERNBERT-HELDOUT-TEST-REPORT.md](./RUN-03-MODERNBERT-HELDOUT-TEST-REPORT.md).
