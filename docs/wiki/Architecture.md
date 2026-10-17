# Architecture

## The map

```
                    ┌── corpus feeds (colocated data) ─────────────────────┐
                    │  Enron-Evaluation-Environment   claims-data-eda      │
                    │  mailroom-corpus-eda   (mailroom-corpus, P0–P6 EDA)  │
                    └──────────────────────────┬───────────────────────────┘
                                               ▼
┌────────────────────────┐        ┌───────────────────────────────────────┐
│  llm-dojo-scoring      │◀───────│           llm-mailroom                │
│  shared scoring engine │ import │  LangGraph multi-agent pipeline       │
└────────────────────────┘        └──────────────────┬────────────────────┘
                                                     ▼
┌── surfaces ──────────────────────────────────────────┐
│  The-Mailroom (visualizer)     local-mailroom-sandbox│
│  Digital-Mailroom dispatch board (Vercel)            │
└──────────────────────────┬───────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────┐
│  Digital-Mailroom — this standalone repo             │
│  (central truth; every box lives in it)              │
└──────────────────────────────────────────────────────┘
```

## Every repository, with links

All seven packages live in this monorepo (`packages/`) as git subtrees and
mirror independent `Exios66/*` repositories that remain standalone and
operational. GitHub Pages sites exist for four of them.

> **Pruned in DMR-079:** `llm-entity-extraction` and `llm-mailroom-graph`
> are standalone `Exios66/*` repos only (no longer synced); `agent-mailroom`
> is preserved on branch `feature/agent-mailroom`. Hub `v0.8.0` is the last
> release containing them.

| Layer | Repository | GitHub Pages |
| --- | --- | --- |
| Hub (central truth, this repo) | [LLM-Mailroom-Services/Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) | — |
| Hub — served board (`board-site/`, Vercel) | [digital-mailroom-theta.vercel.app](https://digital-mailroom-theta.vercel.app) | — |
| Corpus feed | [Exios66/Enron-Evaluation-Environment](https://github.com/Exios66/Enron-Evaluation-Environment) | [exios66.github.io/Enron-Evaluation-Environment](https://exios66.github.io/Enron-Evaluation-Environment/) |
| Corpus feed | [Exios66/claims-data-eda](https://github.com/Exios66/claims-data-eda) | [exios66.github.io/claims-data-eda](https://exios66.github.io/claims-data-eda/) |
| Corpus EDA + HF upload helpers | [Exios66/Mailroom-Corpus-EDA](https://github.com/Exios66/Mailroom-Corpus-EDA) | [exios66.github.io/Mailroom-Corpus-EDA](https://exios66.github.io/Mailroom-Corpus-EDA/) |
| Shared scoring engine | [Exios66/llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring) | — |
| LangGraph pipeline | [Exios66/llm-mailroom](https://github.com/Exios66/llm-mailroom) | — |
| Pixel-art visualizer console | [Exios66/The-Mailroom](https://github.com/Exios66/The-Mailroom) | [exios66.github.io/The-Mailroom](https://exios66.github.io/The-Mailroom/) (pixel console root; **terminal** `/docs/terminal/` pending live publish — [DMR-013](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/18)) |
| Local-first LLM sandbox | [Exios66/local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox) | — |

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
└── packages/                    # one directory per standalone repo (git subtree)
```

The specialist subagent roster (Task tool) and its rules are documented in
[[Subagents]].

Heavy assets (docs demos/screenshots, example PDFs, report archives) are
pruned from the monorepo; the exceptions are the corpus-eda EDA
deliverables, tracked in full per human directive (HUB-008).
