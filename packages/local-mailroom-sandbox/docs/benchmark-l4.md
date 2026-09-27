# Modal L4 Qwen benchmark kit (specialist 5×30)

Reproducible, stable Modal+vLLM **L4** runs of **Qwen/Qwen3-8B** for
specialist extract cost extrapolation to the full mailroom-dataset
(`FAMILY_CORPUS_SIZE=3302` at `FAMILY_HF_REVISION`).

## Pins (do not drift)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B` (bf16 default; AWQ optional — see cost-saver path) |
| GPU | `L4` (`max_containers=1`, `min_containers=0`) |
| Image | `v0.29.0` |
| `max_model_len` | `16384` |
| Job concurrency | per-doc-type (DMR-078): correspondence/insurance **5**, corporate/contracts **4**, merger **3** |
| Scaledown | `120` s attended (DMR-076); restore **600** for unattended/overnight |
| Generation budgets | `job/specialist_posture.py` → overlay `max_tokens` / `max_input_chars` (fit Qwen 16k) |
| Cost / wall abort | `job.cost_cap_usd` + `job.max_wall_seconds` per run-30 YAML (runner fails loud) |
| Merger specialist | `merger_agreement_specialist` (dedicated; issue #9) — not `contracts_specialist` |
| Dataset | `Lucius-Morningstar/mailroom-dataset` @ `46a4d3c240a36671cde0182fff4960f6b8b73aca` |
| `sample_seed` | `42` |
| Strata limit | `30` per class (150 docs total) |
| Modal accounts | **Two operators / two wallets** (DMR-077); Hermes `hermes-agent-jjb` is Track A default |

Run YAMLs: `config/runs/run-30-*-specialist.yaml` (150 docs total).  
Suite manifests: `config/runs/suites/run-30-specialists-{track-a,track-b,full}.yaml`.

## Two-operator split (DMR-077 — preferred)

Run the five specialists on **two people**, **two warmed 1×L4 apps**, on
**two separate Modal accounts** (separate credit balances). Each operator
chains their track on **one** warm app — **no teardown between their
configs**; teardown only after their last run.

**Never share one Modal token / `~/.modal.toml` profile across people.**

### Chosen partition

| Track | Configs (order) | Likely busy | Likely total (w/ overhead) |
| --- | --- | --- | --- |
| **A** (3) | contracts → corporate_records → correspondence | ~42.5 min / ~$0.57 | ~49 min / ~$0.65 |
| **B** (2) | merger → insurance_claims | ~39.4 min / ~$0.53 | ~44 min / ~$0.59 |

**Why this split:** merger + contracts are the two heaviest (DMR-075
sec/doc bands). Putting both on one operator stacks ~47.5 min busy;
instead Track A takes contracts + mid + light, Track B takes merger +
insurance. Wall/$ stays within ~$0.06 / ~5 min. (Alternative
merger+insurance+correspondence vs contracts+corporate is less balanced
on wall.)

Pre-flight:

```bash
sandbox metrics estimate-suite --suite track-a
sandbox metrics estimate-suite --suite track-b
# single-operator alternative still works:
sandbox metrics estimate-suite --suite full
```

### Modal profiles (names only — no secrets in git)

| Track | Env (optional override) | Default profile name |
| --- | --- | --- |
| A | `SANDBOX_MODAL_PROFILE_TRACK_A` | `hermes-agent-jjb` (Hermes Agent Gmail) |
| B | `SANDBOX_MODAL_PROFILE_TRACK_B` | **required** — set to the second account’s `modal profile` name |

```bash
# Operator A
export SANDBOX_MODAL_PROFILE_TRACK_A=hermes-agent-jjb   # optional; this is the default
modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current   # must print hermes-agent-jjb

# Operator B (separate laptop / separate ~/.modal.toml credentials)
export SANDBOX_MODAL_PROFILE_TRACK_B=<second-account-profile-name>
modal profile activate "$SANDBOX_MODAL_PROFILE_TRACK_B"
modal profile current   # must print that second profile — never Hermes if A uses Hermes
```

Tokens live only in each operator’s `~/.modal.toml`. Do **not** export
`MODAL_TOKEN_*` into a shared `.env` or chat.

### Operator A runbook

```bash
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_CONTAINERS=1
export MODAL_VLLM_SCALEDOWN_SECONDS=120
export MODAL_VLLM_API_TOKEN="$(openssl rand -hex 24)"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
sandbox run benchmark-check --suite track-a
modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py
# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# Print the ordered loop, or execute it:
sandbox run suite --suite track-a
# sandbox run suite --suite track-a --execute --job-mode endpoint

# Equivalent explicit loop (no teardown between):
for cfg in \
  config/runs/run-30-contracts-specialist.yaml \
  config/runs/run-30-corporate-records-specialist.yaml \
  config/runs/run-30-correspondence-specialist.yaml
do
  sandbox run preflight --config "$cfg" --live
  sandbox run start --config "$cfg" --job-mode endpoint --watch
done

./deploy/teardown_vllm.sh   # ONLY after correspondence
```

### Operator B runbook

```bash
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_CONTAINERS=1
export MODAL_VLLM_SCALEDOWN_SECONDS=120
export MODAL_VLLM_API_TOKEN="$(openssl rand -hex 24)"
export SANDBOX_MODAL_PROFILE_TRACK_B=<second-account-profile-name>

modal profile activate "$SANDBOX_MODAL_PROFILE_TRACK_B"
sandbox run benchmark-check --suite track-b   # uses Track B profile (not Hermes)
modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run suite --suite track-b
# sandbox run suite --suite track-b --execute --job-mode endpoint

for cfg in \
  config/runs/run-30-merger-specialist.yaml \
  config/runs/run-30-insurance-claims-specialist.yaml
do
  sandbox run preflight --config "$cfg" --live
  sandbox run start --config "$cfg" --job-mode endpoint --watch
done

./deploy/teardown_vllm.sh   # ONLY after insurance
```

### After both tracks finish

```bash
sandbox metrics extrapolate --run run-30-contracts-specialist --corpus-size 3302 --docs-per-day 10000
sandbox metrics compare --runs run-30-contracts-specialist,run-30-merger-specialist,run-30-corporate-records-specialist,run-30-correspondence-specialist,run-30-insurance-claims-specialist
```

## Single-operator full suite (alternative)

When only one Modal wallet is available, keep the original warm-once path
(`--suite full` / all five configs). Deploy once → five classes → teardown
after the fifth — same spend posture, longer wall (~1.5× one track).

```text
warm deploy ──► contracts ──► merger ──► corporate ──► correspondence
           ──► insurance ──► ./deploy/teardown_vllm.sh
```

```bash
modal profile activate hermes-agent-jjb
sandbox run benchmark-check --suite full
sandbox run suite --suite full
# or: sandbox metrics estimate-suite --suite full
```

Every run-30 YAML header still documents the warm-once box.

## Loud gate

```bash
# Per-config (unchanged):
sandbox run benchmark-check --config config/runs/run-30-contracts-specialist.yaml
# Per-track:
sandbox run benchmark-check --suite track-a
sandbox run benchmark-check --suite track-b
# exits 1 if wrong Modal profile / unpinned image / concurrency≠posture /
# scaledown≠120 / min_containers≠0 / limit≠30 / missing DMR-074 local prompts /
# missing cost_cap or max_wall / wrong task for 1:1 specialist map
```

## Per-doc-type posture (DMR-078)

| Run | Task | Conc. | max_tokens | max_input_chars | cost_cap | max_wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| correspondence | `correspondence_specialist` | 5 | 2048 | ~15k | $0.40 | 2400s |
| insurance | `insurance_claims_specialist` | 5 | 3072 | ~20k | $0.50 | 3000s |
| corporate | `corporate_records_specialist` | 4 | 4096 | ~22k | $0.55 | 3600s |
| contracts | `contracts_specialist` | 4 | 4096 | ~35k | $0.80 | 4800s |
| merger | `merger_agreement_specialist` | 3 | 4096 | ~36k | $1.00 | 5400s |

Source of truth: `src/mailroom_sandbox/job/specialist_posture.py` (also drives
estimate-suite sec/doc + token tables and overlay budgets). Short docs raise
concurrency to fill continuous batching; long MAUD filings lower it to protect
KV. Input caps fit `max_model_len=16384` so contracts no longer advertise
100k-char windows that cannot fit Qwen on L4.

## Deploy knobs (shared)

```bash
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_CONTAINERS=1
export MODAL_VLLM_SCALEDOWN_SECONDS=120   # attended; restore 600 unattended/overnight
export MODAL_VLLM_API_TOKEN="$(openssl rand -hex 24)"

modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py
# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm
```

## Cost honesty

- Prefer `MODAL_BILLED_GPU_SECONDS=<suite wall>` after the track(s) for GPU $.
- Token $ needs OpenAI-compatible `usage` on items — missing tokens → fields
  omitted (never silent `$0`); extrapolate refuses if both token and GPU $/doc
  are absent.
- Linear extrapolation = `combined_$/doc × N`. `with_overhead` adds one
  cold-start + one scaledown window. Confidence notes always print.

## Pre-flight cost estimate (no GPU spend)

```bash
sandbox metrics estimate-suite                  # all five (single-wallet default)
sandbox metrics estimate-suite --suite track-a
sandbox metrics estimate-suite --suite track-b
sandbox metrics estimate-suite --suite full
sandbox metrics estimate-suite --scaledown-seconds 600   # unattended what-if
sandbox metrics estimate-suite --json
```

Defaults assume Modal L4 @ $0.80/GPU-hr, concurrency 4, one warm app across
the listed configs, cold-start 120 s + scaledown (from YAML, **120** s
attended) + 60 s inter-run gaps. Override with `--sec-per-doc`,
`--gen-tok-per-s`, `--gpu-usd-per-hour`. After a live suite, prefer
`sandbox metrics extrapolate --run …` on measured items.

## Cost-saver path (optional — keep default suite on bf16 Qwen+L4)

| Lever | When | Expected save | Safe for default suite? |
| --- | --- | --- | --- |
| One warm app per track, teardown after last | Always | Avoids extra scaledown tails | **Yes** (runbook default — mandatory) |
| Two-operator A∥B (DMR-077) | Two Modal wallets | ~½ wall-clock vs full serial | **Yes** |
| `scaledown_seconds: 120` + `MODAL_VLLM_SCALEDOWN_SECONDS=120` | Attended operator | ~(600−120)/3600×$0.80 ≈ **$0.11** | **Yes** (DMR-076 default); restore 600 unattended |
| AWQ (`sandbox modal-matrix env Qwen/Qwen3-8B-AWQ`) | After DMR-068 gate (≥1.5× docs/min **and** ≥98% accuracy) | ~30–40% of **busy** GPU $ | **No** until gated — optional path only |
| Lower specialist `max_tokens` (taxonomy 8192) | After measuring p95 completion ≪ 8192 | Decode time only | **No** without histogram — truncates JSON |
| Teardown between classes | Never for cost | **Negative** (extra scaledown) | No |

### Optional AWQ path (one command away — not the default)

DMR-068 accuracy gate is **not** green in-repo for flipping the default
bf16 suite. Keep `run-30-*-specialist.yaml` on `Qwen/Qwen3-8B`. To try AWQ
for a whole-suite swap (not one class):

```bash
eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"
modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py --strategy recreate
# re-point VLLM_BASE_URL, cutover/health, then the same run YAMLs
# (benchmark-check accepts AWQ as a warning, not an error)
```

Do **not** edit run-30 YAMLs for AWQ — those stay Qwen+L4 bf16 for the
cost-eval baseline. Copy a YAML only if an alternate scorecard needs matching
`engine.model` / quantization fields.

## Merger note

`run-30-merger-specialist` uses **train** split (test has only ~17 merger
rows) and task `merger_agreement_specialist` (dedicated MAUD agent — not
`contracts_specialist`). Document that in any published scorecard.

## Specialist prompts (pinned local)

Each run-30 YAML pins the task agent's production text under
`config/prompts/` (not Langfuse floating `production`):

| Run | Agent | Local stem | Source |
| --- | --- | --- | --- |
| contracts | `contracts_specialist` | `contracts_specialist_v33` | vendored `PROMPT_VERSIONS` (mailroom production) |
| merger | `merger_agreement_specialist` | `merger_agreement_specialist_production` | vendored `SYSTEM_PROMPT` + MAUD doctrine |
| corporate-records | `corporate_records_specialist` | `corporate_records_specialist_production` | vendored `SYSTEM_PROMPT` + doctrine |
| correspondence | `correspondence_specialist` | `correspondence_specialist_production` | vendored `SYSTEM_PROMPT` + doctrine |
| insurance-claims | `insurance_claims_specialist` | `insurance_claims_specialist_production` | vendored `SYSTEM_PROMPT` + doctrine |

Refresh: `python scripts/sync_specialist_prompts.py` (or `--check` after vendor sync).
Entity-extraction experimental `contracts_specialist_v34+` are **not** the
mailroom production pin — do not swap without an explicit scorecard decision.
`sandbox run benchmark-check` hard-fails if these local pins drift.

## Advanced: swap model / GPU (not the default path)

Deploy knobs are entirely env-driven (`deploy/modal_vllm.py`). Catalog rows
live in `config/models.yaml` `modal_models:`. **Do not edit run-30 YAMLs**
for a one-off swap — those stay Qwen+L4 for the cost-eval suite.

```bash
sandbox modal-matrix list
sandbox modal-matrix show Qwen/Qwen3-8B-AWQ
eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"          # L4 + AWQ + 32k
# eval "$(sandbox modal-matrix env Qwen/Qwen3-14B)"           # A100-40GB bf16
# eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-FP8)"        # H100 FP8
# eval "$(sandbox modal-matrix env Qwen/Qwen3-8B --gpu A10G)" # GPU override
modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py --strategy recreate
# re-point VLLM_BASE_URL, then sandbox cutover/health --profile modal-vllm
```

Bare env (same effect):

```bash
export MODAL_VLLM_MODEL=Qwen/Qwen3-14B-AWQ
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_QUANTIZATION=awq
export MODAL_VLLM_MAX_MODEL_LEN=32768
export MODAL_VLLM_TP_SIZE=1
# multi-GPU: MODAL_VLLM_GPU=A100-80GB:2 MODAL_VLLM_TP_SIZE=2
```
