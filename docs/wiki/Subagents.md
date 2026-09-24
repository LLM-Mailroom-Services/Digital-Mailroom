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
| File management & organization | `archivist-file-organizer` | repo-layout audits/restructures, directory/file grouping and renames, vendor/snapshot tree upkeep, symlink/workspace hygiene, duplicate detection, junk/orphan sweeps |
| Concise code analysis | `code-analyst` | fast structured verdicts, diff review, root-cause tracing, dead-code confirmation, risk maps of unfamiliar modules |
| Test suite auditing | `test-suite-auditor` | auditing suites themselves: dead/weak tests, stub dishonesty, unpinned error paths, skip discipline, marker hygiene |
| Board evidence | `board-evidence-auditor` | DMR board/card evidence audits, TASKS.md ↔ board_state.py reconciliation, card-law compliance |
| vLLM serving | `vllm-specialist` | `vllm serve` configs, quantization, multi-LoRA, structured outputs, speculative decoding, parallelism, KV-cache/memory tuning, local or Modal-hosted vLLM behind `DEFAULT_PROVIDER=vllm` |
| Modal compute | `modal-specialist` | Modal apps (`@app.function`/`@app.cls`/`@app.server`), Images/Volumes/Secrets/Sandboxes, GPU choice, scale-to-zero, `modal serve`/`deploy`, the repo's `deploy/modal_vllm.py` apps |
| Master governance orchestrator | `orchestrator-governor` | planning + dispatch + governance: reads AGENTS.md + the board first, briefs specialists like cards, chains (never impersonates), holds the card lifecycle, closes with evidence; PRIMARY or SUBAGENT (`mode: all`) |
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
| `.opencode/agents/lucius.md` | HuggingFace & data science (project-local by design — no global mirror) |
| `.opencode/agents/board-evidence-auditor.md` | board/card evidence audits (project-local) |

## Global agent files (all worktrees) + committed mirrors

Since DMR-062, the generalists and reinstate-ables live **globally first**
(canonical file in `~/.config/opencode/agents/<name>.md`, available in
every worktree of the constellation), with **byte-identical committed
mirrors** under `.opencode/agents/`:

| Global file (`~/.config/opencode/agents/`) | Committed mirror (`.opencode/agents/`) |
| --- | --- |
| `athena-database-agent.md` | identical copy |
| `atom.md` | identical copy |
| `hazel-ui-software-master.md` | identical copy |
| `jarvis-systems-maximizer.md` | identical copy |
| `archivist-file-organizer.md` | identical copy |
| `code-analyst.md` | identical copy |
| `test-suite-auditor.md` | identical copy |
| `orchestrator-governor.md` | identical copy |

The project copy is a harmless no-op while identical (project config
overrides global with the same content). **Drift between the two is a
housekeeping defect** — `diff -r ~/.config/opencode/agents .opencode/agents`
must stay clean for the mirrored names. Project-local specialists (`prompt-engineer`, `vllm-specialist`,
`modal-specialist`, `board-evidence-auditor`, `lucius`) stay project files
by design (repo-specific protocols).

## The orchestrator-governor dispatch protocol

`orchestrator-governor` is the master governance orchestrator (`mode: all`,
DMR-062): a planning agent that treats the board as the job site and the
specialists as subcontractors. Its protocol (encoded in the agent file):

1. Read `AGENTS.md` + the task board FIRST, then the agent files of every
   specialist it will dispatch (brief to the file, never from memory).
2. Break the mission into units — one specialty, one deliverable, one
   evidence contract each — and name the handoff seams between units.
3. Brief each specialist like a card: card ID, scope paths/seams, evidence
   contract ("what must be green, what the report must name").
4. Enforce the four roster rules (one specialist per concern; brief like a
   card; the caller owns the work; verify current upstream docs).
5. Hold the card lifecycle: claim → in_progress → close-with-proof — and
   spawn follow-up cards for anything discovered-but-undelivered BEFORE
   the parent closes.

Run it as a PRIMARY agent to plan/drive a session, or as a SUBAGENT to have
any primary agent hand it a mission and receive a dispatched plan with the
evidence each specialist returned.

**Restart opencode after adding a project agent** so the Task tool picks it up.

All generalists on the roster are `mode: all` (DMR-062 for
athena/atom/hazel/jarvis/archivist/code-analyst/test-suite-auditor/
orchestrator-governor; DMR-020 for vllm/modal; `lucius`,
`board-evidence-auditor`, `prompt-engineer` as project files) — callable
through the Task tool as subagents and selectable directly as primary
agents. Verify with `opencode agent list`.

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
- **Skills are the second layer.** Load the `hf-dataset-publish` or `langfuse`
  opencode skill (`.opencode/skills/`) when a task matches its description, and the
  package-local `.cursor/skills/` (openrouter, ollama, modal, langfuse,
  apache-phoenix, braintrust, huggingface, langgraph, dojo-scoring,
  legalbench) for provider/sink depth inside a package.
- **Out of scope stays out of scope.** The `prompt-engineer` mutates prompts
  from evidence; it never changes what "correct" means, the scorer, the
  ground truth, or the schema — hand those to the owning surface.

Provenance: DMR-008 (2026-09-09) — the roster landed in `AGENTS.md` with the
dedicated `vllm-specialist` + `modal-specialist` project agents; issue #12
closed with the card. The `prompt-engineer` project agent and its GEPA
provenance file predate the roster. DMR-062 (2026-09-14) completed the team:
the four roster entries that were claimed-but-unregistered
(`athena-database-agent`, `atom`, `hazel-ui-software-master`,
`jarvis-systems-maximizer` — `opencode agent list` proved they did not
exist) were materialized as global agents, and the four new
hyper-specialists (`archivist-file-organizer`, `code-analyst`,
`test-suite-auditor`, `orchestrator-governor`) joined under the
global-file + committed-mirror rule; issue #62.
