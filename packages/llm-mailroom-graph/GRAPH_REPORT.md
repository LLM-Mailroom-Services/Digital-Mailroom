# Graph Report - llm-mailroom  (2026-09-13)

> Source: llm-mailroom @ `2a212e76a62b` (v0.7.1, mailroom-dataset v9 corpus pin 46a4d3c2) — extracted from the Digital-Mailroom monorepo checkout.
## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2373 nodes · 5700 edges · 156 communities (114 shown, 28 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 180 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2ba3a4ef`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 134
- Community 136
- Community 138
- Community 140
- Community 141
- Community 142
- Community 144
- Community 145
- Community 149
- Community 150
- Community 151
- Community 155

## God Nodes (most connected - your core abstractions)
1. `ensure_schema()` - 55 edges
2. `load_config()` - 50 edges
3. `async_session()` - 50 edges
4. `load_env()` - 46 edges
5. `BaseAgent` - 41 edges
6. `BaseAgent` - 39 edges
7. `get_managed_prompt()` - 34 edges
8. `build_graph()` - 33 edges
9. `setup_logging()` - 32 edges
10. `inbox_dir()` - 31 edges

## Surprising Connections (you probably didn't know these)
- `ops_sweep()` --uses--> `OpsMonitor`  [INFERRED]
  src/api/main.py → src/pipeline/ops_monitor.py
- `OpsMonitor` --uses--> `BossAgent`  [INFERRED]
  src/pipeline/ops_monitor.py → src/agents/boss.py
- `ArbiterAgent` --uses--> `BaseAgent`  [INFERRED]
  src/agents/arbiter.py → src/agents/base.py
- `BossAgent` --uses--> `BaseAgent`  [INFERRED]
  src/agents/boss.py → src/agents/base.py
- `ComplianceSpecialist` --uses--> `BaseAgent`  [INFERRED]
  src/agents/compliance_specialist.py → src/agents/base.py

## Import Cycles
- None detected.

## Communities (156 total, 28 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (61): Event, _move_rejected_to_failed(), Close the conveyor loop for a rejected review: move the file from the review…, _ensure_dirs(), classified_dir(), clear_ingestion_paused(), count_inbox_pending(), ensure_dirs() (+53 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (64): Message, accepted_extensions(), Accepted inbox file extensions from taxonomy.yaml (with defaults)., load_env(), build_echo_body(), build_echo_html(), deliver_attachment(), echoes_enabled() (+56 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (47): ArbiterAgent, BaseAgent, Judgment arbitration on failed judge verdicts., Decide the outcome for a judge-rejected extraction. Returns ``{decision,…, build_structured_schema(), BossAgent, BaseAgent, ComplianceSpecialist (+39 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (38): FakeLangChainLLM, _FakeStructuredRunner, is_classify_call(), MAILROOM-LOCAL (not from upstream): deterministic fake LangChain LLM. The…, Runnable returned by ``with_structured_output``: invoke() yields the…, Extract the human text from a LangChain message list, handling multimodal list…, Replacement for the ChatOpenAI instance the vendored agents construct. -…, user_text_from_messages() (+30 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (32): Read the upload-metadata sidecar for an inbox file (or None)., read_inbox_meta(), default_environment(), Assign `OBSERVABILITY_ENVIRONMENT` when nothing is set yet. Every entrypoint…, Inject an SMTP client factory (test/smoke seam). Pass None to reset., Snapshot of the Gmail intake channel state (safe for /health)., Inject an IMAP client factory (test/smoke seam). Pass None to reset., set_imap_factory() (+24 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (37): _clamp_extraction(), _deterministic_header_extraction(), extraction_schema_for(), GmailTriageAgent, _parse_model_json(), BaseAgent, Gmail intake triage agent — free-model single-document lane (HUB-037). The free…, Grounded, LLM-free best-effort header pass over short documents (HUB-049).… (+29 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (43): _catalog_by_trace(), completed_filenames(), enrich_sample_row(), expected_fields_for_sample(), expected_fields_meta(), finalize_report(), find_sample_text(), hf_corpus_honesty() (+35 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (33): build_new_rows(), check_contract(), clean_keywords(), clean_subject_matter(), _content_tokens(), fetch_config_rows(), head_tail_window(), labeler_prompt() (+25 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (26): BaseAgent, Sorter Reviewer agent — Lane A second-opinion classification (KANBAN-062).…, Independent second-opinion classifier (blind re-classification)., Independently classify the document. Returns ``{doc_type, contract_subtype,…, SorterReviewerAgent, KANBAN-062 (Lane A): independent agent second opinion on a medium-band…, review_classify_node(), build_structured_schema() (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.15
Nodes (32): DocumentRecord, get_document(), get_documents_by_stage(), get_error_rate_by_doc_type(), get_matter_documents(), get_recent_documents(), get_stuck_documents(), list_documents() (+24 more)

### Community 10 - "Community 10"
Cohesion: 0.10
Nodes (32): client_kwargs(), flush_langfuse(), get_trace_id(), install_on_dropped(), instrument_openai_client(), observation(), _optional_float(), _optional_int() (+24 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (32): _archived_docs(), _catalog_doc(), _cosine(), _doc_text(), _embed(), embedding_model_name(), embeddings_enabled(), _extracted() (+24 more)

### Community 12 - "Community 12"
Cohesion: 0.16
Nodes (31): date, main(), Namespace, _run(), audit_to_row(), daily_audit_path(), daily_documents_path(), document_to_row() (+23 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (31): ensure_field_score_configs(), ExtractionScoreResult, Wire deterministic field scoring into Langfuse (GitHub issue #5). The scoring…, Idempotent: register the field-scoring configs in the Langfuse project. The…, Score one extraction deterministically and push every score to Langfuse,…, score_and_log_extraction(), _client(), create_trace_score() (+23 more)

### Community 14 - "Community 14"
Cohesion: 0.14
Nodes (29): as_clause_lines(), enrich_contract_extraction(), flatten_cuad_clause_labels(), flatten_maud_clause_labels(), infer_merger_consideration(), normalize_consideration(), parse_json_obj(), Any (+21 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (29): DataFrame, cache_dir(), _cached_get_bytes(), dataset_sha(), _http_get_bytes(), _http_get_json(), load_config_frame(), load_corpus() (+21 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (26): _prompt_versions(), Prompt versions bound during the run (best-effort; Langfuse-managed prompts…, _append(), _build_versions(), Docclass prompt variants for every mailroom classification-chain role.…, Pure-appended docclass variant: base is a STRICT PREFIX of the result., Derive every variant from the live production template of that role., # NOTE: fragment assertions in tests target SHORT substrings that do not cross (+18 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (29): after_report(), Route after procedural matter-record assembly. The reporter LLM is retired;…, Ordered extraction-schema field names used as scoring labels., schema_fields(), align_class(), _as_float(), class_misses_ground_truth(), collect_review_causes() (+21 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (28): get_relations_mode(), Relations clerk mode readout (HUB-052) — the effective live/pilot posture plus…, free_only_enabled(), Whether the free-only LLM guardrail is on (``MAILROOM_LLM_FREE_ONLY``). Opt-in…, clear_config_cache(), Drop the cached taxonomy + the bins module-level copy (HUB-052). The mode…, _drop_env_kill_switch(), _edit_taxonomy() (+20 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (28): after_arbiter(), after_boss(), after_classify(), after_extraction(), after_extraction_gated(), after_human_review(), after_judge(), after_retry_classify() (+20 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (28): clause_handoff(), Additive specialist instructions listing every CUAD / MAUD inventory., skip_conflict_field(), _compact(), enrich_extraction(), _normalize(), normalize_claim_type(), normalize_communication_type() (+20 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (27): _all_edges(), _catalog_meta(), _circular_positions(), _ego_graph(), _global_graph(), graph_data(), graphs_dir(), graphs_enabled() (+19 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (16): ChatOpenAI, BaseAgent, _is_retryable_error(), ABC, Exception, Lazily build the LangChain ``ChatOpenAI`` client. Uses the OpenRouter base URL…, Call ``fn()`` retrying transient failures with backoff + jitter. Mirrors…, True when this agent's model accepts image input. Vision capability is config-… (+8 more)

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (15): ImageExtractor, BaseAgent, Path, Image extraction agent — uses vision-capable LLMs to extract text from images.…, PDFTranscriber, BaseAgent, Path, PDF transcription agent — converts PDF documents to markdown for downstream… (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.11
Nodes (26): _build_handoff_context(), _build_specialist_dispatch(), _detect_conflict(), _enrich_contract_result(), _extract_dispatch_key(), extract_node(), _norm_str(), _normalized_compare() (+18 more)

### Community 25 - "Community 25"
Cohesion: 0.11
Nodes (24): Seconds since the watcher last beat, or None when no heartbeat exists. A…, watcher_heartbeat_age(), Watcher status notifications (HUB-050). A dead process cannot email anyone, so…, Send one concise stylized status email. Fail-soft: logs and returns False on…, Inject an SMTP client factory (test/smoke seam). Pass None to reset., Kill-switch (``MAILROOM_WATCHER_STATUS``): off disables every status email and…, The human's status inbox (``MAILROOM_STATUS_EMAIL``)., Gmail channel SMTP settings (the same account the echoes send from). (+16 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (24): _escape(), generate_pdf_from_text(), is_real_sample(), _load_manifest(), prepare_samples(), Path, True when a manifest row is a real committed legal document. Real samples are…, Materialize every manifest row under data/samples/. Returns its path. (+16 more)

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (22): ArgumentParser, build_parser(), main(), LegalBench suite CLI. Run a LegalBench task, trace it to Langfuse, and log the…, build_record(), One experiment-log record in the upstream schema (see the JSONL header of…, LegalBench evaluation suite — a second lens on model quality. The suite runs…, log_run() (+14 more)

### Community 28 - "Community 28"
Cohesion: 0.15
Nodes (22): Append a hash-chained audit entry for a human review decision. Awaited from the…, _write_review_audit_entry(), _load_audit_rows(), Audit chain rows + hash-chain verdict for the echo body (best-effort)., AuditLogEntry, build_audit_entry(), compute_audit_hash(), compute_audit_hash_v1() (+14 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (23): DeclarativeBase, Base, get_latest_relation_hash(), get_relation_chain(), _latest_ledger_row(), _monotonic_timestamp(), normalize_edge(), put_embedding() (+15 more)

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (21): OpenAI, _check_llm_provider(), Best-effort LLM provider connectivity check. Resolves the provider for the…, assert_free_model(), get_llm(), get_llm_client(), get_llm_model(), instrument_client() (+13 more)

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (23): _articles(), _clean_ws(), _companies(), extract_compliance_fields(), extract_contract_fields(), extract_corporate_fields(), extract_correspondence_fields(), extract_insurance_fields() (+15 more)

### Community 32 - "Community 32"
Cohesion: 0.16
Nodes (22): is_free_model(), The free-model predicate (shared by the guardrail and the failover swarm): a…, _free_swarm(), _is_json_mode_400(), _is_modal_url(), _is_model_capability_error(), _is_retryable(), is_transient_error() (+14 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (22): apply_intake(), Normalize ``text`` and emit the ``normalize-intake`` span. Returns…, _extract_text_from_docx(), _extract_text_from_image(), _extract_text_from_pdf(), _file_sha256(), _file_size(), intake_node() (+14 more)

### Community 34 - "Community 34"
Cohesion: 0.16
Nodes (21): _build_evaluator_request(), _build_output_definition(), _build_rule_request(), _client(), _current_evaluator_prompt(), _ensure_llm_connection(), _existing_rule_ids(), main() (+13 more)

### Community 35 - "Community 35"
Cohesion: 0.15
Nodes (16): RotatingFileHandler, Structured logging setup for Mailroom entrypoints. Configures `structlog` once…, Structlog processor that emits the rendered event dict to a rotating stdlib…, _RotatingFileSink, setup_logging(), _base_env(), main(), run_config() (+8 more)

### Community 36 - "Community 36"
Cohesion: 0.16
Nodes (20): _parse_resolve_payload(), Accept JSON (The-Mailroom proxy) or form-urlencoded (legacy clients). The-…, all_specialist_schema_keys(), apply_classification_override(), coerce_extracted_data(), complete_human_extraction(), live_doc_types(), normalize_optional_str() (+12 more)

### Community 37 - "Community 37"
Cohesion: 0.15
Nodes (20): Dojo per-class sorter catalog (empty for unknown / retired types)., Catalog keys the classification guard accepts for ``doc_subclass``. Contract…, sorter_subclass_catalog(), valid_sorter_subclasses(), finalize_sorter_result(), Normalize sorter JSON: CUAD ``contract_subtype`` + per-class ``doc_subclass``.…, apply_classification_guard(), apply_extraction_guard() (+12 more)

### Community 38 - "Community 38"
Cohesion: 0.16
Nodes (20): _denial_reasons(), determination_consistency_is_quality(), honesty_trace_metadata(), insurance_determination_consistent(), insurance_determination_issues(), insurance_expected_set_is_homogeneous(), insurance_gt_is_homogeneous(), _norm_determination() (+12 more)

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (20): _contracts_from_annotations(), _contracts_from_txt(), _download(), download_all(), _list_hf_files(), _load_subtype_taxonomy(), main(), _normalize_category() (+12 more)

### Community 40 - "Community 40"
Cohesion: 0.17
Nodes (19): FastAPI, _check_database(), _embed_watcher_running(), health(), lifespan(), ops_status(), Best-effort database connectivity check (SQLite or Postgres)., flush_health() (+11 more)

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (13): get_prompt(), list_prompts(), PROMPT_TEMPLATES(), Get a prompt by version name. Args: version: Prompt version key (e.g.,…, List all available prompt versions., Return all prompt templates as a dict. Single source of truth for…, ComplianceFilingSpecialist, CorporateRecordsSpecialist (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (12): get_specialist(), normalize_extraction(), BaseAgent, Shared extract() implementation over a per-class schema., Extract a long document in overlapping chunks and merge the passes. Documents…, Sum per-chunk usage dicts (prompt/completion/total tokens, cost)., Paragraph-aware chunking with a trailing overlap window. Paragraphs…, Union the per-chunk extractions into one composite output. List fields union… (+4 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (19): agent_uses_vision(), _any_specialist_uses_vision(), is_vision_capable(), max_pages(), pipeline_uses_vision(), Path, Vision-capable model helpers for the mailroom pipeline. Some input agents (e.g.…, Render pages of a PDF to a list of PNG image data-URIs. `cap` is the page… (+11 more)

### Community 44 - "Community 44"
Cohesion: 0.17
Nodes (19): build_expected_fields(), Catalog labels + post-hoc fills. Hub / explicit values are never overwritten., dedicated_suite(), field_types_for_class(), gt_schema_coverage(), list_dedicated_suites(), Any, Dedicated scoring suite for every live mailroom specialist. Dojo… (+11 more)

### Community 45 - "Community 45"
Cohesion: 0.19
Nodes (19): active_corpus(), adapt_hub_row(), example_for_class(), example_rows(), examples_by_class(), hub_sample(), load_example_pack(), pipeline_corpora() (+11 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (19): _attach_field_scoring(), diff_report(), filter_real_samples(), _ground_truth_scores(), _ingest_scores(), main(), misfile_candidates(), _parse_expected_fields() (+11 more)

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (18): CompletedProcess, append_record(), default_log_path(), default_sibling_root(), git_snapshot(), _inside(), Any, Path (+10 more)

### Community 48 - "Community 48"
Cohesion: 0.13
Nodes (12): CorrespondenceSpecialist, BaseAgent, InsuranceClaimsSpecialist, BaseAgent, get_extraction_schema(), Return the extraction JSON schema for a doc type (None if unknown)., enrich_insurance_from_text(), normalize_specialist_extraction() (+4 more)

### Community 49 - "Community 49"
Cohesion: 0.16
Nodes (19): archive_node(), _catalog_upsert(), catalog_write_node(), _finalize_aborted(), human_review_node(), _lane_b_manifest_fields(), _maybe_export_warehouse(), Any (+11 more)

### Community 50 - "Community 50"
Cohesion: 0.18
Nodes (6): BaseAgent, ABC, True when this agent's model accepts image input and (optionally) page images…, Build the user-message content for a document input. Vision-capable models get…, Domain skill files appended below the managed prompt (Langfuse prompt linking…, Truncate document text to the agent's configured input budget, marking the…

### Community 51 - "Community 51"
Cohesion: 0.14
Nodes (15): classify_image(), clean_prediction(), extract_confidence(), extract_reasoning(), extract_runner_up(), Path, Extract the model's self-reported confidence (0-1) from a response., Classify a document image using a vision model through OpenRouter API. Args:… (+7 more)

### Community 52 - "Community 52"
Cohesion: 0.15
Nodes (17): CorpusUnavailable, _fingerprint(), load_cuad_qa(), load_family_rows(), _normalize_prediction(), Any, Path, RuntimeError (+9 more)

### Community 53 - "Community 53"
Cohesion: 0.16
Nodes (17): braintrust_observation(), braintrust_pipeline_trace(), configure(), _event_metadata(), flush_braintrust(), instrument_openai_client(), _is_braintrust_available(), is_configured() (+9 more)

### Community 54 - "Community 54"
Cohesion: 0.17
Nodes (16): pipeline_trace(), Root chain observation for one document run (one trace per document). See…, claim_file(), _finalize_claimed_on_error(), _intake_context(), _intake_meta_from_sidecar(), _is_already_processed(), _is_triage_route() (+8 more)

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (16): AsyncSession, _apply_sqlite_pragmas(), check_connectivity(), close_db(), _engine_kwargs(), _ensure_models_imported(), get_engine(), get_session() (+8 more)

### Community 56 - "Community 56"
Cohesion: 0.17
Nodes (16): _bounded(), Node wrapper enforcing the per-run hard cutoff: wall-clock deadline and…, compute_run_metrics(), Core per-run metrics, computed for EVERY finished run regardless of the tracing…, check_token_budget(), estimate_cost(), get_call_timeout_seconds(), get_deadline_seconds() (+8 more)

### Community 57 - "Community 57"
Cohesion: 0.18
Nodes (13): AgentTool, _build_toolkit(), get_tools(), Per-agent TOOL registry for the vendored LangChain agents. Each designated…, Return the agent's toolkit (built once, cached)., Render the agent's tool descriptions as a prompt appendix so the model knows…, render_tools(), _tool_field_types() (+5 more)

### Community 58 - "Community 58"
Cohesion: 0.15
Nodes (15): bool_env(), get_env(), load_env(), Load ``braintrust.env`` then ``.env`` into the environment (idempotent).…, Validate that all given environment variables are set and non-empty. Returns…, Get an environment variable with a default fallback., Get a boolean environment variable., require_env() (+7 more)

### Community 59 - "Community 59"
Cohesion: 0.28
Nodes (16): all_local_pack_samples(), compliance_local_samples(), corporate_extraction_samples(), _hydrate(), insurance_contrast_samples(), local_pack_status(), _mean(), _perfect_extract_summary() (+8 more)

### Community 60 - "Community 60"
Cohesion: 0.16
Nodes (15): arbiter_node(), _build_checkpointer(), build_graph(), _clean_fields_for_judge(), compile_report_node(), get_compiled_graph(), judge_verify_node(), Drop pipeline metadata keys before judge/arbiter input (mirrors the… (+7 more)

### Community 61 - "Community 61"
Cohesion: 0.13
Nodes (16): dataset_trace_metadata(), _emit_pipeline_result(), _execute_run(), _persist_provenance(), _public_ground_truth(), A-10: persist doc → run → model → prompt → cost → latency provenance. The audit…, Trace-safe ground truth (no expected_fields payloads / document text). The-…, Emit the single `pipeline-result` generation observation per document. This is… (+8 more)

### Community 62 - "Community 62"
Cohesion: 0.14
Nodes (9): LegalBenchAgent, Any, BaseAgent, Model agent for LegalBench runs. Reuses the vendored ``BaseAgent`` machinery —…, One agent instance per task run; answers via structured JSON., LegalBench tasks use the task prompt as-is (no sorter skills)., Yes/no answer with evidence + confidence., One-of-N family classification with confidence. (+1 more)

### Community 63 - "Community 63"
Cohesion: 0.19
Nodes (12): BaseException, classify_run_failure(), failure_audit_detail(), Any, Classify pipeline crashes so aborted runs are distinguishable. ``run_pipeline``…, Return ``failure_class``, ``reason``, and ``detail`` for an abort., _status_code(), Exception (+4 more)

### Community 64 - "Community 64"
Cohesion: 0.18
Nodes (13): Enum, document_source(), Parked / bin document text or original bytes (The-Mailroom PR #20). Default:…, _extract_source_text(), guess_content_type(), locate_document_file(), Path, Best-effort locate the on-disk file for a manifest across bins. (+5 more)

### Community 65 - "Community 65"
Cohesion: 0.15
Nodes (15): get, analyze_audit_database(), _document_payload_from_manifest(), get_matter(), get_queue(), lookup_document_endpoint(), Parse and summarize the full local audit DB (catalog companion). Returns…, Live view of the inbox → processing queue. The inbox bin IS the queue: files… (+7 more)

### Community 66 - "Community 66"
Cohesion: 0.15
Nodes (15): boss_escalation_node(), _emit_stage_audit(), _fetch_matter_context(), _latest_audit_hash(), _persist_scores(), Best-effort fetch of archived matter records for the Boss / conflict detection.…, Run a coroutine from a sync context: schedule it on the running loop when one…, Best-effort fetch of the last entry_hash for this doc_id (the previous link of… (+7 more)

### Community 67 - "Community 67"
Cohesion: 0.17
Nodes (15): _chunk_config(), _extract_compliance(), _extract_contracts(), _extract_corporate_records(), _extract_correspondence(), _extract_insurance_claims(), _instantiate_specialist(), Name → extract function. Keys MUST match taxonomy ``specialist:`` values. (+7 more)

### Community 69 - "Community 69"
Cohesion: 0.22
Nodes (14): attach_single_doc_extras(), _numeric_extra(), Any, ExtractionScoreResult, Dedicated specialist scoring suites from llm-dojo-scoring 0.11.0.…, Score one document with the dedicated specialist suite. Falls back to…, Score cleaned intake output against the deterministic clerk gold. Returns the…, Attach intake-suite scores to the active trace (no-op when tracing is off). (+6 more)

### Community 70 - "Community 70"
Cohesion: 0.20
Nodes (14): main(), _perturb_date(), _perturb_entity_list(), _perturb_free_text(), _perturb_money(), _perturb_name(), _predictions_for(), Random (+6 more)

### Community 71 - "Community 71"
Cohesion: 0.28
Nodes (14): _api(), check_payload(), _die(), main(), publish(), Namespace, Path, Validate the Space card + Docker payload. Returns human-readable notes. (+6 more)

### Community 72 - "Community 72"
Cohesion: 0.24
Nodes (7): FileSystemEventHandler, InboxHandler, _infer_matter_id(), Path, Matter id for an inbox file: meta sidecar > parent folder > name suffix. Upload…, Only processable documents enter the conveyor. Without this filter, watchdog…, Debounced claim for created / modified / moved-into-inbox events.…

### Community 73 - "Community 73"
Cohesion: 0.18
Nodes (10): _LangChainSorterAgent, Split ``text`` into overlapping windows, preserving EVERY character. Paragraph-…, sliding_windows(), _merge_sorter_reads(), Sorter agent — LangChain version vendored from llm-entity-extraction. Re-…, Merge per-window classification reads (deterministic, no truncation). -…, Mailroom-configured sorter. - Model/budget defaults come from ``taxonomy.yaml``…, Classify a document, optionally with page images attached. Returns ``(doc_type,… (+2 more)

### Community 74 - "Community 74"
Cohesion: 0.21
Nodes (13): archive_document(), _file_sha256(), Path, Best-effort sha256 of the archived file (audit A-7)., archive_dir(), move_to_archive(), Move a file to the archive with a collision-safe name (audit A-20). POSIX…, _file_sha256() (+5 more)

### Community 75 - "Community 75"
Cohesion: 0.29
Nodes (10): LLM-as-a-judge that evaluates extraction completeness against the source…, ComplianceFilingExtraction, ContractExtraction, CorporateRecordExtraction, CorrespondenceExtraction, get_extraction_schema(), InsuranceClaimExtraction, BaseModel (+2 more)

### Community 76 - "Community 76"
Cohesion: 0.19
Nodes (10): BaseAgent, Relations agent — LLM judgment pass over relation candidates (HUB-040). The…, Full I/O capture for one judgment call (fail-soft): system prompt, user…, Judge candidate pairs. Input: deterministic candidates ( dicts with…, Clamp the model's answer: closed type vocabulary, 0.0-1.0 confidence, bounded…, RelationsAgent, validate_judgments(), _write_judgment_debug() (+2 more)

### Community 77 - "Community 77"
Cohesion: 0.25
Nodes (13): equivalent_subtypes(), Return True when two subtype keys are the same family or members of the same…, _binary_f1(), _ece(), _mean(), Any, Deterministic scoring for LegalBench runs — every number computed locally. No…, Expected calibration error over confidence/outcome pairs. (+5 more)

### Community 78 - "Community 78"
Cohesion: 0.18
Nodes (9): _build_manifest_index(), _get_manifest_index(), RuntimeError, Re-queue (or retire) processing/<worker_id>/ files orphaned by a crashed…, Build ``{filename: {delivery_key: stage}}`` from all terminal manifests. A…, Return the cached manifest index, rebuilding if stale., Another watcher already holds ``watcher.lock`` (or this process already…, Watcher (+1 more)

### Community 79 - "Community 79"
Cohesion: 0.29
Nodes (13): _client(), _existing_placements(), json_dumps(), main(), _placement_kwargs(), # NOTE: dimension on `model` (the requested model string, e.g., _score_widget(), _spec_to_request() (+5 more)

### Community 80 - "Community 80"
Cohesion: 0.18
Nodes (8): Arbiter agent — Lane B judgment arbitration (KANBAN-063). Architecture…, CorporateRecordsSpecialist, BaseAgent, _block(), classification_doctrine(), extraction_doctrine(), Production pipeline doctrine appended onto frozen predecessor prompts. Each…, Shared extraction closer for specialist SYSTEM_PROMPT mutations.

### Community 81 - "Community 81"
Cohesion: 0.23
Nodes (12): format_intake_prior(), Render the advisory intake read as the sorter's prior block. Labeled advisory —…, classify_node(), _existing_processing_doc_id(), _normalize_review_decision(), _paused_review_result(), Map a Command(resume=...) payload to approved/rejected, or None if invalid., Normalize an ``interrupt()`` pause into a review-bin pipeline result. The node… (+4 more)

### Community 82 - "Community 82"
Cohesion: 0.19
Nodes (11): attach_run_scores(), ensure_score_configs_if_enabled(), _environment(), legalbench_trace(), Any, question_observation(), Langfuse tracing for LegalBench runs. One trace per run (deterministic seed =…, Open the per-run Langfuse trace (no-op when tracing is disabled). (+3 more)

### Community 83 - "Community 83"
Cohesion: 0.26
Nodes (11): _memory_dir(), _memory_path(), Path, Per-agent OUTCOME MEMORY for the vendored LangChain agents. Every designated…, Count outcomes by source and by feedback keyword (for observability)., Append one outcome row to the agent's ledger (best-effort)., Render the last ``k`` outcomes for this agent+doc_type as a prompt appendix —…, recent_context() (+3 more)

### Community 84 - "Community 84"
Cohesion: 0.24
Nodes (11): _date_pair_days(), extraction_diagnostics(), _mean(), _median(), parse_duration_days(), _r2(), Run-level diagnostic metrics for extraction scoring. Ported from ``llm-entity-…, Coefficient of determination ``1 - SS_res/SS_tot`` over (predicted, expected)… (+3 more)

### Community 85 - "Community 85"
Cohesion: 0.21
Nodes (11): Warm the score-config schema OFF the document path (O-1).…, warmup_score_configs(), Whether the single-document Gmail triage lane is on (default: with the…, triage_enabled(), _code_sha(), _gmail_intake_line(), Short HEAD sha (once, fail-soft) so status emails name the running code., Operator-readable heartbeat payload (readers depend only on `ts`). (+3 more)

### Community 86 - "Community 86"
Cohesion: 0.18
Nodes (11): Request, active_api_tokens(), assert_bind_allowed(), _csv_tokens(), listen_host(), _platform_hint(), Bind host for ``python -m api.main`` (default loopback)., Refuse off-loopback binds without a live bearer token (audit L-2). (+3 more)

### Community 87 - "Community 87"
Cohesion: 0.27
Nodes (5): _hash(), MockLegalBenchModel, Any, Deterministic mock model for LegalBench runs (no network, no OpenAI). Answers…, Implements the LegalBenchAgent interface deterministically.

### Community 88 - "Community 88"
Cohesion: 0.29
Nodes (10): bootstrap_ci(), _clean(), delta_significance(), Any, Random, Bootstrap confidence intervals and small-sample delta testing. Ported verbatim…, Coerce a per-document score list to floats, dropping None/non-numeric., Percentile-bootstrap 95% CI over per-document scores. Returns ``{"lo", "hi",… (+2 more)

### Community 89 - "Community 89"
Cohesion: 0.25
Nodes (10): _init_opentelemetry(), _instrument_openai(), instrument_openai_client(), is_configured(), phoenix_enabled(), Arize Phoenix tracing backend — local, cost-free default for llm-mailroom.…, Return ``client`` with Phoenix auto-tracing activated (no-op if disabled).…, Return True when Phoenix tracing should be active (default: enabled). (+2 more)

### Community 90 - "Community 90"
Cohesion: 0.47
Nodes (10): apply_pin(), _bare(), current_pin(), _github_headers(), latest_release_tag(), main(), _normalize_tag(), Path (+2 more)

### Community 91 - "Community 91"
Cohesion: 0.33
Nodes (10): _caption_from_text(), _download(), fetch_atticus(), fetch_legalbench(), fetch_pileoflaw(), main(), Path, Yield (record, url) for courtlistener opinions, streaming + aborting early per… (+2 more)

### Community 92 - "Community 92"
Cohesion: 0.33
Nodes (10): _client(), main(), _parse_since(), datetime, Path, Poll a trace's scores until they arrive or the timeout elapses. LLM-as-a-judge…, sync_logs(), _trace_basics() (+2 more)

### Community 93 - "Community 93"
Cohesion: 0.20
Nodes (10): post, ops_resume(), ops_sweep(), _rate_limit_upload(), Run a one-off Boss ops-monitor sweep on demand. Mirrors the scheduled…, Clear the ingestion-pause flag so the watcher resumes processing. The ops…, Queue a file into the inbox (The-Mailroom PR #30 Inbox proxy). The Observatory…, Sliding-window rate limit for /upload (audit L-18). (+2 more)

### Community 94 - "Community 94"
Cohesion: 0.20
Nodes (9): build, builder, dockerfilePath, deploy, healthcheckPath, healthcheckTimeout, restartPolicyMaxRetries, restartPolicyType (+1 more)

### Community 95 - "Community 95"
Cohesion: 0.24
Nodes (5): _extract_family(), _family_labels(), get_task(), LegalBenchTask, LegalBench task registry. Two task families, per the LegalBench taxonomy: -…

### Community 96 - "Community 96"
Cohesion: 0.22
Nodes (9): _apply_taxonomy_settings(), field_is_ambiguous(), get_type_bands(), DEPRECATED shim — the field-scoring implementation moved to the package. As of…, Per-field-type ambiguous-band overrides from ``field_scoring.type_bands``.…, Is this field score in the (possibly type-specific) ambiguous band? Band check…, Load the embedding model OFF the document path (O-10). The first grounded run…, Map ``config/taxonomy.yaml`` ``field_scoring:`` onto package Settings. Best-… (+1 more)

### Community 97 - "Community 97"
Cohesion: 0.40
Nodes (9): cutover_agent(), cutover_all(), list_agents(), list_local_models(), load_config(), main(), recommend_cutover_order(), save_config() (+1 more)

### Community 98 - "Community 98"
Cohesion: 0.25
Nodes (5): _LangChainContractsSpecialist, ContractsSpecialist, Contracts specialist — LangChain version vendored from llm-entity-extraction.…, Mailroom-configured contracts specialist. - Model/budget defaults come from…, ContractsSpecialist

### Community 99 - "Community 99"
Cohesion: 0.25
Nodes (9): get_audit_trail(), get_document_status(), Reject unvalidated identifiers before they reach manifest paths (L-21)., Resolve a REVIEW / RECONSIDER item (The-Mailroom PR #18 / #20). Body (JSON or…, resolve_review(), _validate_doc_id(), load_manifest(), copy_to_inbox() (+1 more)

### Community 101 - "Community 101"
Cohesion: 0.28
Nodes (9): context_block(), context_injection_enabled(), llm_pass_enabled(), Effective ``relations:`` block from taxonomy.yaml with defaults., Kill-switch for the whole layer: taxonomy ``relations.enabled`` AND the…, The LLM judgment pass is opt-in via taxonomy ``relations.llm`` (OFF in the…, Bounded, advisory RELATED block for agent prompts / the echo. Empty string when…, relations_config() (+1 more)

### Community 102 - "Community 102"
Cohesion: 0.31
Nodes (8): main(), _print_human(), Namespace, _run(), analyze_audit_db(), list_audit_doc_ids(), Every doc_id that has at least one audit entry (ordered)., Parse the full local audit DB into summary stats for operators. Returns counts…

### Community 103 - "Community 103"
Cohesion: 0.31
Nodes (9): load_ground_truth_labels(), load_hf_rows(), _paginate_viewer(), ``max_scan <= 0`` means unlimited (do not use on the 247k Enron set)., Map filename → {expected, expected_subclass} from config=ground_truth. These…, Load default-config text rows joined to ground_truth labels on filename., _scan_cap(), _take_rows() (+1 more)

### Community 104 - "Community 104"
Cohesion: 0.42
Nodes (8): build_report(), _clean_extracted(), _field_score_for(), _fmt_usd(), _json_block(), _load_config(), main(), _manifest_rows()

### Community 105 - "Community 105"
Cohesion: 0.39
Nodes (7): classes_match(), normalize_class(), Any, Classification KPIs after ``merger_agreement`` became a live MAUD class. Dojo…, True when predicted equals expected. MAUD is not CUAD., Run-level exact accuracy. ``aligned_*`` keys equal exact (deprecated)., score_exact_classification()

### Community 107 - "Community 107"
Cohesion: 0.25
Nodes (5): Background archive sweep; daemon thread, one sweep per interval., Start the sweeper inside the watcher process (enabled-only, never raises) — the…, RelationsSweeper, start_embedded_relations_scanner(), stop_embedded_relations_scanner()

### Community 108 - "Community 108"
Cohesion: 0.39
Nodes (6): _json(), main(), offline_pins(), probe(), Any, Return a structured probe of both hosted Spaces.

### Community 109 - "Community 109"
Cohesion: 0.38
Nodes (6): docclass_prompts_enabled(), langchain_prompt_version(), managed_prompt_lookup(), Opt-in KANBAN-090 docclass prompt arm at runtime. Production agent prompts stay…, Rewrite a LangChain prompt key to its docclass variant when enabled., Return (Langfuse agent_name, fallback text) for BaseAgent prompts. When the…

### Community 110 - "Community 110"
Cohesion: 0.29
Nodes (7): _check_cost_watchdog(), _fetch_openrouter_prices(), _price_for(), Warn at $0.15, abort the run at $0.20 (cumulative across all samples)., Mirror _wrap_client's usage/cost accounting for a LangChain response., Fetch live OpenRouter pricing (per-token), normalized to $/M tokens. The…, _record_langchain_response()

### Community 111 - "Community 111"
Cohesion: 0.40
Nodes (5): family_classification_prompt_v1(), get_prompt(), Versioned LegalBench task prompts. Prompt version = experiment identity in the…, Fill the 25-family list into the multiclass prompt (called per run so the…, Resolve a prompt version to its system-prompt text.

### Community 113 - "Community 113"
Cohesion: 0.33
Nodes (4): acquire_watcher_lock(), Exclusive file lock so the API-embedded watcher and ``python -m…, Non-blocking exclusive lock on ``<MAILROOM_BASE_DIR>/watcher.lock``. Returns…, _WatcherLock

### Community 114 - "Community 114"
Cohesion: 0.60
Nodes (5): _aggregate(), _cell(), main(), _print_table(), _scores_of()

### Community 116 - "Community 116"
Cohesion: 0.40
Nodes (3): load_skills(), Per-agent SKILL FILES for the vendored LangChain agents. Each designated agent…, Return the agent's skill files as an appended prompt section. ``max_chars``…

### Community 117 - "Community 117"
Cohesion: 0.50
Nodes (4): post_relations_mode(), BaseModel, Flip the relations clerk mode (HUB-052) — pilot (deterministic-only) or live…, RelationsModeRequest

### Community 118 - "Community 118"
Cohesion: 0.50
Nodes (4): _direct_pdf_text(), Deterministic PDF text extraction (pdfplumber → pypdf fallback). NEVER invokes…, Deterministic, LLM-free pre-check: can the free triage team handle this…, _triage_capability_check()

## Knowledge Gaps
- **8 isolated node(s):** `mailroom`, `builder`, `dockerfilePath`, `healthcheckPath`, `healthcheckTimeout` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 873 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_env()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 11`, `Community 140`, `Community 12`, `Community 15`, `Community 16`, `Community 21`, `Community 25`, `Community 26`, `Community 28`, `Community 30`, `Community 34`, `Community 35`, `Community 39`, `Community 40`, `Community 46`, `Community 70`, `Community 79`, `Community 85`, `Community 92`, `Community 101`, `Community 102`, `Community 107`, `Community 114`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `load_config()` connect `Community 30` to `Community 0`, `Community 2`, `Community 5`, `Community 8`, `Community 11`, `Community 13`, `Community 18`, `Community 23`, `Community 24`, `Community 32`, `Community 34`, `Community 35`, `Community 36`, `Community 40`, `Community 43`, `Community 56`, `Community 57`, `Community 67`, `Community 75`, `Community 81`, `Community 93`, `Community 96`, `Community 101`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `inbox_dir()` connect `Community 0` to `Community 65`, `Community 33`, `Community 1`, `Community 36`, `Community 99`, `Community 4`, `Community 6`, `Community 40`, `Community 72`, `Community 3`, `Community 78`, `Community 46`, `Community 81`, `Community 85`, `Community 93`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `BaseAgent` (e.g. with `ArbiterAgent` and `BossAgent`) actually correct?**
  _`BaseAgent` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `mailroom`, `builder`, `dockerfilePath` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06330988522769344 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.058823529411764705 - nodes in this community are weakly interconnected._