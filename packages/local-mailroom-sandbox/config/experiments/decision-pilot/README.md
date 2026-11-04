# Decision reviewer — Pilot 1

## Offline proof (no services or credentials)

```bash
pip install -e '.[dev]'
python -m pytest tests/test_decision_pilot.py tests/test_review_cli.py tests/test_reviewer_spec.py tests/test_decision_backends.py -q
```

The six original, fictional exhibits are in
`data/fixtures/pilot/decision_review.jsonl`: clean accept, disagreement, low
confidence, ineligible label, unavailable reviewer, and no usable text.
The insurance example is synthetic, not evidence about real claims.

`tests/test_decision_pilot.py` uses the actual vendored graph, temporary SQLite
checkpoints/catalog and real bin/archive files. Sorter and specialist calls are
canned; the decision backend is a mock with a registered subclass added by the
test adapter. Sorter confidence is injected at 0.93, and a separate test uses 0.99: `decision_only`
classes reach Lane A at any sorter confidence. The blank
exhibit additionally injects a sorter result: ordinarily the sorter parks blank
text before the decision reviewer. Routing, guards and persistence are not
mocked. External HTTP is blocked.

The tests verify:

- The accepted row reaches procedural report compilation, catalog and archive.
- Each failed condition parks before extraction, retaining the sorter label and
  structured reviewer evidence, with zero LLM-reviewer calls.
- `sandbox review list`, `show` and `resolve` call the actual API endpoints
  in-process (no embedded watcher or listening socket).
- Approval with an explicit class override reaches extraction/archive both
  immediately and after rebuilding the graph over the same SQLite checkpoint.
- Rejection reaches the failed bin, not archive; a second resolve is refused.

These are mechanical integration tests, not calibration or production
qualification. They do not claim to exercise all 13 conditional graph nodes.

## Manual terminal client

Against an API you deliberately started, select its URL and token through
`MAILROOM_API_URL` / `MAILROOM_API_TOKEN`, then:

```bash
sandbox review list
sandbox review show DOC_ID
sandbox review resolve DOC_ID --decision approved --doc-type corporate_record --notes 'operator checked class'
sandbox review resolve DOC_ID --decision rejected --notes 'operator rejected'
```

Choose **one** resolve action per document. Approving resumes extraction and
can make paid model calls on the server. Approving a `reviewer_disagreement`
needs `--doc-type`, and `--doc-type` is refused with `--decision rejected`.
A timeout is not a cancellation; inspect the queue before retrying. Keep the
token in the environment, never the URL.
Use HTTPS for a remote API; HTTP is intended for a trusted loopback connection.

## Routing

Classes listed under the run's `reviewer.classes` are `decision_only`. Other
classes keep the LLM reviewer.

- A decision class reaches its reviewer at any sorter confidence, after the
  sorter's retries. A high-confidence sorter has no retries and goes straight
  to the reviewer.
- Agreement at the cutoff goes to `extract`: the reviewer's label matches the
  sorter's, both are configured classes, and the reviewer's confidence is at or
  above that class's cutoff.
- A sorter below its low band may be corrected by a reviewer at the cutoff. The
  reviewer's label must be a configured class and its confidence must meet the
  cutoff; it replaces the sorter's label.
- An unsure reviewer (below its cutoff, or no usable answer) parks for a person,
  as does any disagreement with a medium or high sorter.
- A document with no usable text parks without a backend call.
- Cutoffs are provisional until issue #208 calibrates them.

Every backend accepts every class, including `correspondence`, because the
Enron corpus is public (SAND-086 was cancelled).

## Reviewer backends

| Backend | Runs on |
| --- | --- |
| `jev` | TypeSafe, a third party (`TYPESAFE_API_KEY`). `model` must be a versioned id such as `jev-1.13.0`; `jev-latest` and `jev-preview` are refused. Endpoint jobs only. |
| `api` | The `sorter_reviewer` agent on an OpenRouter route, a third party (`OPENROUTER_API_KEY`). `model` must be an exact id such as `openai/gpt-6-luna`; `-latest` and `~` aliases are refused. Needs an `agent_routes.sorter_reviewer` entry with provider `openrouter` serving the same model. Endpoint jobs only. |
| `local` | The `sorter_reviewer` agent on your own serving route |
| `mock` | Offline tests |

`api` also needs a model different from the sorter's. Freeze a reviewer for an
experiment with `sandbox experiment create --decision-reviewer BACKEND:MODEL`
and one or more `--decision-class CLASS=CUTOFF`; the two flags must be given together.

`local` needs a model different from the sorter's and an
`agent_routes.sorter_reviewer` entry with provider `modal-vllm` or `vllm` that
serves it. Preflight compares the models activation installs, so an
`agent_models` override counts. A `vllm` route must point at a loopback,
private or link-local address, the run's own engine host, or an app in this
`MODAL_WORKSPACE`; preflight refuses anything else. Set its cutoffs per class. Its
confidence is the model's own and is uncalibrated, so tune them first.
`google/gemma-4-E4B-it` is an unmeasured candidate: the repo has no results for
it on this deployment. `config/runs/reviewer-probe-gemma4.yaml` must pass first
(`scripts/calibrate_reviewer.py --run reviewer-probe-gemma4 --probe`: a
finished run with every locked document answered, 9 of 10 answers naming a
live class with a confidence, and a mean of at most 10 s per document). Then
`config/runs/reviewer-calibration-gemma4.yaml` runs one L4 over 40 train
documents per class, capped at $1, and
`scripts/calibrate_reviewer.py --run reviewer-calibration-gemma4` picks each
class's cutoff on half the draw and reports it on the other half. Answers count
toward the class the reviewer predicted, because that class's cutoff admits
them. The script refuses a run that is not done or misses a locked document. A class
with no cutoff is left out of `reviewer.classes`, so it keeps the LLM reviewer,
which runs only on medium-confidence sorter results. The holdout is half of the usable answers predicted
as each class, so its size varies by class. `holdout_documents` is that size;
`holdout_accepted` is the denominator of the reported accuracy and its interval.
Treat the intervals as a first estimate.

## Remaining release and live gates

The current generated vendor snapshot is pinned to standalone decision-reviewer
commit `45e7075c193ffc0e8bcf2ffa982069b5e39491b6`. It is an interim branch
snapshot, not a merged release. Upstream merge/push requires explicit approval.

No live `experiment.yaml` is staged and no paid pilot has run. Before creating
or launching the 12-document live pilot, confirm all of:

1. Data terms reviewed and the credential provisioned outside chat.
2. Insurance card-like matches cleared or excluded; correspondence left out of this draw (item 3).
3. Pinned source revision and seed-42 draw: four each from contract, corporate
   record and insurance claim; untuned per-class cutoff 0.9.
4. Explicit spend cap and signed experiment review/preflight/launch approval.
5. A running review API sharing the pilot's bins, catalog and SQLite checkpoints.
6. Teardown plan and measured per-document routing/cause/cost evidence.

See `docs/superpowers/plans/2026-10-30-decision-reviewer-poc.md`, Task 9.
Serving proof, shadow pilots and qualification remain
the separate later plans in the design, not deliverables of this offline proof.
