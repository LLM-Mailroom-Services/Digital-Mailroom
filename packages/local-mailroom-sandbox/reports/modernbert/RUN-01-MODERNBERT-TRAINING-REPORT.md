# Training report — ModernBERT run-1 (initial leg)

First Modal GPU training leg for the hierarchical ModernBERT intake classifier.
This run produced the epoch-2 checkpoint that run-2 resumed from; it is **not**
the published Hub bundle.

| | |
| --- | --- |
| run_id | `20260920-173810` |
| resume artifact | `/checkpoints/runs/20260920-173810-e2` (referenced by run-2 `summary.json`) |
| backbone | `answerdotai/ModernBERT-base` |
| data | `Lucius-Morningstar/mailroom-modernbert-training` @ `5b72a345cd3c057b736bea4910fdbef6509ad1c3` |
| spawn | Modal app `mailroom-ml-train`, L4 GPU (see `mailroom-ml/deploy/README.md`) |
| epochs (this leg) | 2 (checkpoint suffix `-e2`) |

## What is preserved

The mailroom-ml repo retains **no standalone `summary.json`** for run-1 on disk
today. Evidence is indirect:

- Run-2 hyperparameters record `"resume": "/checkpoints/runs/20260920-173810-e2"`.
- Trainer resume semantics carry the **original** `run_id` and accumulated wall
  time forward (`f37e58c` — provenance fix on `main`).

## Interpretation

Run-1 established the first fine-tuned weights on the leak-audited, clerk-normalized
training table (3,302 document rows; windowed train/val split). Run-2 continued from
the end of epoch 2 rather than restarting from the base model, so **run-1 metrics
cannot be isolated** from run-2’s logged epoch table without the Modal volume
archive for `20260920-173810`.

## Held-out test

No run-1-only test eval is checked into mailroom-ml or this sandbox. Treat
[RUN-02-MODERNBERT-HELDOUT-TEST-REPORT.md](./RUN-02-MODERNBERT-HELDOUT-TEST-REPORT.md)
as the first archived held-out test for the lineage that includes run-1 weights.

## Operator notes

After the **live run-3 SSH session** completes, if the new job resumes from an
older checkpoint rather than from `ModernBERT-base`, confirm whether that resume
path includes `20260920-173810-e2` or a later run id before comparing test scores.
