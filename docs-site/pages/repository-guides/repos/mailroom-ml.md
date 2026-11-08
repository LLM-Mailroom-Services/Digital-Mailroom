---
icon: brain
title: mailroom-ml
---

# mailroom-ml

**The ModernBERT intake fast-path classifier: training, calibration, evaluation and ONNX serving.**

|            |                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------- |
| Repository | [LLM-Mailroom-Services/mailroom-ml](https://github.com/LLM-Mailroom-Services/mailroom-ml)               |
| Status     | Standalone contractor repo, not a governed monorepo member                                              |
| Serves     | llm-mailroom, eval-environment, Mailroom-Corpus-EDA, and the mailroom-issues intake-overhaul epic (#85) |
| Board      | `governance/TASKS.md` (light tracking)                                                                  |

## What it does

Most documents are easy to classify. mailroom-ml trains a ModernBERT encoder that handles those quickly and cheaply, so the LLM sorter only has to deal with the messy, ambiguous and sparse tail.

* **Heads.** One `doc_type` head for the five classes, plus one subclass head per class. Head vocabularies come from the observed ground truth, not a hardcoded list.
* **Windowing.** 8,192-token context with 512-token overlap and a plurality vote across windows.
* **Calibration.** Temperature scaling per head, and an out-of-distribution energy probe.
* **Routing.** A document takes the fast path only when calibrated probability, window agreement and margin together clear the gate. Everything else, including catch-all `other`, goes to the LLM.
* **Serving.** ONNX on CPU is the primary path; a Modal app is the fallback.

## Training and serving details

* **Input construction.** `v1` (title, blank line, body) is the default and matches the published training revision. `v2` adds tagged `[FILE_NAME]`, `[TITLE]` and `[WINDOW_INDEX]` prefixes (`--input-construction v2`). Never mix v2 windows into the v1 Hub pin.
* **Subclass logit adjustment.** The trainer can apply a log-prior adjustment to subclass logits (`subclass_logit_adjust`). Inference applies the matching adjustment at decode time (`apply_subclass_decode_logit_adjust`), so training and serving stay consistent. Added in `de992dd` (2026-10-06).
* **Subclass loss.** `subclass_loss_norm: count` normalizes the subclass loss by label count. The doc_type head takes `--label-smoothing`. The subclass head takes `--subclass-label-smoothing` (default `0.0`).
* **Sidecar files.** `routing_thresholds.json` holds the selective-risk threshold from evaluation. `ood_probe.json` holds the energy probe, written from validation logits and never from the held-out test. A missing probe means "no probe", not "in distribution".
* **Reports.** `training/write_eval_report.py` generates every report from recorded `eval_*.json` files. See [Results](#results).

## Results

Latest run: **M9b** (`20261006-021245`), measured 2026-10-06 on the 323-document held-out test at 8,192 tokens. Values come from [`reports/M9a-REPORT-20261006-021245.md`](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/reports/M9a-REPORT-20261006-021245.md) and the paired comparison [`reports/memos/M9b-COMPARE-vs-ArmB-20261006-021245.md`](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/reports/memos/M9b-COMPARE-vs-ArmB-20261006-021245.md).

| Metric | Arm B (2026-09-27) | M9b (2026-10-06) |
| ------ | ------------------ | ---------------- |
| doc_type accuracy | 0.9505 (307/323) | 0.9505 (307/323) |
| Subclass accuracy, conditional | 0.5831 (179/307) | 0.6287 (193/307) |

M9b trained for 4 epochs with `loss_lambda_dt` 0.65, `subclass_logit_adjust` 1.0 and `subclass_loss_norm` `count`. Every head is marked excluded from the fast path in the report (`merger_agreement` has the highest calibrated ECE, 0.2134). Treat these figures as classifier results on this test split. They are not pipeline results. The other ModernBERT reports are in [eval-environment reports](../../experiment-reports/eval-environment-reports.md#modernbert-ownership-boundary).

## How it connects to the pipeline

llm-mailroom's intake node can call it through `agents/bert_intake.py`. The integration is fail-open: with `MAILROOM_BERT_INTAKE` off (the default), the package missing, the model missing, or any error, intake carries on with the deterministic clerk. The result is always recorded as an `intake_handoff` so downstream steps can rely on it being present.

## Quick start

```bash
git clone https://github.com/LLM-Mailroom-Services/mailroom-ml.git
cd mailroom-ml
uv sync --extra dev
uv run pytest -m "not fullcorpus"
```

Extras: `train` (torch, transformers), `serve` (onnxruntime, fastapi), `deploy` (modal). The core tests pass without any of them.

## Rules worth knowing

* Pin Hub revisions; never train or evaluate on a live tip. The canonical eval corpus is `mailroom-dataset` at `ed7576b6` (v9.1 data commit, as of 2026-10-07); training uses `mailroom-modernbert-training`.
* The training set is leak-free and clerk-normalized. Do not reintroduce a title or filename label leak.
* Subclass surfaces are consumed from the canonical taxonomy, never redefined here.

## Its documentation

* [README](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/README.md)
* [AGENTS.md](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/AGENTS.md)
* [docs/mailroom-modernbert-classifier-model-card.md](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/docs/mailroom-modernbert-classifier-model-card.md) — model card
* [docs/intake-classifier-combined-plan.md](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/docs/intake-classifier-combined-plan.md) — the plan
* [docs/plan-amendment.md](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/docs/plan-amendment.md) — amendments to the plan (data governance, leak-free splits, calibrated abstention)
* [reports/README.md](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/reports/README.md) — report generator and chart galleries
* [docs/enrichment-publish-runbook.md](https://github.com/LLM-Mailroom-Services/mailroom-ml/blob/main/docs/enrichment-publish-runbook.md) — enrichment tiers and publishing
