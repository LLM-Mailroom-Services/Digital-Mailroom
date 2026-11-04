# Design and launch an experiment

The `sandbox experiment` commands compose the existing locked run lifecycle and
vendored mailroom pipeline. They select a design, prepare paired document draws,
review every configuration, require initials for spend, smoke a small locked subset,
launch sequential cells, stop their managed apps, and compile outcome reports.
Creating or reviewing an experiment never calls Hugging Face, an LLM, or Modal.
Preflight may download the pinned Hub data; it does not deploy or probe an LLM.

## Select the design and settings

```bash
sandbox experiment designs
sandbox modal-matrix list
sandbox agents list
sandbox experiment create --help
```

`single` creates one cell. `sand42` creates the four replica/concurrency cells
`1×8`, `1×16`, `2×8`, and `2×16`. Each class uses the same pinned revision, seed,
and exact prepared dataset bytes across cells; preflight refuses different draws.
The default task runs all five specialists, with 50 documents per class and
proportional subclass quotas from the SAND42 templates. Sample sizes smaller than
the number of subclasses cover only the largest strata; review `strata_actual`
before signing. Repeated `--doc-class` and `--subclass` narrow the corpus.

```bash
sandbox experiment create sand42-next \
  --design sand42 --samples 50 --seed 42 \
  --model Qwen/Qwen3-8B-AWQ --gpu L4 \
  --set engine.vllm.max_num_seqs=16 \
  --set engine.vllm.gpu_memory_utilization=0.90 \
  --max-tokens 8192 --temperature 0.1 \
  --trace-sink langfuse --cost-cap-usd 1.00 --max-wall-seconds 2400
```

By default this writes `config/experiments/sand42-next/experiment.yaml` and its
run YAMLs. `--output DIR` chooses another new directory. Existing directories
are never overwritten. `--set PATH=YAML_VALUE` changes existing nested fields,
including vLLM options, prompts, job settings, and per-agent generation knobs;
unknown paths fail. `--design single` also accepts `--replicas` and `--concurrency`.
`--gpu H100` selects another GPU class; `--gpu A100-80GB:2` requests tensor parallel
GPUs within each container, while `--replicas 2` means independent containers.

`--cost-cap-usd` (GPU), `--max-wall-seconds` (the wall ceiling after which the run
aborts and its fleet is torn down) and `--api-cost-cap-usd` (OpenRouter token
spend) are optional. Create fills each unset ceiling with a recommendation derived
from the design (`src/mailroom_sandbox/job/budget_advice.py`): documents, effective
concurrency (at most 4 in flight per Modal replica), the task's per-document latency
band, cold start and scaledown, the GPU rate of every Modal app the run deploys, and
the token price and calls per document of every API model, with a 1.5× margin. A GPU
cap is only recommended for runs that warm a Modal GPU; an API cap only for runs that
bill API tokens. Flags and `--set job.*` values win. Create prints configured against
recommended for each run, and `experiment review` lists the same block per run under
`budget` (with `warnings` wherever a ceiling is unset or below its recommendation). The
sand42 example above sets `--cost-cap-usd 1.00`, which create flags as below the merger
recommendation. These are planning figures: replace them with a smoke run's
measurements when you have one.

Hub selectors are `--dataset`, `--dataset-config`, `--split`, `--revision` (a full
commit SHA), `--samples`, `--seed`, `--doc-class`, and `--subclass`. The default is
the family's frozen dataset SHA and all splits. `--local-dataset FILE.jsonl` uses
a local fixture instead. New studies have distinct run IDs and app names.

## Full pipeline and per-agent models

Use `--task pipeline` to run the complete vendored mailroom graph. Each selected
class contributes `--samples` documents to the combined dataset. Reviewers stay
enabled; the computational report compiler remains deterministic and has no model.

API-only default:

```bash
sandbox experiment create pipeline-api --task pipeline \
  --provider openrouter --model qwen/qwen3.7-flash \
  --agent-model judge=deepseek/deepseek-v4-flash \
  --samples 10 --trace-sink langfuse
```

Modal/vLLM default with API agents (hybrid):

```bash
sandbox experiment create pipeline-hybrid --task pipeline \
  --model Qwen/Qwen3-8B-AWQ --gpu L4 --samples 10 \
  --agent-route sorter=openrouter:qwen/qwen3.7-flash \
  --agent-route judge=openrouter:deepseek/deepseek-v4-flash \
  --agent-route contracts_specialist=modal-vllm:Qwen/Qwen3-8B \
  --trace-sink langfuse
```

Larger specialists (SAND-079): `--specialist-tier mid` serves the specialists
from `Qwen/Qwen3.5-35B-A3B`, and `--specialist-tier full` from the judge's
`Qwen/Qwen3.5-27B` app. See
[providers](setting-up/providers.md) (Specialist tiers) for the tier table.

```bash
sandbox experiment create pipeline-full --task pipeline \
  --specialist-tier full --samples 10 --trace-sink langfuse
```

`--agent-model NAME=MODEL` changes a model on its current transport.
`--agent-route NAME=PROVIDER:MODEL` changes both. Routes override the global
provider, and explicit agent-model choices win last. Model/route selections are
locked and hashed; start/resume refuses configuration drift. The sandbox adapter
uses the same resolution seam for native and LangChain agents, so API credentials
are never borrowed for a GPU endpoint or vice versa. Unknown and retired agents
are rejected.

For a distinct endpoint, credential variable, GPU, or serving configuration, put
an explicit route in a file and pass `--agent-route NAME=@path/to/route.yaml`:

```yaml
provider: modal-vllm
model: Qwen/Qwen3-8B-AWQ
modal:
  app: sandbox-vllm-my-study-contracts
  gpu: L4
  max_containers: 1
  min_containers: 0
  scaledown_seconds: 120
  image_tag: v0.29.0
vllm:
  max_model_len: 32768
  quantization: awq_marlin
  max_num_seqs: 16
  enforce_eager: false
  enable_prefix_caching: true
```

Managed routes derive their URL from `MODAL_WORKSPACE` and `modal.app`. Share the
same app/configuration across agents to share a model deployment; incompatible
settings for the same app are refused. Shorthand routes with identical settings
share a generated app. All managed apps are sandbox-scoped and are stopped in
reverse order even when another deployment or smoke fails. Existing active apps
are refused rather than replaced or stopped.

An existing OpenAI-compatible endpoint uses `provider: vllm`, `model`, `base_url`,
and optionally `api_key_env`. A general API uses `provider: api`, `model`,
`base_url`, and a required `api_key_env`. OpenRouter defaults to
`OPENROUTER_API_KEY`. Store actual credentials in environment variables or `.env`,
not in YAML; route URLs reject embedded credentials/query parameters. Existing
`run start --config run.yaml --agent-route ...` also accepts these route choices;
`run resume --config ...` verifies them against the lock.

## Decision reviewer

A decision reviewer is a second model that re-reads the documents of its decision
classes in the full pipeline before extraction (the Lane A check). Freeze one with two flags, which
must be given together:

- `--decision-reviewer BACKEND:MODEL` picks the backend and its model:
  - `local:MODEL` runs the `sorter_reviewer` agent on the run's in-house route. The
    route must serve MODEL, and MODEL must differ from the sorter's model.
  - `api:PROVIDER/MODEL` runs the same agent on an OpenRouter route, pinned to one
    id such as `api:openai/gpt-6-luna`. Unpinned ids (`-latest`, `~` aliases) are refused.
  - `jev:jev-X.Y.Z` calls TypeSafe's Jev through Pydantic AI (`pip install -e ".[decision]"`,
    `TYPESAFE_API_KEY`). Only a versioned id is accepted; mock runs and Modal jobs refuse it.
  - `mock:mock` answers from a fixed table, offline. Use it for wiring checks.
- `--decision-class CLASS=CUTOFF` (repeatable) names each class the reviewer handles,
  with its cutoff in [0, 1]. Names must be live taxonomy classes. No backend refuses
  a class, correspondence included.

Routing, for a decision class:

- The class reaches its reviewer at any sorter confidence, after the sorter's retries.
- Agreement at the cutoff (confidence at or above it) goes to extract.
- A sorter below its low band may be corrected by a reviewer at the cutoff.
- An unsure reviewer, or disagreement with a medium or high sorter, parks the
  document for human review (`sandbox review list|show|resolve`).
- Cutoffs are provisional until issue #208.

```bash
sandbox experiment create pipeline-reviewed --task pipeline \
  --provider openrouter --model qwen/qwen3.7-flash \
  --agent-route sorter_reviewer=openrouter:openai/gpt-6-luna \
  --decision-reviewer api:openai/gpt-6-luna \
  --decision-class contract=0.90 --decision-class merger_agreement=0.90 \
  --decision-class corporate_record=0.90 --decision-class correspondence=0.90 \
  --decision-class insurance_claim=0.90 \
  --samples 10 --trace-sink none
```

The reviewer is written to the run's `reviewer:` block and into the pipeline's
taxonomy, so it governs routing in `--task pipeline` runs. Preflight checks it:
`local` and `api` need a `sorter_reviewer` route that serves the reviewer's model.

### Reuse the serving image

Modal experiments deploy from the workspace's published `sandbox-vllm:<image_tag>`, so
run `sandbox modal publish-image` once per Modal account first. `--no-named-image` on
`experiment create` builds the image instead.

### Calibrate the cutoffs

`config/runs/reviewer-calibration-luna.yaml` runs `openai/gpt-6-luna` as the reviewer
over 200 labelled training documents (40 per class) with a `$0.25` API cap. Its header
estimates about $0.07. Start it through the signed run lifecycle (a paid run asks for
initials unless `--initials` is given), then calibrate:

```bash
sandbox run preflight --config config/runs/reviewer-calibration-luna.yaml
sandbox run start --config config/runs/reviewer-calibration-luna.yaml
python scripts/calibrate_reviewer.py --run reviewer-calibration-luna --probe
python scripts/calibrate_reviewer.py --run reviewer-calibration-luna
```

Each class also reports `top_confidence`, `top_confidence_documents` and
`top_confidence_wrong`. Wrong answers at the top confidence are confidence saturation:
no cutoff removes them. This run samples ordinary documents, so it does not measure
wrong corrections on hard documents; issue #208 tracks that separately.

- `--probe` checks a finished run is fit to calibrate: at least 9 taxonomy-valid
  answers and a mean of at most 10 s per document. It exits 1 when the run fails.
- Without `--probe`, each class's answers are grouped by the class the reviewer
  predicted and split in half by a seeded shuffle (`--seed`, default 42). The cutoff
  is the lowest confidence at which the first half reaches `--target` accuracy
  (default 0.95); the second half reports what that cutoff delivers. A class that
  never reaches the target gets `null` and should not be configured as reviewed.
- The script refuses a run that is not done or is missing locked documents. It prints
  the per-class result and writes `reports/reviewer-calibration/<run>.json`.

`config/runs/pipeline-luna-qwen-smoke.yaml` is the matching smoke: the full pipeline
over OpenRouter on the 7-row fixture, with Qwen3.7 Flash as the engine model, judge
and boss, Luna as the `sorter_reviewer`, and an API reviewer at 0.90 for all five
classes. Its cutoffs are provisional until the calibration has run.

## Review, authorize, smoke, and launch

Copy `config/.env.example` to the checkout's `.env` and set the credentials and
`MODAL_WORKSPACE` needed by your routes. The CLI loads the checkout's root `.env`
first and then `config/.env`; exported environment variables take precedence over
both, and root `.env` takes precedence over `config/.env`. Both files are
gitignored. A route's `api_key_env` can name any valid environment variable: put
its value in either file or export it, and put only the variable name in YAML.
Local `HF_TOKEN` is used for local Hub access; managed Modal downloads use the
named Modal Hugging Face secret described in the template.

The selected trace
sink must be configured too: Langfuse is the default; `none`, explicit `otlp`, and
an optional Phoenix sidecar are available. Phoenix does not replace The-Mailroom's
Langfuse sink. Live tracing needs `pip install -e ".[observability]"`; the Modal
launcher requires the verified `modal==1.6.2` CLI.

```bash
sandbox experiment review --config config/experiments/pipeline-hybrid/experiment.yaml
sandbox experiment preflight --config config/experiments/pipeline-hybrid/experiment.yaml
sandbox experiment launch --config config/experiments/pipeline-hybrid/experiment.yaml
```

Preflight refuses a live Modal run whose `job.concurrency` is above 1 while
`engine.vllm.max_inputs` is 0: the GPU would bill while requests queue. Mock runs
are not checked.

Launch displays every cell's complete settings, prepared row counts and hashes,
prompts, generation limits, models, routes, managed GPUs/replicas, deployment
environment, trace sink, and smoke/run budgets. It then asks for **2–6 initials**.
For a terminal without interactive input, explicitly supply `--initials JB` after
reviewing the output. There is no automatic `--yes` authorization.

Initials are a local operator attestation, not cryptographic identity verification.
The private `spend-authorization.json` receipt binds initials, time, the generation,
configuration, effective endpoints, and campaign smoke settings. Changed settings,
endpoints, re-locked data/prompts, or an expired receipt require a new signature.
The lower-level `run start`, `run resume`, and paid `run preflight --live` also
require a valid signed review. Mock endpoint runs do not require spend approval;
remote Modal workers still cost money even when their LLM calls are mocked.

Only after signing does the launcher prewarm/deploy, verify endpoints and served
models, and execute a **separate locked smoke dataset**. The default is one document
per specialist run; pipeline smoke covers one document per selected class.
`--smoke-rows` and `--smoke-cost-cap-usd` configure the smoke budget when creating
the experiment. A failed, missing, or partially processed smoke blocks the full
run. Every explicit route receives its own connectivity/chat check.

Cost caps are runtime estimates of GPU time, not hard invoice limits. Modal image
builds, CPU prewarm, cold boot, scaledown, concurrent replicas/model deployments,
and in-flight calls can add charges. OpenRouter is token-billed, so the GPU cap
does not limit it: `api_cost_cap_usd` does. It prices every observed token at the
highest price among the run's API models and is checked before each document. A
paid run that sends any agent to an unpriced model is refused. The review lists
the three ceilings and each API model's price. Configure provider-side spending
limits when a hard billing ceiling is required. Teardown runs after each cell on
success, failure, or interruption.

## Observe and analyze

In another terminal:

```bash
sandbox experiment watch --config config/experiments/pipeline-hybrid/experiment.yaml
sandbox board --probe-interval 60
```

The browser observer follows the campaign's `current-run` file as jobs change.
The services strip reads published doctor snapshots; periodic board checks stay
offline unless `--live` is explicitly supplied (live Modal probes can keep a GPU
warm). Full pipeline runs persist per-document evidence and update progress.

```bash
sandbox experiment report --config config/experiments/pipeline-hybrid/experiment.yaml
sandbox run status --config config/experiments/pipeline-hybrid/runs/<run-id>.yaml
sandbox run cancel --run-id <run-id>
```

`report.md` and `report.json` beside the manifest show successful/expected counts,
errors, configuration links, scorer aggregates, stored per-document score means,
and paired cell deltas when dataset bytes and complete coverage match. The
`## Quality` table gives each run's headline (`overall_extraction_score`), its
class-native metric (CUAD category F1, MAUD accuracy or field F1), schema
adherence, token totals and median latency; `## Paired comparisons` gives each
cell's deltas against the first complete cell of its task, with the paired 95% CI and the
better/worse/tie split. `## Sand42 metrics` gives the card contract of
[SAND42-EXPERIMENT-DESIGN.md](SAND42-EXPERIMENT-DESIGN.md) section 5 for every run: ok rate and
quality with 95% CIs over documents attempted, schema-valid rate, cost per 1k usable records,
docs/min/GPU, goodput at the SLO, latency, tokens and review rate. Mock and API-only runs
show `—` in the cost column, because they bill no GPU. An API-only run's token spend is
`runs[].sand42.api_cost` in `report.json` when its models are priced. Each run that has
completed documents gets a full card at `cards/<run-id>.card.json` beside the report
(runs with none have no card), and `report.json` holds the same summary under
`runs[].sand42`. The card is the per-run JSON that `sandbox run card --config` reads for
the SAND-042 cell reports under `reports/SAND42/`.

Full-pipeline items store per-document `class_correct`, `stage_correct`, the extraction scores,
tokens and the review outcome (`review_causes`, `review_verdict`, `escalation_reason`,
`reviewer_doc_type`, `reviewer_confidence`). `## Pipeline routing` shows stages, review rate and
accuracy for the run and each class, then the review causes. A pipeline run mixes
classes, so it meets its SLO only when every class meets its own. Incomplete
runs stay visibly incomplete. Native dated quality/serving artifacts remain under
`reports/`; a Modal job's mailroom state sits under `<run>/mailroom` on the `sandbox-runs`
Volume. A failed document scores 0.0 in the quality mean and its
interval, even when it kept a partial score; a document with nothing to score
it against is counted as unscored and left out. Re-running
launch rechecks locked configurations and skips completed jobs. A failed smoke
must be investigated and safely reset with the existing run lifecycle before retry.

For an offline end-to-end check, add `--mock --local-dataset FILE.jsonl
--trace-sink none` to create. `create` refuses a local file with fewer rows of a
class than `--samples`, and drops the template's Hub subclass quotas when the file
cannot fill them. The default tests use fake tools and local data; the opt-in CLI
contract checks in `tests/test_service_cli_smoke.py` do not deploy.

## Pre-flight smoke before an experiment day

```bash
sandbox datasets pull                 # once: the pinned Hub dataset into data/cache/
python scripts/smoke_campaign.py      # about a minute; no provider, deploy or spend
```

The script runs three mock campaigns through create, preflight, launch and report:
the five specialists, the paired `sand42` grid (contracts and mergers) and the full
connected pipeline. It fails unless every run completes, paired cells share dataset
bytes, every run's extraction headline is 1.0 and the pipeline classifies every
document correctly. Pipeline stage is reported but not gated: llm-mailroom's
extraction coverage check currently sends every contract and merger agreement to
review even for a perfect answer (SAND-081). A mock specialist answers with the
row's ground truth rewritten into the specialist's output schema
(`mock_llm.oracle_extraction`): CUAD spans become `cuad_clauses`, MAUD labels
become `maud_clauses`, JSON-string lists become lists, and ground-truth-only keys
are dropped. That answer scores 1.0 on every scoreable row of the pinned corpus,
so anything less means ground truth or predictions no longer reach the Dojo
scorers in the shape they read. Mock scores check the wiring, never a model.
Run stores go to a temporary directory; `--keep DIR` keeps them for inspection.
