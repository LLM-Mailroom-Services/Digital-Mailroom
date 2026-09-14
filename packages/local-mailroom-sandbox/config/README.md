<div align="center">

# ⚙️ Sandbox Configuration

**Configuration files for the local-mailroom-sandbox package.**

</div>

---

## Structure

| Path | Contents |
|:---|:---|
| [`mailroom.taxonomy.base.yaml`](mailroom.taxonomy.base.yaml) | Document classes, agents, prompts |
| [`taxonomy.overlay.yaml`](taxonomy.overlay.yaml) | Overlay applied on top of the base |
| [`models.yaml`](models.yaml) | Serving/model catalog (providers, quantization, GPU) |
| [`components.yaml`](components.yaml) | Agent roster + retired/optional components |
| [`profiles/`](profiles/) | Provider serving profiles |
| [`runs/`](runs/) | Job-run spec examples |
| [`prompts/`](prompts/) | Prompt overrides/registry |

## Profile selection

Profiles are selected with the **`SANDBOX_PROFILE`** env var
(`ollama`, `vllm-local`, `modal-vllm`, `vllm-remote`, `llamacpp`,
`lmstudio`, `openrouter`) — see [`profiles/README.md`](profiles/README.md).

## Environment

The env template is `.env.example` at the package root (copy to `.env` and
fill in provider keys). `sandbox` commands load it automatically.

## Related Files

- `src/` — Source code
- `data/` — Test data
- `.env.example` — Environment template (package root)