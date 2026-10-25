"""Intake normalize mirror + pipeline eval scorer contract."""

from mailroom_ui.intake_normalize import deterministic_normalize, looks_messy
from mailroom_ui.pipeline_eval import aligned, classify_failure, score_rows


def test_empty_text_is_not_messy():
    cleaned, stats = deterministic_normalize("")
    assert cleaned == ""
    assert stats["changed"] is False
    assert looks_messy(cleaned, stats) is False


def test_normalize_is_idempotent():
    raw = "Hello   world.\r\n\r\n\r\nagree-\nment\n"
    once, _ = deterministic_normalize(raw)
    twice, stats = deterministic_normalize(once)
    assert once == twice
    assert stats["changed"] is False


def test_markdown_table_rows_keep_internal_spaces():
    raw = "| col  a | col  b |\n\n\nNext."
    cleaned, _ = deterministic_normalize(raw)
    assert "| col  a | col  b |" in cleaned


def test_normalize_collapses_and_unwraps():
    cleaned, stats = deterministic_normalize("A\u00a0B\n\n\n\nagree-\nment")
    assert "A B" in cleaned
    assert "agreement" in cleaned
    assert stats["changed"] is True
    assert looks_messy("x\n" * 30) is True
    clean, st = deterministic_normalize("Hello world.\n\n1. Clause.")
    assert looks_messy(clean, st) is False


def test_eval_scorer_exact_and_failures():
    rows = [
        {"expected": "contract", "predicted": "contract", "stage": "archived",
         "exact_ok": True, "aligned_ok": True},
        {"expected": "merger_agreement", "predicted": "merger_agreement", "stage": "archived",
         "exact_ok": True, "aligned_ok": True},
        {"expected": "merger_agreement", "predicted": "contract", "stage": "archived",
         "exact_ok": False, "aligned_ok": False},
        {"expected": "correspondence", "predicted": "contract", "stage": "archived",
         "exact_ok": False, "aligned_ok": False},
        {"expected": "corporate_record", "predicted": "corporate_record",
         "stage": "failed", "error": "extraction failed", "exact_ok": True, "aligned_ok": True},
    ]
    summary = score_rows(rows)
    assert summary["n"] == 5
    assert abs(summary["exact_accuracy"] - 0.6) < 1e-9
    assert abs(summary["aligned_accuracy"] - 0.6) < 1e-9
    assert classify_failure(rows[1]) == "ok"
    assert classify_failure(rows[2]) == "wrong_class"
    assert classify_failure(rows[3]) == "wrong_class"
    assert classify_failure(rows[4]) == "failed"
    assert aligned("merger_agreement", "merger_agreement")
    assert not aligned("merger_agreement", "contract")
    assert not aligned("correspondence", "contract")
    assert summary["confusion"]["merger_agreement"]["contract"] == 1
    assert summary["confusion"]["correspondence"]["contract"] == 1
    assert summary["subclass_accuracy"] is None
    assert summary["n_subclass"] == 0


def test_eval_subclass_accuracy_uses_contract_subtype():
    rows = [
        {"expected": "contract", "predicted": "contract", "stage": "archived",
         "exact_ok": True, "aligned_ok": True,
         "expected_subclass": "license", "contract_subtype": "license"},
        {"expected": "compliance_filing", "predicted": "compliance_filing",
         "stage": "archived", "exact_ok": True, "aligned_ok": True,
         "expected_subclass": "10-K", "doc_subclass": "8-K"},
        {"expected": "contract", "predicted": "contract", "stage": "archived",
         "exact_ok": True, "aligned_ok": True},
    ]
    summary = score_rows(rows)
    assert summary["n_subclass"] == 2
    assert abs(summary["subclass_accuracy"] - 0.5) < 1e-9


def test_traces_to_rows_lifts_subclass_and_gt():
    from scripts.eval_pipeline import traces_to_rows

    rows = traces_to_rows([{
        "id": "t-sub",
        "input": {"filename": "sec.txt", "ground_truth": {
            "expected_hf_class": "compliance_filing",
            "expected_subclass": "10-K",
        }},
        "output": {
            "stage": "archived",
            "doc_type": "compliance_filing",
            "sorter": {"doc_type": "compliance_filing", "doc_subclass": "10-K"},
        },
        "metadata": {},
        "scores": [],
    }])
    assert rows[0]["expected"] == "compliance_filing"
    assert rows[0]["expected_subclass"] == "10-K"
    assert rows[0]["predicted_subclass"] == "10-K"
    assert rows[0]["subclass_ok"] is True


def test_attach_manifest_joins_trace_id_and_local_filename():
    from scripts.eval_pipeline import attach_manifest

    rows = [
        {"trace_id": "abc", "filename": "local.txt", "predicted": "contract",
         "expected": None, "exact_ok": False, "aligned_ok": False, "stage": "archived"},
        {"trace_id": "zzz", "filename": "other.txt", "predicted": "correspondence",
         "expected": None, "exact_ok": False, "aligned_ok": False, "stage": "archived"},
        {"trace_id": "maud", "filename": "maud.txt", "predicted": "merger_agreement",
         "expected": None, "exact_ok": False, "aligned_ok": False, "stage": "archived"},
    ]
    import json
    from pathlib import Path
    path = Path("/tmp/mailroom-eval-manifest.json")
    path.write_text(json.dumps({
        "samples": [
            {"trace_id": "abc", "expected": "merger_agreement", "local_filename": "local.txt"},
            {"trace_id": "maud", "expected": "merger_agreement", "local_filename": "maud.txt"},
        ]
    }), encoding="utf-8")
    out = attach_manifest(rows, str(path))
    assert out[0]["expected"] == "merger_agreement"
    # v0.6.0: MAUD merger_agreement is not aligned with CUAD contract.
    assert out[0]["aligned_ok"] is False
    assert out[0]["exact_ok"] is False
    assert out[1]["expected"] is None
    assert out[2]["expected"] == "merger_agreement"
    assert out[2]["aligned_ok"] is True
    assert out[2]["exact_ok"] is True


def test_trace_latency_prefers_pipeline_duration_score():
    from scripts.eval_pipeline import traces_to_rows

    rows = traces_to_rows([
        {
            "id": "trace-1",
            "timestamp": "2026-08-25T04:00:00Z",
            "updatedAt": "2026-08-25T04:20:00Z",
            "input": {"filename": "doc.txt"},
            "output": {"stage": "archived", "doc_type": "contract"},
            "scores": [
                {"name": "run_duration_seconds", "value": 12.5},
            ],
        }
    ])

    assert rows[0]["seconds"] == 12.5


def test_eval_score_map_keeps_newest_duplicate():
    from scripts.eval_pipeline import _score_map

    scores = [
        {"name": "total_tokens", "value": 10722},
        {"name": "total_tokens", "value": 7748},
    ]

    assert _score_map(scores)["total_tokens"] == 10722
