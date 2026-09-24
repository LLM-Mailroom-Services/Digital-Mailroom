import os


class TestValidateExtraction:
    def test_parse_error_flag(self):
        from observability.scores import validate_extraction

        result = validate_extraction("contract", {"_parse_error": True})
        assert result["parse_error"] is True
        assert result["schema_valid"] is False

    def test_valid_extraction(self):
        from observability.scores import validate_extraction

        result = validate_extraction(
            "contract",
            {
                "parties": ["ACME", "Zenith"],
                "effective_date": "2024-01-15",
                "term_length": "3 years",
                "cuad_clauses": ["uptime"],
                "governing_law": "Delaware",
                "contract_value": None,
                "renewal_terms": None,
            },
        )
        assert result["parse_error"] is False
        assert result["schema_valid"] is True

    def test_invalid_type_marks_schema_invalid(self):
        from observability.scores import validate_extraction

        # parties must be a list; a string should fail validation
        result = validate_extraction("contract", {"parties": "ACME"})
        assert result["schema_valid"] is False

    def test_unknown_doc_type_is_not_schema_valid(self):
        from observability.scores import validate_extraction

        result = validate_extraction("not_a_real_type", {"foo": 1})
        assert result["schema_valid"] is False
        result_unknown = validate_extraction("unknown", {"_unsupported": True})
        assert result_unknown["schema_valid"] is False

    def test_merger_agreement_validates_against_dedicated_schema(self):
        from observability.scores import validate_extraction

        result = validate_extraction(
            "merger_agreement",
            {
                "parties": ["Parent Inc.", "Target Corp."],
                "effective_date": "2024-06-01",
                "governing_law": "Delaware",
                "merger_consideration": "all_cash",
            },
        )
        assert result["parse_error"] is False
        assert result["schema_valid"] is True


class TestEmitPipelineScores:
    def test_scores_computed_when_tracing_disabled(self):
        # Scores are ALWAYS computed (persisted to the catalog even without a
        # tracing backend); only trace attachment is backend-gated.
        os.environ["OBSERVABILITY_PROVIDER"] = "none"
        try:
            from observability.scores import emit_pipeline_scores

            scores = emit_pipeline_scores(
                {
                    "doc_id": "d1",
                    "stage": "archived",
                    "doc_type": "contract",
                    "classification_confidence": 0.9,
                    "extracted_data": {"parties": ["A"]},
                },
                metrics={
                    "run_aborted": 0,
                    "run_duration_seconds": 1.5,
                    "total_tokens": 42,
                    "llm_call_count": 3,
                    "estimated_cost_usd": 0.001,
                    "classification_attempts": 1,
                    "extraction_attempts": 1,
                },
            )
            assert scores["stage_completed"] == 1
            assert scores["parse_error"] == 0
            assert scores["schema_valid"] == 1
            assert scores["classification_confidence"] == 0.9
            assert scores["run_aborted"] == 0
            assert scores["total_tokens"] == 42
            assert scores["llm_call_count"] == 3
            assert scores["estimated_cost_usd"] == 0.001
            assert scores["success_rate"] == 1
            assert "class_correct" not in scores
        finally:
            os.environ.pop("OBSERVABILITY_PROVIDER", None)


def test_bert_fast_path_scores_registered_in_dojo_registry():
    """KANBAN-061 integrity: every mailroom SCORE_CONFIGS name, including the
    #106 BERT fast-path set, resolves in the llm-dojo-scoring registry."""
    from llm_dojo_scoring import load_registry

    from observability.scores import SCORE_CONFIGS

    reg = load_registry()
    names = {c["name"] for c in SCORE_CONFIGS}
    bert_fast_path = {
        "bert_pass",
        "bert_sorter_agreement",
        "bert_fail_soft",
        "bert_elapsed_ms",
        "fast_path_est_cost_usd",
    }
    assert bert_fast_path <= names
    missing = [n for n in names if n not in reg.metrics]
    assert not missing, f"unregistered SCORE_CONFIGS names: {missing}"
    # mailroom-only names must be flagged as not computed upstream
    assert reg.get("bert_pass").source is None
    assert reg.get("bert_fail_soft").ground_truth == "none"


def test_bert_fast_path_score_types_and_wire_cap():
    from observability.scores import SCORE_CONFIGS, langfuse_score_name

    by_name = {c["name"]: c for c in SCORE_CONFIGS}
    assert by_name["bert_pass"]["data_type"] == "BOOLEAN"
    assert by_name["bert_sorter_agreement"]["data_type"] == "BOOLEAN"
    assert by_name["bert_fail_soft"]["data_type"] == "BOOLEAN"
    assert by_name["bert_elapsed_ms"]["data_type"] == "NUMERIC"
    assert by_name["fast_path_est_cost_usd"]["data_type"] == "NUMERIC"
    for name in by_name:
        assert len(langfuse_score_name(name)) <= 35, name


def test_estimate_fast_path_cost_usd_derived_distinct_from_llm_call_cost():
    """#106 non-conflation contract: the fast-path cost is a pure derivation
    of bert_elapsed_ms and never lands in estimated_cost_usd."""
    from observability.scores import (
        SCORE_CONFIGS,
        estimate_fast_path_cost_usd,
    )

    names = {c["name"] for c in SCORE_CONFIGS}
    assert "fast_path_est_cost_usd" in names
    assert "estimated_cost_usd" in names
    assert estimate_fast_path_cost_usd(0.0) == 0.0
    assert estimate_fast_path_cost_usd(-5.0) == 0.0
    # monotonic, energy-model-shaped: doubling wall-clock doubles the cost
    a = estimate_fast_path_cost_usd(100.0)
    b = estimate_fast_path_cost_usd(200.0)
    assert 0.0 < a < b
    assert b == round(2 * a, 10)


def test_langfuse_score_name_aliases_overlong_verified_precision():
    from observability.scores import langfuse_score_name

    assert langfuse_score_name("extraction_overall_verified_precision") == (
        "extraction_verified_precision"
    )
    assert langfuse_score_name("run_duration_seconds") == "run_duration_seconds"
    assert len("extraction_verified_precision") <= 35


def test_emit_pipeline_scores_class_correct_is_exact_not_aligned():
    os.environ["OBSERVABILITY_PROVIDER"] = "none"
    try:
        from observability.scores import emit_pipeline_scores

        hit = emit_pipeline_scores({
            "stage": "archived",
            "doc_type": "merger_agreement",
            "ground_truth": {"expected_hf_class": "merger_agreement"},
            "extracted_data": {"parties": ["A"]},
        })
        assert hit["class_correct"] == 1
        miss = emit_pipeline_scores({
            "stage": "archived",
            "doc_type": "contract",
            "ground_truth": {
                "expected_doc_class": "merger_agreement",
                "expected_hf_class": "merger_agreement",
            },
            "extracted_data": {"parties": ["A"]},
        })
        assert miss["class_correct"] == 0
    finally:
        os.environ.pop("OBSERVABILITY_PROVIDER", None)


class TestFirstPassSuccess:
    """Production STP: no ground truth, no reroute/reprocess."""

    def test_clean_archive_is_first_pass(self):
        from observability.scores import first_pass_success

        assert first_pass_success(
            {
                "stage": "archived",
                "classification_attempts": 1,
                "extraction_attempts": 1,
                "judge_verdict": "skipped",
            },
            {
                "stage_completed": 1,
                "schema_valid": 1,
                "parse_error": 0,
                "guardrail_triggered": 0,
                "run_aborted": 0,
            },
        ) is True

    def test_does_not_require_ground_truth(self):
        from observability.scores import emit_pipeline_scores
        import os

        os.environ["OBSERVABILITY_PROVIDER"] = "none"
        try:
            scores = emit_pipeline_scores(
                {
                    "stage": "archived",
                    "doc_type": "contract",
                    "classification_attempts": 1,
                    "extraction_attempts": 1,
                    "judge_verdict": "skipped",
                    "extracted_data": {
                        "parties": ["ACME", "Zenith"],
                        "effective_date": "2024-01-15",
                        "term_length": "3 years",
                        "cuad_clauses": ["uptime"],
                        "governing_law": "Delaware",
                    },
                }
            )
            assert "class_correct" not in scores
            assert scores["success_rate"] == 1
        finally:
            os.environ.pop("OBSERVABILITY_PROVIDER", None)

    def test_retry_is_not_first_pass(self):
        from observability.scores import first_pass_success

        assert first_pass_success(
            {
                "stage": "archived",
                "classification_attempts": 2,
                "extraction_attempts": 1,
            },
            {
                "stage_completed": 1,
                "schema_valid": 1,
                "parse_error": 0,
                "guardrail_triggered": 0,
            },
        ) is False

    def test_lane_a_review_is_not_first_pass(self):
        from observability.scores import first_pass_success

        assert first_pass_success(
            {
                "stage": "archived",
                "classification_attempts": 1,
                "extraction_attempts": 1,
                "review_verdict": "reviewer_agrees",
            },
            {
                "stage_completed": 1,
                "schema_valid": 1,
                "parse_error": 0,
                "guardrail_triggered": 0,
            },
        ) is False

    def test_human_review_and_abort_are_not_first_pass(self):
        from observability.scores import emit_pipeline_scores
        import os

        os.environ["OBSERVABILITY_PROVIDER"] = "none"
        try:
            reviewed = emit_pipeline_scores(
                {
                    "stage": "review",
                    "doc_type": "contract",
                    "review_decision": "pending_review",
                    "extracted_data": {"parties": ["A"]},
                },
                metrics={"classification_attempts": 1, "extraction_attempts": 1},
            )
            assert reviewed["success_rate"] == 0
            aborted = emit_pipeline_scores(
                {
                    "stage": "failed",
                    "run_aborted": True,
                    "extracted_data": {},
                },
                metrics={"run_aborted": 1},
            )
            assert aborted["success_rate"] == 0
            assert aborted["stage_completed"] == 0
        finally:
            os.environ.pop("OBSERVABILITY_PROVIDER", None)

    def test_guardrail_or_transient_retry_is_not_first_pass(self):
        from observability.scores import first_pass_success

        scores = {
            "stage_completed": 1,
            "schema_valid": 1,
            "parse_error": 0,
            "guardrail_triggered": 1,
        }
        assert first_pass_success(
            {
                "stage": "archived",
                "classification_attempts": 1,
                "extraction_attempts": 1,
                "classification_guardrail": ["unknown class"],
            },
            scores,
        ) is False
        assert first_pass_success(
            {
                "stage": "archived",
                "classification_attempts": 1,
                "extraction_attempts": 1,
                "transient_retries_classify": 1,
            },
            {
                "stage_completed": 1,
                "schema_valid": 1,
                "parse_error": 0,
                "guardrail_triggered": 0,
            },
        ) is False

    def test_gt_class_miss_does_not_define_the_flag(self):
        """Live traffic has no GT. A clean operational path still scores 1
        even when a later pilot label would have been a class miss."""
        from observability.scores import emit_pipeline_scores
        import os

        os.environ["OBSERVABILITY_PROVIDER"] = "none"
        try:
            scores = emit_pipeline_scores(
                {
                    "stage": "archived",
                    "doc_type": "contract",
                    "classification_attempts": 1,
                    "extraction_attempts": 1,
                    "judge_verdict": "skipped",
                    "extracted_data": {"parties": ["A"]},
                    "ground_truth": {"expected_doc_class": "correspondence"},
                }
            )
            assert scores["class_correct"] == 0
            assert scores["success_rate"] == 1
        finally:
            os.environ.pop("OBSERVABILITY_PROVIDER", None)

