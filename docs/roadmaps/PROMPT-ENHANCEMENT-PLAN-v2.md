# Mailroom pipeline prompt enhancement plan (SAND-034)

**Status:** diagnosis complete, plan proposed, no API or GPU spend incurred.
**Scope:** every LLM node in the LangGraph pipeline. In depth: the sorter and
the five extraction specialists (correspondence, insurance claims, contracts,
merger agreements, corporate records). Structural audit: intake, sorter
reviewer, the three judges, arbiter, boss and the compile stage (section 4.7),
plus how prompts are served and promoted through Langfuse (section 6a). As run in
this sandbox (Qwen3-8B-AWQ on Modal, SAND-032) and in
[eval-environment](https://github.com/LLM-Mailroom-Services/eval-environment)
(OpenRouter API legs, GEPA prompt lineage).
**Goal:** shorter, structurally simpler prompts that keep every lexical cue the
tasks depend on, sequenced to make the GEPA loop more effective, not to replace it.

Evidence labels used throughout:

- **Measured** — computed from logged predictions or report tables (sources in
  the appendix).
- **Inferred** — follows from code or prompt text plus measured behavior.
- **Hypothesis** — plausible, needs a check the sandbox cannot run offline
  (usually because Hub ground-truth field values are not available here).

---

## 1. Summary

The largest losses are not in the wording GEPA is tuning. They come from the
contract between prompt, schema and scorer, and from where the sorter spends its
prompt budget.

1. **Specialists emit `null` where the schema requires a list** (measured).
   Replaying 286 logged API predictions through the vendored Pydantic schemas:
   insurance validates **3/60**, correspondence **8/60**, contracts **8/58**,
   merger **36/48**, corporate **41/60**. The v1 prompts already say
   "unstated list → []"; the call path never sends the schema it tells the model
   to follow. This is the cause of the sandbox's 22% insurance schema validity.
2. **81% of the sorter prompt (14.0k of 17.2k characters) is contract-subtype
   rules** (measured). The four other classes get almost no boundary guidance,
   and the sorter's dominant error is sending them to `contract`: in the
   1,000-doc run, 35 of 136 corporate records and 10 of 18 merger agreements
   (contract precision 0.796).
3. **The sorter's output spec omits `doc_subclass`** (measured). It is required
   only in trailing doctrine and in a catalog placed *after* the document.
   Qwen3-8B left it empty on 13 of 20 documents (subclass accuracy 5%); Granite,
   which follows the catalog, reached 60%.
4. **Vocabularies disagree across layers** (measured). Corporate records: 11 sorter
   catalog keys, 5 specialist `record_type` tokens, 10 mailroom-ml head labels.
   Contracts: ground truth uses CUAD folder names (`License_Agreements`,
   `Joint Venture _ Filing`) while prompts emit keys (`license`,
   `joint_venture`); eval-environment's subclass scorer does not map them, so
   correct contract subclasses score as wrong.
5. **Instructions leak into outputs** (measured). Granite copied a fenced
   instruction block from the merger prompt verbatim as a JSON key, and
   flattened the contracts prompt's `reasoning` object into top-level `summary`
   and `entries` keys. DeepSeek's merger run lost 10 of 20 documents to
   truncated JSON.
6. **Flat means hide subclass trade-offs** (measured). Corporate v2 vs
   production is −0.010 overall but −0.158 on charter amendments and +0.098 on
   subsidiary lists. Correspondence v2's +0.042 comes mostly from notices
   (+0.146) and letters (+0.092).

7. **Exception routing trusts self-reported confidence that does not track
   quality** (measured). The judge, retry and review lanes fire on
   extraction-confidence bands (contract band 0.90–0.97). On the API legs the
   correlation between the specialist's confidence and its score is −0.22
   (insurance, Qwen3-8B), −0.03 and −0.08 (contracts, Qwen3-8B and Granite),
   and no corporate-records leg emitted a confidence at all. Mean insurance
   confidence is 0.94 against a mean score of 0.75. The other nodes' prompts
   are sound in content but repeat the same doctrine two or three times each
   (section 4.7).

Braintrust review: the live trace API was not reachable from this environment; the tracked Mailroom-Evals backlog index shows GEPA's OBSERVE manifests include failures from at least five degenerate runs and no sorter experiments (section 7a).

**Plan in one line:** fix the output contract in code first (Phase 0), move
every lexical cue into compact tables inside a fixed prompt skeleton (Phase 1),
then let GEPA mutate within that skeleton under two added gates (cue coverage,
per-subclass non-regression) and a size-aware Pareto frontier (Phase 2).

Expected effect, stated as targets for the promotion gate rather than claims:
sorter prompt −60% (17.2k → ~7k characters) with all 65 title cues and 41 worked
decisions preserved; specialist schema validity ≥ 0.95 for all classes; no
subclass with n ≥ 5 regressing by more than 0.05.

---

## 2. Data and method

All analysis is offline, from tracked files:

| source | what it provides |
| --- | --- |
| eval-environment `reports/experiment_log.jsonl` | 15 canonical specialist runs (3 models × 5 tasks, 20 docs each) with full predictions and score components; sorter runs with per-case predictions at n = 20 |
| sandbox `reports/SAND-32/*/SAND032-*-REPORT.md` | Qwen3-8B-AWQ per-document scores, schema flags and tokens, n = 50–100 per class; Stage 10 v2 prompts at n = 75 (paired on 50) |
| sandbox `reports/serving/SAND-32/SAND032-S6-SORTER1000-REPORT.md` | isolated sorter over 458 documents: per-class precision/recall and confusion matrix |
| prompts | eval-environment `prompts/*.md` (v1, v2, GEPA `mutations.json`); sandbox `config/prompts/*.txt`; vendored `langchain_agents/prompts.py` and `sorter_agent.py` |
| schemas | vendored `schemas.documents` (the Pydantic models used for schema validity) |

Limits: Hub ground-truth *field values* are not available offline (the Hub is
not reachable from this environment and the tracked manifests carry only class
and subclass). Field-level accuracy is therefore inferred from score components
(precision, recall, entity-list F1) and from fill rates, not measured per field.
The analysis script is reproducible from the files above; the numbers in this
document were produced by it.

---

## 3. Cross-cutting failure taxonomy

### F1 — Output contract: nulls where the schema requires lists or strings (measured)

Logged API predictions validated against the vendored Pydantic schemas
(parse errors excluded):

| class | valid | top violations (count) |
| --- | --- | --- |
| insurance_claim | 3 / 60 | `denial_reasons` null (57), `damages_description` null (30), `supporting_documents` null (28) |
| correspondence | 8 / 60 | `additional_recipients` null (52), `action_items` null (31) |
| contract | 8 / 58 | `maud_clauses` null (50) |
| corporate_record | 41 / 60 | `signatories` null (18) |
| merger_agreement | 36 / 48 | `maud_clauses` null (12) |

Every v1 and v2 prompt already states "unstated list → []". The eval-environment
call appends "conforming to the provided json schema" but requests only
`response_format: json_object` and never sends a schema (inferred from
`src/evals/specialist_llm.py`). The model sees `(string[])` in prose next to a
repeated "→ null" convention and takes the more frequent pattern. GEPA's
corporate v2 mutation ("signatories never null") fixes one field of this class
of error by adding prompt text.

### F2 — Salience imbalance and rule accretion in the sorter (measured)

| section of `sorter_v1` | characters | share |
| --- | ---: | ---: |
| contract subtype rules 6–28 | 13,995 | 81.3% |
| production doctrine | 1,694 | 9.8% |
| preamble and general rules 1–5 | 978 | 5.7% |
| output spec | 361 | 2.1% |
| subtype keys | 187 | 1.1% |

The 23 contract rules were added one corpus exception at a time. "Marketing"
appears 30 times across three overlapping rules (16, 26, 27); rule 17 ("annex
inheritance") is missing but cited by rules 25 and 26. The five class
descriptions get one line each, and the corporate description omits four of its
own catalog subclasses (indentures, board resolutions, officer certificates,
subsidiary lists). The model's prior is pulled toward `contract` for anything
titled "…Agreement", which is exactly how indentures, rights agreements and
merger agreements are titled.

### F3 — Vocabulary divergence across layers (measured)

| class | sorter catalog | specialist field | ground truth | mailroom-ml head |
| --- | --- | --- | --- | --- |
| corporate_record | 11 keys | `record_type`: 5 tokens | 9–10 subclass labels | 10 labels |
| contract | 25 family keys + other | `cuad_family` keys | CUAD folder names | 26 labels |
| insurance_claim | 6 CMS types + open list ("…are also valid") | `claim_type` | 6 subclass labels | 6 labels |
| correspondence | 8 keys, no definitions | `communication_type` | 7–8 labels | 8 labels |

Consequences: the corporate specialist must map 10 shapes onto 5 tokens by rule
(v2 maps `charter_amendment` → `articles_of_incorporation`, the subclass that
lost 0.158 in the paired comparison), and eval-environment's subclass scorer
(`score_subclass`, lowercase and underscore only) counts `license` vs
`License_Agreements` as wrong.

### F4 — Cross-class schema leakage (measured)

The contracts schema carries `merger_consideration` and `maud_clauses` "so older
payloads parse"; the prompt then spends a rule telling the model to leave them
empty, and 50 of 58 contract predictions fail validation on `maud_clauses`
anyway. The correspondence prompt lists ten other-class keys not to emit.
Negative lists grow with every class added and teach the model the forbidden
key names.

### F5 — Instructions leaking into outputs (measured)

- Granite emitted a key whose name is the merger prompt's fenced block of MAUD
  question names, and top-level `summary` / `entries` keys from the contracts
  prompt's `reasoning` object.
- The contracts prompt asks for a `reasoning` object with one evidence entry per
  populated field *before* the values; Granite's median completion on contracts
  is 11,351 tokens, DeepSeek's 5,590.
- DeepSeek's merger run: 10 of 20 documents failed to parse (truncated output,
  one key cut to `subject_m`).

### F6 — Measurement confounds (measured unless noted)

- Paired comparisons in Stage 10 differ by the whole prompt lineage
  (production → simplified v1 → GEPA v2), not only by the GEPA edit.
- Means hide subclass trade-offs (section 1, item 6).
- The sorter's parse-error fallback returns `correspondence` at confidence 0.3,
  contradicting the prompt's "never substitute correspondence" doctrine
  (`sorter_agent.classify_json`).
- eval-environment truncates sorter input to about 12k characters (per the
  sorter v3 mutation note); the vendored sorter reads whole documents (prompt
  tokens up to 297,760 in the 1,000-doc run). Sorter results from the two repos
  are not comparable (inferred).
- The Qwen3-8B API legs request thinking off, yet correspondence completions
  have a 4,119-token median (inferred: hidden reasoning tokens still generated
  and billed).

### F7 — Routing on uncalibrated confidence (measured)

`judge_gate`, `after_extraction_gated` and the retry/review thresholds in
`config/taxonomy.yaml` route every document on `extraction_confidence`: the
specialist's self-report, clamped by `apply_extraction_guard` only when the
structural guard fails. Pearson r between that confidence and the
per-document score on the API legs:

| class | Qwen3-8B / Qwen3.7-flash | Granite | DeepSeek |
| --- | --- | --- | --- |
| correspondence | 0.61 | 0.76 | 0.54 |
| insurance claims | −0.22 | 0.34 | 0.10 |
| contracts | −0.03 | −0.08 | 0.86 |
| merger agreements | 0.57 | 0.05 | 0.92 |
| corporate records | not emitted | not emitted | not emitted |

Where r is near zero or negative, the judge lane samples documents at random
with respect to quality, and a confident wrong extraction skips it entirely.
A deterministic signal is already available: schema validity, list-field
fill rate and the guard's issue count. Blending those into the routed
confidence (or gating on them directly) is a code change, not a prompt change,
and is added to Phase 0 below. Hypothesis to confirm in Phase 1v: the blended
signal correlates with score at r ≥ 0.5 for every class.

---

## 4. Per-task diagnosis

### 4.1 Sorter

| evidence | value |
| --- | --- |
| 1,000-doc isolated run (Qwen3-8B-AWQ, 458 docs scored) | accuracy 0.895, macro-F1 0.864 |
| recall by class | contract 0.994 · insurance 1.000 · correspondence 0.951 · corporate 0.743 · merger 0.444 |
| errors into `contract` | 35 corporate records, 10 merger agreements |
| API n = 20, Qwen3-8B | class 0.70, subclass 0.05; 3/3 mergers → contract; 3/5 corporate → contract; `doc_subclass` empty on 13/20 |
| API n = 20, Granite | class 0.90, subclass 0.60 |
| API n = 100 | class 0.91–0.95, subclass 0.49–0.64 across three models |

Root causes: F2 (salience), missing `doc_subclass` in the output spec, catalog
after the document, a nullable free-text `doc_subclass` in the JSON schema, and
no class-boundary cues for the look-alikes (indenture, rights agreement,
certificate of amendment, Exhibit 21 subsidiary list, Agreement and Plan of
Merger).

Lexical nuance to preserve: all 65 quoted title cues and 41 worked `->`
decisions in the contract rules (these encode real corpus conventions:
title-wins families, development preference, maintenance for O&M consortia, SEC
joint filing → joint_venture), plus the doctrine lines (policy → contract,
demand letter about a contract → correspondence, court opinion → unknown).

### 4.2 Correspondence

| evidence (API, 3 models) | value |
| --- | --- |
| overall | 0.41–0.51 |
| precision / recall | 0.13–0.19 / 0.19–0.28 |
| entity-list F1 | 0.058–0.061 (all models) |
| fill rate: recipient / date / sender | 0.39–0.45 / 0.39–0.50 / 0.65–0.78 |
| `communication_type` vs subclass | 14–19 / 20; press_release → email and notice → email dominate |
| sandbox v2 vs production (paired 50) | +0.042; notice +0.146, letter +0.092, email +0.036, memo −0.008 |

Root causes: entity lists fail on every model, which points at name format and
list shape rather than model capacity (inferred; needs a ground-truth look);
Enron header fields are left empty half the time (hypothesis: headers are
stripped or not recognized as sender/recipient lines); press releases and
notices are read as emails. The per-subclass briefs in the v1 lineage are what
lifted rare types, so they are nuance to keep.

### 4.3 Insurance claims

| evidence | value |
| --- | --- |
| overall (API) | 0.71–0.80; best-performing class everywhere |
| schema validity | 3/60 API, 0.22–0.24 in the sandbox |
| fill: `denial_reasons` / `adjuster` | 0.00 / 0.15–0.20 |
| confidence vs score correlation | −0.22 to +0.34 (uninformative) |
| weakest subclass | carrier (0.625 mean across models); auto strongest (0.873) |
| sandbox v2 vs production | −0.005; outpatient −0.010, auto −0.009 |

Root causes: F1 almost entirely. The extraction itself is strong; the output
contract is what fails. The CMS-specific cues (MSN Notice ID, Part B/D, NPI
lines, "Claim total paid by Medicare") are the nuance to keep.

### 4.4 Contracts

| evidence | value |
| --- | --- |
| overall (API) | 0.48–0.62 |
| precision / recall | 0.10–0.12 / 0.35–0.52 (over-extraction) |
| f1 = 0 documents | 1–7 / 20 |
| completion tokens (median) | 3,324 Qwen · 5,590 DeepSeek · 11,351 Granite |
| schema validity | 8/58 (`maud_clauses` null) |
| sandbox CUAD clause-detection F1 | 0.596 micro (38 labeled docs) |

Root causes: F4 (MAUD fields in the contract schema), F5 (reasoning object
inflating output), long `cuad_clauses` lists that lower precision, and the CUAD
folder-name mismatch (F3) in subclass scoring.

### 4.5 Merger agreements

| evidence | value |
| --- | --- |
| overall (API) | 0.24–0.45 |
| precision / recall | 0.02–0.09 / 0.10–0.40 |
| f1 = 0 documents | 4–16 / 20 |
| parse errors | DeepSeek 10/20, Qwen 3.7 Flash 2/20 |
| `merger_consideration` vs subclass | 3/10–16/20; ground-truth `other` (9 of 20 docs) predicted as all_cash / all_stock / mixed |
| sandbox MAUD micro accuracy | 4.0% generic prompt, 8.5% MAUD prompt (coverage 33%) |

Root causes: the MAUD question list is long enough to truncate outputs and is
formatted as a fenced block that models copy (F5); the `other` consideration
type has no definition, so models pick the nearest cash/stock label; the dataset
collapses several MAUD sub-questions under one name (documented in the SAND-032
reports), which caps achievable accuracy.

### 4.6 Corporate records

| evidence | value |
| --- | --- |
| overall (API) | 0.40–0.44 |
| precision / recall | 0.08–0.10 / 0.20–0.23 |
| f1 = 0 documents | 8–10 / 20 |
| schema validity | 41/60 (`signatories` null) |
| hardest subclasses | officer_certificate 0.25, charter_amendment 0.30, indenture 0.34 |
| sandbox v2 vs production | −0.010; charter_amendment −0.158, subsidiary_list +0.098 |

Root causes: F3 (10 subclasses mapped onto 5 `record_type` tokens by prose
rule); the charter-amendment mapping is a **hypothesis** to check against Hub
`gt_fields` before any prompt change; low precision suggests over-long
`keywords` and `subject_matter` (inferred).

### 4.7 Other graph nodes

The compiled graph (`graph/build_graph.py`) has 13 nodes. Besides `classify`
(sorter) and `extract` (specialists), six make LLM calls; the rest are
deterministic. None of the six has a live scored run in either repo:
eval-environment holds only 2-document smoke runs for intake, arbiter, boss,
judge→arbiter and the full chain, and every sandbox `judge` and `pipeline`
row is a mock. Findings below therefore come from the prompt text and the
routing code (inferred), not from outputs.

Every node's system prompt is a frozen `*_V0` block plus a "production
doctrine" block from `llm/prompt_doctrine.py`, served through Langfuse as
`mailroom-<agent>` with the local text as fallback.

| node | prompt (words) | role | main issues |
| --- | --- | --- | --- |
| `intake` (intake clerk) | 353 | triage + OCR clean + section map, advisory only | three jobs in one call; class list injected but no subclass catalog, yet it is told to emit `doc_subclass`; section roles are contract-shaped (`recitals`, `termination`) for all five classes |
| `review_classify` (sorter reviewer) | 483 (216 V0 + 267 doctrine) | blind second opinion in the medium band | shares the sorter's F2/F3 blind spots but not the sorter's 65 contract cues, so a reviewer "disagree" on contracts is weak evidence; rule 4 and `FIVE_CLASSES` state the demand-letter boundary twice |
| `judge_verify`, completeness | 480 | exception-lane completeness verdict | 16k-character input cut; gate depends on F7; rules 3, 6 and the doctrine all restate "absent is not missing" |
| judge, classification | 510 | offline classification audit | the doctrine adds "court opinion → unknown" while V0 rule 2 says "a judicial decision about a contract is a court opinion", a class the live taxonomy no longer has |
| judge, correctness | 364 | offline factual audit | the cleanest of the three; same truncation rules repeated |
| `arbiter` | 421 | accept / retry named fields / human review | `fields_to_fix` must be schema names but the schema is not in the prompt; the judge's findings arrive as prose, so field names are reconstructed |
| `boss_escalation` | 428 | same-class matter conflicts; also an ops-monitor role | two roles in one prompt, the in-graph call carries the ops-monitor half as dead weight |
| `compile_report` | 44 (retired LLM path) | deterministic `compile_matter_record` in this sandbox | nothing to tune; keep the retired prompt out of GEPA |

Cross-node patterns:

1. **Stale taxonomy in V0 text.** The sorter reviewer and classification judge
   V0 prompts still name "court opinion" as a class. The doctrine that follows
   says court opinions map to `unknown`. The model sees both; the later block
   usually wins, but the contradiction costs tokens and invites drift. Fix by
   editing V0 once (it is "frozen" only by convention) instead of patching
   with doctrine.
2. **Duplicated doctrine.** `FIVE_CLASSES` (74 words) is appended to the
   sorter, reviewer, classification judge, completeness judge, arbiter and
   boss prompts; `NUMERIC_ZERO` and `VISION_ADDITIVE` recur similarly. The
   judges and arbiter never need the full class-boundary paragraph, only the
   assigned class's schema. Deduplicating V0 and doctrine per node removes
   roughly 25–35% of each prompt (estimate from the word counts above)
   without dropping a rule.
3. **Schema not in the prompt.** Judges and the arbiter are told to "judge
   only registered schema fields" but receive the schema only as a response
   format, not as the list of fields to check. The same F1 fix applies:
   inject the field list for the assigned class into the user message.
4. **Intake overload.** One call triages, repairs OCR and builds a section map.
   Its output is advisory; the sorter ignores it by design. Split or trim:
   keep triage + `cleaned_text` (useful for scanned mail) and make the
   section map class-aware or drop it until a consumer uses it.
5. **Boss role split.** Serve two prompts (`mailroom-boss` in-graph,
   `mailroom-boss-ops` for the sweep) so each call carries one role.

Skeleton for these nodes (same ROLE / SCOPE / CUES / PRECEDENCE / FIELDS /
OUTPUT order as section 5.2): CUES becomes the node's decision criteria
(judge labels and thresholds, arbiter's three actions), FIELDS the injected
schema for the assigned class, and the shared doctrine is included only where
the node actually decides class membership (sorter, reviewer, classification
judge).

---

## 5. Design: concise prompts that keep the nuance

### 5.1 Principles

1. **Types belong in code, cues belong in the prompt.** Enforce list/string/enum
   shape with a JSON schema or post-parse coercion; spend prompt tokens only on
   what the model cannot infer: the vocabulary and the cues.
2. **Nuance is lexical, not rhetorical.** Keep every quoted title, header token,
   form code and worked decision. Drop meta-instructions ("read quickly", "be
   decisive"), all-caps emphasis, repeated negations and negative key lists.
3. **Conventions as data.** A precedence table with one row per family replaces
   23 numbered prose rules and makes conflicts visible (and testable).
4. **One vocabulary per field, shared end to end.** Sorter catalog, specialist
   field, ground truth and scorer use the same keys, with an explicit alias map
   for corpus folder names.
5. **Placement.** Role, scope, catalog and output contract before the
   document; the document last; nothing required after it.

### 5.2 Fixed skeleton (all six prompts)

```
ROLE        one line: what this agent is and the single decision it makes
SCOPE       is / is not (the look-alike classes only, one line each)
CUES        table: subclass | title / header cues | fields to read first
PRECEDENCE  ordered rules for conflicts (sorter: family table; specialists: ≤ 5 rules)
FIELDS      one line per field: name, meaning, extraction cue (no type or null prose)
OUTPUT      "Return one JSON object matching the schema." (schema sent by the caller)
```

Stable block headers give GEPA fixed `anchor_head`s for surgical mutations.

### 5.3 Sorter, redesigned

- **Class boundaries first** (new, about 1.2k characters): cue lines for the
  look-alikes that currently fall into `contract`: "Indenture" / trustee /
  "Supplemental Indenture" → corporate_record; "Rights Agreement" with a rights
  agent → corporate_record; "Certificate of Amendment" → corporate_record;
  "Subsidiaries of the Registrant" / Exhibit 21 → corporate_record; "Agreement
  and Plan of Merger", "Merger Sub", "Effective Time", per-share merger
  consideration → merger_agreement.
- **Contract families as one table** (replaces rules 6–28, target ≤ 4k
  characters): columns *family · title cues · operative cues · wins over · loses
  to*. Every quoted title cue and worked decision becomes a cell; "annex
  inheritance" (the missing rule 17) becomes an explicit row: schedules,
  exhibits and annexes inherit the parent agreement's family. Example rows:

  | family | title cues | operative cues | wins over | loses to |
  | --- | --- | --- | --- | --- |
  | promotion | "Promotion", "Co-Promotion", "Promotion and Distribution" | promote, detail, field force | marketing, distributor | — |
  | outsourcing | "Outsourcing", "Manufacturing Outsourcing" | outsourced function | manufacturing | — |
  | marketing | "Marketing" (alone or with agency, reseller, manufacturing, servicing, co-branding), "Remarketing" | promotion, placement, servicing of owner's products | agency, distributor, reseller, manufacturing, co_branding, joint_venture | license, transportation, hosting when primary; affiliate |
  | development | "Development", "Collaborative Development and Commercialization" | development plan, milestones, trial timelines, JSC, development funding | distributor, supply, sponsorship, license, collaboration, franchise | manufacturing, marketing, hosting, promotion as operating core |
  | maintenance | "License and Maintenance", "Operation and Maintenance", "Customization Schedule", capital/liquidity maintenance | support, O&M cost allocation | license, joint_venture, service, development | — |
  | joint_venture | "Joint Filing Agreement/Statement" (Schedule 13D/13G) | — | other, non-contract | — |

- **Output contract**: `doc_type`, `doc_subclass` (required whenever the class
  has a catalog), `contract_subtype` (contract only), `confidence`,
  `reasoning` (one sentence). Per-class enum in the JSON schema.
- **Catalogs with one-line definitions** for every class (correspondence
  currently has none), placed before the document.
- **Code changes, not prompt:** parse error → `unknown` (not correspondence);
  one input policy for both repos (title block + first N characters, with N
  chosen by a cost/accuracy check on the 1,000-doc draw).
- **Optional two-pass variant** (test after the single-pass redesign):
  pass 1 doc_type with boundary cues only; pass 2 subclass with that class's
  catalog only. Cost: one extra short call; benefit: each pass sees only its
  decision's cues.

Size target: about 7k characters (−60%), with a cue-coverage test (5.5) proving
every title cue and decision survived.

### 5.4 Specialists

| class | change | why |
| --- | --- | --- |
| all | send the Pydantic schema (JSON-schema mode) or coerce `null` → `[]` for list fields after parsing; remove "→ null" / "→ []" prose; remove negative key lists | F1, F4 |
| all | one-sentence `subject_matter`, ≤ 8 `keywords`, stated in FIELDS | precision (inferred) |
| correspondence | keep the per-subclass brief (it drove the v2 gain); add header-line cues for sender / recipient / date (From:, To:, Sent:, Date:) and the press-release vs email and notice vs email distinctions as CUES rows | recall, subclass confusions |
| insurance | no wording change beyond F1; keep the CMS cues | extraction is already strong |
| contracts | drop `merger_consideration` / `maud_clauses` from the contract schema; replace the pre-value `reasoning` object with a one-line reason; cap `cuad_clauses` to present categories with a cue per category | F4, F5, precision |
| merger | MAUD question names as a plain CUES list (no code fence); define `other` consideration; emit only answered questions (already the rule) with a hard cap tied to max tokens | F5, parse errors |
| corporate | settle the `record_type` vocabulary against Hub `gt_fields` first (hypothesis on charter amendments); then one CUES row per subclass including indenture, officer certificate, subsidiary list | F3 |

### 5.5 Keeping the nuance: a cue inventory with a coverage gate

1. Extract every lexical cue from the current prompts into
   `prompts/cues/<role>.yaml`: quoted titles, header tokens, form and field
   codes (MSN Notice ID, CLM_ID, NPI, Part B/D), MAUD question names and valid
   classes, CUAD family keys and their folder aliases, and each worked decision
   as a (input cue → label) pair.
2. A test asserts 100% of inventoried cues appear in the compressed prompt (as a
   table cell or a CUES row). A compression that drops a cue fails before any
   spend.
3. The inventory also generates the alias map that fixes the scorer
   (`License_Agreements` → `license`), so prompt, schema and scorer share one
   vocabulary.

---

## 6. How this complements GEPA

GEPA (eval-environment, pinned to gepa-ai/gepa `b265bf9`) runs reflective,
surgical mutations: anchored edits, a +120-character budget per specialist
(Gate 5), OBSERVE manifests grounded in Braintrust traces, and N = 20 A/B on
Qwen 3.7 Flash. The Stage 10 check showed the correspondence gain carries over to
Qwen3-8B-AWQ, which supports the loop itself.

| gap | effect on GEPA | complement |
| --- | --- | --- |
| structural defects (F1, F3–F6) dominate the failure manifests | reflection spends mutations on contract bugs (e.g. "signatories never null") | Phase 0 fixes them in code, so OBSERVE sees language-level failures |
| Gate 5 only bounds growth | prompts can only get longer | allow net-negative mutations; add a **compression operator** that must pass the cue-coverage gate |
| single-objective acceptance on the mean | subclass losses are accepted (charter_amendment −0.158) | use GEPA's instance frontier keyed by subclass, with minibatches stratified by subclass; reject if any subclass with n ≥ 5 drops > 0.05 |
| length is not an objective | no pressure toward concision | Pareto frontier over (score, prompt tokens); GEPA's objective/hybrid frontier types support this |
| anchors are free text | mutations drift when headings change | the fixed skeleton (5.2) gives stable anchors |
| transfer is checked ad hoc | Flash gains may not hold on the served model | standard promotion step: paired n ≥ 50 per class on Qwen3-8B-AWQ (as Stage 10 did) |

### 6a. Langfuse serving and promotion

Prompts reach the graph through `llm/prompts.get_managed_prompt`: the
`production` label of `mailroom-<agent>` in Langfuse, with the in-code text as
fallback when Langfuse is off or unreachable. Consequences for this plan:

- Offline tests and mock runs exercise the fallback, never the served prompt.
  Add a drift check (hash of served `production` vs local text per agent) to
  `sandbox health` so a GEPA promotion to Langfuse cannot silently diverge
  from what the offline suite validated.
- Promote by label, not by edit: publish the new version under a
  `candidate` label, run the paired gate in section 7 with that label
  pinned, then move `production`. Langfuse keeps the version history needed
  for rollback.
- Link each generation to its prompt version (`langfuse_prompt=` is already
  passed), so per-node scores in Langfuse can be split by prompt version.
  This is the view the trace review in 7a needs for the non-specialist nodes,
  which have no Braintrust experiments at all.

---

## 7. Evaluation and promotion protocol

- **Draws:** seed-42, nested, paired on identical documents; n ≥ 50 per class
  (n = 20 only for OBSERVE).
- **Noise floor:** a Stage 3 repeat moved correspondence by 0.004 on Qwen3-8B-AWQ
  (thinking off); the older 20/50-doc runs showed ±0.02. Treat |Δ| < 0.01 as
  noise.
- **Promotion gates:** paired mean Δ ≥ +0.02 · no subclass (n ≥ 5) worse by
  more than 0.05 · schema validity not lower · median completion tokens not
  higher · cue coverage 100% · sign test reported.
- **Report per subclass**, not only means, and state which lineage step is
  being compared (production vs v1 vs a GEPA child).
- **Sorter:** score class and subclass separately, per class, with the alias
  map applied; report `doc_subclass` fill rate.

---

## 7a. Braintrust traces (Mailroom-Evals)

**What was reviewed.** The live Braintrust API (`api.braintrust.dev`) is blocked
by this environment's network policy, so trace spans and model reasoning could
not be read from here. The review used eval-environment's tracked
Braintrust-derived index, `reports/gepa/braintrust_backlog_index.json` (project
Mailroom-Evals, 33 specialist experiments, 97 failures merged into GEPA OBSERVE
manifests).

**Findings from the index (measured):**

- **The backlog mixes degenerate runs into GEPA's reflection signal.** Of 25
  runs with n ≥ 20, at least five are superseded or broken runs whose scores
  reflect pipeline bugs of the time, not prompt wording: contracts `023347Z`
  (0.076), correspondence `022738Z` (0.000) and Granite `044805Z` (0.100),
  insurance `023050Z` (0.202), corporate `022810Z` (0.182). Their failures are
  merged into OBSERVE manifests alongside the canonical runs.
- **Eight of 33 runs are probes or empty** (n < 20).
- **Only 3 of 25 full runs link a Braintrust dataset**, so most traces cannot be
  joined back to their dataset rows from Braintrust alone.
- **The sorter is absent**: the index covers the five specialists only, so
  GEPA has no trace-grounded failure signal for the sorter.

**Complement to GEPA:** restrict OBSERVE manifests to the canonical runs listed
in `API-LEG-MASTER-REPORT.md` (the "final" stems), add the sorter classification
experiments to the backlog, and link every experiment to its dataset.

**Trace review to run once `api.braintrust.dev` is allowed** (read-only; no
model spend). eval-environment already has the tool:
`scripts/gepa_observe_specialists.py --braintrust-backlog --enrich-braintrust`.
Pull the canonical experiments for all five specialists and the sorter
(`043145Z`, `070900Z`, `100340Z`, `101020Z`, `101544Z`), then check these
hypotheses from sections 3–4 against the model's own reasoning and raw output:

| hypothesis | trace evidence that settles it |
| --- | --- |
| null lists come from the unseen schema, not from misreading the text (F1) | raw completions: are list fields `null` even when the reasoning names items? |
| the sorter's contract sink is title-driven (F2) | sorter reasoning on corporate/merger docs routed to contract: does it cite "Agreement" in the title? |
| hidden reasoning tokens on the Qwen3-8B legs (F6) | span token counts vs visible completion length |
| merger truncation comes from long `maud_clauses` output (F5) | last tokens of the 10 truncated DeepSeek completions |
| correspondence misses headers (4.2) | input spans: are From/To/Sent lines present in what the model saw? |
| charter amendments mapped to the wrong `record_type` (4.6) | per-field expected vs predicted in the scorer spans |

## 8. Roadmap

| phase | work | where | spend |
| --- | --- | --- | --- |
| 0 — contract fixes | send the JSON schema (or coerce list nulls); drop MAUD fields from the contract schema; sorter parse error → unknown; CUAD folder alias map in eval-environment scoring; one sorter input policy; blend schema validity and guard issues into routed confidence (F7); inject the class field list into judge and arbiter calls | eval-environment, llm-mailroom (vendored), sandbox scorer | none (offline tests) |
| 0b — re-score | re-score all logged predictions with the fixed schema handling and alias map to set the new baselines | both repos | none |
| 1 — skeleton + cues | cue inventories and coverage test; rewrite sorter to the table form; move all six prompts to the skeleton, keeping v1-lineage subclass briefs |
| 1b — other nodes | fix stale "court opinion" V0 text; deduplicate V0 + doctrine per node; split boss in-graph and ops prompts; trim or class-scope the intake section map; Langfuse drift check in `sandbox health` | llm-mailroom (via monorepo), sandbox | none |
| 1n — node evals | first scored runs for judge, arbiter and reviewer: n = 40 labelled judge/arbiter cases built from existing specialist predictions and their scores | eval-environment | small; needs approval | eval-environment prompts, sandbox `config/prompts` | none until validation |
| 1v — validate | paired n = 75 per class on Qwen3-8B-AWQ 1×L4 (Stage 10 cost ≈ $0.14 for three classes); sorter on a stratified 500-doc draw | sandbox | about $0.5–1 (estimate from SAND-032 ledgers); needs approval |
| 2 — GEPA under new gates | compression operator, cue gate, subclass frontier, size objective | eval-environment | per GEPA budget |
| 0c — trace review | read-only Braintrust pull of canonical specialist + sorter experiments; settle the six hypotheses in 7a | eval-environment tooling | none (needs `api.braintrust.dev` network access) |
| 3 — open questions | corporate `record_type` vs Hub `gt_fields`; MAUD `other` definition; whether Enron headers survive preprocessing | dataset owners | none |

No step above has been run; Phase 1v is the first point that would spend.

---

## Appendix A — sources

- eval-environment `e5d8766`: `reports/experiment_log.jsonl`; canonical runs
  `20260927T033031Z/053647Z/105317Z` (correspondence), `035135Z/054211Z/105400Z`
  (insurance), `035621Z/054738Z/105549Z` (contracts), `022750Z/082404Z/110153Z`
  (merger), `042239Z/065622Z/110828Z` (corporate); sorter `043145Z`, `070900Z`
  (n = 20), `100340Z`, `101020Z`, `101544Z` (n = 100).
- eval-environment `prompts/` (v1, v2, `mutations.json`),
  `src/evals/specialist_llm.py`, `src/evals/scoring.py`,
  `.opencode/agents/PROMPT_ENGINEER_GEPA_PROVENANCE.md`.
- sandbox `reports/serving/SAND-32/SAND032-S6-SORTER1000-REPORT.md`,
  `reports/serving/SAND-32/SAND032-V2-PROMPT-PROMOTION.md`, `reports/SAND-32/*/SAND032-S3-*`,
  `reports/SAND-32/*/SAND032-S10-*`.
- vendored `llm-mailroom`: `langchain_agents/sorter_agent.py`,
  `langchain_agents/prompts.py`, `schemas/documents.py`,
  `graph/build_graph.py` (node wiring), `graph/routing.py` (`judge_gate`),
  `pipeline/guards.py` (`apply_extraction_guard`), `llm/prompt_doctrine.py`,
  `llm/prompts.py`, `agents/{intake,sorter_reviewer,judge,arbiter,boss,reporter}.py`;
  `config/taxonomy.yaml` confidence bands.
- mailroom-ml `088530b`: head label counts (`AGENTS.md`), per-head support in
  `reports/eval_m9a-*.json`.
