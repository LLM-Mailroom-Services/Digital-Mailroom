# Architecture

## The map

```
Corpus feeds ────────────────> llm-mailroom (13-node pipeline)
                                     ▲             │
local-mailroom-sandbox ── executes ────┘             │ uses
  offline/local + Modal/vLLM GPU harness            ▼
  │                                         llm-dojo-scoring
  └────────────── uses scoring ─────────────> ALL engine + metrics

llm-mailroom ────────────────┐
local-mailroom-sandbox ──────┴── Langfuse / API ──> The-Mailroom
                                                  shared visualizer

Committed standalone sources ── import ──> Digital-Mailroom packages/
Imported workspace packages ── generate ─> sandbox vendor snapshots
Digital-Mailroom owns hub wiring, governance, board, and integration tooling.
```

Standalone **llm-dojo-scoring owns ALL scoring engine logic and metrics**;
standalone **llm-mailroom owns the 13-node pipeline**. Standalone
**local-mailroom-sandbox is the core offline/local and Modal/vLLM GPU testing
interface that executes that pipeline**. Standalone **The-Mailroom is the
shared visualizer used by BOTH llm-mailroom and sandbox through Langfuse/API**.

Digital-Mailroom imports committed authoritative package sources and generates
vendors. Implement package changes in the owning standalone source first;
never duplicate the pipeline or scorer in the hub, edit imported package or
vendor copies as implementation sources, or push hub implementations back.
Hub-owned wiring, governance, board, and integration tooling remain here.
See [[Sub-Package-Sync]] and [[Releases]] for import and release gates.

## Every repository, with links

Five core packages are imported into this hub (`packages/`) as git subtrees
from authoritative standalone `Exios66/*` repositories (four built, one
virtual). Two core packages and the two external corpus feeds have GitHub
Pages sites.

> **Pruned in DMR-079:** `llm-entity-extraction` and `llm-mailroom-graph`
> are standalone `Exios66/*` repos only (no longer synced); `agent-mailroom`
> is preserved on branch `feature/agent-mailroom`. Hub `v0.8.0` is the last
> release containing them.

| Layer | Repository | GitHub Pages |
| --- | --- | --- |
| Hub (integration, this repo) | [LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) | — |
| Hub — served board (`board-site/`, Vercel) | [digital-mailroom-theta.vercel.app](https://digital-mailroom-theta.vercel.app) | — |
| Corpus EDA + HF upload helpers | [Exios66/Mailroom-Corpus-EDA](https://github.com/Exios66/Mailroom-Corpus-EDA) | [exios66.github.io/Mailroom-Corpus-EDA](https://exios66.github.io/Mailroom-Corpus-EDA/) |
| Shared scoring engine | [Exios66/llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring) | — |
| LangGraph pipeline | [Exios66/llm-mailroom](https://github.com/Exios66/llm-mailroom) | — |
| Pixel-art visualizer console | [Exios66/The-Mailroom](https://github.com/Exios66/The-Mailroom) | [exios66.github.io/The-Mailroom](https://exios66.github.io/The-Mailroom/) (pixel console root; **terminal** `/docs/terminal/` pending live publish — [DMR-013](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/18)) |
| Local-first LLM sandbox | [Exios66/local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox) | — |

## External corpus feeds and preserved checkouts

Enron and claims remain usable standalone feeds; their datasets, taxonomy and
published sites retain their identities. DMR-093 removes their local copies
from the active workspace after #162. Both preservation branches point to
`59c879d9fb4480084e53137e2e9fb25650933944`; PR162 must keep these package trees byte-identical.

| Layer | Repository | GitHub Pages |
| --- | --- | --- |
| Corpus feed | [Exios66/Enron-Evaluation-Environment](https://github.com/Exios66/Enron-Evaluation-Environment) | [exios66.github.io/Enron-Evaluation-Environment](https://exios66.github.io/Enron-Evaluation-Environment/) |
| Corpus feed | [Exios66/claims-data-eda](https://github.com/Exios66/claims-data-eda) | [exios66.github.io/claims-data-eda](https://exios66.github.io/claims-data-eda/) |

Browse [Enron's preserved package](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/enron-evaluation-environment/packages/Enron-Evaluation-Environment) or
[claims' preserved package](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/claims-data-eda/packages/claims-data-eda). Use a separate checkout of the
preservation branch for its original complete workspace (including the old
hub chart generator). To selectively restore a package, reconcile membership,
sync entries, dependencies and tests explicitly; keep current root metadata.
The earlier `feature/agent-mailroom` preservation branch remains unchanged.

## The 13-node pipeline (llm-mailroom v0.7.1)

`intake → after_intake → classify → (retry_classify) → review_classify → extract →
(retry_extract) → judge_verify → arbiter → human_review / boss_escalation →
compile_report → catalog_write → archive → relations scan`.

(`after_intake`, #99: BERT fast-path skip → extract as `bert_intake`; gate-failed
triages → reviewer guard (#100 M5a) in verify/skip modes, else straight to classify.)

Two auxiliary flows operate outside the 13-node graph: the **Gmail triage
lane** (free OpenRouter model for single-document email uploads) and the
**relations clerk** (post-archive deterministic association scanning with
optional LLM judgment).

The **compile_report** node is the **computational procedural reporter**
(deterministic matter-record assembly — no LLM call); the reporter *agent*
is retired. The **intake** node is the **ingest specialist** (HUB-038) —
one fused TRIAGE + CLEAN + PREPARE pass over sliding windows. Classification
second opinions run through the **sorter reviewer** (Lane A), which stays
live.

## Repository layout

```
Digital-Mailroom/
├── AGENTS.md                    # workspace conventions (read before editing)
├── governance/TASKS.md          # the task board (single source of truth)
├── board-site/                  # served Kanban dispatch board (Vercel deploy root)
├── scripts/                     # sync_packages.py, board_state.py, github_labels.py, release_chain.py
├── .github/                     # YAML issue/PR templates, labels.json, CI workflow
├── .opencode/agents/            # specialist subagent roster (see [[Subagents]])
├── docs/wiki/                   # THIS wiki (version-controlled; sync-wiki.sh)
└── packages/                    # five imported core directories (git subtrees)
```

The specialist subagent roster (Task tool) and its rules are documented in
[[Subagents]].

Heavy assets (docs demos/screenshots, example PDFs, report archives) are
pruned from the monorepo; the exceptions are the corpus-eda EDA
deliverables, tracked in full per human directive (HUB-008).
