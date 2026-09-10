---
name: modal
description: Deploy and cut over to Modal-hosted vLLM for local-mailroom-sandbox (sandbox-vllm app). Use when the user needs remote GPU inference, SANDBOX_PROFILE=modal-vllm, modal deploy/token, or MODAL_VLLM_* knobs — not for default CPU/Ollama work.
---

# Modal vLLM (remote GPU serve)

**When:** No suitable local GPU, user asks for Modal, or profile `modal-vllm`.  
**Prefer Ollama** for everyday local/CPU smoke ([ollama](../ollama/SKILL.md)). Local NVIDIA compose uses profile `vllm-local` + compose `vllm` (not Modal).

Pinned: Modal SDK **1.5.5** (`[deploy]` extra) + vLLM **v0.28.0**
(`vllm/vllm-openai:v0.28.0`, matching the local compose pin). Full workflow:
[`deploy/README.md`](../../../deploy/README.md).

## Deploy

```bash
pip install -e ".[deploy]"
modal token new
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_API_TOKEN="$(openssl rand -hex 24)"
# optional: HF_TOKEN for gated weights

modal run deploy/modal_vllm.py::download_model   # pre-warm weights (CPU-only)
modal deploy deploy/modal_vllm.py                # prints the modal.run URL
```

App name: **`sandbox-vllm`** (sandbox-scoped; Volumes `sandbox-hf-cache` +
`sandbox-vllm-cache`). Source: `deploy/modal_vllm.py`.

Tear down: `modal app stop sandbox-vllm` (Volumes persist).

## Cut over the sandbox

```bash
# .env
SANDBOX_PROFILE=modal-vllm
DEFAULT_PROVIDER=vllm
VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
VLLM_API_KEY=<same as MODAL_VLLM_API_TOKEN>
```

```bash
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm     # 401 = VLLM_API_KEY mismatch
sandbox pilot --local --profile modal-vllm
```

Compose for Modal profile only starts **langfuse** (no local vLLM container).

## Knobs

| Env | Default |
| --- | --- |
| `MODAL_VLLM_MODEL` | `Qwen/Qwen3-8B` |
| `MODAL_VLLM_GPU` | `L4` |
| `MODAL_VLLM_MAX_MODEL_LEN` | `32768` |
| `MODAL_VLLM_QUANTIZATION` | empty |
| `MODAL_VLLM_IMAGE_TAG` | `v0.28.0` (pin; never `latest`) |
| `MODAL_VLLM_REVISION` | empty (HF revision) |
| `MODAL_VLLM_TP_SIZE` | from GPU `:N` suffix (1 single-GPU) — must match `MODAL_VLLM_GPU="A100-80GB:2"` for 70B-class |
| `MODAL_VLLM_API_TOKEN` | empty (bearer) |
| `HF_TOKEN` | optional Hub auth |
| `MODAL_VLLM_SCALEDOWN_SECONDS` | `900` |
| `MODAL_VLLM_MAX_CONTAINERS` | `1` (cost guard) |
| `MODAL_VLLM_MIN_CONTAINERS` | `0` (scale-to-zero) |
| `MODAL_VLLM_STARTUP_TIMEOUT_SECONDS` | `1200` |

Cost: L4 ≈ $0.80/hr while warm (rates: modal.com/pricing, verified
2026-09-09); GPU billing stops after the scaledown window; `download_model`
is CPU-only. Check spend with `modal billing summary`.

## SDK gotchas (1.5.5)

- `Secret.from_local` was **removed** — use `from_dict` (skips missing keys,
  which keeps `HF_TOKEN`/`MODAL_VLLM_API_TOKEN` optional) or
  `from_local_environ` (raises on missing).
- `@modal.web_server` is supported; `@app.server` (1.5.1+) is the modern
  path — migration notes in `deploy/README.md` (do not migrate ad hoc).
- Memory snapshots are not enabled: GPU snapshots are alpha, vLLM needs the
  dedicated KV-cache-discarding pattern, and weight loads are storage-bound.

## Boundaries

- Do not use Modal for default pytest or `--mock` paths.  
- Do not rename the Modal app to mailroom's production name — keep `sandbox-vllm`.  
- Still activate via `runtime.activate("modal-vllm")` so taxonomy overlay rewrites agents.
- Never commit tokens; only variable names appear in the repo.

## Related

- Local default: [ollama](../ollama/SKILL.md)  
- Hub weights: [huggingface](../huggingface/SKILL.md)  
- Docs: `deploy/README.md`, `docs/remote-serving.md`, `docs/providers.md`
