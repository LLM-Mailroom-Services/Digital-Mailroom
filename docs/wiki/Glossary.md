# Glossary

Terms you will meet in cards, commits and code.

## Workspace and process

| Term | Meaning |
| :--- | :--- |
| **Hub** | This repo, `LLM-Mailroom-Services/Digital-Mailroom`. It integrates packages and owns wiring, governance, the board and tooling. |
| **Standalone** | An authoritative `Exios66/*` package repo. It owns that package's code and releases. |
| **Core member** | One of the five workspace packages (four built plus virtual `mailroom-corpus-eda`). |
| **Virtual member** | A workspace member with `package = false`: it has no build and isn't installed. |
| **Import / pull** | `sync_packages.py pull`: bring committed standalone source into `packages/*`. The only direction packages move. |
| **Cursor** | The recorded upstream SHA for each package in `scripts/packages_sync.json`. |
| **Snapshot** | A content-verified record of the hub's package copy against the cursor. |
| **Vendor snapshot** | A generated copy of workspace packages under the sandbox's `vendor/`. Made by `sync_vendor.py`, never hand-edited. |
| **Monorepo-ahead** | Files in the hub copy that differ from the cursor's upstream. A drift signal, never a push order. |
| **Pin** | A published git tag/SHA in a dependency line (such as dojo `v0.24.2`). It is bumped only when the pinned package is released. |
| **Preservation branch** | A branch keeping a pruned package intact (`feature/agent-mailroom`, `feature/enron-evaluation-environment`, `feature/claims-data-eda`). |
| **Feeder / feed** | An external corpus source (Enron, claims) that feeds the corpus EDA. |

## Board

| Term | Meaning |
| :--- | :--- |
| **Card (`DMR-0NN`)** | One unit of tracked work on `governance/TASKS.md`. It is the routing prefix for commits. |
| **`HUB-0NN`** | A predecessor-board card ID from `Exios66/mailroom-dev`. History only, never for new work. |
| **Lanes** | `unassigned` → `assigned` → `in_progress` → `needs_attention` → `done`. |
| **Evidence** | The card text naming commits, suite counts and proof. A card is not done without it. |
| **Archive** | The append-only bottom of the board where finished cards live. |
| **Served board / dispatch board** | The live, issue-backed Vercel site at `board-site/`. |
| **`pull-issues` / `sync-issues`** | Reverse and forward sync between served-board issues and `TASKS.md`. |

## Pipeline

| Term | Meaning |
| :--- | :--- |
| **13-node pipeline** | The `llm-mailroom` LangGraph state machine: intake → classify → extract → judge/arbiter → human review / boss → compile → catalog → archive. |
| **SorterAgent** | The classifier that assigns a document class and confidence. |
| **Sorter reviewer** | A second-opinion pass on classification. |
| **Judge / Arbiter** | The completeness lane: the Judge checks completeness, the Arbiter decides stand, re-extract or human review. |
| **Boss** | The adjudicator for matter conflicts, which never resolves them silently by recency. |
| **`compile_report`** | Deterministic matter-record assembly. No LLM call. |
| **Hash-chained archive** | The audit trail in which each record commits to the previous one. |
| **Relations clerk** | Post-archive scan that associates related documents. |
| **Live classes** | `contract`, `merger_agreement`, `corporate_record`, `correspondence`, `insurance_claim` (see `docs/v7-taxonomy.md`). |
| **Subclass** | A second-level document-type label within a class. It is not an intent label. |
| **v7 / v8 / v9** | Corpus schema generations. The pipeline pins `mailroom-dataset` v9.1. |

## Scoring and corpus

| Term | Meaning |
| :--- | :--- |
| **Dojo** | `llm-dojo-scoring`. It owns all scoring engine logic and metrics. |
| **GEPA** | Prompt-mutation/optimization runs against the scorers. |
| **EDA** | Exploratory data analysis, here the P0–P6 corpus phases in `mailroom-corpus-eda`. |
| **`mailroom-dataset`** | The current corpus on the HF Hub (`Lucius-Morningstar/mailroom-dataset`). |
| **`mailroom-corpus`** | The frozen v8 baseline corpus. |

## Tooling

| Term | Meaning |
| :--- | :--- |
| **Surgical / package / cross-package / full tiers** | The four test tiers in `docs/TESTING.md`. |
| **Honest double** | A test fake that can express real failure modes (malformed JSON, 429, timeout). |
| **Observatory** | The hosted view of The-Mailroom's visualizer. |
| **Specialist subagent** | A roster persona (docs, UI, data, prompts, vLLM, Modal, audit) invoked per concern. See [[Subagents]]. |
