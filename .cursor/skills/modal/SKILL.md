---
name: modal
description: Modal vLLM is not deployed from The-Mailroom. Use when the user asks for Modal, sandbox-vllm, GPU inference, or MODAL_VLLM_* from this checkout — redirect to local-mailroom-sandbox deploy/modal_vllm.py; do not add Modal apps or GPU serve code here.
---

# Modal (not deployed here)

**When:** Remote GPU, `modal deploy`, `sandbox-vllm`, or “run Qwen on Modal
for the floor”.  
**Prefer** [local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox)
`.cursor/skills/modal` (`deploy/modal_vllm.py`, app name `sandbox-vllm`).
This visualizer does not ship a Modal app.

## What to do instead

1. Deploy/serve from the sandbox (or production `llm-mailroom` if that is the
   asked producer).
2. Let that process write `document-pipeline` traces to Langfuse.
3. Point The-Mailroom `LANGFUSE_*` at that project and run `mailroom-web`.

Local NVIDIA compose (`vllm-local`) is also a sandbox concern, not this repo.

## Boundaries

- Do not add `modal_vllm.py` or GPU Dockerfiles here.
- Do not rename or reuse production Modal app names from this visualizer.
- Default pytest and the pixel floor never call Modal.

## Related

- Local CPU/LLM: [ollama](../ollama/SKILL.md)
- Hub weights (sandbox): that repo’s huggingface skill
- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
