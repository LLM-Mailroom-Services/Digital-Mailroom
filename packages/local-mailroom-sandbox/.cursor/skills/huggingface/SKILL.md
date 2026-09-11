---
name: huggingface
description: Hugging Face Hub usage for local-mailroom-sandbox — fixture schema, sandbox datasets pull, HF cache, and Modal/vLLM weight downloads. Use for Hub datasets, HF_TOKEN, mailroom-corpus slices, or model pulls; prefer offline data/fixtures and sandbox datasets prepare when network-free work is enough. For general Hub CLI depth, also follow the hf-cli plugin skill.
---

# Hugging Face (sandbox data + weights)

**When:** Hub dataset pulls, model downloads for vLLM/Modal/Ollama-from-Hub, `HF_TOKEN`, or docclass schema work.  
**Prefer offline fixtures** (`data/fixtures/`, `sandbox datasets prepare`) for default tests and notebooks 01–03. Never require Hub in pytest.

## Offline first

| Asset | Path | Network? |
| --- | --- | --- |
| Catalog + gold | `data/fixtures/` (+ `ATTRIBUTION.md`) | No |
| Synthetic HF mini slice | `data/fixtures/hf/docclass_mini.jsonl` | No |
| Prepared JSONL | `data/runtime/prepared/` via `sandbox datasets prepare` | No |
| Hub head cache | `data/cache/` via `sandbox datasets pull` | **Yes** |

```bash
sandbox datasets prepare                                    # offline cleaners
sandbox datasets pull --dataset Lucius-Morningstar/mailroom-corpus --max-rows 50
#   pinned revision eafe1ab4c0d3… (FAMILY_HF_REVISION), ground_truth + default
#   merged on filename, content_sha256 verified, exit 1 on any failure (DMR-056)
```

Default Hub id in code: `Lucius-Morningstar/mailroom-corpus`
(`mailroom_sandbox.datasets.HF_DATASET` / `job.spec.HF_DEFAULT_REPO`).

## Auth + cache

```bash
# optional
export HF_TOKEN=hf_...
# compose vLLM / Modal read HF_TOKEN; Modal volume sandbox-hf-cache
```

Compose `vllm` mounts named volume `hf_cache`. Modal (both apps) uses the
huggingface_hub 1.x default Xet backend (`HF_XET_HIGH_PERFORMANCE=1`); the
old `[hf_transfer]` extra / `HF_HUB_ENABLE_HF_TRANSFER` are dead (DMR-056).

## When to use which HF surface

| Task | Tool |
| --- | --- |
| Sandbox evals / pilots | Offline fixtures + prepared JSONL |
| Stream a tiny Hub slice | `sandbox datasets pull` / `pull_hf_dataset` |
| Choose a local GGUF / serve recipe | Prefer [ollama](../ollama/SKILL.md) or llama.cpp profile; use Hub only for the weight source |
| Deploy weights on Modal | [modal](../modal/SKILL.md) + `HF_TOKEN` if gated |
| Full Hub CLI (upload, buckets, papers, …) | Cursor **hf-cli** / other Hugging Face plugin skills — this skill stays sandbox-scoped |

## Boundaries

- Do not vendor multi-MB CUAD PDFs; the legalbench suite corpus stays
  upstream (llm-mailroom `scripts/fetch_full_cuad.py`; DMR-057 vendored tree
  carries code only, not the corpus).  
- Synthetic `hf/docclass_mini.jsonl` matches Hub schema but is **not** Hub content.  
- Default CI/pytest: no Hub calls.

## Related

- Router: [sandbox-tool-router](../sandbox-tool-router/SKILL.md)  
- Evals: `docs/evals.md`  
- Attribution: `data/fixtures/ATTRIBUTION.md`
