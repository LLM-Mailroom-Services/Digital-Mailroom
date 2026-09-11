# Quickstart — the full CLI in one page

Everything you need to install the sandbox and drive it with `sandbox`.
Every command below was exercised against a **fresh in-repo `.venv`** with
`pip install -e ".[dev]"` (DMR-058) — no other install, no network required
for the offline paths. Deep dives: [`SANDBOX-GUIDE.md`](SANDBOX-GUIDE.md)
(setup/ops), [`jobs.md`](jobs.md), [`evals.md`](evals.md),
[`remote-serving.md`](remote-serving.md), [`providers.md`](providers.md).

## 0. Install (in the repo, into a repo-local venv)

```bash
cd <checkout>                        # repo root (or packages/local-mailroom-sandbox in the monorepo)
python3 -m venv .venv                # deps live INSIDE the repo — never the machine env
.venv/bin/pip install -e ".[dev]"    # base + pytest + hf hub (datasets pull)
cp config/.env.example .env          # profiles/tracing knobs (edit if needed)
export PATH="$PWD/.venv/bin:$PATH"   # or call ./.venv/bin/sandbox explicitly
```

Optional extras, only when you need them:

| Extra | Adds | Needed for |
| --- | --- | --- |
| `[pipeline]` | langchain stack (vendored mailroom's live paths) | `legalbench --suite`, live mailroom agent calls |
| `[hf]` | `huggingface_hub`, `pyarrow` (also in `[dev]`) | `sandbox datasets pull`, `hf-pilot` |
| `[observability]` | Langfuse SDK + OTEL | live tracing (`trace.sink: langfuse`) |
| `[deploy]` | Modal SDK 1.5.5 (pinned) | `sandbox run --job-mode modal`, `deploy/modal_vllm.py` |
| `[notebooks]` | Jupyter + pandas/matplotlib | `sandbox up --compose-profile jupyter` |

The family code is **already vendored and tracked** (`vendor/llm-mailroom`
v0.6.0, `vendor/llm-dojo-scoring` v0.12.2) — a fresh checkout runs offline.

## 1. The command surface at a glance

```
sandbox up | down | health | pull-models | fetch-deps | cutover
       | agents list|show | pipeline watcher|api
       | pilot | hf-pilot | legalbench
       | eval <task> | matrix | metrics compare
       | datasets pull|prepare | traces export
       | profiles | tunnel plan|up|status|down
       | run preflight|start|status|resume|cancel|list
       | prompts list|show
```

Global flags (before the subcommand is NOT where they live — see §2):

```
--profile NAME         # SANDBOX_PROFILE env works too
--model TAG            # override EVERY agent's model
--agent-model NAME=TAG # surgical per-agent override (repeatable, wins last)
--prompt STEM          # local prompt variant stem, e.g. sorter_local_v0
```

## 2. Flag placement rules (the only real gotcha)

- `--profile` goes on the **group** command for `tunnel` and `run`:

  ```bash
  sandbox tunnel --profile vllm-remote plan        # NOT: tunnel plan --profile …
  sandbox run --profile modal-vllm preflight --config config/runs/x.yaml
  ```

- Everywhere else `--profile` is accepted on the leaf command
  (`sandbox cutover --profile ollama`, `sandbox eval sorter --profile ollama`, …).
- A `--profile` **before** the subcommand is clobbered by the subparser
  default — always pass it after, or set `SANDBOX_PROFILE`.

## 3. Stack bring-up (Docker/Ollama)

```bash
sandbox up                              # compose: langfuse + provider (add --compose-profile jupyter)
sandbox up -d                           # detach
sandbox down                            # stop compose stack
sandbox pull-models                     # ollama pull qwen3:8b (+ profile pull_models)
sandbox pull-models qwen3:14b qwen3:8b  # explicit list
sandbox health                          # provider /v1/models + chat + langfuse + phoenix
```

- `health` exits 1 with a JSON report when anything is down (no traceback).
- No Docker daemon / no Ollama → clean one-line errors, exit 1.

## 4. Vendored family (self-containment)

```bash
sandbox fetch-deps        # refresh vendor/ snapshots from pinned tags (NETWORK, optional)
sandbox fetch-deps --visualizer   # + clone The-Mailroom
```

`fetch-deps` re-snapshots the pinned upstream trees into `vendor/` and leaves
the diff for you to commit. It is layout-aware and non-destructive — a bad
clone never half-wipes the tracked tree (DMR-058).

## 5. Config surface — see what is wired where

```bash
sandbox profiles                        # list provider profiles (ollama, vllm-local, modal-vllm, …)
sandbox agents list                     # effective agent→provider→model assignments (JSON)
sandbox agents show sorter              # one agent incl. observation + dojo profile
sandbox cutover                         # assignment table for the active profile
sandbox cutover --agent-model judge=qwen3:14b   # surgical override, wins last
sandbox cutover --profile modal-vllm    # any profile
sandbox prompts list                    # all pipeline-agent prompt names (local + Langfuse)
sandbox prompts show sorter             # resolution: source / name / version / sha
sandbox prompts show sorter --variant sorter_local_v0   # local variant stem
```

## 6. Datasets & fixtures

```bash
sandbox datasets prepare                # offline: load/clean fixtures → data/runtime/prepared/ (no network)
sandbox datasets pull                   # LIVE pinned Hub pull (NETWORK):
#   Lucius-Morningstar/mailroom-corpus@eafe1ab4c0d3 (ground_truth/test) → data/cache/…, sha256-verified
sandbox datasets pull --max-rows 50 --config ground_truth --split test --revision <sha-or-tag>
sandbox datasets pull --dataset Lucius-Morningstar/mailroom-corpus --max-rows 20
```

- `pull` exits 1 on any failure (live-or-loud) — a clean `error: …` line, with
  a `pip install -e ".[hf]"` hint when the Hub client is missing.

## 7. Smoke the machinery (no LLM) — always works offline

```bash
sandbox pilot --mock                     # full fixture pilot through the connected machinery
sandbox hf-pilot --check                 # verify fixture/GT schema without running
sandbox hf-pilot --mock                  # HF docclass mini-pilot, mocked
sandbox legalbench --task contract_qa --mock             # offline LegalBench fixture
sandbox legalbench --task contract_qa --n 5 --seed 42    # seeded draw (never first-N)
sandbox legalbench --task contract_qa --suite --n 3 --seed 7 --mock
#   vendored real-suite path: needs `pip install -e ".[pipeline]"` + the CUAD
#   corpus (`python scripts/fetch_full_cuad.py` inside the vendored tree)
sandbox eval sorter --mock               # isolated agent eval
sandbox eval judge --mock
sandbox eval pipeline --mock             # connected graph scoring (full 13-node path)
sandbox eval pipeline --mock --connected # same (flag is accepted on pipeline)
sandbox eval sorter --dry-run --name my-exp   # plan only; --name for the experiment log
sandbox matrix --providers ollama --models qwen3:8b --prompts sorter_local_v0 --mock --sample 4
```

Live versions: drop `--mock` (needs a running provider + model):
`sandbox pilot --local`, `sandbox eval sorter --local`, `sandbox matrix … --local`.

## 8. Spec-driven jobs (`sandbox run`)

```bash
sandbox run preflight  --config config/runs/example.yaml          # resolve + validate + lock
sandbox run preflight  --config config/runs/example.yaml --dry-run # plan only
sandbox run preflight  --config config/runs/example.yaml --mock    # dataset lock incl. sha256
sandbox run start      --config config/runs/example.yaml --mock    # run per-item w/ checkpoints
sandbox run status     --config config/runs/example.yaml           # run_id resolves from the yaml
sandbox run status     --run-id fixture-sorter-smoke --watch
sandbox run resume     --config config/runs/example.yaml --mock
sandbox run cancel     --config config/runs/example.yaml
sandbox run list
sandbox run --profile modal-vllm start --config config/runs/x.yaml --job-mode modal --mock
```

- `--config` alone is enough for status/resume/cancel — the embedded `run_id`
  is resolved from the spec (DMR-058).
- Modal job mode needs `[deploy]` (`pip install -e ".[deploy]"` + `modal token new`);
  without it you get a pointed hint, not a traceback.
- Locked runs live under `data/runtime/runs/<run_id>/`; results land in
  `reports/experiment_log.jsonl`.

## 9. Serving comparisons, tracing, remote

```bash
sandbox metrics compare --runs local,modal,api    # table + scorecard from serving fixtures
sandbox eval local_vs_api --mock                  # offline serving comparison (fixtures)
sandbox eval local_vs_api --from-log              # …or from reports/experiment_log.jsonl
sandbox traces export                             # dump recorded trace ids → data/traces/export.json
sandbox tunnel --profile vllm-remote plan         # print the exact ssh forward command
sandbox tunnel --profile vllm-remote up           # start detached (pidfile under data/runtime/)
sandbox tunnel --profile vllm-remote status
sandbox tunnel --profile vllm-remote down
sandbox pipeline watcher                          # long-running Langfuse watcher (mailroom env)
sandbox pipeline api                              # long-running API server
```

## 10. Canonical workflows

**Offline smoke (CI / no LLM / no network):**
```bash
pip install -e ".[dev]" && sandbox datasets prepare \
  && sandbox pilot --mock && sandbox eval sorter --mock \
  && sandbox run preflight --config config/runs/example.yaml --mock
```

**Local Ollama (default profile):**
```bash
sandbox up && sandbox pull-models && sandbox health \
  && sandbox pilot --mock && sandbox pilot --local
```

**Modal remote GPU:**
```bash
pip install -e ".[deploy]" && modal token new
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B MODAL_VLLM_GPU=L4 MODAL_VLLM_API_TOKEN=$(openssl rand -hex 24)
modal run deploy/modal_vllm.py::download_model && modal deploy deploy/modal_vllm.py
export VLLM_BASE_URL=https://<ws>--sandbox-vllm-serve.modal.run/v1 VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox health --profile modal-vllm && sandbox run --profile modal-vllm start --config … --job-mode modal
```

## 11. Verification

```bash
.venv/bin/python -m pytest -q        # 230 passed / 1 skipped (network-free; live tests need SANDBOX_LOCAL_LLM=1)
sandbox health                       # everything green: exit 0
```

## 12. Troubleshooting (DMR-058 CLI sweep findings)

| Symptom | Cause / fix |
| --- | --- |
| `ModuleNotFoundError: numpy` on first `sandbox` call | stale editable install; `pip uninstall mailroom-sandbox` then `pip install -e ".[dev]"` |
| `sandbox datasets pull` says `pip install -e "[hf]"` | base install is offline-first; Hub client lives in `[dev]`/`[hf]` |
| `legalbench --suite` says `[pipeline]` | suite needs the vendored langchain stack → `pip install -e ".[pipeline]"` |
| `run … --job-mode modal` says `[deploy]` | Modal SDK is an opt-in extra → `pip install -e ".[deploy]"` + `modal token new` |
| `sandbox tunnel --profile X plan` "unrecognized arguments" | `--profile` belongs on `tunnel`, not on `plan` (see §2) |
| `run status --config …` demands `--run-id` | fixed (DMR-058): `--config` resolves the run_id; still passes an explicit `--run-id` to override |
| `sandbox up` prints a Python traceback | fixed (DMR-058): compose/ollama/ssh failures are one-line errors, exit 1 |
| `fetch-deps` wiped part of `vendor/` | fixed (DMR-058): layout-aware + validates before touching the tracked tree |