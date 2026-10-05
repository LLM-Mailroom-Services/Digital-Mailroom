# Training report — ModernBERT run-2 (published)

Second training leg; **selected checkpoint shipped** as
`Lucius-Morningstar/mailroom-modernbert-classifier` and mirrored locally at
`mailroom-ml/artifacts/run2-published/` (sandbox feeder default:
`MODERNBERT_MODEL_PATH`).

| | |
| --- | --- |
| run_id | `20260920-214259` |
| resume | `/checkpoints/runs/20260920-173810-e2` (run-1 epoch 2) |
| Hub target | `Lucius-Morningstar/mailroom-modernbert-classifier` |
| local bundle | `../mailroom-ml/artifacts/run2-published/` |
| backbone | `answerdotai/ModernBERT-base` |
| data | `Lucius-Morningstar/mailroom-modernbert-training` @ `5b72a345…` |
| windows | 4,497 train / 489 validation (model card) |
| seed | 42 |

## Hyperparameters (from `summary.json`)

| knob | value |
| --- | --- |
| epochs | 2 |
| batch × grad accum | 4 × 8 (effective 32) |
| lr | 2e-5 |
| max_length | 8192 |
| loss_lambda_dt | 0.65 |
| weight_mode / cap | `sqrt-inverse` / 10 |
| label_smoothing | 0.05 |
| mlp_heads | true |
| early_stop_patience | 2 |
| subclass_min_train_rows | 12 |
| eval_test | true |

## Validation (per epoch)

| epoch | val_loss | doc_type doc acc | doc_type macro-F1 (observed) | doc_type ECE (calibrated) |
| --- | --- | --- | --- | --- |
| 1 | 1.0041 | 0.8859 | 0.8524 | 0.0201 |
| 2 | **0.9121** | **0.9195** | **0.9051** | **0.0205** |

**Selection:** epoch **2** — best validation doc_type macro-F1 (observed) subject to
calibrated doc_type ECE ≤ 0.05 (`gate_met: true`). This closed the calibration gate
that blocked the earlier published artifact (`gate_met: false` on the pre-run-2
bundle per run-3 postmortem).

## Per-head validation (selected epoch 2)

| head | window acc | macro-F1 (observed) | ECE (calibrated) |
| --- | --- | --- | --- |
| doc_type | 0.9141 | 0.9051 | 0.0205 |
| insurance_claim | 0.8889 | 0.8085 | 0.0500 |
| corporate_record | 0.5405 | 0.2218 | 0.1037 |
| merger_agreement | 0.4656 | 0.1988 | 0.0350 |
| correspondence | 0.5161 | 0.0980 | 0.1050 |
| contract | 0.1630 | 0.0899 | 0.0630 |

## Reading

Run-2 is the **production** fast-path bundle: strong doc_type head (macro-F1 ≈ 0.91
observed on val) with calibrated ECE within budget. Subclass heads for contract and
correspondence remain at majority-prior levels (window accuracy ≈ class priors);
insurance_claim is the control head that learns well. Subclass ECE on several heads
exceeds 0.05 — the later **head exclusion policy** (run-3 serving work) keeps those
heads off the deterministic fast path even when doc_type passes.

## Artifacts

- `summary.json`, `labels.json`, `temperatures.json`, `model.safetensors`, `heads.pt`
- Model card narrative: `artifacts/run2-published/README.md` (mirrors Hub README)

Held-out test interpretation:
[RUN-02-MODERNBERT-HELDOUT-TEST-REPORT.md](./RUN-02-MODERNBERT-HELDOUT-TEST-REPORT.md).
