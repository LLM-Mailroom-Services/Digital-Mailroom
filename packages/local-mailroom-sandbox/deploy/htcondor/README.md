# CHTC / HTCondor integration (HUB-026)

Run the sandbox's serving + evals on the **Center for High Throughput
Computing** (CHTC, UW–Madison) or any HTCondor pool. Everything below is
grounded in CHTC's live user docs (chtc.cs.wisc.edu/uw-research-computing) —
log-in requirements, GPU Lab roster and job classes, container/staging rules,
and the current `condor_ssh_to_job` policy — with the specific pages linked
inline. Two paths, chosen by one question: **can you reach the job over
SSH?**

| Path | Works on | Mechanism | Files |
| --- | --- | --- | --- |
| **Batch eval** (recommended) | CHTC shared GPU Lab + any pool | The job hosts vLLM itself for its lifetime, runs the evals in-process, transfers `results/` back — no server, no tunnel | `vllm_batch_eval.sub` + `run_batch_eval.sh` |
| **Server** | Researcher-**owned** GPU machines only | Long-lived vLLM server job + `condor_ssh_to_job` forward → `vllm-remote` profile | `vllm_serve.sub` + `serve_vllm.sh` |

> **Policy (2026-04-22):** CHTC removed `condor_ssh_to_job` from the
> **shared** GPU machines ("Use GPUs" guide, interactive-GPU policy note);
> it remains available on group-owned/prioritized GPUs, and `condor_submit
> -i` interactive jobs are still open to all users. Monitor running jobs
> with `condor_tail` instead of SSH. A tunnel-based server on the shared
> pool is structurally impossible — that is why the batch path exists.

## 1. Account + login (their "Log in to CHTC" / "Configure SSH" pages)

- **Account:** request via CHTC's account form (chtc.cs.wisc.edu →
  "Request Account"); your welcome email names your assigned access point.
- **Access points:** `ap2001.chtc.wisc.edu` or `ap2002.chtc.wisc.edu`
  (formerly submit1/submit2) — **use the one in your welcome email**.
- **Login requires:** your UW–Madison **NetID + password**, **Duo MFA**,
  and a connection to the **campus network or UW VPN** (no off-campus
  plain SSH).
- **Connection reuse (recommended):** ControlMaster in `~/.ssh/config`
  avoids re-typing password + Duo on every file transfer:
  `Host *.chtc.wisc.edu` / `ControlMaster auto` / `ControlPersist 2h` /
  `ControlPath ~/.ssh/connections/%r@%h:%p` (create `~/.ssh/connections`).
  **Port forwards must be established on the initial (master) connection** —
  they cannot be added later on a reused connection. (Mosh is suggested by
  CHTC for flaky links but does **not** support port forwarding.)
- Help: chtc@cs.wisc.edu, community forum (community.chtc.wisc.edu),
  office hours Tue/Thu.

## 2. Operating system + software strategy (their OS/containers guides)

- Execute nodes run CHTC's **RHEL-family Linux**; you cannot log into them
  directly on the shared pool. Two supported ways to control your
  environment, in preference order:
  1. **Apptainer containers** (what our templates use):
     `container_image = docker://vllm/vllm-openai:...` pulls straight from
     Docker Hub; a prebuilt `.sif` can be served from `/staging` via
     `osdf:///chtc/staging/...` (add `requirements = (HasCHTCStaging ==
     true)`). Containers carry their **own OS** — the clean answer to
     "which glibc/CUDA?" — and GPU servers have nvidia-docker integration
     (CHTC recommends `nvidia/cuda` `12.1.1-devel`-based images for
     compiled code; the vLLM image already bundles its CUDA runtime).
  2. **Portable conda** (the no-container route): build the env **ON the
     access point** (Linux), never on your Mac — `conda-pack` output must
     match the execute nodes' glibc. See
     [`../conda/environment.yml`](../conda/environment.yml) for the env
     and the `conda pack -n mailroom-sandbox` command.
- Building a custom `.sif` must happen in an **interactive build job**
  (`condor_submit -i`), then `mv` it to `/staging/$USER` — never build on
  the login node.
- `/staging` is the large-data system for inputs too big for `/home`
  (model weights!); note CHTC is running a **/staging transition (May 15 –
  Aug 31, 2026)** for personal staging directories — check their
  "staging transition" page before relying on old paths. Jobs using
  staging declare `requirements = (HasCHTCStaging == true)`.

## 3. GPU Lab specifics (their "Use GPUs" guide)

**Roster** (explore live with
`condor_status -af Machine TotalGpus GPUs_DeviceName GPUs_Capability`):

| GPU | Capability | VRAM |
| --- | --- | --- |
| Tesla P100 | 6.0 | 16 GB |
| RTX 2080 Ti | 7.5 | 10 GB |
| A100 (40/80 GB) | 8.0 | 40/80 GB |
| L40 / L40S | 8.9 | 45 GB |
| H100 80GB HBM3 | 9.0 | 80 GB |
| H200 | 9.0 | 141 GB |

**Job classes** (GPU Lab policy — defaults differ from the rest of the
HTC system; unspecified = `medium`):

| Class | Max runtime | Per-user cap |
| --- | --- | --- |
| `short` | 12 h | 2/3 of GPU Lab GPUs |
| `medium` | 24 h | 1/3 of GPU Lab GPUs |
| `long` | 7 days | up to 4 GPUs in use |

Our batch template uses `short` (a fixture eval run is well under 12 h and
short jobs get the most parallel capacity). Submit-file knobs that matter:

- `request_gpus = 1` — **required on every GPU job**, even outside the Lab.
- `gpus_minimum_memory = 24000` — Qwen3-8B bf16 weights (~16 GB) + KV
  cache exclude the 10–16 GB cards; lower it only for smaller models.
- `gpus_minimum_capability = 8.0` (optional) — Ampere+ keeps
  FlashAttention-era vLLM kernels happy; drop it to reach the P100/2080 Ti
  for small-model smoke tests.
- `CUDA_VISIBLE_DEVICES` is set **by HTCondor** — never override it in the
  job script (two jobs would share a GPU).
- `+is_resumable = true` — lets sub-4–6 h / checkpointable jobs use
  group-owned backfill GPUs (forfeits the 72 h guaranteed runtime of
  non-GPU-Lab servers; interruptible).
- Non-GPU-Lab capacity exists (group-owned backfill, `gzk` servers — no
  /staging, no Docker — OSG pool, UW Grid); talk to the facilitators
  before using it. `request_disk` must cover the container image + weights.

## 4. One-time setup (access point)

```bash
ssh <you>@ap2001.chtc.wisc.edu          # your assigned AP; Duo + VPN
# 1. sandbox package tarball (from a monorepo checkout you push/copy over)
git archive --format=tar.gz -o mailroom-sandbox.tar.gz HEAD packages/local-mailroom-sandbox
#    (run_batch_eval.sh expects the tarball to contain a mailroom-sandbox/
#     directory — archive the subtree if you copied only the package)
# 2. portable conda env — BUILD IT HERE, on the AP (glibc match; see §2)
conda env create -f deploy/conda/environment.yml
pip install -e ".[pipeline]"             # inside the env, package root
#    [pipeline] carries mailroom + its langchain stack so the execute-node
#    install is a no-op fallback; run_batch_eval.sh still pins
#    mailroom@v0.6.0 explicitly (the extra floats on main).
conda pack -n mailroom-sandbox -o env-mailroom-sandbox.tar.gz
# 3. submit
mkdir -p logs
condor_submit vllm_batch_eval.sub
```

`run_batch_eval.sh` unpacks the env, installs the eval stack
(`mailroom@v0.6.0` + the sandbox), and **proves it is importable before
starting vLLM** — a missing stack fails the job instead of silently scoring
mocks. It then serves `Qwen/Qwen3-8B` with the same engine argv as
`deploy/docker-compose.yml` and `deploy/modal_vllm.py` (`--max-model-len
32768 --gpu-memory-utilization 0.90 --max-num-seqs 256
--no-enable-log-requests`; override per submission via the `.sub`
`environment` line, including `TP_SIZE` for 70B-class multi-GPU jobs), waits
for `/v1/models` (hard failure on death or a 20-minute timeout), then runs
`sandbox eval sorter --local` / `eval extract --local` with
`SANDBOX_PROFILE=vllm-local` and `--model "$MODEL"` so the agents always
request the served model. A final **live-or-loud guard** fails the job if any
experiment-log record shows `offline_fallback > 0`. Results land in the job's
`results/` directory (absolute path — the script `cd`s into the unpacked
package, so the dir is anchored at submission time); watch progress with
`condor_tail <cluster>.<process>`.

## 5. Server path (owned GPUs only)

```bash
condor_submit vllm_serve.sub
condor_q -long <cluster> | grep -E 'RemoteHost|Owner'   # find the job
condor_ssh_to_job <cluster>.<proc>                      # owned machines only
```

`condor_ssh_to_job` lands you on the execute node; forward it home (from
the machine that can reach the job — e.g. the access point — or chained):

```bash
ssh -N -L 18000:localhost:8000 <you>@<execute-node-hostname>
```

Then attach the sandbox — exactly what `vllm-remote` + `sandbox tunnel`
automate (run from the machine where you built the forward):

```bash
export SANDBOX_TUNNEL_HOST=<jump-host>      # machine that can reach the job
export SANDBOX_TUNNEL_USER=<you>
# optional: SANDBOX_TUNNEL_PORT / SANDBOX_TUNNEL_KEY
sandbox tunnel --profile vllm-remote plan   # print the exact ssh command
sandbox tunnel --profile vllm-remote up     # detached forward, pidfile in data/runtime/
sandbox health --profile vllm-remote        # /v1/models + json_object probe
sandbox eval sorter --local                 # against the remote weights
sandbox tunnel --profile vllm-remote down
```

`VLLM_API_KEY` (if you set one on the server) is picked up by both the
health probe and the tunneled profile via the `api_key_env` contract.

## 6. Same tunnel, any GPU box

The CHTC server path is just one instance: `vllm-remote` + `sandbox tunnel`
works unchanged for a lab GPU box, a cloud VM, or a labmate's machine —
anything that can run `vllm serve` and that you can SSH to. CHTC is not
special here; only the job submission is.
