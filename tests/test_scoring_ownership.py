"""Hand-counted behavior and dependency-boundary tests for sandbox scoring."""

import importlib.util
from pathlib import Path

import llm_dojo_scoring as dojo
import pytest

from mailroom_sandbox.eval import cuad_scoring, maud_scoring, scoring
from mailroom_sandbox.job import grid_cards
from mailroom_sandbox.job.checkpoint import RunStore


def test_cuad_uses_dojo_without_recomputing_or_copying(monkeypatch):
    """The adapter returns the actual engine result and forwards raw inputs."""
    pred, gt, result = {"cuad_clauses": ["Parties: x"]}, {"Parties": []}, {"engine": object()}
    calls = []

    def engine(actual_pred, actual_gt):
        """Record exact engine inputs and return a distinctive payload."""
        calls.append((actual_pred, actual_gt))
        return result

    monkeypatch.setattr(dojo, "score_sandbox_cuad", engine)
    assert cuad_scoring.score_cuad(pred, gt) is result
    assert calls == [(pred, gt)]
    assert calls[0][0] is pred and calls[0][1] is gt


def test_maud_uses_dojo_without_recomputing_or_copying(monkeypatch):
    """A future Dojo correction reaches the sandbox through its public API."""
    pred, gt, result = {"maud_clauses": ["No-Shop: Yes"]}, {"No-Shop": {"answer": "Yes"}}, {"engine": object()}
    calls = []

    def engine(actual_pred, actual_gt):
        """Record exact engine inputs and return a distinctive payload."""
        calls.append((actual_pred, actual_gt))
        return result

    monkeypatch.setattr(dojo, "score_sandbox_maud", engine)
    assert maud_scoring.score_maud(pred, gt) is result
    assert calls == [(pred, gt)]


@pytest.mark.parametrize("benchmark", ["cuad", "maud"])
def test_engine_error_is_not_hidden_by_local_scoring(monkeypatch, benchmark):
    """Dojo failures propagate through thin adapters rather than changing rubrics."""
    def broken(*args):
        """Represent a source-engine failure that must remain visible."""
        raise RuntimeError("Dojo scoring defect")

    monkeypatch.setattr(dojo, f"score_sandbox_{benchmark}", broken)
    module = cuad_scoring if benchmark == "cuad" else maud_scoring
    with pytest.raises(RuntimeError, match="Dojo scoring defect"):
        getattr(module, f"score_{benchmark}")({}, {})


def test_asymmetric_cuad_fixture_keeps_presence_and_value_contract():
    """Two hits, one false positive and three misses yield P=2/3,R=2/5,F1=1/2."""
    gt = {"Parties": [{"text": "Acme"}], "Governing Law": [{"text": "New York"}],
          "Anti-Assignment": [{"text": "no assignment"}], "Audit Rights": [{"text": "audit"}],
          "Renewal Term": [{"text": "annual"}], "Exclusivity": []}
    pred = {"parties": ["Acme"], "governing_law": "New York", "cuad_clauses": ["Exclusivity: x", "Unknown: x"]}
    out = cuad_scoring.score_cuad(pred, gt)
    assert (out["cuad_tp"], out["cuad_fp"], out["cuad_fn"]) == (2, 1, 3)
    assert (out["cuad_presence_precision"], out["cuad_presence_recall"], out["cuad_presence_f1"]) == (0.6667, 0.4, 0.5)
    assert (out["cuad_value_checked"], out["cuad_value_correct"], out["cuad_out_of_universe"]) == (2, 2, 1)
    assert cuad_scoring.score_cuad({}, {})["cuad_presence_f1"] is None
    assert cuad_scoring.score_cuad({}, {"Parties": []})["cuad_presence_f1"] == 0.0


def test_maud_excludes_null_gt_but_keeps_catalog_none_and_asymmetric_counts():
    """Four labeled questions, three answers, two correct and one conflict give 1/2,2/3."""
    cor = "Agreement provides for matching rights in connection with COR"
    gt = {cor: {"answer": "None"}, "Type of Consideration": {"answer": "All Cash"},
          "Breach of No Shop": {"answer": "No"}, "No-Shop": {"answer": "Yes"},
          "Specific Performance": {"answer": None}}
    pred = {"maud_clauses": [f"{cor}: None", "Type of Consideration: All Cash", "Breach of No Shop: Yes", "Breach of No Shop: No"]}
    out = maud_scoring.score_maud(pred, gt)
    assert (out["maud_questions"], out["maud_answered"], out["maud_correct"], out["maud_conflicts"]) == (4, 3, 2, 1)
    assert out["maud_accuracy"] == 0.5
    assert out["maud_precision_answered"] == 2 / 3
    assert (out["maud_clean_questions"], out["maud_clean_correct"], out["maud_clean_accuracy"]) == (3, 2, 2 / 3)
    assert maud_scoring.score_maud({}, {"Specific Performance": {"answer": None}})["maud_accuracy"] is None


@pytest.mark.parametrize("doc_type,benchmark,headline", [
    ("contract", "cuad", "cuad_presence_f1"),
    ("merger_agreement", "maud", "maud_accuracy"),
])
def test_row_keeps_dojo_benchmark_headline_and_suite_score(monkeypatch, doc_type, benchmark, headline):
    """Row formatting preserves the suite score and routes the canonical benchmark result."""
    class Suite:
        """Minimal honest suite whose result differs from the benchmark."""
        field_types = {}

        def score(self, expected, predicted, **kwargs):
            """Return a known suite aggregate to expose headline replacement."""
            return {"extraction_overall_score": 0.83}

    raw_gt = {"not": "preparsed"}
    calls = []

    def benchmark_engine(predicted, labels):
        """Return a distinct benchmark score and retain raw-label evidence."""
        calls.append(labels)
        return {headline: 0.271, "canonical_marker": True}

    monkeypatch.setattr(scoring, "suite_for_doc_type", lambda _: Suite())
    monkeypatch.setattr(scoring, "assess_extraction_payload", lambda *args, **kwargs: {})
    monkeypatch.setattr(dojo, f"score_sandbox_{benchmark}", benchmark_engine)
    out = scoring.score_extraction_row(doc_type, {}, {f"{benchmark}_clause_labels": raw_gt})
    assert out["overall_extraction_score"] == 0.271
    assert out["suite_overall_extraction_score"] == 0.83
    assert out["canonical_marker"] is True
    assert out["scoring_method"] == f"suite+{benchmark}"
    assert calls == [raw_gt] and calls[0] is raw_gt


def _card(tmp_path, scores):
    """Build an offline card from scored rows and one excluded failed item."""
    store = RunStore(tmp_path / "runs" / "score-review")
    store.write_lock({"run_id": "score-review", "task": "contracts_specialist", "profile": "ollama", "job": {"mock": True}, "dataset": {"limit": len(scores)}})
    for i, score in enumerate(scores):
        store.append_item({"item_id": f"DOC-{i}", "index": i, "ok": True, "score": score})
    store.append_item({"item_id": "ERROR", "index": len(scores), "ok": False,
                       "score": {"scoring_method": "suite+cuad", "cuad_tp": 1000, "cuad_presence_f1": 1.0}})
    return grid_cards.collect_card(store, wall_seconds=1.0)


def test_card_uses_pooled_dojo_counts(tmp_path):
    """One perfect event plus nine misses pools to F1=2/11, not mean F1=1/2."""
    a = {"scoring_method": "suite+cuad", "cuad_tp": 1, "cuad_fp": 0, "cuad_fn": 0, "cuad_presence_f1": 1.0}
    b = {"scoring_method": "suite+cuad", "cuad_tp": 0, "cuad_fp": 0, "cuad_fn": 9, "cuad_presence_f1": 0.0}
    assert _card(tmp_path / "asym", [a, b])["quality"]["clause"]["f1"] == 0.1818


def test_card_keeps_zero_distinct_from_absent(tmp_path):
    """A labeled miss remains numeric zero while an unlabeled row remains null."""
    b = {"scoring_method": "suite+cuad", "cuad_tp": 0, "cuad_fp": 0, "cuad_fn": 9, "cuad_presence_f1": 0.0}
    zero = _card(tmp_path / "zero", [b])["quality"]["clause"]
    assert (zero["precision"], zero["recall"], zero["f1"]) == (0.0, 0.0, 0.0)
    absent = _card(tmp_path / "absent", [{"scoring_method": "suite+cuad", "cuad_presence_f1": None}])["quality"]["clause"]
    assert (absent["precision"], absent["recall"], absent["f1"]) == (None, None, None)


def test_card_uses_dojo_pooling_result(monkeypatch, tmp_path):
    """Card producer chooses successful rows and delegates numerical pooling."""
    calls = []
    result = {"kind": "maud", "canonical_marker": 17}

    def aggregate(benchmark, rows):
        """Expose report population and avoid accidental local recomputation."""
        calls.append((benchmark, rows))
        return result

    monkeypatch.setattr(dojo, "aggregate_sandbox_scores", aggregate)
    monkeypatch.setattr(grid_cards, "aggregate_sandbox_scores", aggregate)
    score = {"scoring_method": "suite+maud", "maud_questions": 3}
    assert _card(tmp_path, [score])["quality"]["clause"] is result
    assert calls == [("maud", [score])]


def test_sand032_report_uses_dojo_pooling(monkeypatch):
    """Historical report shares the same engine while retaining presentation."""
    path = Path(__file__).resolve().parents[1] / "scripts/sand032/report.py"
    spec = importlib.util.spec_from_file_location("review_sand032_report", path)
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    calls = []

    def aggregate(benchmark, rows):
        """Distinguish real delegation from same-result copied arithmetic."""
        calls.append((benchmark, rows))
        return {"kind": "cuad", "docs_labeled": 1, "precision": 0.123, "recall": 0.456, "f1": 0.789, "value_correct": 0, "value_checked": 0}

    monkeypatch.setattr(report, "aggregate_sandbox_scores", aggregate)
    monkeypatch.setattr(dojo, "aggregate_sandbox_scores", aggregate)
    score = {"scoring_method": "suite+cuad", "cuad_tp": 1, "cuad_presence_f1": 1.0}
    items = {"ok": {"ok": True, "score": score}, "error": {"ok": False, "score": score}}
    rendered = "\n".join(report.scoring_section({"items": items}))
    assert "0.123 / 0.456 / **0.789**" in rendered
    assert calls == [("cuad", [score])]
