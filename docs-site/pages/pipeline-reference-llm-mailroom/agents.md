---
description: The specification for every agent.
icon: robot
title: Agents
---

# Agents

This page is the specification for every agent in the pipeline. For each agent it gives the trigger, the input, the output, and the design rule it enforces. Read the roster below first to find your agent. Each section after the roster stands alone.

## The roster at a glance

An *agent* here is any component that does one job on a document. Only some of them call a language model. The rest are deterministic code that follows the same contract, so the graph treats them uniformly.

| Stage | Agent | Calls an LLM? | Model tier | One-line job |
| --- | --- | --- | --- | --- |
| Intake | Intake clerk | Deterministic core always; LLM pass only for messy or over-budget text | `fast` | Normalize text, optionally triage, clean and map sections |
| Intake | PDF transcriber | Only for scanned or garbled PDFs | `vision` | Faithful text from a PDF |
| Intake | Image extractor | Yes | `vision` | Faithful text from an image |
| Classify | Sorter | Yes | `fast` | Assign document class, subclass and confidence |
| Classify | Sorter reviewer (Lane A) | Yes | `fast` | Blind second opinion when the sorter is only moderately sure |
| Extract | Five class specialists | Yes | `extract` | Fill the class schema (contracts, merger agreements, corporate records, correspondence, insurance claims) |
| Verify | Judge (Lane B) | Yes, only in the ambiguous band | `extract` | Check the extraction for completeness |
| Verify | Arbiter (Lane B) | Yes, only after a partial or incomplete verdict | `extract` | Rule: accept with caveats, re-extract, or send to a human |
| Escalate | Boss | Yes | `extract` | Adjudicate conflicts and repeated low confidence |
| File | Report assembler | No | none | Format the extraction into the report |
| File | Archivist | No | none | Move the file, write the manifest, seal the audit entry |
| Outside the graph | Gmail triage | Yes, on a free model | `fast` | Fast single-document lane for Gmail uploads |
| Outside the graph | Relations agent | Deterministic scan; LLM judgment pass is off by default | `fast` | Link related documents and matters after archiving |

Model tiers (`fast`, `extract`, `vision`) are set per agent in `config/taxonomy.yaml`, together with a `max_tokens` cap. The concrete model behind a tier is configuration and changes more often than this page; see [Configuration](configuration.md) for the current assignment.

Three ideas recur in every entry below:

* **Independence.** The sorter reviewer never sees the sorter's label, and the judge and arbiter are separate calls. Agreement is computed by the graph, so one model cannot grade its own work.
* **No truncation.** No document is ever cut to fit a context window. Long text is processed in overlapping windows and the results are merged deterministically.
* **Fail soft.** Optional or advisory components (LLM intake, Gmail triage, relations) degrade to deterministic behavior on any error. They never block a document.

***

## Agent Architecture

Native agents inherit from `agents/base.py:BaseAgent` and share a common interface. The vendored Sorter, Contracts Specialist and Merger Agreement Specialist instead build a LangChain `ChatOpenAI` with structured output (see below):

```python
class BaseAgent(ABC):
    agent_name: str               # Must match key in config/taxonomy.yaml agents:

    def __init__(self):
        self.client, self.model = get_llm(self.agent_name)

    @abstractmethod
    def system_prompt(self) -> str: ...

    def _call_llm(self, user_message, response_format=None, temperature=None,
                  max_tokens=None, system_prompt=None) -> str: ...

    def _call_structured(self, user_message, json_schema, temperature=0.1,
                         system_prompt=None) -> dict: ...
```

Key design points:

* `self.client` and `self.model` are resolved from `config/taxonomy.yaml` → `llm/providers.py` → `llm/client.py`
* `system_prompt()` fetches the **Langfuse-managed prompt** (`mailroom-<agent_name>`, production label) via `llm/prompts.py:get_managed_prompt`. If Langfuse is unavailable, it falls back to the identical template shipped in code. Behavior never depends on the observability backend. Sync templates with `scripts/sync_prompts.py`.
* `_call_structured()` uses `response_format={"type": "json_object"}` and embeds the JSON schema in the prompt. It also appends boilerplate that puts the literal token `json` in the messages, because some providers reject requests without it.
* Every LLM call goes through `llm/retry.py:retry_chat_completion` (transient failures only: connection errors, timeouts, 429, 5xx) and a `max_tokens` cap from the agent's `taxonomy.yaml` entry.
* When a managed prompt is active, the client passes it to the OpenAI call as `langfuse_prompt=`. This links each generation to its exact prompt version in the trace UI.
* Every agent has a distinct system prompt ("personality") aligned with its role

### Vendored agents and which prompt runs in production

The Sorter, Contracts Specialist and Merger Agreement Specialist are **vendored LangChain agents**. Their code comes from `github.com/Exios66/llm-entity-extraction` and was re-vendored to that repository's current HEAD on 2026-08-15. It is imported into `langchain_agents/` with mailroom plumbing adapted in: page and vision handling, run-deadline checks and per-call usage accounting. Each adaptation is marked `MAILROOM PATCH`, so a re-vendor can find and re-apply them.

These agents use `langchain-openai`'s `ChatOpenAI` with `with_structured_output` instead of `agents/base.py`. That difference matters when debugging: retries, token caps and prompt linking follow the vendored path, not the `BaseAgent` contract above.

The most common confusion is the difference between *prompt history* and *production prompt*:

* **History.** Eval loops pin an explicit lineage key through `langchain_agents/prompts.py:PROMPT_VERSIONS` (`sorter_v0…v15`, `sorter_condensed_v1`, `sorter_condensed_v5`, `contracts_specialist_v1…v33`). This is an append-only record of every version tried.
* **Classify in production uses **`sorter_condensed_v5`**: the sandbox's condensed v1 with one corporate rule reversed — a bylaw amendment is `bylaws`, never `board_resolution` (v10 corpus rule C) — replacing V15. On a 275-document prime sample of verified labels it fixed 108 class answers against V15's 100, broke none, and uses a ~3.7k-character system prompt instead of ~25k (llm-mailroom v0.9.3, 2026-11-07). V13 remains a frozen insurance-class experiment derived from V0.
* **Extract in production** uses the sandbox and eval-environment **frozen v1** stems for all five specialists. The text is served from the llm-dojo-scoring `production_prompts` catalog, pinned in `pyproject.toml`. `src/llm/frozen_v1/lineage.json` records the sha256 and length of each prompt, so a prompt cannot drift unnoticed. The `.txt` files in `src/llm/frozen_v1/` are superseded and not packaged. `contracts_specialist_v33` is eval-only.

The Mailroom wrappers resolve these templates through `get_managed_prompt` (`mailroom-<agent>`, `production` label). The wrappers are `agents/sorter.py`, `agents/contracts_specialist.py`, `agents/merger_agreement_specialist.py`, and the native `BaseAgent` specialists. So the LangGraph `classify` and `extract` nodes share one Langfuse surface. Sync with `scripts/sync_prompts.py`. All other agents follow the `BaseAgent` contract above.

***

## Agent Roster

### 1. Sorter (`agents/sorter.py`)

| Attribute       | Value                                                        |
| --------------- | ------------------------------------------------------------ |
| **Node**        | `classify`, `retry_classify`                                 |
| **Trigger**     | New document in `/processing`                                |
| **Input**       | Raw document text (+ page images for vision-capable models)  |
| **Output**      | `doc_type` + `contract_subtype` + `confidence` + `reasoning` |
| **Personality** | Fast, decisive, flags ambiguity instead of guessing          |

**System prompt seed:** "You are a fast, decisive legal document classifier operating in a transactional/corporate law firm's mailroom."

The shared five-class doctrine in the classification prompts describes `merger_agreement` and `contract` by what they are. It does not name the MAUD or CUAD corpora (llm-mailroom#102, as of 2026-10-07).

The Sorter is the first LLM call in the pipeline. It reads the document text and determines which of the configured document classes it belongs to. The list of available classes is dynamically read from `config/taxonomy.yaml`, so adding a new document type automatically expands the Sorter's options.

The Sorter is a **vendored LangChain agent**: `agents/sorter.py` re-exports `langchain_agents.sorter_agent.SorterAgent`. It works as follows:

* It classifies via `with_structured_output` against the `SORTER_SCHEMA`.
* It uses the production `sorter_condensed_v5` prompt (the sandbox's condensed v1 with the bylaw rule reversed).
* It adds a **contract-subtype dimension**. For contracts it assigns one of 25 CUAD agreement families (affiliate, license, distributor, franchise, …) or `other`. The keys are `CONTRACT_SUBTYPE_KEYS`, normalized via `normalize_subtype`. Non-contracts carry `contract_subtype=None`.
* `classify()` returns a 4-tuple `(doc_type, contract_subtype, confidence, reasoning)`. The subtype flows into state, the classification guard, the extraction handoff context, the report, and the catalog.

**No-truncation doctrine (HUB-038):** the mailroom subclass bypasses the upstream HEAD+TAIL truncation. It classifies documents past the input budget in overlapping sliding windows, so it reads every character. Each call carries `WINDOW i OF n` markers. The window results merge deterministically:

* plurality vote among non-unknown classes;
* mean confidence of the agreeing windows;
* first non-null subtype and subclass;
* joined reasoning.

The advisory intake read rides every window as a labeled prior. Page images attach to the first window only.

***

### 1b. Sorter Reviewer (`agents/sorter_reviewer.py`)

| Attribute       | Value                                                                         |
| --------------- | ----------------------------------------------------------------------------- |
| **Node**        | `review_classify` (Lane A)                                                    |
| **Trigger**     | Medium-band classification that survived `retry_classify`                     |
| **Input**       | Document text (+ page images); **blind** to the sorter's answer               |
| **Output**      | Independent `doc_type` + `contract_subtype` + `doc_subclass` + `confidence`   |
| **Personality** | Independent second opinion; agreement is computed by the graph, not the model |

Fires only where the pipeline previously sent the document to a human. Independence is the point: the reviewer never sees the sorter's label. The graph node compares the two opinions and either applies the reviewer's class or escalates to human review.

***

### 2. Contracts Specialist (`agents/contracts_specialist.py`)

| Attribute       | Value                                                       |
| --------------- | ----------------------------------------------------------- |
| **Node**        | `extract`, `retry_extract`                                  |
| **Trigger**     | `doc_type` is `contract` (CUAD)                             |
| **Input**       | Contract text + `ContractExtraction` schema (+ page images) |
| **Output**      | Structured extraction + confidence                          |
| **Personality** | Meticulous, formal, precise to a fault                      |

**Output schema fields:**

| Field            | Type          | Description                                        |
| ---------------- | ------------- | -------------------------------------------------- |
| `document_name`  | `str \| None` | The name of the contract                           |
| `parties`        | `list[str]`   | All named parties                                  |
| `effective_date` | `str \| None` | Contract effective date                            |
| `term_length`    | `str \| None` | Duration                                           |
| `governing_law`  | `str \| None` | Governing jurisdiction                             |
| `contract_value` | `str \| None` | Total contract value                               |
| `renewal_terms`  | `str \| None` | Renewal conditions                                 |
| `cuad_family`    | `str \| None` | CUAD agreement family                              |
| `cuad_clauses`   | `list[str]`   | Present CUAD categories as `"<label>: <evidence>"` |

The Contracts Specialist is also a **vendored LangChain agent**: `agents/contracts_specialist.py` re-exports `langchain_agents.specialist_agents.ContractsSpecialist`. Its production prompt is the sandbox / eval-environment **frozen v1** stem. The dojo `production_prompts` catalog serves it (Langfuse `mailroom-contracts_specialist`). It is not entity-extraction `contracts_specialist_v33`.

`normalize_extraction` guarantees every schema field is present. If `confidence` is missing, it is derived from the share of fields actually found. The specialist extracts CUAD `contract` only. MAUD `merger_agreement` has its own specialist and `MergerAgreementExtraction` schema. The two labels are not interchangeable.

It accepts a **`handoff_context`**, which is the chained-eval pattern. The graph passes the sorter's classification (`doc_type` + `contract_subtype` + confidence) into the extraction call. The specialist then extracts with the expected clause set of that agreement family in mind. Every live specialist accepts the same optional `handoff_context` parameter.

***

### 2b. Merger Agreement Specialist (`agents/merger_agreement_specialist.py`)

| Attribute       | Value                                                                      |
| --------------- | -------------------------------------------------------------------------- |
| **Node**        | `extract`, `retry_extract`                                                 |
| **Trigger**     | `doc_type == merger_agreement` (MAUD)                                      |
| **Input**       | Merger-agreement text + `MergerAgreementExtraction` schema (+ page images) |
| **Output**      | Structured extraction + confidence                                         |
| **Personality** | Meticulous MAUD reader; consideration and closing-condition facts only     |

**Output schema fields:**

| Field                  | Type          | Description                                                                           |
| ---------------------- | ------------- | ------------------------------------------------------------------------------------- |
| `document_name`        | `str \| None` | Agreement title as stated                                                             |
| `parties`              | `list[str]`   | Parent, Merger Sub, Target as named                                                   |
| `effective_date`       | `str \| None` | Effective Date (ISO when a calendar date is stated)                                   |
| `effective_time`       | `str \| None` | Effective Time as written                                                             |
| `governing_law`        | `str \| None` | Governing-law jurisdiction                                                            |
| `merger_consideration` | `str \| None` | `all_cash` / `all_stock` / `mixed_cash_stock` / `mixed_cash_stock_election` / `other` |
| `maud_clauses`         | `list[str]`   | Answered LegalBench MAUD questions as `"<Question>: <Answer>"`                        |
| `intent`               | `str \| None` | Short controlled label                                                                |
| `subject_matter`       | `str \| None` | One grounded sentence                                                                 |
| `keywords`             | `list[str]`   | Up to 8 grounded terms                                                                |

`cuad_family` and `cuad_clauses` are not primary on this class. The specialist wraps the LangChain `MergerAgreementSpecialist` (chunked extraction for long MAUD agreements) and serves the frozen v1 stem (from the dojo `production_prompts` catalog) via `get_managed_prompt`. Dojo suite key stays `merger_agreement`.

***

### 3. Corporate Records Specialist (`agents/corporate_records_specialist.py`)

| Attribute       | Value                                              |
| --------------- | -------------------------------------------------- |
| **Node**        | `extract`, `retry_extract`                         |
| **Trigger**     | `doc_type == corporate_record`                     |
| **Input**       | Document text + `CorporateRecordExtraction` schema |
| **Output**      | Structured extraction + confidence                 |
| **Personality** | Methodical, loves structure and hierarchy          |

**Output schema fields:**

| Field            | Type          | Description                                                                                                                             |
| ---------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `entity_name`    | `str`         | Legal entity name                                                                                                                       |
| `record_type`    | `str`         | Hub extract tokens: `articles_of_incorporation`, `bylaws`, `powers_of_attorney`, `rights_instrument`, `other` (sorter catalog is wider) |
| `effective_date` | `str \| None` | Date the record took effect                                                                                                             |
| `intent`         | `str \| None` | Short controlled label (e.g. `record_governance`)                                                                                       |
| `subject_matter` | `str \| None` | One grounded sentence                                                                                                                   |
| `keywords`       | `list[str]`   | Up to 8 grounded terms                                                                                                                  |
| `signatories`    | `list[str]`   | Who signed/approved                                                                                                                     |
| `jurisdiction`   | `str \| None` | State/country of incorporation                                                                                                          |
| `filing_number`  | `str \| None` | Official filing reference                                                                                                               |

**Honest gap (dojo v0.28.1):** there is **no external extraction benchmark** for this class (nothing CUAD/MAUD-shaped). The published `mailroom-dataset` set has **450** `corporate_record` rows with record-type subclasses. Dataset v9 expanded this class from 39 legacy S-1 rows by +411 EDGAR exhibits (see [SEC corporate records](../mailroom-dataset/source-corpora/edgar-corporate-records.md)). The Hub extract inventory stays the five tokens above. Do not treat those rows as clause-level gold.

Mailroom scores a **local extraction pack** (`observability.local_eval_packs`, mock/check only) built from committed fixtures. Its `expected_fields` are schema-complete (entity\_name, subject\_matter, keywords, signatories, …). Extra Hub `ground_truth` columns are joined when present, never invented.

***

### 4. Correspondence Specialist (`agents/correspondence_specialist.py`)

| Attribute       | Value                                             |
| --------------- | ------------------------------------------------- |
| **Node**        | `extract`, `retry_extract`                        |
| **Trigger**     | `doc_type == correspondence`                      |
| **Input**       | Document text + `CorrespondenceExtraction` schema |
| **Output**      | Structured extraction + confidence                |
| **Personality** | Reads between the lines, tracks narrative/intent  |

**Output schema fields:**

| Field                   | Type            | Description                                    |
| ----------------------- | --------------- | ---------------------------------------------- |
| `sender`                | `str`           | Who sent it                                    |
| `recipient`             | `str`           | Who received it                                |
| `additional_recipients` | `list[str]`     | Cc'd / copied parties                          |
| `communication_type`    | `str`           | letter, email, memo, notice, demand, etc.      |
| `communication_date`    | `str \| None`   | When it was sent                               |
| `intent`                | `str \| None`   | Short controlled label (e.g. `demand_payment`) |
| `subject_matter`        | `str \| None`   | One grounded sentence                          |
| `keywords`              | `list[str]`     | Up to 8 grounded terms                         |
| `demand_amount`         | `float \| None` | Exact dollar amount demanded (demand letters)  |
| `action_items`          | `list[str]`     | At most 3 concrete actions                     |
| `urgency`               | `str`           | routine, time-sensitive, urgent, critical      |
| `confidence`            | `float`         | Extraction confidence (evidence-derived)       |

***

### 5. Compliance specialist (removed 2026-09-15)

Removed in commit `59c47401` (2026-09-15), which deleted the docclass arm. That commit removed the compliance specialist module, its extraction schema, its prompts, and its eval fixtures. Nothing is retained as inert machinery for local eval packs. The five-class taxonomy is final: `contract`, `corporate_record`, `correspondence`, `merger_agreement`, `insurance_claim`. Everything else is `unknown` (human review). Documents of the retired compliance-filing type route as `unknown`. Do not recreate this specialist or its schema.

***

### 6. Insurance Claims Specialist (`agents/insurance_claims_specialist.py`)

| Attribute       | Value                                                                              |
| --------------- | ---------------------------------------------------------------------------------- |
| **Node**        | `extract`, `retry_extract`                                                         |
| **Trigger**     | `doc_type == insurance_claim`                                                      |
| **Input**       | Document text + `InsuranceClaimExtraction` schema                                  |
| **Output**      | Structured extraction + confidence                                                 |
| **Personality** | Detail-driven claims analyst — documents what the file shows, never argues with it |

**Output schema fields:**

| Field                    | Type            | Description                                                                                                                                                       |
| ------------------------ | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `claim_number`           | `str \| None`   | Claim reference number                                                                                                                                            |
| `policy_number`          | `str \| None`   | Policy the claim is filed under                                                                                                                                   |
| `insurer`                | `str`           | Insurance carrier                                                                                                                                                 |
| `insured_party`          | `str`           | Policyholder / insured party                                                                                                                                      |
| `claim_type`             | `str`           | CMS/DE-SynPUF `pde` / `inpatient` / `outpatient` / `carrier`, plus legacy FNOL lines (`auto`, `property`, `liability`, `health`, `life`, `workers_comp`, `other`) |
| `date_of_loss`           | `str \| None`   | Date of the loss event                                                                                                                                            |
| `date_filed`             | `str \| None`   | Date the claim was filed                                                                                                                                          |
| `claimed_amount`         | `float \| None` | Amount claimed                                                                                                                                                    |
| `adjuster`               | `str \| None`   | Assigned adjuster; null is valid for CMS / DE-SynPUF rows                                                                                                         |
| `damages_description`    | `str`           | Damages narrative                                                                                                                                                 |
| `coverage_determination` | `str`           | approved, denied, partial, pending                                                                                                                                |
| `denial_reasons`         | `list[str]`     | Stated denial reasons                                                                                                                                             |
| `supporting_documents`   | `list[str]`     | Documents referenced as supporting the claim                                                                                                                      |
| `intent`                 | `str \| None`   | Short controlled label (e.g. `coverage_denial`)                                                                                                                   |
| `subject_matter`         | `str \| None`   | One grounded sentence                                                                                                                                             |
| `keywords`               | `list[str]`     | Up to 8 grounded terms                                                                                                                                            |
| `claim_checklist`        | `list[str]`     | Present claim categories as `"<Category>: <evidence>"`                                                                                                            |
| `confidence`             | `float`         | Extraction confidence (evidence-derived)                                                                                                                          |

A first-class document class, added in mailroom v0.4.0 / KANBAN-067. It has a schema registry entry, a taxonomy doc\_class and agent block, a graph dispatch node, classifier vocabulary, and sorter prompt coverage.

**Honest gap (dojo v0.28.1):** Hub rows are CMS DE-SynPUF source tables (`carrier`/`inpatient`/`outpatient`/`pde`). Typed extraction plus field-micro P/R/F1/F2 are scored. **`determination_consistency` and `amount_exactness` are registered scorers.** CMS GT is homogeneous: every row has `coverage_determination=approved` and empty `denial_reasons`. So Hub `determination_consistency` is **gated**; it is not a quality KPI on GT-shaped rows. A local contrast pack (approved / denied / partial) exercises the scorer off that tautology.

The same three determinations also live on the pilot manifest as synthetic mock-only PDFs: `insurance_01` approved, `insurance_02` denied, `insurance_03` partial. `prepare_samples.py` renders them from `docs/examples/sources/insurance/`. So `--mock` pilots cover `insurance_claim` end-to-end, and `--real` refuses them via `is_real_sample`. Mailroom still records a local field invariant on traces. Candidate corpus EDA lives in [`claims-data-eda`](https://github.com/Exios66/claims-data-eda).

***

### Retired classes (`court_opinion`, `due_diligence`)

Retired from the live pipeline in v0.5.0 / PR #21. The sorter emits `unknown` (human review); there is no specialist dispatch, extraction schema, or managed prompt. Dojo keeps historical suites with `retired=True` (`list_suites(live_only=True)` excludes them). **Court opinions:** LegalBench remains the real benchmark surface. **Due diligence:** zero rows in `mailroom-dataset`.

***

### 7. Report assembler (`agents/reporter.py`)

| Attribute       | Value                                                                         |
| --------------- | ----------------------------------------------------------------------------- |
| **Node**        | `compile_report`                                                              |
| **Trigger**     | Extraction complete, confidence sufficient (or arbiter `accept_with_caveats`) |
| **Input**       | Specialist extraction + optional arbiter caveats                              |
| **Output**      | Deterministic `_report` string on `extracted_data`                            |
| **Personality** | none — procedural                                                             |

Happy-path LLM calls stop at classify + extract. `compile_report` is a **procedural** assembler (no `get_llm("reporter")`): it formats the specialist JSON plus any durable arbiter caveats into `extracted_data._report`. Archivist remains the success-path durable sink.

***

### 8. Archivist (`agents/archivist.py`)

| Attribute       | Value                                 |
| --------------- | ------------------------------------- |
| **Node**        | `archive`                             |
| **Trigger**     | Report compiled                       |
| **Input**       | Full manifest + file path             |
| **Output**      | Archive path + audit log entry        |
| **Personality** | Quiet, exhaustive, never skips a step |

The Archivist is NOT an LLM agent. It is a procedural function that:

1. Moves the file to `/archive/<matter_id>/<doc_type>/`
2. Writes the manifest as a JSON sidecar
3. Creates a hash-chained audit log entry

***

### 8b. Intake clerk (`agents/intake.py`)

| Attribute       | Value                                                                                                                                                      |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Node**        | the first-class `intake` node — the intake agent IS the ingest specialist (the ingest + intake steps are ONE; span `normalize-intake` + `intake-llm-prep`) |
| **Trigger**     | every document after text extraction (deterministic core); LLM pass gated to messy / over-sorter-budget documents                                          |
| **Input**       | transcribed `doc_text`                                                                                                                                     |
| **Output**      | cleaned text + stats (`messy`, `changed`, hyphen unwraps, collapsed blanks); LLM pass: advisory triage read + section map + optional structural cleaning   |
| **Personality** | the intake clerk — first agent in the pipeline, one fused TRIAGE + CLEAN + PREPARE pass                                                                    |

The deterministic clerk is the MANDATORY baseline and never skipped. It is dojo `llm_dojo_scoring.intake` gold, re-exported byte-compatible. It applies Unicode NFC, newline/NBSP/zero-width/C0 cleanup, hyphen unwrap, blank collapse, trim, and `looks_messy`. The-Mailroom mirrors `deterministic_normalize` / `looks_messy` in `mailroom_ui/intake_normalize.py`. It reads the span on every `document-pipeline` trace, and Hugging Face pilots depend on it.

**LLM-assisted pass (HUB-038).** On top of the clerk, an LLM pass (ONE fused call per window) TRIAGES, CLEANS, and PREPARES the document for the classification and extraction agents:

* **Triage** — an advisory first read: primary doc class + subclass + confidence + gist + keywords. It has the same vocabulary-clamped shape as the free triage team's `validate_triage`. It rides the terminal manifest's `intake.triage` and the completion echo's INTAKE TRIAGE section. The sorter gets it as a labeled prior and re-classifies independently. Intake NEVER overrules the sorter.
* **Clean** — structural repair of messy OCR-ish text (join run-together lines, drop repeated header/footer artifacts; never alters facts). The model's output is re-run through the deterministic clerk so `prep_invariants` hold; the dojo scores it as `method: llm` against the clerk gold (`score_intake`).
* **Prepare** — a section map (heading + role + document-absolute char offsets, deterministically validated: in-bounds, monotonic, catalog roles) so downstream routing can see document structure.

**No-truncation doctrine (human directive 2026-09-03).** Documents are NEVER truncated. Anything past an input budget is processed in overlapping sliding windows (`agents.intake.sliding_windows`). The windows break on paragraphs and overlap by 15%, mirroring the extraction chunker. The window results merge deterministically:

* Per-window triage reads vote: plurality among non-unknown classes, ties broken on confidence.
* Section offsets are translated to document-absolute positions and overlap-deduped.
* Partial-window cleaning is never spliced back.

The same doctrine governs the sorter. `agents/sorter.py` bypasses the vendored HEAD+TAIL truncation and classifies over-budget documents window-by-window. The reads merge by plurality vote, mean confidence of the agreeing windows, first non-null subtype, and joined reasoning. Every call carries `WINDOW i OF n` markers.

**Gate + cost.** The LLM pass fires ONLY for documents that need it (`looks_messy`, or longer than the sorter's input budget — clean short documents pay zero). One fused call per window on the cheapest paid model (`qwen3.7-flash`; the free tier stays the Gmail triage lane's privilege). `MAILROOM_LLM_INTAKE=0` disables the LLM pass entirely; every failure fails soft to the deterministic clerk output — intake never blocks a run.

***

### 9. Boss (`agents/boss.py`)

| Attribute       | Value                                        |
| --------------- | -------------------------------------------- |
| **Node**        | `boss_escalation`                            |
| **Trigger**     | Data conflict or repeated low confidence     |
| **Input**       | Manifest + conflicting matter context        |
| **Output**      | Decision: approved or review                 |
| **Personality** | Calm under pressure, makes the judgment call |

**Two implementation paths, one personality:**

1. **In-graph (`boss_escalation` node)**: synchronously adjudicates within a document's pipeline run.
2. **Ops-monitor (`pipeline/ops_monitor.py`)**: separate scheduled process sweeping the catalog for systemic issues.

Both share the same system prompt voice — consistent persona across both invocation contexts.

***

### 10. PDF Transcriber (`agents/pdf_transcriber.py`)

| Attribute       | Value                                                               |
| --------------- | ------------------------------------------------------------------- |
| **Node**        | `intake` (via `_read_file_text`)                                    |
| **Trigger**     | PDF with < `pdf_direct_chars_per_page` chars/page (scanned/garbled) |
| **Input**       | PDF file                                                            |
| **Output**      | Markdown text + confidence + method (`direct` / `llm`)              |
| **Personality** | Faithful transcription only — no fact changes                       |

A hybrid agent: text-based PDFs are transcribed **directly** from `pdfplumber`/`pypdf` extraction (no LLM, seconds), while scanned or garbled PDFs get an LLM markdown reformat pass. The threshold is `pipeline.pdf_direct_chars_per_page` in `taxonomy.yaml`.

***

### 10b. Image Extractor (`agents/image_extractor.py`)

| Attribute       | Value                                                         |
| --------------- | ------------------------------------------------------------- |
| **Node**        | `intake` (via `_read_file_text` / `_extract_text_from_image`) |
| **Trigger**     | Image file (jpg/png/gif/webp/tiff/bmp)                        |
| **Input**       | Image bytes as a data-URI                                     |
| **Output**      | Visible text + confidence + method (`vision`)                 |
| **Personality** | Faithful transcription of visible text — no interpretation    |

A vision LLM agent with its own `taxonomy.yaml` entry and Langfuse-managed prompt (`mailroom-image_extractor`). Transient provider failures retry through `retry_chat_completion`; persistent failure raises so the intake node can route the document to review rather than silently substituting a fallback marker.

***

### 11. Judge (`agents/judge.py`)

| Attribute       | Value                                                                                                                             |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Node**        | `judge_verify` (Lane B) **and** offline (`scripts/run_quality_judges.py`)                                                         |
| **Trigger**     | In-graph: any extraction in the ambiguous band (`low <= extraction_confidence < judge_band_high`). Offline: a finished pilot run. |
| **Input**       | Document text + extracted data (+ sorter reasoning, offline)                                                                      |
| **Output**      | Completeness / classification / correctness scores + labels                                                                       |
| **Personality** | Expert legal reviewer; rubric-driven, evidence-citing                                                                             |

The Judge is **part of the document graph** as the gated Lane B completeness check (`judge_verify_node`). Most documents never see this call: clean high-confidence extractions skip it (zero added LLM calls). When it fires, verdicts land on state (`complete` proceeds, `partial`/`incomplete` go to the arbiter, hard failure fail-safes) and scores are emitted via `observability.scores.emit_in_pipeline_judge_scores`.

The same agent also runs **offline** against a finished pilot (`scripts/run_quality_judges.py`) and audits pipeline output against the **task specification** (taxonomy doc classes + extraction schemas):

| Method                         | Measures                                                    |
| ------------------------------ | ----------------------------------------------------------- |
| `judge_completeness`           | Did the specialist capture every field the document states? |
| `judge_classification`         | Is the sorter's assigned class correct for the document?    |
| `judge_extraction_correctness` | Are extracted values factually accurate (no fabrication)?   |

Each dimension returns a score + label + reasoning, ingested as Langfuse scores on the document's trace. Offline run: `PYTHONPATH=src python src/scripts/run_quality_judges.py --real` (or `--mock`).

***

### 11b. Arbiter (`agents/arbiter.py`)

| Attribute       | Value                                                                         |
| --------------- | ----------------------------------------------------------------------------- |
| **Node**        | `arbiter` (Lane B)                                                            |
| **Trigger**     | In-pipeline judge verdict is `partial` or `incomplete`                        |
| **Input**       | Specialist extraction **and** the judge's findings                            |
| **Output**      | Bounded decision: `accept_with_caveats` / `retry_extraction` / `human_review` |
| **Personality** | Final judgment authority; constrained to three outcomes                       |

When the completeness judge rejects an extraction, the arbiter — not the raw pipeline — decides. `retry_extraction` is bounded by `arbiter_retry_max` (`retry_extraction` approval-inclusive; the state counter `arbiter_retry_count` is compared against it); exhausted retries escalate to human review.

***

### 12. Gmail intake triage (`agents/gmail_triage.py`)

| Attribute       | Value                                                                                                                          |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Node**        | none — the single-document Gmail triage lane (watcher claim time, Gmail channel only)                                          |
| **Trigger**     | one accepted attachment per email (`route: triage`) and `MAILROOM_GMAIL_TRIAGE` on (default with the channel)                  |
| **Input**       | The same `doc_text` the pipeline would read (via `graph.build_graph._read_file_text`, after deterministic `apply_intake` prep) |
| **Output**      | `intake.triage`: `primary_doc_class` + `doc_subclass` + `confidence` + `gist` + `keywords`; own `triage_*` audit section       |
| **Personality** | Fast, grounded intake clerk — the accurate log, not the final word                                                             |

The lane runs on the **free OpenRouter triage team** (`openrouter/free`, the Free Models Router: $0 in `cost_models`, rate-limited). Using a free model is deliberate, because single-document Gmail uploads must not accumulate paid-agent spend. The lane performs the **core steps and functionalities of the full pipeline** — deterministic preparation, triage classification, auditable-hash archive with a terminal manifest, and the completion echo — without calling any paid agent. Emails with **two or more accepted attachments drop the triage approach** and run the FULL paid pipeline per document (`route: pipeline`; triage is never dispatched).

> The end-to-end operator manual for the Gmail intake route — enabling the channel, the upload/subject-line format contract, all pathways from Gmail into the pipeline, and troubleshooting — is [`docs/gmail-intake.md`](gmail-intake.md).

**Capability pre-check + honest handoff.** Before the lane runs, a deterministic, LLM-free check (`pipeline/watcher.py:_triage_capability_check`) verifies that the free team can handle the single document. This prevents doomed runs. Documents beyond the free models' reach go to the full paid pipeline:

* image-only inputs (`image_requires_vision`);
* scanned PDFs with no direct text (`scanned_pdf_requires_transcription`);
* unreadable inputs;
* a deterministic text length above the `gmail_triage` `max_input_chars` budget (`exceeds_free_budget:N>M`).

**Merger agreements are typically excessively long and almost always exceed the free models' classification capability.** The handoff reason rides `intake.triage_handoff` onto the terminal manifest and the completion echo ("triage handoff: … — handled by the full pipeline"). The lane's test matrix validates every canonical doc type: contract, merger\_agreement, insurance\_claim, corporate\_record, correspondence. Each is accepted when it is within the free capability envelope.

The triage read is **advisory by design** and never overrules the pipeline agents. It is only dispatched on single-document Gmail instances, where no pipeline run happens. The overrule guard is the standing invariant. Audit entries use their own namespaced section (`triage_ingested` / `triage_classified` / `triage_archived`). So the stored audits are never conflated with the pipeline's `ingested`/`classified`/`extracted`/`archived` vocabulary.

It fails soft. A missing `OPENROUTER_API_KEY`, a rate limit, or a provider error never blocks intake. The failure is logged, and the document parks in `review/` with reason `triage_llm_unavailable`. `validate_triage` clamps the output to the live taxonomy vocabulary: unknown class → `unknown`, confidence 0.0–1.0, ≤6 keywords, 300-char gist. Registration: `llm/prompts.py:prompt_templates()` (synced with `scripts/sync_prompts.py`), agent config in `config/taxonomy.yaml`.

***

### 13. Relations agent (`agents/relations.py`)

| Attribute       | Value                                                                                                                                                                                                                                                                                                                                                              |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Node**        | none — the post-archive association pass + the background archive sweep (HUB-040)                                                                                                                                                                                                                                                                                  |
| **Trigger**     | deterministic layer: every terminal manifest (dispatched off the document path — incl. the Gmail triage lane, which also writes the doc's catalog row so the scan can find it, HUB-051) + a watermark-incremental sweep every `MAILROOM_RELATIONS_SCAN_SECONDS` (embedded in the watcher). LLM judgment pass: config-gated (`relations.llm`, **OFF in the pilot**) |
| **Input**       | deterministic: catalog + manifests + archived text (embeddings cached per document). LLM pass: top-k candidate pairs with signal evidence (gists/keywords — never raw text)                                                                                                                                                                                        |
| **Output**      | typed, scored edges (`relation_edges`) + hash-chained ledger entries (`relation_log`) + advisory RELATED context for agents/echo + knowledge-graph exports                                                                                                                                                                                                         |
| **Personality** | the mailroom's research clerk — files everything near everything it relates to, records the relationship itself                                                                                                                                                                                                                                                    |

The **relations layer** links associated topics, documents, and matters across the archive. It is the lawyer's research methodology as infrastructure. Its deterministic signals are all free:

* `same_matter`;
* keyword Jaccard (`topic_overlap`);
* shared parties (`party_overlap`);
* embedding cosine via the dojo's sentence-transformers model (`semantic_similarity`), computed ONCE per document and cached in `relation_embeddings`;
* a temporal evidence boost.

Edges live in `relation_edges`, with canonical endpoints, a closed six-type vocabulary, and a per-document cap. Every scan and every new edge is an entry in the layer's **own hash-chained ledger** (`relation_log`, `__relations__` scope). It follows the same tamper-evident law as the document audit; verify it with `python -m pipeline.relations_scan --verify-ledger`. Each document's own audit chain gains a `relations_linked` event.

The **LLM judgment pass** (`RelationsAgent.judge`, WIRED in HUB-051) reviews the scanner's top-`top_k_llm_candidates` **ambiguous-band** pairs. These are signals that suggest but do not clear a deterministic threshold: the near-miss set from the same scan. The pass returns typed judgments + rationale. A confidence gate (`llm_confidence_gate`, default 0.55) admits `llm_asserted` edges into the same upsert + ledger path as the deterministic ones. The scanner re-validates the agent's output against its OWN proposed pairs: closed vocabulary, pair normalization, and unproposed-pair refusal. It applies these checks twice, so nothing unvalidated reaches the ledger.

`relations.llm: false` keeps the pilot deterministic-only, which is compatible with the free-tier guardrail. To turn it on in production, edit the taxonomy, or use one of these:

* `python -m pipeline.relations_mode live [--model <name>] [--restart-watcher]`;
* the API's `POST /api/relations/mode` (HUB-052). The embedded watcher picks the flip up with no restart.

It is registered as `mailroom-relations` in `llm/prompts.py`.

**Consumption** (the longitudinal loop): a bounded, labeled advisory `RELATED` block rides the sorter/specialist handoff context and the Gmail completion echo. Later documents inherit everything the archive already knows.

**Knowledge graphs** (`python -m pipeline.relations_graph`) come in three kinds:

* matter graphs (typed doc nodes + related-matter bridges);
* the global inter-matter graph (edges aggregated to pair weights);
* document ego-graphs.

They export as GraphJSON + GraphML (stdlib, always) and Plotly HTML + PNG (optional deps, graceful skip) under `<base>/relations/graphs/`. Each export writes a `relations_graph_rendered` ledger event. The layer fails soft everywhere, and the document path never waits on it.

***

## Evaluating individual agents

Live Langfuse evaluators stay **pipeline-level** (`pipeline-result` generation, two independent judges) by design. To score one agent without running the 14-node graph, use the local isolation harness:

```bash
PYTHONPATH=src python src/scripts/run_agent_eval.py --list
PYTHONPATH=src python src/scripts/run_agent_eval.py --agent sorter --mock
PYTHONPATH=src python src/scripts/run_agent_eval.py --agent insurance_claims_specialist --mock --n 3
PYTHONPATH=src python src/scripts/run_agent_eval.py --agent all --mock --n 1 --self-check
```

`observability/agent_eval.py` loads labeled cases from test fixtures, local eval packs, and the live manifest. It invokes a single agent and scores it with the same deterministic classifiers and field scorers the pipeline uses. `prepare_samples.is_real_sample` gates `--real` (CUAD / LegalBench only). Synthetic insurance / corporate / correspondence samples are mock-only, matching `run_pilot.py`.

This is the methodology for iterating on a single specialist or the sorter without paying for a full document-pipeline run. It does **not** replace the live `mailroom-pipeline-judge` / `mailroom-pipeline-quality` evaluators.

***

## Adding a New Agent

1.  Define the extraction schema in `schemas/documents.py`:

    ```python
    class NewDocTypeExtraction(BaseModel):
        field_1: str = ""
        field_2: str | None = None
    ```
2. Register the schema in `EXTRACTION_SCHEMAS` dict.
3.  Create the agent in `agents/` with its prompt as a module-level template constant:

    ```python
    SYSTEM_PROMPT = """..."""
    class NewDocTypeSpecialist(BaseAgent):
        agent_name = "new_specialist"
        def system_prompt(self) -> str:
            text, self._langfuse_prompt = get_managed_prompt(self.agent_name, SYSTEM_PROMPT)
            return text
        def extract(self, doc_text: str) -> dict: ...
    ```
4. Add a dispatch entry in `graph/build_graph.py` under `extract_node` and `retry_extract_node`.
5. Add the agent config in `config/taxonomy.yaml` under both `doc_classes` and `agents` (with `max_tokens`).
6. Register the template in `llm/prompts.py:prompt_templates()` and sync: `PYTHONPATH=src python src/scripts/sync_prompts.py`
