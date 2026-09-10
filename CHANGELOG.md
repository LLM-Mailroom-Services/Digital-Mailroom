# Changelog — Digital-Mailroom

All notable changes to the **Digital-Mailroom monorepo itself** (workspace wiring,
cross-package governance, sync tooling, corpus governance, hub infrastructure)
are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html) — while
the hub is `0.x` (pre-1.0), a **MINOR** bump may carry breaking workspace
changes; **PATCH** is fixes-only. Every hub release is an annotated git tag
`vX.Y.Z` (`mailroom-hub vX.Y.Z` message) mirrored as a GitHub Release; the
`[Unreleased]` section accumulates between releases.

Scope note: the hub chain versions the **monorepo as a whole**. Package-level
releases (llm-mailroom, llm-dojo-scoring, …) are cut in their standalone
repositories per the release train (HUB-005) — see each package's own
`CHANGELOG.md`; the standalone repos remain the release vehicles for deployed
surfaces. The pre-import history in this repository (before 2026-08-30)
belongs to the standalone mailroom lineage that became `packages/llm-mailroom`
and is recorded there, not here.

## [Unreleased]
### Added

- **Org-migration reference audit + CI gate (DMR-006, 2026-09-09):** the
  hub-identity migration from `Exios66/mailroom-dev` to
  `LLM-Mailroom-Services/Digital-Mailroom` is now audited and enforced.
  New `docs/reports/audits/org_migration_audit.md` + `.json` inventory every
  reference across three tiers — migrate (hub), intentional package-mirror
  (`Exios66/*` standalone repos), and historical (HUB-era) — and new
  `scripts/audit_references.py` fails CI (wired into
  `.github/workflows/board-governance.yml`) on any non-allowlisted stale hub
  reference. Sweep applied to the issue-template config links, the changelog
  scope line + compare/release footer, the wiki pages (Home, _Sidebar,
  Getting-Started, FAQ incl. the stale Root-Directory note, Board-Governance,
  Releases, Architecture), the README family, `docs/docclass-merged-plan.md`,
  `.opencode/agents/prompt-engineer.md`, `LICENSE`, the README footer
  (LLM-Mailroom-Services · Exios66 · grantmooslin), and `sync_packages.py`'s
  propagation message. Package mirrors, upstream pins, and HUB-era history are
  deliberately unchanged (allowlisted).
- **Standalone board restart + served dispatch board (DMR-001/DMR-002/DMR-003,
  2026-09-09):** the Digital-Mailroom clone now runs its own task board and
  served site. **DMR-001** restarts `governance/TASKS.md` in a fresh `DMR-`
  namespace (predecessor `HUB-*` cards stay canonical in `Exios66/mailroom-dev`;
  lineage recorded in the board header) and re-points every board tool at
  `LLM-Mailroom-Services/Digital-Mailroom`: `scripts/board_state.py`
  (`DEFAULT_REPO`, card/archive/lane/issue regexes, project title),
  `scripts/github_labels.py`, `.github/labels.json`, `scripts/release_chain.py`,
  `scripts/release_notes.py`, and the `.github/ISSUE_TEMPLATE/hub_card.yml`
  template; the 32-label kanban taxonomy was seeded in the new repo. **DMR-002**
  stands up the new Vercel project `digital-mailroom` (Root Directory
  `board-site`, Vercel Authentication off, `GITHUB_TOKEN` production secret)
  serving the issue-backed board at
  **https://digital-mailroom-theta.vercel.app** — `board-site/lib/gh.js`,
  `board-site/api/board/[id].js` and `board-site/index.html` now read/write the
  new repo under the `DMR-` prefix with the new CORS origins, and a repo-root
  `.vercelignore` keeps CLI deploys limited to `board-site/`. **DMR-003**
  verified the predecessor board stays modifiable (`PATCH /api/board/HUB-064`
  through the original proxy) and disabled Vercel Authentication on project
  `mailroom-dev` so raw deployment URLs (e.g.
  `mailroom-4sc2d0sxd-lucius-projects-54efe0bb.vercel.app`) serve publicly.
  Docs currency: `AGENTS.md` board/served-board sections, `README.md` hub +
  governance pointers, `docs/wiki/Served-Board.md` and `docs/wiki/sync-wiki.sh`.
- **Release-notes generator + template (`.github/RELEASE_TEMPLATE.md` +
  `scripts/release_notes.py`):** all hub GitHub Releases now render their body
  with `python scripts/release_notes.py X.Y.Z` — it compiles the freshly-cut
  `## [X.Y.Z]` changelog section (the detailed change summary) with the merged
  pull requests in the release window (`gh`-resolved, offline git fallback)
  and the key HUB-card commits into a single `--notes-file` body that always
  carries: a summary + epoch title, highlights (one line per landed card), the
  full changelog section, the related PRs, the critical commits, and
  changelog + `v<prev>...v<ver>` compare references. Options: `--title`
  (epoch suffix), `--out` (write the notes file), `--no-net`, `--json`.
  Template placeholders mirror the generated sections — edit the template to
  change what every release carries, never hand-type a body. Docs: wiki
  Releases.md "Release-notes template" section + AGENTS.md command index.
- **Served Kanban board deployed live (HUB-055, 2026-09-06):** the HUB-055
  dispatch board is now served in production at
  **https://mailroom-dev.vercel.app** (Vercel project `mailroom-dev`, deploy
  root `board-site/`). Read path (`GET /api/board` → live kanban cards from
  the `kanban`-labeled issues) and write-back (`PATCH /api/board/HUB-0NN`)
  verified end-to-end in production against `Exios66/mailroom-dev` via the
  zero-dependency token proxy; `GITHUB_TOKEN` stored as a Vercel production
  secret.
- **Served-board docs + governance integration (HUB-058, 2026-09-06):** new
  wiki page `docs/wiki/Served-Board.md` documents the live dispatch board
  end to end (layout, read/write API contract, config/env secrets, redeploy
  workflow, `pull-issues` reconciliation) and is cross-linked from the wiki +
  AGENTS.md; stale wiki pages refreshed (Home facts → corpus v8/2,000 rows +
  6-built/4-virtual + hub v0.4.0 + served-board row; Architecture surfaces +
  layout; Releases deploy surfaces + actual `--notes-file` cut practice; FAQ
  canonical-dataset + served-board Q&A; Getting-Started live-board pointer;
  Sub-Package-Sync sweep one-liner + HUB-044 caveat). Governance law
  reconciled in TASKS.md §"Issues vs board": the board-only carve-out is
  retired for the card↔issue law — every board card carries a `kanban`
  synced issue (or it won't appear on the served board) + the post-site-edit
  `pull-issues` obligation.

## [0.4.0] - 2026-09-05
### Added

- **Terminal-stylized TUI + terminal GH Pages site for The-Mailroom
  (HUB-054, 2026-09-04):** the The-Mailroom package's TUI was rebuilt as a
  full typed-command REPL over a rich Live frame — `mailroom@floor:~$` prompt,
  status header + scrollback + prompt, raw-key line editor (backspace/arrows/
  Tab completion/Ctrl+L/Ctrl+C), background floor poller pushing AgentLab
  banners, split into `tui/commands.py` (registry + man pages) / `views.py`
  (renderers) / `corpus.py` (Hub corpus client over `mailroom_ui/hf_corpus.py`)
  / `repos.py` (constellation manifest + fail-soft GitHub enrichment). Command
  set: help/man/clear/history/date/echo/uname/neofetch/floor/review/sessions/
  metrics/inspect/debug/filter + `corpus ls|show|search|stats` + `repos ls|
  open` + `open <name>`. `mailroom_console.py` re-exports every legacy
  renderer (existing 24 TUI tests pass unchanged; extended to 37). New CLI
  flags `--view corpus|repos`, `--corpus …`, `--repos …`. A new terminal
  GH Pages site (`terminal/` — owlcot-family: CRT overlay, amber/green/cyan
  themes, ghost-text Tab completion, history + prefs in localStorage, boot
  sequence, animated man pages) is staged to `gh-pages:/docs/terminal/` by
  `publish_pages.sh` (pixel console stays the root); commands cover the
  snapshot traces + LIVE corpus browsing via datasets-server (CORS verified)
  + the constellation repo browser. `scripts/export_corpus_catalog.py` writes
  the slim `site/data/corpus.json` catalog (filename/class/subclass/sha/split
  + row-index offsets; `--check` verifies counts + sha integrity; 2,000 rows
  live-verified). `hf_corpus.fetch_rows` gains offset/page_sleep/429 backoff.
  The-Mailroom release 0.3.0 → 0.4.0 (its own package cut). Pipeline
  architecture diagrams updated for the v0.4.0 agent roster.
- **Served Kanban Dispatch Board — live, issue-backed web site (HUB-055,
  2026-09-05):** the composed `mailroom-dispatch-board.html` enhanced board is
  wired into a served path on Vercel with automatic site updates + editability.
  Every board card is now a synced GitHub issue (seeded #23–#30 + relabeled
  #22 as HUB-055's mirror; one card = one issue with `kanban`/`stage/*`/
  `priority/*`/`domain/*` labels). Serve path is `board-site/` (Vercel Root
  Directory): `api/board.js` GETs live cards from `labels=kanban` issues and
  POSTs new ones; `api/board/[id].js` PATCHes lane/priority/body/assignees
  (lane moves swap the `stage/*` label + post a dated "Board lane move"
  comment; archive = close, restore = reopen); `index.html` is the adapted
  dispatch board fetching `/api/board` with a LIVE/OFFLINE badge and
  write-through on every move/save. Tokenized proxy is zero-dependency
  (`fetch` only). `board_state.py pull-issues` reversed the sync (issues →
  TASKS.md lanes + a dated Evidence note, never auto-creates cards) so the
  board stays canonical after site edits; `sync-issues` remains the
  board → labels leg. Docs: AGENTS.md "Served Kanban board" section.

### Fixed

- `board_state.py` parse_board now splits open-table rows on unescaped pipes
  only and unescapes `\|` — board rows embedding literal pipes inside code
  spans (e.g. HUB-054's `corpus ls|show|search|stats`) previously mangled
  the Owner cell and hid the issue link (HUB-055).
- **Stray `v0.4.0` hub tag retargeted (removal, HUB-056, 2026-09-05):** the
  annotated `v0.4.0` tag (pointing at The-Mailroom's package-release commit
  `fc55be3`) was cut on the hub by mistake during the HUB-054 session — the
  hub `pyproject.toml` stayed `0.2.0` and no `## [0.4.0]` CHANGELOG section
  ever existed. It broke the release chain (`release_chain.py check`: tag
  with no section + version-skew errors). Per human directive the stray tag
  was retargeted out of the chain (deleted locally + remotely) and this
  release cuts the real official `## [0.4.0]` hub section + annotated
  `mailroom-hub v0.4.0` tag in its place. Upstream package releases
  (llm-mailroom `v0.6.0`, The-Mailroom `v0.4.0`) were never implicated.

## [0.3.0] - 2026-09-05

### Added

- **Relations agent — semantic linking + auditable relations ledger + knowledge
  graphs** (HUB-040, 2026-09-03): the mailroom pipeline learns document
  relationships across the archive. Storage: new `relation_edges`/`log`/
  `embeddings`/`scan_state` SQLite tables with an independent hash-chained
  ledger (own SHA-256 chain, monotonic-timestamp fix for `verify_chain`
  compat). Signals: deterministic scanner — same-matter, keyword-Jaccard,
  party-overlap, and embedding-cosine (per-type best edges, compute-once
  embedding cache, watermark-incremental sweeps). Judgment: the `RelationsAgent`
  closed-vocabulary LLM pass narrows ambiguous near-misses (mailroom-relations
  prompt, taxonomy `relations` block, `llm:false` pilot default, config-gated)
  and refuses to propose unvetted pairs. Delivery: post-archive dispatch x3 +
  handoff-context RELATED block + echo RELATED section + watcher-embedded
  sweeper; knowledge graphs (matter/global/ego projections; stdlib
  GraphJSON+GraphML, optional Plotly HTML+PNG; ledger render events); 13-test
  hermetic suite (ledger integrity/tamper, upsert novelty, signals,
  compute-once cache, kill-switches, incremental sweep, context block, LLM
  validator, KG projections/renderers); hermetic + hang-proof embedding path
  (env kill-switch + 90s bounded model load — a dojo model download never
  stalls a scan) and the relations background dispatch killed in tests to fix
  a failed `tmpdir` teardown race in the Gmail triage suite.
- **Insurance-claim subclass alignment with the v8 synthetic LOB claims**
  (HUB-041, 2026-09-03): the mailroom-corpus v8 GT (`eafe1ab4`) carries SIX
  insurance subclasses (carrier/inpatient/outpatient/pde + property 200
  GNOTHEIA + auto 150 BDR; 50 strata) but several surfaces still taught or
  accepted only the four CMS tokens. Landed: dojo `corpus.py`
  `DOC_TYPE_SUBCLASSES`/`CORPUS_SUBCLASS_SURFACES` + `mailroom.py`
  `HUB_SUBCLASS_INVENTORIES` gain property/auto (v8 counts pinned in tests);
  entity `sorter_agent.py` `INSURANCE_CLAIM_SUBCLASSES` (flows into the
  DOCCLASS/PILOT `doc_subclass` enums — property/auto rows are now scoreable);
  The-Mailroom `pipeline_schema.DOC_SUBCLASS_BY_CLASS`; llm-mailroom
  `doc_inventories` fallback catalog + `taxonomy.yaml`/sorter insurance
  descriptions; sandbox fixture gains property/auto rows. **New prompt
  versions under the mailroom naming convention** (human directive; existing
  `*_docclass_*` keys are frozen experiment identity):
  `sorter_mailroom_v0` (extended arm, off v7) and `sorter_mailroom_pilot_v0`
  (pilot arm, off pilot v3) extend rule 40 with the two LOB tokens — defaults
  unchanged until a same-surface A/B; The-Mailroom
  `mailroom_ui/docclass_prompts.py` mirrors the pilot key byte-identical
  (32 keys). **Subclass-parity layer in `scripts/taxonomy_parity.py`** (all
  classes): the Hub GT vocabulary (pinned per class from `eafe1ab4`) must be
  covered by every subclass catalog surface (dojo catalogs + observed-GT
  table, entity taxonomy `subclasses:` blocks + sorter lists, The-Mailroom
  schema mirror, llm-mailroom doc_inventories fallback + extract claim_type
  inventory) with extras tolerated only from documented rosters; CI path
  triggers extended to the new surface files; verified pre-fix drift is
  detected (mutation checks).
- **Gmail triage free-swarm failover** (HUB-039, 2026-09-04): the single-doc
  pilot hit OpenRouter's shared free-pool saturation (all 5 retry attempts on
  the SAME `z-ai/glm-5.2:free` → review park). Fix: ordered free-model
  failover in the retry ladder — `taxonomy.yaml: free_model_swarm`
  (glm-5.2 → ling-3.0-flash-fin → nemotron-3.5-lightning → inkling →
  inkling-small → dots-3-note → laguna-s → laguna-xs → lfm-2.5), rotation on
  `RateLimitError` AND model-capability 400s (`_is_model_capability_error` —
  generic 400s never rotate), paid models NEVER rotate, a request parks only
  when the whole swarm is limited; full triage I/O debug capture
  (`data/debug/triage/<UTC>_<file>/`, `triage_llm_io`/`parse_failed`/
  `llm_call_failed` events) + robust JSON recovery (markdown fences /
  prose-wrapped). `llm/client.py:is_free_model` extracted as the shared
  predicate; the vendored ChatOpenAI chokepoint enforces the free-only pilot
  guardrail; `llm_free_failover`/`llm_free_swarm` events. Live chain proof:
  glm-5.2 429 → ling capability-400 → nemotron served the read
  (`insurance_claim`, 0.95).
- **Gmail echo depth expansion** (2026-09-04): HTML multipart report +
  processing timeline + WHAT HAPPENED narrative + `friendly_reason`;
  reviewer escalation now carries the exception text; station-signoff;
  multipart support in smoke/tests; `gmail_intake` state file written via
  atomic `tmp`+`replace` (crash-safe persistence).
- **intake-provenance-aware already-processed dedup** (HUB-043, 2026-09-04):
  the watcher's filename-only rule silently dropped legitimate re-sent
  documents forever — a new email (new Message-ID) carrying an
  already-processed filename was refused every sweep. A file's `/upload`
  sidecar (`message_id`/`upload_id`) must now MATCH the terminal manifest's
  intake provenance to count as processed; mismatch = a NEW document that
  MUST claim. The triage lane also dispatches the relations scan on terminal
  manifests (`relations_sweeper`).
- **Watcher status channel** (HUB-050, 2026-09-04): 🔴 down alerts + 🟢
  relaunch confirmations to the operator email (`pipeline/status_notify.py`,
  (exactly three kinds — running/down/still_down) — HTML+text, fail-soft,
  kill-switch `MAILROOM_WATCHER_STATUS`); EXTERNAL watchdog
  (`python -m pipeline.watchdog`) — pid-dead/missing-heartbeat →
  immediate 🔴, pid-alive-but-stale → 2 consecutive stale checks, 🟠 reminders
  only while an outage is active; enriched atomic heartbeat
  (`touch_watcher_heartbeat(extra)` — pid/host/started_at/git-sha). Live drill
 2026-09-04: kill → down in 30s, relaunch → running; anti-spam posture
  (no periodic healthy-status digests). Watchdog alert-retry hardened in
  the same audit pass.
- **Relations clerk production-readiness** (HUB-051, 2026-09-04): the
  research/review clerk was archived code-complete but a NO-OP on live
  (triage lane never wrote the `documents` catalog row → scanner skipped
  everything; the LLM judgment pass was dead code; the documented
  `relations_scan` CLI crashed; embedding cosine never worked outside tests).
  Landed: `pipeline/relations_scan.py` CLI, triage catalog upserts on BOTH
  triage terminal paths (+ `file_sha256` persistence), wired `_llm_judgment_
  edges` (top-K on the ambiguous band, `llm_confidence_gate` 0.55,
  `llm_asserted` edges, re-validation), `_embed` driven by the dojo's shared
  `_EmbeddingMatcher` singleton (local ST + remote fallback, 90s-bounded,
  fail-soft), 7 stale `processing` catalog rows reconciled, judgment
  I/O debug capture (`recover_processing.py --catalog`). Live proof: 4 docs
  → 7 edges (6 same_matter + 1 party_overlap), ledger chain OK (189 entries),
  real LLM judgment ran through the free-swarm failover and was correctly
  refused by the gate.
- **Relations clerk mode toggle** (HUB-052, 2026-09-04):
  `pipeline/relations_mode.py` — `python -m pipeline.relations_mode
  status|pilot|live [--model] [--restart-watcher]`: `status` prints the
  effective posture + every knob; `pilot`/`live` edit taxonomy.yaml SURGICALLY
  (section-tracked line rewrite, comments byte-preserved, atomic
  temp+replace), remove a stale `MAILROOM_RELATIONS_LLM` kill-switch, clear
  in-process config caches so the current thread honors the flip immediately;
  model validation (cost_models / `:free`), paid-under-free-only refused.
  The smoother path: authenticated `GET/POST /api/relations/mode` on the
  FastAPI — POST applies + clears caches, embedded watcher honors it with NO
  restart.
- **claims-data-eda: real insurance-claim corpus PDF samples** (HUB-046,
  2026-09-04): 8 real corpus documents from `Lucius-Morningstar/mailroom-corpus`
  (`ground_truth_hardened.jsonl`, 950 insurance_claim rows; sampled
  carrier/inpatient/outpatient/pde ×2, seed 42) rendered as byte-faithful A4
  PDFs of the verbatim `doc_text` via deterministic zero-dep
  `scripts/render_samples.py` into `docs/examples/` with `manifest.json`
  (provenance + sha256) + README; guard tests, managed PDF writer (Courier/
  WinAnsi, xref-valid, multi-page). Prune-doctrine exception recorded
  (like HUB-008).
- **Enron-Evaluation-Environment: cleanly formatted Markdown samples of the
  Enron email correspondence** (HUB-047, 2026-09-04): regenerable
  `scripts/build_samples.py` walks the maildir via the index walker and
  renders a taxonomy-stratified, seeded, bounded selection into `samples/`
  (16 samples + generated README index; 2 per subclass key; reservoir 120
  per stratum; walk cap 517,401 = full corpus; body cap 6000; seed 20150507
  = the tarball date). Clean formatting law: H1 subject, header metadata
  table, maildir provenance, subclass label + labeler evidence, attachments;
  body `>`-quoted replies as Markdown blockquotes, forwarded content split
  via the shared `_strip_forwarded`. `voicemail`/`other` strata empty (the
  documented text-only labeler limitation).
- **Gmail triage key/concise entity extraction for ALL document types via
  the EXISTING EXTRACTION_SCHEMAS** (HUB-048, 2026-09-04): `triage()` now
  returns BOTH the classification read AND a per-class `extraction` object
  driven by `schemas.documents.EXTRACTION_SCHEMAS` (the same Pydantic models
  the paid specialists use): `extraction_schema_for()` derives the field map
  per class (normalizing `float|None`/`anyOf` to real JSON `number`), short-
  document emphasis in the prompt, `_clamp_extraction` drops cross-class
  fields/caps lists(10)/strings(200). Rides `intake_meta["triage"]
  ["extraction"]` → manifest → echo "EXTRACTED KEY ENTITIES (triage)".
  Advisory + fail-soft preserved.
- **Gmail triage lane: unknown-class extraction fallback + confidence gate +
  transient-LLM review parking** (HUB-049, 2026-09-04): `unknown` primary
  class no longer yields empty extraction — `_unknown_class_extraction()`
  merges model correspondence keys with `_deterministic_header_extraction()`
  (regex `From:/To:/Date:/Subject:` + Enron markdown-table forms; grounded
  values only); `validate_triage` routes unknown → fallback. Watcher
  confidence gate: `unknown` class or confidence < taxonomy `low` (0.88)
  parks the doc in REVIEW (`triage_unknown_class`/`triage_low_confidence`,
  `triage_reviewed` audit, ⏸ echo) instead of archiving an untrusted read.
  Transient LLM failures park with `triage_llm_unavailable: <type>: <msg>`.
- **Repo-wide mailroom-corpus HF dataset loader + corpus-sourced Gmail pilot
  notebook** (HUB-053, 2026-09-04): `pipeline/hf_corpus_loader.py` — the
  canonical loading path for the mailroom-corpus family (labels from the
  `ground_truth` config joined with `doc_text` from the blind `default`
  config on `filename`): /parquet ladder + on-disk cache + load-time
  integrity proof (`content_sha256` == sha256(`doc_text`), verified
  1792/1792 live), `/rows` pagination fallback, literal-slash sha
  provenance, `datasets` optional (never a dependency).
  `notebooks/gmail_pilot_lab.py` + `14_gmail_pilot.ipynb` — the expert
  pilot loop: config → preflight (heartbeat/channel/allowlist/corpus) →
  corpus pick (integrity-verified snapshot offline / live Hub behind
  `NB-OPT-IN-NETWORK`) → FIRE interlock (mock inbox drop w/ the poller's
  exact sidecar | real SMTP w/ fail-fast allowlist guard) → watch →
  evidence (catalog row, audit hash-chain, relations edges, echo) → corpus
  GT comparison → `data/pilot_runs/<stamp>_<token>/report.{json,md}`.
  LIVE: record 65s/30s real+post-fix fires, 9 relations edges, verdict FAIL
  7/10 (honest GT surface).
- **Propagation sweep — all 10 feeder repositories in line with the monorepo
  (third sweep)** (HUB-005, 2026-09-04): llm-mailroom, The-Mailroom,
  agent-mailroom, llm-dojo-scoring, local-mailroom-sandbox pushed upstream;
  cursors re-baselined; the sanctioned all-packages one-liner
  (`push --all --patch`) verified; the ingest/intake consolidation tail —
  every remaining package mention consolidated; git `commit-message` doctrine
  + reword session note (human directive 2026-09-04).

### Changed

- The sorter's live doc-class surface now comes from `get_all_doc_types()` —
  `status: retired` entries are filtered, so the sorter schema/classifier/
  gmail triage prompts reflect only the 5 primary doc classes + `unknown`
  (2026-09-04).
- `compliance_filing` retired from live docs + the visualizer schema (HUB-054
  #15) — the 5-class + `unknown` set is the live roster.

### Fixed

- `release_chain.py cut` no longer requires `## [Unreleased]` to be the file's
  first line — the section header is located anywhere in the CHANGELOG and
  the preamble (title + scope note) is preserved when stamping a release
  section (discovered while cutting v0.2.0).

## [0.2.0] - 2026-09-03

### Added

- **Gmail intake channel + single-document free-triage lane** (HUB-037,
  2026-09-03): the agent mailbox (`llmmailroom@gmail.com`) is a second intake
  route in `packages/llm-mailroom` — stdlib IMAP-SSL poller embedded in the
  watcher (the lock holder stays the single intake authority), `/upload`
  sidecar routing, `[M:<id>]` subject matters, `\Seen` + Message-ID dedup,
  sender allowlist, ✅ check reaction at claim time (both routes, with a
  terminal-stage retry + `reactions_failed` counter), on-thread completion
  echoes, intake awareness on every terminal manifest, and the FREE-model
  single-document triage lane (`agents/gmail_triage.py`, `z-ai/glm-5.2:free` —
  free models kept deliberately): core pipeline steps without the paid agents
  (deterministic prep → triage classification → auditable-hash archive → echo)
  with its own `triage_*` audit section, a deterministic capability pre-check
  that honestly hands off oversized/vision-only/scanned documents to the full
  paid pipeline (`intake.triage_handoff`), and all five canonical doc types
  validated through the lane. Multi-document emails run the full paid
  pipeline (triage never dispatched).
- **Intake agent v2 — triage + clean + prepare** (HUB-038, 2026-09-03): the
  pipeline's first node is now a SINGLE `intake` node — the intake agent IS
  the ingest specialist (human directive: the ingest/intake split was an
  unintentional naming mistake; unified constellation-wide). The
  LLM-assisted pass (one fused call per window) TRIAGES (advisory read —
  same vocabulary-clamped shape as the free triage team, fed to the sorter as
  a labeled prior), CLEANS (gated structural repair, re-normalized through
  the deterministic dojo clerk so `prep_invariants` hold), and PREPARES
  (validated section map). **No-truncation doctrine (human directive):**
  documents are NEVER truncated — anything past an input budget is processed
  in overlapping sliding windows (`sliding_windows`, paragraph-boundary, 15%
  overlap) so every character is read; the sorter classifies window-by-window
  and merges deterministically (plurality vote, mean confidence of agreeing
  windows), the retry path no longer slices text, and partial-window cleaning
  is never spliced. Cost + efficiency: the LLM pass fires only for
  messy/over-budget documents on the cheapest paid model (`qwen3.7-flash`);
  `MAILROOM_LLM_INTAKE=0` disables; failures fail soft. Prompt registry
  15 → 17 (`mailroom-gmail_triage`, `mailroom-intake`); model registry gains
  the free `z-ai/glm-5.2:free` tier.
- **Ingest/intake unification rename sweep** (HUB-038 follow-up,
  2026-09-03): graph node `ingest` → `intake` (span `intake-document`; the
  `ingested` audit event stays — compliance vocabulary) across the whole
  constellation: llm-mailroom (`entry_route`, `intake_node`, tracing
  registry), The-Mailroom (`Stage.INTAKE` enum, `pipeline_schema.py`
  mirrors, `trace_interpreter.py`, TUI labels, web/hosted JS stage maps,
  tests, demo scripts), agent-mailroom (`pipeline/ingest.py` →
  `intake.py`), local-mailroom-sandbox and llm-dojo-scoring span mirrors,
  and the pipeline lab notebook.
- **Gmail free-triage production-pilot readiness** (HUB-039, 2026-09-03):
  sender-allowlist pilot roster documented in `packages/llm-mailroom`
  `.env.example` (production pilot roster; empty = accept all).
- **Propagation sweep — all 10 feeder repositories in line with the
  monorepo** (HUB-005 reopened, 2026-09-03): HUB-038/039 payload propagated
  upstream via `sync_packages.py` — llm-mailroom (16 files), The-Mailroom
  (22), agent-mailroom (7 + the `ingest.py`→`intake.py` renames carried by a
  real subtree pull + full-history subtree push after the HUB-021 patch path
  refused the cursor gap), llm-dojo-scoring (1), local-mailroom-sandbox (1);
  cursors re-baselined per package in `scripts/packages_sync.json`.

- **mailroom-corpus v8 — insurance LOB expansion + full GT conformance**
  (HUB-028, 2026-09-02): the corpus grows 1,650 → **2,000 rows** (strata
  48 → 50) with (a) +200 `property` rows from
  `gratex/GNOTHEIA-synthetic-insurance-dataset` (Apache-2.0 — FNOL bundles
  stratified by loss event, determination `pending`), (b) +150 `auto` rows
  from `bdr-ai-org/insurance-motor-claims-decision-v1` (MIT — decision
  letters stratified by accident type × APPROVE/REVIEW/REJECT with all
  reject rows, feature-grounded denial reasons, adjuster pseudonyms), and
  (c) full GT conformance: intent/subject_matter/keywords + intent
  provenance populated on ALL 950 insurance rows (600 CMS backfilled via
  deterministic template derivation — was 246/600 subject/keywords, 600/600
  intent; 200 property + 150 auto authored at build), claimed_amount
  recovered from doc text on 10 v7 gap rows, metadata union
  (source_dataset/source_revision/source_row_id/lob/peril/license) on every
  entry, and **test-split nullification** (96 test insurance rows carry
  zero empty class-relevant keys). Published via the centralized
  corpus-eda helpers with sha256 local==hub verification; card v8 +
  §84 hardening sections; datasets-server conversion green. XpertSystems
  samples (ins001/007/hlt015) excluded for CC-BY-NC-4.0 license conflict;
  INSURBIAS (CC-BY-4.0) deferred to v9. Builder: `v8_build.py` +
  `scripts/build_v8.py` (7 new tests; corpus-eda suite 73 passed).
- **§84 hardened release rebuilt on the v8 base** (HUB-032, 2026-09-02):
  the interleaved HUB-028/HUB-022 publishes left the Hub mixed (blind
  `default` 2,000 rows vs `ground_truth` 1,650×60) — the rebuild applies
  the identity → eval_contract → §14A hardening chain to ALL 2,000 rows and
  republishes `ground_truth` (60 cols) + `bundles` + `fixtures` via
  `scripts/publish_hardened.py`. Published v7 `document_id`s unchanged
  (0 drift over 1,474 train rows); the v8 LOB rows (200 GNOTHEIA + 150 BDR)
  carry their own `source_corpus`/`annotation_source` (via
  `metadata.source_dataset`) and pinned upstream `source_revision` instead
  of collapsing into the CMS class map; annotation provenance counts now
  950 synthetic (600 DE-SynPUF + 200 GNOTHEIA + 150 BDR);
  thread reconstruction unchanged (19 rows in 7 threads — all
  correspondence; insurance rows carry no custodian). Bundles re-derived
  over the v8 base (anchor sets shift — insurance family now spans
  carrier + auto anchors); fixtures byte-identical. Card §84 section
  refreshed; sha256 local==hub (10/10); all §91 release gates green;
  corpus-eda suite 73 passed.
- **§84 v0.3 STREAM eval tier** (2026-09-02): NEW `streams` config (§27–§29/
  §48) — `RUN-SIM-001` interleaves the 10 bundle matters round-robin
  (A1 B1 A2 C1 B2 … — §28 never matter-contiguous) with 12 no-matter
  `distractor` rows on a 4-position cadence (§29); every row carries
  `simulation_run_id` + `sequence_position` (strictly reproducible, §27).
  62 rows / 39 cols; published + sha256-verified (13/13). Stream builder
  `mailroom_eda.bundles.build_streams` with 3 new tests.
### Changed

- The-Mailroom stage enum + TUI/web/hosted labels: `ingest` → `intake`
  (visualizer mirrors the unified pipeline topology).
- `agents/sorter.py` bypasses the vendored HEAD+TAIL truncation — over-budget
  documents classify in sliding windows with a deterministic merge; the
  advisory intake prior + retry preamble reach every window.

### Fixed

- Gmail smoke mock hermetics: `run_mock` now forces the mock sender +
  allowlist — the HUB-039 `.env` pilot roster had started rejecting the mock
  sender (smoke is hermetic against the real `.env`).
- Sync-cursor/content handling for renamed package paths: a real subtree
  pull + full-history subtree push is now the documented path when a
  monorepo-side rename leaves the upstream tip uncontained (patch push
  cannot carry deletions).

## [0.1.0] - 2026-09-02

First hub release: the monorepo as development source of truth for the
LLM-Mailroom constellation — 10 workspace packages, the governance stack, the
sync driver, and the hardened mailroom-corpus lineage (renamed from
docclass-merged). Package versions at this tag: llm-mailroom v0.6.0,
llm-dojo-scoring v0.13.0, llm-entity-extraction v0.21.0, The-Mailroom v0.3.0,
agent-mailroom v0.2.0, local-mailroom-sandbox v0.1.0.

### Added

- **Monorepo + uv workspace** (HUB-001): 9 family repos imported via git
  subtree (mailroom-corpus-eda followed as the 10th, HUB-007); one uv
  workspace, one lockfile, one virtualenv; member dependencies resolve via
  `[tool.uv.sources]` workspace redirects while published git pins stay
  intact; monorepo-aware test repairs (import-shadow markers, pruned-asset
  skip guards, UTC/CWD anchoring).
- **Sub-package sync driver** (HUB-002, HUB-021): `scripts/sync_packages.py`
  (status / pull / push / snapshot over git subtree) with the HUB-021
  hardening — blob-tree containment oracle (gitignore-aware; pruned heavy
  assets are doctrine, not drift), cursor-gap refusal on `snapshot` unless
  `--force`, re-baseline guard that kills the pull re-import loop, scripted
  `push --patch` for non-fast-forward cursors, and per-package monorepo-ahead
  payload surfaced in `status`.
- **GitHub governance tooling** (HUB-014): `scripts/board_state.py`
  (status/card/check/sync-issues/project-init/project-sync over
  `governance/TASKS.md`), declarative label taxonomy (`.github/labels.json`)
  + `scripts/github_labels.py` audit, YAML issue/PR templates, blocking CI
  gate (`.github/workflows/board-governance.yml`), optional Projects v2
  mirror.
- **Document-class taxonomy-parity gate** (HUB-019 §65A):
  `scripts/taxonomy_parity.py` — strict AST-level equality across taxonomy
  sources (mailroom sorter vocab, specialist registry, dojo corpus types,
  entity pilot universe, v7 taxonomy doc, sandbox fixtures), wired blocking
  into CI.
- **Corpus governance, docclass-merged → mailroom-corpus** (HUB-019/022/023):
  baseline freeze `docclass-merged-v0.1-working` at the true tip with audit
  manifest (`scripts/baseline_audit.py`), canonical dataset contract
  (`docs/DOCCLASS_CONTRACT.md`), identity/provenance/hash schema
  (`document_id` from source identity, content hashes), contract test suite
  (15 passed), P1 eval hardening (`eval_contract`, class×subclass×source×field
  coverage matrix, §14A matter/group backfill decision); the HF dataset was
  renamed `Lucius-Morningstar/docclass-merged` → `Lucius-Morningstar/
  mailroom-corpus` (Hub move preserves history; 57 monorepo files updated
  with prompt-version keys and trace tags immutable).
- **Version-controlled GitHub wiki** (HUB-017): `docs/wiki/` (10 pages) +
  `sync-wiki.sh` (`--check` drift mode).
- **Corpus EDA deliverables tracked in full** (HUB-008 exception): figures,
  interactive HTMLs, tables, and summary reports are canonical in the
  monorepo — never pruned.

### Changed

- Root docs reworked for the monorepo (README architecture map, AGENTS.md
  governance + workspace rules, task board) — HUB-003; docs-currency sweeps
  after every surface-touching card (HUB-010, HUB-016, HUB-018).
- Heavy-asset doctrine: docs demos/screenshots, sample PDFs, and report
  archives are pruned from the hub (HUB-003/004) — with the corpus-EDA
  deliverables exception above.

### Fixed

- `run_all.py` subset runs / `--no-interactive` no longer clobber
  `reports/SUMMARY_REPORT.*` (HUB-009); P3 figure counter corrected 27 → 30
  to disk truth (HUB-012).
- Sync-cursor incident mechanics structurally guarded after the HUB-012/013/
  018 reconciliations (containment oracle + gap refusal + re-baseline, HUB-021).
- Upstream drift reconciled across all packages; `sync status` 10/10 in sync
  (HUB-004, HUB-018); stale pins/counts swept (HUB-010/016/018).

[Unreleased]: https://github.com/LLM-Mailroom-Services/Digital-Mailroom/compare/v0.4.0...HEAD
[0.3.0]: https://github.com/LLM-Mailroom-Services/Digital-Mailroom/compare/v0.3.0...v0.4.0
[0.2.0]: https://github.com/LLM-Mailroom-Services/Digital-Mailroom/compare/v0.2.0...v0.3.0
[0.1.0]: https://github.com/LLM-Mailroom-Services/Digital-Mailroom/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/LLM-Mailroom-Services/Digital-Mailroom/releases/tag/v0.1.0
[0.2.0]: https://github.com/LLM-Mailroom-Services/Digital-Mailroom/releases/tag/v0.2.0
[0.3.0]: https://github.com/LLM-Mailroom-Services/Digital-Mailroom/releases/tag/v0.3.0
[0.4.0]: https://github.com/LLM-Mailroom-Services/Digital-Mailroom/releases/tag/v0.4.0
