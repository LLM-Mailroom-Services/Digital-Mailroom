# Specialist subagents

Every specialty in the constellation has a dedicated subagent. Invoke it
through the **Task tool** (`subagent_type: <name>`) instead of improvising
outside your expertise — specialty work done inline is a defect even when it
happens to be correct. The subagent's returned report is the evidence for that
slice of the card.

## The roster

| Specialty | `subagent_type` | Call it for |
| --- | --- | --- |
| Data & databases | `athena-database-agent` | datasets (HF/Kaggle/Braintrust), schema design, ingestion/transformation pipelines, data QA, ML data preparation |
| HuggingFace & data science | `lucius` | HF downloads/uploads/edits, `datasets`/`transformers`, EDA, statistical analysis, model training/eval, database upkeep |
| Prompt engineering | `prompt-engineer` | run-failure diagnosis, GEPA mutations, prompt A/Bs across the llm-entity-extraction + llm-mailroom surfaces |
| Docs & board | `atom` | READMEs/wikis/changelogs, doc-drift detection, Kanban board upkeep, inter-agent coordination, repo restructuring |
| Software & UI | `hazel-ui-software-master` | UI/UX, fullstack, HTML/JS/CSS, bug fixes, local network testing, app architecture |
| Systems & repo hygiene | `jarvis-systems-maximizer` | performance triage, memory/CPU hogs, disk usage, cache cleanup, repo bloat, process prioritization |
| vLLM serving | `vllm-specialist` | `vllm serve` configs, quantization, multi-LoRA, structured outputs, speculative decoding, parallelism, KV-cache/memory tuning, local or Modal-hosted vLLM behind `DEFAULT_PROVIDER=vllm` |
| Modal compute | `modal-specialist` | Modal apps (`@app.function`/`@app.cls`/`@app.server`), Images/Volumes/Secrets/Sandboxes, GPU choice, scale-to-zero, `modal serve`/`deploy`, the repo's `deploy/modal_vllm.py` apps |
| Codebase exploration | `explore` | fast read-only searches ("where is X", "how does Y work") before you edit |
| General multi-step | `general` | research/execution spanning several specialties with no single owner |

## Project agent files

Project agents are committed under `.opencode/agents/` — version-controlled
and reviewed like code:

| File | Role |
| --- | --- |
| `.opencode/agents/vllm-specialist.md` | vLLM serving playbook (vLLM stable-grounded) + repo wiring + guardrails |
| `.opencode/agents/modal-specialist.md` | Modal SDK-grounded primitives/CLI/GPU discipline + the repo's deploy apps |
| `.opencode/agents/prompt-engineer.md` | the GEPA diagnostic evaluator / prompt engineer |
| `.opencode/agents/PROMPT_ENGINEER_GEPA_PROVENANCE.md` | provenance documentation for the prompt-engineer agent — **not** a callable subagent |

**Restart opencode after adding a project agent** so the Task tool picks it up.

## Rules that make the roster work

- **One specialist per concern.** Do not ask a subagent to do another
  specialty's job; chain them (e.g. `explore` → `vllm-specialist` →
  `modal-specialist` → `prompt-engineer`).
- **Brief the specialist like a card.** Pass the card ID, the exact scope,
  the files/seams involved, and the evidence contract (what must be green,
  what the report must name). A vague prompt returns a vague report.
- **The caller owns the work.** Subagent output is a report, not a merged
  change: the calling agent writes the files, runs the gates, updates
  `governance/TASKS.md`, and commits — the specialist is evidence, not an
  author of record.
- **Specialists verify current upstream docs** (vLLM stable, Modal SDK, HF
  Hub APIs, Langfuse) before writing configuration; a report that quotes a
  version without checking it is incomplete.
- **Skills are the second layer.** Load the `huggingface`, `langfuse`, or
  `customize-opencode` skill when a task matches its description, and the
  package-local `.cursor/skills/` (openrouter, ollama, modal, langfuse,
  apache-phoenix, braintrust, huggingface, langgraph, dojo-scoring,
  legalbench) for provider/sink depth inside a package.
- **Out of scope stays out of scope.** The `prompt-engineer` mutates prompts
  from evidence; it never changes what "correct" means, the scorer, the
  ground truth, or the schema — hand those to the owning surface.

Provenance: DMR-008 (2026-09-09) — the roster landed in `AGENTS.md` with the
dedicated `vllm-specialist` + `modal-specialist` project agents; issue #12
closed with the card. The `prompt-engineer` project agent and its GEPA
provenance file predate the roster.
