"""Reviewer cutoff calibration from a labelled run (SAND-085)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import load_run_spec

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("calibrate_reviewer", ROOT / "scripts/calibrate_reviewer.py")
calibrate_reviewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibrate_reviewer)


CLASSES = {"contract", "correspondence", "merger_agreement"}


def _store(tmp_path, items, rows, state="done"):
    store = RunStore(tmp_path / "run")
    store.dir.mkdir(parents=True, exist_ok=True)
    store.dataset_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    for item in items:
        store.append_item(item)
    store.write_checkpoint(state=state, cursor=len(items), total=len(rows))
    return store


def _run(tmp_path, answers, name="contract"):
    rows = [{"id": str(i), "expected_doc_class": name} for i in range(len(answers))]
    items = [{"item_id": str(i), "ok": True, "pred": {"doc_type": label, "confidence": confidence}}
             for i, (label, confidence) in enumerate(answers)]
    return _store(tmp_path, items, rows)


def test_cutoff_is_the_lowest_confidence_reaching_the_target():
    rows = [(0.5, False), (0.7, False), (0.8, True), (0.9, True)]
    assert calibrate_reviewer._cutoff(rows, 0.95) == 0.8


def test_holdout_reports_what_the_cutoff_delivers(tmp_path):
    # 20 right `contract` answers at 0.9, and 20 wrong ones at 0.5 on correspondence.
    rows = [{"id": str(i), "expected_doc_class": "contract" if i < 20 else "correspondence"} for i in range(40)]
    items = [{"item_id": str(i), "ok": True, "pred": {"doc_type": "contract", "confidence": 0.9 if i < 20 else 0.5}}
             for i in range(40)]
    result = calibrate_reviewer.calibrate(_store(tmp_path, items, rows), classes=CLASSES)["classes"]["contract"]
    assert result["cutoff"] == 0.9
    assert result["holdout_accuracy"] == 1.0
    assert 0 < result["holdout_share_accepted"] < 1


def test_class_that_never_reaches_the_target_gets_no_cutoff(tmp_path):
    result = calibrate_reviewer.calibrate(_run(tmp_path, [("correspondence", 0.9)] * 10), classes=CLASSES)
    assert result["classes"]["contract"]["cutoff"] is None


def test_failed_answers_cannot_clear_a_cutoff(tmp_path):
    rows = [{"id": "a", "expected_doc_class": "contract"}]
    store = _store(tmp_path, [{"item_id": "a", "ok": False, "pred": None}], rows)
    assert calibrate_reviewer._rows(store, CLASSES) == {"contract": []}


def test_answers_count_against_the_class_they_predict(tmp_path):
    # A confident `contract` on correspondence must weigh against the contract cutoff.
    rows = [{"id": "a", "expected_doc_class": "correspondence"}, {"id": "b", "expected_doc_class": "contract"}]
    items = [{"item_id": "a", "ok": True, "pred": {"doc_type": "contract", "confidence": 0.95}},
             {"item_id": "b", "ok": True, "pred": {"doc_type": "contract", "confidence": 0.9}}]
    assert calibrate_reviewer._rows(_store(tmp_path, items, rows), CLASSES) == {
        "contract": [(0.95, False), (0.9, True)], "correspondence": []}


def test_out_of_taxonomy_answers_clear_no_cutoff(tmp_path):
    store = _run(tmp_path, [("invoice", 0.99)] * 4)
    assert calibrate_reviewer._rows(store, CLASSES) == {"contract": []}


@pytest.mark.parametrize("state", ["running", "paused"])
def test_unfinished_runs_are_refused(tmp_path, state):
    rows = [{"id": str(i), "expected_doc_class": "contract"} for i in range(4)]
    items = [{"item_id": "0", "ok": True, "pred": {"doc_type": "contract", "confidence": 0.9}}]
    with pytest.raises(ValueError, match=state):
        calibrate_reviewer.calibrate(_store(tmp_path, items, rows, state=state), classes=CLASSES)


def test_done_runs_missing_locked_documents_are_refused(tmp_path):
    rows = [{"id": str(i), "expected_doc_class": "contract"} for i in range(4)]
    items = [{"item_id": "0", "ok": True, "pred": {"doc_type": "contract", "confidence": 0.9}}]
    with pytest.raises(ValueError, match="3 of 4"):
        calibrate_reviewer.calibrate(_store(tmp_path, items, rows), classes=CLASSES)


def _probe_store(tmp_path, valid, latency_ms=2000.0, doc_type="contract", answered=10, state="done"):
    rows = [{"id": str(i), "expected_doc_class": "contract"} for i in range(10)]
    items = [{"item_id": str(i), "ok": True, "latency_ms": latency_ms,
              "pred": {"doc_type": doc_type, "confidence": 0.9 if i < valid else None}} for i in range(answered)]
    return _store(tmp_path, items, rows, state=state)


def test_probe_passes_on_valid_fast_answers(tmp_path):
    verdict = calibrate_reviewer.probe(_probe_store(tmp_path, 9), classes=CLASSES)
    assert verdict["passed"] and verdict["valid_answers"] == 9


def test_probe_fails_on_missing_confidences(tmp_path):
    assert not calibrate_reviewer.probe(_probe_store(tmp_path, 8), classes=CLASSES)["passed"]


def test_probe_fails_when_too_slow(tmp_path):
    assert not calibrate_reviewer.probe(_probe_store(tmp_path, 10, latency_ms=11000.0), classes=CLASSES)["passed"]


def test_probe_fails_on_out_of_taxonomy_answers(tmp_path):
    verdict = calibrate_reviewer.probe(_probe_store(tmp_path, 10, doc_type="invoice"), classes=CLASSES)
    assert not verdict["passed"] and verdict["valid_answers"] == 0


def test_probe_fails_on_an_unfinished_run(tmp_path):
    verdict = calibrate_reviewer.probe(_probe_store(tmp_path, 9, answered=9, state="paused"), classes=CLASSES)
    assert not verdict["passed"] and "paused" in verdict["incomplete"]


def test_probe_uses_the_live_taxonomy_by_default(tmp_path):
    assert calibrate_reviewer.probe(_probe_store(tmp_path, 9))["passed"]


def test_probe_run_stays_inside_its_budget():
    run = load_run_spec(ROOT / "config/runs/reviewer-probe-gemma4.yaml")
    assert run.dataset.limit == 10 and run.job.cost_cap_usd <= 0.25 and run.job.max_wall_seconds <= 300


def test_calibration_run_is_capped_and_uses_a_non_qwen_model():
    run = load_run_spec(ROOT / "config/runs/reviewer-calibration-gemma4.yaml")
    assert run.task == "sorter_reviewer" and run.engine.model.startswith("google/gemma-4")
    assert run.job.cost_cap_usd <= 1.0 and run.engine.modal.max_containers == 1


def test_saturation_counts_answers_at_the_top_confidence(tmp_path):
    # A cutoff cannot separate these: both the right and the wrong answer score 1.0.
    rows = [{"id": str(i), "expected_doc_class": "contract" if i < 3 else "correspondence"} for i in range(4)]
    items = [{"item_id": str(i), "ok": True, "pred": {"doc_type": "contract", "confidence": 0.8 if i == 0 else 1.0}}
             for i in range(4)]
    result = calibrate_reviewer.calibrate(_store(tmp_path, items, rows), classes=CLASSES)["classes"]["contract"]
    assert result["top_confidence"] == 1.0
    assert result["top_confidence_documents"] == 3
    assert result["top_confidence_wrong"] == 1


def test_calibrate_rejects_a_target_outside_zero_to_one(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore

    for target in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="target accuracy"):
            calibrate_reviewer.calibrate(RunStore(tmp_path / "r"), target=target)


def test_every_answer_is_tested_once_and_the_lower_bound_decides(tmp_path):
    rows = [{"id": str(i), "expected_doc_class": "contract"} for i in range(150)]
    items = [{"item_id": str(i), "ok": True, "pred": {"doc_type": "contract", "confidence": 0.9}} for i in range(150)]
    result = calibrate_reviewer.calibrate(_store(tmp_path, items, rows), classes=CLASSES)["classes"]["contract"]
    assert result["holdout_accepted"] == 150 and result["meets_target"] is True


def test_a_small_perfect_class_does_not_meet_the_target(tmp_path):
    rows = [{"id": str(i), "expected_doc_class": "contract"} for i in range(40)]
    items = [{"item_id": str(i), "ok": True, "pred": {"doc_type": "contract", "confidence": 0.9}} for i in range(40)]
    result = calibrate_reviewer.calibrate(_store(tmp_path, items, rows), classes=CLASSES)["classes"]["contract"]
    assert result["holdout_accuracy"] == 1.0 and result["meets_target"] is False


def _targets_run(tmp_path):
    """A reviewer run with a saved handoff and verified targets next to it."""
    rows = [{"id": "a", "expected_doc_class": "contract", "expected_subclass": "License_Agreements"},
            {"id": "b", "expected_doc_class": "corporate_record", "expected_subclass": "board_resolution"},
            {"id": "c", "expected_doc_class": "merger_agreement", "expected_subclass": "other"},
            {"id": "d", "expected_doc_class": "contract", "expected_subclass": "Service"}]
    targets = [
        {"id": "a", "target_doc_class": "contract", "target_subclass": "license",
         "use_for_class": True, "use_for_subclass": True},
        # label corrected: a Certificate of Amendment labelled board_resolution
        {"id": "b", "target_doc_class": "corporate_record", "target_subclass": "charter_amendment",
         "use_for_class": True, "use_for_subclass": True},
        # unannotated merger: class scored, subclass not
        {"id": "c", "target_doc_class": "merger_agreement", "target_subclass": None,
         "use_for_class": True, "use_for_subclass": False},
        # ambiguous: not scored at all
        {"id": "d", "target_doc_class": None, "target_subclass": None,
         "use_for_class": False, "use_for_subclass": False},
    ]
    handoff = tmp_path / "handoff" / "train.jsonl"
    handoff.parent.mkdir(parents=True)
    handoff.write_text("")
    (tmp_path / "handoff" / "train.targets.jsonl").write_text("".join(json.dumps(t) + "\n" for t in targets))
    items = [
        {"item_id": "a", "ok": True, "pred": {"doc_type": "contract", "doc_subclass": "license", "confidence": 0.99}},
        {"item_id": "b", "ok": True, "pred": {"doc_type": "corporate_record", "doc_subclass": "charter_amendment",
                                              "confidence": 0.99, "verdict": "continue_with_subclass_correction"}},
        {"item_id": "c", "ok": True, "pred": {"doc_type": "merger_agreement", "doc_subclass": "all_cash",
                                              "confidence": 0.99}},
        {"item_id": "d", "ok": True, "pred": {"doc_type": "correspondence", "confidence": 0.99}},
    ]
    store = _store(tmp_path, items, rows)
    store.write_lock({"reviewer": {"handoff_run": str(handoff), "handoff": {
        "b": {"sorter_doc_type": "corporate_record", "sorter_doc_subclass": "board_resolution"}}}})
    return store


def test_targets_next_to_the_handoff_are_the_default_truth(tmp_path):
    store = _targets_run(tmp_path)
    truth = calibrate_reviewer.Truth(store)
    assert truth.source.startswith("targets ") and "sha256" in truth.source
    assert truth.doc_class("d") is None
    assert truth.subclass("c") == (False, None)
    assert calibrate_reviewer.Truth(store, labels=True).source == "dataset labels"


def test_scoring_against_targets_skips_unscored_rows(tmp_path):
    store = _targets_run(tmp_path)
    classes = {"contract", "corporate_record", "merger_agreement", "correspondence"}
    truth = calibrate_reviewer.Truth(store)
    rows = calibrate_reviewer._rows(store, classes, truth)
    assert "correspondence" not in rows or rows["correspondence"] == []
    assert all(correct for values in rows.values() for _, correct in values)
    sub = calibrate_reviewer.subclass_report(store, truth)
    assert (sub["subclass_correct"], sub["subclass_scored"]) == (2, 2)
    out = calibrate_reviewer.routing(store, {"contract": 0.5, "corporate_record": 0.5,
                                             "merger_agreement": 0.5, "correspondence": 0.5}, truth)
    assert out["misrouted"] == 0 and out["not_scored"] == 1
    # the corrected label makes the sorter's board_resolution a subclass error
    assert out["verdicts_by_expected"] == {
        "continue_with_subclass_correction": {"continue_with_subclass_correction": 1}}


def test_raw_labels_count_the_label_noise_as_reviewer_errors(tmp_path):
    store = _targets_run(tmp_path)
    sub = calibrate_reviewer.subclass_report(store, calibrate_reviewer.Truth(store, labels=True))
    assert sub["subclass_correct"] < sub["subclass_scored"]


def test_targets_missing_a_locked_document_are_refused(tmp_path):
    store = _targets_run(tmp_path)
    path = tmp_path / "short.targets.jsonl"
    path.write_text(json.dumps({"id": "a", "target_doc_class": "contract", "use_for_class": True}) + "\n")
    with pytest.raises(ValueError, match="no row for 3"):
        calibrate_reviewer.Truth(store, path)
