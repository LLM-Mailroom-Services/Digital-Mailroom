# Remote serving: Modal, vLLM, SSH tunnels, CHTC, conda

The sandbox is local-first, but its eval surfaces are provider-agnostic:
anything that speaks OpenAI `/v1` can back a profile. Four supported paths,
one env contract (`VLLM_BASE_URL` / `VLLM_API_KEY` everywhere).

| Path | Profile | Best for |
| --- | --- | --- |
| Local vLLM (GPU host) | `vllm-local` | a machine with the GPU in front of you |
| Modal-hosted vLLM | `modal-vllm` | zero-infra remote GPU, public HTTPS endpoint |
| SSH-tunneled vLLM | `vllm-remote` | lab GPU boxes, owned CHTC machines, any SSH host |
| Batch in-job (no server) | — (job-hosted) | CHTC shared GPU Lab (no SSH into jobs) |

## Local vLLM

```bash
sandbox up --compose-profile vllm        # docker compose, needs NVIDIA GPU
sandbox health --profile vllm-local
```

The compose service pins `vllm/vllm-openai:v0.28.0` — the same engine
version as the Modal app — and sends the shared test-sandbox argv:
`--host 0.0.0.0 --port 8000 --max-model-len 32768
--gpu-memory-utilization 0.90 --max-num-seqs 256
--no-enable-log-requests`. Compose substitution reads your shell env or
`deploy/.env` (the compose project directory):

| Env | Default | Notes |
| --- | --- | --- |
| `VLLM_MODEL` | `Qwen/Qwen3-8B` | HF repo id |
| `VLLM_MAX_MODEL_LEN` | `32768` | KV-cache budget |
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.90` | vLLM's default is `0.92`; 0.90 leaves headroom on a 24 GB L4 / shared GPU |
| `VLLM_MAX_NUM_SEQS` | `256` | concurrency cap (matches the Modal default) |
| `VLLM_API_KEY` | empty | when set, `/v1/*` requires the bearer (same contract as Modal) |
| `HF_TOKEN` | empty | gated/private weights |

Quantized checkpoints and pinned revisions are one-off command overrides —
the image entrypoint is `vllm serve`, so the first argument is the model:

```bash
docker compose -f deploy/docker-compose.yml --profile vllm run --rm --service-ports \
  vllm Qwen/Qwen3-8B-AWQ --host 0.0.0.0 --port 8000 --max-model-len 32768 \
  --gpu-memory-utilization 0.90 --max-num-seqs 256 --no-enable-log-requests
```

The Modal app exposes both as deploy knobs (`MODAL_VLLM_QUANTIZATION`,
`MODAL_VLLM_REVISION`); `--revision` is the reproducibility pin for runs.

## Modal

Modal SDK **1.5.5** (pinned in the `[deploy]` extra) + vLLM **v0.28.0**
(the newest upstream stable, v0.29.0, flips the engine core — bump both pins
after a parity run); full workflow (knobs, costs, security, troubleshooting)
in [`deploy/README.md`](../deploy/README.md).

```bash
pip install -e ".[deploy]" && modal token new
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_API_TOKEN=<secret>

modal run deploy/modal_vllm.py::download_model   # pre-warm weights (CPU-only)
modal deploy deploy/modal_vllm.py                # prints the URL

export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox health --profile modal-vllm              # 401 = token mismatch
```

Cost posture: scale-to-zero after 900 s idle, `max_containers=1` by default
(L4 ≈ $0.80/hr while warm; rates at modal.com/pricing, verified 2026-09-09).
Teardown: `modal app stop sandbox-vllm` — weights survive in the
`sandbox-hf-cache` Volume.

## SSH tunnels (`vllm-remote` + `sandbox tunnel`)

For a vLLM server on any machine you can SSH to. The profile's `tunnel:`
block names the env vars — nothing secret lives in this repo.

```bash
export SANDBOX_TUNNEL_HOST=gpu.lab.example
export SANDBOX_TUNNEL_USER=jdoe
# optional: SANDBOX_TUNNEL_PORT (default 22), SANDBOX_TUNNEL_KEY
sandbox tunnel --profile vllm-remote plan    # print the exact ssh command
sandbox tunnel --profile vllm-remote up      # detached forward → localhost:18000
sandbox health  --profile vllm-remote
sandbox eval sorter --local                  # evals hit the tunneled engine
sandbox tunnel  --profile vllm-remote down
```

CLI conventions (whole `sandbox` CLI, not just tunnel): pass `--profile`
AFTER the subcommand (`sandbox tunnel --profile vllm-remote up`) or via
`SANDBOX_PROFILE` — a `--profile` placed before the subcommand is clobbered
by the subparser default (pre-existing argparse behavior in this CLI).

The forward is an `ssh -N -L` with `ExitOnForwardFailure` + keepalives;
`up` refuses to double-forward a live port and records the pid under
`data/runtime/tunnel-<profile>.pid`.

## CHTC (HTCondor)

See [`deploy/htcondor/README.md`](../deploy/htcondor/README.md) for the
full walkthrough — grounded in CHTC's live docs: access points + Duo/VPN
login requirements, the GPU Lab roster and job classes (short 12h / medium
24h / long 7d), container/staging rules, and the one constraint that shapes
everything: **`condor_ssh_to_job` is unavailable on CHTC's shared GPU Lab
machines** (allowed on researcher-owned machines), so:

- **Shared pool → batch path** (`vllm_batch_eval.sub`): the job hosts vLLM
  itself, runs the sandbox evals in-process, transfers `results/` back
  (`condor_tail` for monitoring).
- **Owned machines → server path** (`vllm_serve.sub`): long-lived vLLM job
  + `condor_ssh_to_job` forwarding → the `vllm-remote` profile above.

## Conda

[`deploy/conda/environment.yml`](../deploy/conda/environment.yml) defines
the CPU-first `mailroom-sandbox` env (vLLM stays out — it carries its own
CUDA stack and lives in a container). For CHTC, ship the env portably:

```bash
conda pack -n mailroom-sandbox -o env-mailroom-sandbox.tar.gz
```

## Health contract

Every path converges on the same probes: `sandbox health` GETs
`{base}/v1/models` and posts a 1-token `json_object` chat; structured-output
gaps surface as `json_object_ok: false` (vLLM ≥0.8 and Modal's image pass).

Bearer semantics (vLLM v0.28.0): `VLLM_API_KEY` (or `--api-key`) makes the
server require `Authorization: Bearer <token>` on the `/v1`, `/v2`,
`/inference`, and `/cohere` path prefixes. `/health` is a liveness endpoint
and is deliberately **unauthenticated** — `sandbox health` validates the
token through the authenticated `/v1/models` probe (a 401 there means token
mismatch; use `/health` only for "is the process up"). Modal-hosted servers
return 503 while scaled to zero, so retry rather than treating 503 as a
failure.
