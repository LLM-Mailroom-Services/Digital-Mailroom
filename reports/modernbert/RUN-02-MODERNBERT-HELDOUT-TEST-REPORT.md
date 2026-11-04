# Held-out test report — ModernBERT run-2 (published checkpoint)

Document-level evaluation on the **323-document test split** at the end of training
(`--eval-test`), using the run-2 **epoch-2 selected** weights in
`artifacts/run2-published/`. Metrics below are taken from `summary.json` test block
(no separate GPU harness JSON is archived for run-2 in mailroom-ml).

| | |
| --- | --- |
| run_id | `20260920-214259` |
| checkpoint | run-2 epoch 2 (published bundle) |
| n_docs | 323 |
| eval mode | trainer integrated test pass (full documents, window merge) |

## Headline metrics

| metric | value |
| --- | --- |
| doc_type accuracy | **0.9319** (301 / 323) |
| subclass accuracy (conditional on correct doc_type) | **0.5449** (164 / 301) |
| subclass scorable | 301 |
| subclass unscorable | 0 |

## Interpretation

**Doc type (primary intake gate):** 93.2% accuracy on held-out documents is strong
enough for a deterministic pre-check before the LLM sorter. Errors (22 documents)
are the main residual risk for mis-routing entire matters to the wrong specialist
leg.

**Subclass (conditional):** Given a correct doc_type, the model picks the right
subclass label 54.5% of the time. That aligns with validation: contract and
correspondence heads barely beat priors, while insurance_claim carries most of the
usable subclass signal. For product semantics, **subclass from ModernBERT should not
be treated as Verify-grade** for contract/correspondence on this checkpoint; the LLM
specialist path remains authoritative.

**Comparison baseline for later runs:**

| run | doc_type test acc | subclass conditional |
| --- | --- | --- |
| run-2 (this report) | **0.9319** | 0.5449 |
| run-3 trainer test (Sep 21) | 0.9288 | 0.5733 |
| run-3 GPU harness (Sep 21) | 0.8947 | 0.526 |

Run-3’s trainer-integrated test slightly **trades** doc_type accuracy for subclass
conditional accuracy versus run-2; the separate full-context GPU harness reports
lower doc_type accuracy (see run-3 held-out report). When the **live run-3 SSH
session** finishes, re-run `training/eval_modernbert.py --json` and compare against
the run-2 row above using the same harness for apples-to-apples.

## P0 gates (program targets, report-only)

Run-3 eval JSON records program gates for context (not run-2-specific):

- P0 doc_type ≥ 0.95 — run-2 trainer test **does not meet** (0.9319).
- P0 subclass ≥ 0.75 — **not met** (0.5449).

## Sandbox consumption

Default local feeder resolves run-2-published:

```bash
export MAILROOM_ML_SRC=…/mailroom-ml
export MODERNBERT_MODEL_PATH=$MAILROOM_ML_SRC/artifacts/run2-published
sandbox modernbert status
sandbox modernbert eval --sample 323 --json   # after live run-3 completes, point MODERNBERT_MODEL_PATH at the new bundle
```

Synthetic sorter comparison fixtures live under
`data/fixtures/serving/sorter_vs_modernbert.json` (not live measurements).
