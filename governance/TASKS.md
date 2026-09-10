# TASKS.md — the Digital-Mailroom task board

The single source of truth for cross-agent task state in the **Digital-Mailroom
standalone repo** (`LLM-Mailroom-Services/Digital-Mailroom`): what is
**assigned**, **in progress**, **needs attention**, and **done**. Every agent
(and human contributor) reads this board before working and keeps it current
while working. It is a WORKING DOCUMENT, not documentation — modify it as work
happens, never delete history (finished cards move to the Archive at the bottom).

**Lineage (DMR-001, 2026-09-09):** this board was restarted fresh for the
standalone Digital-Mailroom version. The predecessor board — the `HUB-*` cards
of the original `Exios66/mailroom-dev` monorepo — remains canonical for that
repo; HUB-era history and evidence live there and in this repo's git history
(`git log --follow -- governance/TASKS.md`). The `DMR-` namespace starts at
DMR-001 and never reuses HUB numbers.

Scope: **this repo's monorepo-level work** (workspace wiring, cross-package
governance, board tooling, docs, releases). Work scoped to a single package is
tracked by that package's own governance — this board holds the hub view and
cross-package cards.

**Machine-readable state (DMR-001):** this board is computationally readable
via `python scripts/board_state.py` — `status` (snapshot, `--json` for
machines), `card DMR-0NN` (one card + its commits), `check` (invariants:
structural contradictions exit 1; hygiene drift is warned), `sync-issues`
(label sync onto synced issues), `pull-issues` (import served-board lane moves
back into this file), `project-init`/`project-sync` (GitHub Projects v2
mirror). The label taxonomy for issues lives in `.github/labels.json`
(`stage/*` = these lanes, `attention/*` = the needs_attention tags, `type/*`,
`priority/*`, `domain/*`, `kanban` marker); the CI gate
`.github/workflows/board-governance.yml` runs `check` + the label audit on
every change to `governance/`, `scripts/`, or `.github/`.

**Served board:** the live, issue-backed dispatch board for this repo is
**https://digital-mailroom-theta.vercel.app** (Vercel project
`digital-mailroom`, deploy root `board-site/`, `GITHUB_TOKEN` production
secret). It reads `kanban`-labeled issues in
`LLM-Mailroom-Services/Digital-Mailroom`; writes (move/edit/archive) PATCH
back to those issues. The canonical board stays this file — run
`board_state.py pull-issues` to import site-side lane moves, `sync-issues` to
push this file's truth into the issues.

## How to use — four steps

1. **Read first.** Read this board (and open GitHub issues) at session start,
   before any task: cards claimed by others, cards covering the work you were
   about to do, and open needs-attention items. Never duplicate or race a
   claimed card.
2. **Claim.** Claim an `unassigned` card by moving it to `assigned` and setting
   Owner to your agent name + date. The moment ANY work exists — a first edit,
   a diff, a branch, a run in flight — the card moves to `in_progress`. Label
   it before the code, never after; the table must never lie about reality.
3. **Work with the card current.** Update status and Evidence as you go.
   Stuck or awaiting review? Move to `needs_attention` with a tagged note
   (`needs:` blocked-on / `review:` evidence / `decision:` the question).
   Anything discovered but not delivered spawns its own card BEFORE your card
   closes.
4. **Close with proof.** `done` requires: the package suite(s) for the touched
   packages green, `git status` clean for the card's scope, Evidence naming
   the commit(s), and — for synced cards — the GitHub issue closed in the same
   commit. Then move the card to the Archive. An agent is NOT done until its
   card says so.

## Lanes

| Lane | Meaning |
|---|---|
| `unassigned` | Queued and unclaimed — free for the next available agent or team to claim. Owner must be `unclaimed`. |
| `assigned` | Claimed (or queued with an owner), nothing underway — no draft, no diff, no branch. |
| `in_progress` | ANY work exists and an owner holds it. ONE owner per card. |
| `needs_attention` | Blocked, awaiting review, or awaiting a decision — the Evidence note says which (`needs:` / `review:` / `decision:`). |
| `done` | Finished, verified, evidenced — moved to the Archive below. Never deleted; reopen by moving back to `unassigned` with a dated note. |

## Open cards

| Card | Status | Task | Owner | Issue | Evidence |
|---|---|---|---|---|---|
| DMR-011 | `unassigned` | Harden `sync_packages.py patch_push` so uncommitted work can never propagate: copy committed blobs (`git archive HEAD` / `git ls-tree`) and/or re-assert a per-package clean-tree guard before each package copy; retire the AGENTS.md + wiki race caveat when done. **Status:** the committed-blob extraction fix is shipped (DMR-028); the AGENTS.md + wiki race caveat retirement may still be pending — verify. | unclaimed | [#16](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/16) | synced from HUB-044 [#28](https://github.com/Exios66/mailroom-dev/issues/28); DMR-028 shipped `git ls-tree -r -z HEAD` + `git cat-file blob` fix |
| DMR-012 | `unassigned` | Gmail triage production-readiness residuals: live re-send/provenance operator proof, CI secret-presence check (`GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD`), Langfuse/Phoenix trace checklist for `gmail-triage`, ops-lamp alerting on `checks.gmail_intake`, and watcher-stability/free-swarm/failed-bin runbooks. HUB-037/039/043/048 deliveries are in place — do not redo. | unclaimed | [#17](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/17) | synced from HUB-064 [#43](https://github.com/Exios66/mailroom-dev/issues/43) |
| DMR-013 | `unassigned` | Run the live `packages/The-Mailroom/scripts/publish_pages.sh` so the terminal site goes live at the Pages root (currently the v0.3.0 pixel console is served; `/terminal/` 404s) and verify `publish_pages.sh --status`; TUI/site code, 0.4.0 release, and upstream sync are already delivered. | unclaimed | [#18](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/18) | synced from HUB-054 [#25](https://github.com/Exios66/mailroom-dev/issues/25); only the live publish is pending |
| DMR-014 | `unassigned` | Specialist mutations on mailroom-corpus v7+v8: implement structured specialist mutation operators + fitness/registry and run the first evolution pass. `needs:` tokenizer-budget alignment (GT-integrity half now evidenced by the HUB-032 reconciliation + `content_sha256` loader proof). | unclaimed | [#19](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/19) | synced from HUB-062 [#11](https://github.com/Exios66/mailroom-dev/issues/11); no mutation operators/registry exist yet; DMR-035 confirmed 2026-09-10 |
| DMR-015 | `unassigned` | Derive mailroom-named successor keys for the frozen pre-v8 insurance-subclass surfaces — vision sorter rule 40 (`sorter_docclass_vision_v1`), `_PILOT_CONTEXT`, `reviewer_docclass_pilot_v0` — teaching the v8 six-token set (carrier/pde/outpatient/inpatient + property/auto), plus the docclass-pilot examples refresh; same-surface A/Bs before any default change. Coordinate `_PILOT_CONTEXT` with DMR-016. | unclaimed | [#20](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/20) | synced from HUB-042 [#30](https://github.com/Exios66/mailroom-dev/issues/30); surfaces still 4-token at `src/prompts.py:1266`; DMR-033 confirmed 2026-09-10 |
| DMR-016 | `unassigned` | Add NEW docclass judge/reviewer/arbiter/boss prompt keys with five-class + `unknown` grading language per plan §67, mirror byte-identical into The-Mailroom (and re-sync the stale 32→59-key mirror), defaults unchanged until a same-surface A/B. `decision:` keep the extended 8-class surface as deliberate eval design (KANBAN-033 lineage) or move to five-class grading. | unclaimed | [#21](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/21) | synced from HUB-020 [#26](https://github.com/Exios66/mailroom-dev/issues/26); extended-8 grading persists at `src/prompts_docclass.py:92-110,246-250,313-315,371-372`; DMR-034 confirmed 2026-09-10 |
| DMR-017 | `unassigned` | GEPA prompt mutations on docclass v7+v8: run the prompt-engineer/GEPA loop against the five-class corpus surface and register the first `mailroom_v` docclass lineage keys (sorter + judge/reviewer) with same-surface A/Bs. `needs:` the DMR-016 five-class decision; never mutate frozen `docclass_*` keys. | unclaimed | [#22](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/22) | synced from HUB-061 [#7](https://github.com/Exios66/mailroom-dev/issues/7); only `sorter_mailroom_v0` (HUB-041) exists; DMR-036 confirmed 2026-09-10 |
| DMR-018 | `unassigned` | v9 corpus candidate: re-evaluate INSURBIAS (CC-BY-4.0 insurance-claim narratives) as a v9 source alongside the P4 expansion priorities — insurance workflow is now MEDIUM with adjuster 150/950 after v8 — license permitting and only with decision/adjudication GT or an explicit GT-gap convention. | unclaimed | [#23](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/23) | synced from HUB-036 [#27](https://github.com/Exios66/mailroom-dev/issues/27); v9 not started, INSURBIAS deferred; DMR-037 confirmed 2026-09-10 |

## Rules that keep the board honest

- **One owner per card.** Never work a card someone else owns — offer help on
  the issue or take over by an explicit handoff recorded in Evidence.
- **Claim before edit.** A card you are about to touch is claimed by you in
  the same session the work starts; an unclaimed card is fair game but must
  be claimed at its first edit.
- **Update, don't duplicate.** Work that addresses an existing card's problem
  updates THAT card — never a parallel card, never a duplicate issue.
- **Later timestamp wins.** If two edits collide on one card, the later dated
  note stands; the overwritten party posts a correction rather than reverting.
- **No silent completion.** A card without its closing Evidence is, to every
  other agent, still in flight.
- **Commit discipline.** Reference cards in commits: `DMR-00N: <summary>` or
  `DMR-00N claimed/reopened` in the message body. **Stage targeted paths
  only:** `git add <explicit paths>` for exactly your card's files — never
  `git add .` / `-A` / a bare directory. This is a shared checkout: before
  every commit, `git status --porcelain` and unstage anything you don't own.

## Issues vs board — the card↔issue law

Every board card has a **synced GitHub issue** in this repo — one card = one
issue, opened from the *Board card (DMR-0NN)* template
(`.github/ISSUE_TEMPLATE/hub_card.yml`). Why this is a law: the served board
at https://digital-mailroom-theta.vercel.app reads `kanban`-labeled issues, so
a card without a synced issue never appears on it. Concretely:

- Open the card's issue before (or while) claiming it; fill the card's
  Issue column with the full link. Apply the `kanban` + `stage/*` +
  `priority/*` + `domain/*` labels (`board_state.py sync-issues` does the
  label mapping from the board).
- **Mirror lane moves both ways** — board → issue: post a dated "Board lane
  move" comment; issue → board (a move made on the served site): run
  `python scripts/board_state.py pull-issues` to report the drift, then
  `--apply` to rewrite the Lane cell + append a dated Evidence note.
- **Close the issue in the SAME commit that archives the card.** A `done`
  card with an open issue (or an open card with a closed one) is a board
  inconsistency — fix it immediately.

## Archive

- **DMR-039** (done 2026-09-10) — **Comprehensive offline sandbox documentation** — Owner `opencode` — DELIVERED: `docs/SANDBOX-GUIDE.md` (14-section complete reference: prerequisites, setup, configuration, provider profiles, full CLI reference, Docker/Jupyter, evaluations, job system, Modal deployment, SSH tunnels, tracing, datasets, metrics, troubleshooting), `docs/wiki/Sandbox-Jobs.md` (job runner deep-dive), `docs/wiki/Sandbox-Modal.md` (Modal deployment guide), updated `docs/wiki/Offline-Sandbox.md` (expanded with quick-start checklist, CLI reference, all features), `_Sidebar.md` nav updated with new pages.
- **DMR-040** (closed 2026-09-10) — **Audit finding incorrect** — Owner `board-evidence-auditor` — Claimed `vllm-specialist.md:83-84` still references `--disable-log-requests` — **factually wrong**: lines 83-84 already have `--no-enable-log-requests` (correct flag). DMR-031 fix already covered this line. Card closed, no action needed.
- **DMR-023** (done 2026-09-10) — **Modal deploy test stub fix — llm-mailroom** — Owner `opencode` — FIXED: `packages/llm-mailroom/src/tests/test_vllm_modal_capability.py` line 30 `_Secret.from_local` → `_Secret.from_dict`. Deploy file already fixed (DMR-029); test mock now matches the live API.
- **DMR-024** (done 2026-09-10) — **Modal deploy test stub fix — llm-entity-extraction** — Owner `opencode` — FIXED: `packages/llm-entity-extraction/tests/test_kanban096_modal_vllm.py` line 44 `_Secret.from_local` → `_Secret.from_dict`. Deploy file already fixed (DMR-030); test mock now matches the live API.
- **DMR-037** (done 2026-09-10) — **Merged into DMR-018** — Owner `board-evidence-auditor` — INSURBIAS v9 evaluation duplicate. Audit finding confirmed the gap (no evaluation exists); work scope already covered by DMR-018.
- **DMR-036** (done 2026-09-10) — **Merged into DMR-017** — Owner `board-evidence-auditor` — GEPA mailroom_v docclass lineage duplicate. Audit finding confirmed the gap (only pilot variants exist); work scope already covered by DMR-017.
- **DMR-035** (done 2026-09-10) — **Merged into DMR-014** — Owner `board-evidence-auditor` — Specialist mutation operators duplicate. Audit finding confirmed the gap (no code exists); work scope already covered by DMR-014.
- **DMR-034** (done 2026-09-10) — **Merged into DMR-016** — Owner `board-evidence-auditor` — Five-class docclass prompt keys duplicate. Audit finding confirmed the gap (extended-8 grading persists); work scope already covered by DMR-016.
- **DMR-033** (done 2026-09-10) — **Merged into DMR-015** — Owner `board-evidence-auditor` — Insurance subclass successor keys duplicate. Audit finding confirmed the gap (4-token set persists); work scope already covered by DMR-015.
- **DMR-032** (done 2026-09-10) — **Audit finding — DMR-026 gap: align htcondor vLLM templates** — Owner `vllm-specialist (opencode)` — VERIFIED + FIXED: both `.sub` files now pin `v0.28.0` (lines 25/33); `serve_vllm.sh:16` uses `--no-enable-log-requests`. Commit `c69f1537`.
- **DMR-031** (done 2026-09-10) — **Audit finding — DMR-025 gap: refresh vllm-specialist.md version policy** — Owner `vllm-specialist (opencode)` — VERIFIED + FIXED: `.opencode/agents/vllm-specialist.md` line 37 states v0.29.0 current stable, v0.28.0 family pin; lines 41-44 document the `--enable-log-requests` rename and Model Runner V2 change.
- **DMR-030** (done 2026-09-10) — **Audit finding — DMR-024 gap: port Modal vLLM fixes to llm-entity-extraction** — Owner `modal-specialist (opencode)` — VERIFIED + FIXED: `Secret.from_dict` (line 90), image `v0.28.0` (line 66), `--no-enable-log-requests` (line 133), `entity-vllm-cache` Volume (line 113), `MODAL_VLLM_REVISION` (lines 70/89/155-157), `modal==1.5.5` pin.
- **DMR-029** (done 2026-09-10) — **Audit finding — DMR-023 gap: port Modal vLLM fixes to llm-mailroom** — Owner `modal-specialist (opencode)` — VERIFIED + FIXED: `Secret.from_dict` (line 96), image `v0.28.0` (line 69), `--no-enable-log-requests` (line 149), `mailroom-vllm-cache` Volume (line 101), `MODAL_VLLM_REVISION` (lines 58/77/143-145), `modal==1.5.5` pin.
- **DMR-028** (done 2026-09-10) — **Fix `sync_packages.py patch_push` race condition** — Owner `opencode` — DELIVERED: replaced `git ls-files` + `shutil.copy2` (copies from working tree, propagating uncommitted changes) with `git ls-tree -r -z HEAD` + `git cat-file blob` (extracts committed blobs only). Retired the HUB-044 race caveat from `AGENTS.md` and `docs/wiki/Sub-Package-Sync.md`. **Verified:** `board_state.py check` 0/0, `scripts/sync_packages.py` no longer touches the working tree during `patch_push`.
- **DMR-027** (done 2026-09-10) — **Sandbox job CLI (`sandbox run`) — vLLM + Modal + OTLP trace sink with locked preflight, resumable checkpoints, job polling, and local↔Modal↔API metrics** — Owner `modal-specialist (opencode)` — DELIVERED (commit `9a988f9`): a spec-driven, resumable eval runner in `packages/local-mailroom-sandbox`. **New code:** `src/mailroom_sandbox/job/` (`spec.py`, `checkpoint.py`, `preflight.py`, `runner.py`, `otel.py`, `metrics.py`, `remote.py`); `src/mailroom_sandbox/corpus.py`; `src/mailroom_sandbox/prompt_registry.py`; `deploy/modal_job.py` worker. **CLI:** `sandbox run preflight|start|status|resume|cancel|list`, `sandbox prompts list|show`, `sandbox metrics compare --runs/--log`. **Verified:** full suite `135 passed / 1 skipped`. Issue [#32](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/32) closed 2026-09-10.
- **DMR-026** (done 2026-09-10) — **Align htcondor vLLM templates** — Owner `vllm-specialist (opencode)` — VERIFIED + FIXED by DMR-032: both `.sub` files now pin `v0.28.0`, `serve_vllm.sh` uses `--no-enable-log-requests`.
- **DMR-025** (done 2026-09-10) — **Refresh vllm-specialist.md version policy** — Owner `vllm-specialist (opencode)` — VERIFIED + FIXED by DMR-031: v0.29.0 current stable, v0.28.0 family pin, `--enable-log-requests` rename documented.
- **DMR-022** (done 2026-09-09) — **vLLM v0.28.0 serving sweep — log-flag rename, memory posture, local↔Modal parity** — Owner `vllm-specialist (opencode)` — DELIVERED (commit `bf9430a`): the vLLM-specific half of the sandbox hardening, delegated to the vllm-specialist and verified by the caller. **Boot-breaking fix:** `--disable-log-requests` does not exist in vLLM v0.28.0 (per-request logging is now opt-in `--enable-log-requests`) — both the Modal argv and the compose command now use `--no-enable-log-requests`; the newly pinned image would otherwise have rejected its own argv at boot. **Memory posture:** `--gpu-memory-utilization 0.90` (below vLLM's 0.92 default) and `--max-num-seqs 256` (vLLM's L4/OpenAI-server default), env-overridable via `MODAL_VLLM_GPU_MEMORY_UTILIZATION`/`MODAL_VLLM_MAX_NUM_SEQS` (compose `VLLM_GPU_MEMORY_UTILIZATION`/`VLLM_MAX_NUM_SEQS`). **Secret passthrough fix:** `MODAL_VLLM_REVISION` + both new knobs joined `CONFIG_ENV_KEYS` — the container re-imports the module, so deploy-time env must travel via the Secret or argv silently falls back to defaults. **Compose parity:** same image tag and argv, `VLLM_MODEL`/`VLLM_MAX_MODEL_LEN` substitution, server-side bearer `VLLM_API_KEY` and `HF_TOKEN` env matching Modal. **Version decision:** keep v0.28.0 in both pins — v0.29.0 (2026-09-09) flips Model Runner V2 to the default for all models with zero soak time; bump both after a live parity run. **Deliberately not added:** prefix caching/chunked prefill (default-on in v0.28.0), async scheduling (experimental), `--enforce-eager`, `--served-model-name`, `--guided-decoding-backend` (replaced by `--structured-outputs-config`), `--swap-space` (removed), KV-cache fp8. **Tests:** `tests/test_modal_vllm.py` 18 → 25 (flag-rename regression, memory env overrides, Secret passthrough, `TestComposeParity`), package suite 83 passed / 1 skipped; `docker compose --profile vllm config` validates.
- **DMR-021** (done 2026-09-09) — **Offline sandbox Modal best-practice hardening — SDK 1.5.5 pin, `Secret.from_local` removal fix, vLLM v0.28.0 image, weight pre-warm, compile-cache Volume, cost guards, contract tests** — Owner `modal-specialist (opencode)` — DELIVERED (commit `0eea320`, pushed): the Modal deploy surface in `packages/local-mailroom-sandbox` is now SDK-1.5.5-valid and pinned. **Critical fix:** SDK 1.5.5 removed `Secret.from_local`, which `deploy/modal_vllm.py` used — the app would have failed at import/deploy; knobs now use `Secret.from_dict` (skips absent keys, preserving optional `HF_TOKEN`/`MODAL_VLLM_API_TOKEN`; `from_local_environ` raises on missing). **Pins:** `modal==1.5.5` in the `[deploy]` extra (was `>=0.73`) + `uv.lock` re-locked; image default `vllm/vllm-openai:v0.28.0` (was `latest`) matching the local compose pin (`v0.29.0` newest upstream stable, noted for a deliberate bump); optional `MODAL_VLLM_REVISION`. **Cold start:** `sandbox-vllm-cache` Volume at `/root/.cache/vllm` (JIT/CUDA graphs) + CPU-only `download_model` pre-warm (`modal run deploy/modal_vllm.py::download_model`, HF cache Volume + commit) + `--check` bearer-aware `/models` probe in the local entrypoint. **Cost discipline:** App cost-allocation tags; `max_containers=1` / `min_containers=0` defaults; `MODAL_VLLM_SCALEDOWN_SECONDS`/`MODAL_VLLM_MAX_CONTAINERS`/`MODAL_VLLM_MIN_CONTAINERS`/`MODAL_VLLM_STARTUP_TIMEOUT_SECONDS` knobs; verified pricing table (L4 ≈ $0.80/hr warm, scale-to-zero after 900 s) with deploy → verify → teardown → security → snapshots/decorator → troubleshooting in `deploy/README.md`. **Tests:** new `tests/test_modal_vllm.py` (18 network-free tests) pins argv, bearer env, secrets, volumes, cost guards, image pin, and regression-guards the removed API; package suite 76 passed / 1 skipped; app imports cleanly against real `modal==1.5.5` (scratch venv).
- **DMR-020** (done 2026-09-09) — **vLLM + Modal agents callable as primary agents and subagents** — Owner `opencode` — DELIVERED (commit `2708190`): `.opencode/agents/vllm-specialist.md` and `.opencode/agents/modal-specialist.md` now carry `mode: all` (were `mode: subagent`), so both are selectable as primary agents **and** callable through the Task tool as subagents; `opencode agent list` (fresh CLI process) reports `vllm-specialist (all)` + `modal-specialist (all)`. `AGENTS.md` roster intro + `docs/wiki/Subagents.md` document the primary+subagent availability. Issue #25 closed 2026-09-09.
- **DMR-019** (done 2026-09-09) — **Adopt the `unassigned` lane — unclaimed cards free to claim** — Owner `opencode` — DELIVERED (commit `6e8d02b`): the served board's five-lane flow is now the canonical board's too — `scripts/board_state.py` `LANES`/`LANE_LABELS` gain `unassigned`/`stage/unassigned` with lane-owner coherence rules; `.github/labels.json` (33-label manifest, synced live) + `hub_card.yml` add the lane; `governance/TASKS.md` documents five lanes. Issue #24 closed 2026-09-09.
- **DMR-010** (done 2026-09-09) — **HUB → DMR open-issue sync — 8 still-open HUB cards mirrored with synced issues + cross-links** — Owner `opencode` — DELIVERED (commit `570f2b9`): the 9 open `kanban` issues on the predecessor board were verified against this checkout; 8 carried open work and are mirrored as DMR-011..DMR-018 (#16–#23). Issue #15 closed 2026-09-09.
- **DMR-009** (done 2026-09-09) — **Repo hygiene + wiki publication — dead-branch prune, residual Speed Insights lockfile delta, subagents + board configs on the wiki** — Owner `opencode` — DELIVERED (commit `da0ea35`): all 8 dead remote branches deleted; wiki published for the first time (14 pages). Issue #13 closed 2026-09-09.
- **DMR-008** (done 2026-09-09) — **Specialist subagent roster in AGENTS.md + dedicated vLLM/Modal subagents** — Owner `opencode` — DELIVERED (commit `468f731`): `AGENTS.md` carries the specialist roster section; new project subagents `.opencode/agents/vllm-specialist.md` and `.opencode/agents/modal-specialist.md`. Issue #12 closed 2026-09-09.
- **DMR-007** (done 2026-09-09) — **Retire stray `board-site` Vercel project + served-board write-path proof** — Owner `human` — DELIVERED (card commit `f3a4042`): the duplicate project `board-site` was deleted via the Vercel API. Issue #11 closed 2026-09-09.
- **DMR-006** (done 2026-09-09) — **Org-migration reference audit + wiring sweep + CI gate** — Owner `opencode` — DELIVERED (commit `849663a`): `docs/reports/audits/org_migration_audit.md` + `.json`, new `scripts/audit_references.py`, wired into CI. Issue #10 closed 2026-09-09.
- **DMR-004** (done 2026-09-09) — **Push-triggered deploys for the served board — Vercel Git integration** — Owner `opencode` — DELIVERED (commit `4347055`): Vercel GitHub App installed, project `digital-mailroom` linked. Issue #8 closed 2026-09-09.
- **DMR-001** (done 2026-09-09) — **Standalone board bootstrap — fresh DMR TASKS.md + tooling re-point** — Owner `opencode` — DELIVERED (commit `be75d1e`): fresh DMR board + full tooling re-point to `LLM-Mailroom-Services/Digital-Mailroom`. Issue #5 closed 2026-09-09.
- **DMR-002** (done 2026-09-09) — **Served dispatch board for the standalone clone — new Vercel project** — Owner `opencode` — DELIVERED (commit `be75d1e`): new Vercel project `digital-mailroom`. Issue #6 closed 2026-09-09.
- **DMR-003** (done 2026-09-09) — **Original mailroom-dev board access — write path + deployment URL** — Owner `human` — DELIVERED (commit `be75d1e`): live write path verified. Issue #7 closed 2026-09-09.
- **DMR-005** (done 2026-09-09) — **Cross-board navigation tabs — DMR ↔ HUB served boards** — Owner `human` — DELIVERED (human directive 2026-09-09): board-switcher cross-links both served boards. Issue #9 closed 2026-09-09.
