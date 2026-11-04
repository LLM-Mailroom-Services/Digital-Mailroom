"""Decisions-API reviewer backend and the guard that keeps a chat model out of the decision role."""

from __future__ import annotations

import pytest

from mailroom_sandbox import decision_backends as db
from mailroom_sandbox.job.spec import ReviewerSpec

DECISIONS = "openai/gpt-6-luna-decisions"


def test_decisions_model_detection():
    assert db.is_decisions_model(DECISIONS)
    assert not db.is_decisions_model("openai/gpt-6-luna")
    assert not db.is_decisions_model(None)


def test_chat_model_cannot_be_the_decision_reviewer_by_default():
    with pytest.raises(ValueError, match="allow_chat_model"):
        ReviewerSpec(backend="api", model="openai/gpt-6-luna", classes={"contract": 0.9})
    ReviewerSpec(backend="api", model="openai/gpt-6-luna", classes={"contract": 0.9}, allow_chat_model=True)


def test_decisions_model_needs_decisions_backend_and_questions():
    with pytest.raises(ValueError, match="backend decisions"):
        ReviewerSpec(backend="api", model=DECISIONS, classes={}, allow_chat_model=True)
    with pytest.raises(ValueError, match="Decisions-API model"):
        ReviewerSpec(backend="decisions", model="openai/gpt-6-luna", questions="reviewer_decisions_v1")
    with pytest.raises(ValueError, match="questions"):
        ReviewerSpec(backend="decisions", model=DECISIONS)
    spec = ReviewerSpec(backend="decisions", model=DECISIONS, questions="reviewer_decisions_v1")
    assert spec.classes == {}
    # Old reviewer blocks dump (and hash) exactly as before.
    assert ReviewerSpec(backend="jev", model="jev-1.13.0", classes={"contract": 0.9}).model_dump() == {
        "backend": "jev", "model": "jev-1.13.0", "classes": {"contract": 0.9}}


def test_empty_classes_only_on_a_calibration_run():
    from mailroom_sandbox.job.spec import RunSpec

    reviewer = {"backend": "decisions", "model": DECISIONS, "questions": "reviewer_decisions_v1"}
    RunSpec(task="sorter_reviewer", reviewer=reviewer)
    with pytest.raises(ValueError, match="at least one class"):
        RunSpec(task="pipeline", reviewer=reviewer)


def test_question_set_builds_doc_type_and_subclass_questions():
    qset = db.load_question_set("reviewer_decisions_v1")
    questions = db.decision_questions(qset)
    assert set(questions["doc_type"]["criteria"]) == {
        "contract", "merger_agreement", "corporate_record", "correspondence", "insurance_claim", "unknown"}
    assert {q for q in questions if q.startswith("subclass__")} == {
        "subclass__contract", "subclass__merger_agreement", "subclass__corporate_record",
        "subclass__correspondence", "subclass__insurance_claim"}
    assert all(q["type"] == "choice" for q in questions.values())


def test_decide_reads_probabilities_and_records_usage(monkeypatch):
    calls = {}

    class Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"model": DECISIONS + "-20261006",
                    "answers": {"doc_type": {"type": "choice", "choice": "merger_agreement",
                                             "probabilities": {"merger_agreement": 0.97, "contract": 0.03}},
                                "subclass__merger_agreement": {"type": "choice", "choice": "all_cash",
                                                               "probabilities": {"all_cash": 0.8, "other": 0.2}},
                                "subclass__contract": {"type": "choice", "choice": "supply"}},
                    "usage": {"input_tokens": 1000, "output_tokens": 0, "cost": 0.0001}}

    def post(url, json, timeout, headers):
        calls.update(url=url, body=json)
        return Resp()

    recorded = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("httpx.post", post)
    monkeypatch.setattr(db, "_record_usage", lambda model, usage: recorded.append(usage))
    out = db.decide("x" * 50, model=DECISIONS, questions={"doc_type": {}}, max_input_chars=10)
    assert calls["url"] == db.DECISIONS_URL and calls["body"]["state"] == "x" * 10
    assert out["doc_type"] == "merger_agreement" and out["confidence"] == 0.97
    assert out["doc_subclass"] == "all_cash" and out["contract_subtype"] is None
    assert out["subclass_confidence"] == 0.8
    assert recorded and recorded[0]["input_tokens"] == 1000


def test_decide_refuses_a_chat_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    with pytest.raises(ValueError):
        db.decide("x", model="openai/gpt-6-luna", questions={})


def test_live_reviewer_uses_the_activated_decisions_reviewer_from_a_worker_thread(monkeypatch):
    """Agent-task workers do not inherit the run lock's ContextVar; the reviewer must still be found."""
    import threading

    from mailroom_sandbox import runtime
    from mailroom_sandbox.eval import agents

    qset = db.load_question_set("reviewer_decisions_v1")
    monkeypatch.setattr(runtime, "_ACTIVE_REVIEWER", {"backend": "decisions", "model": DECISIONS, "question_set": qset})
    seen = {}

    def fake_decide(text, *, model, questions, max_input_chars, qset=None, handoff=None):
        seen.update(model=model, n=len(questions), cap=max_input_chars)
        return {"doc_type": "contract", "confidence": 0.9}

    monkeypatch.setattr(db, "decide", fake_decide)
    out = {}
    worker = threading.Thread(target=lambda: out.update(agents._live_reviewer({"doc_text": "AGREEMENT"})))
    worker.start()
    worker.join()
    assert out["doc_type"] == "contract"
    assert seen == {"model": DECISIONS, "n": 6, "cap": 120000}


def test_zero_output_tokens_are_still_recorded():
    """A Decisions call has no output tokens; the run's usage must still count its input.

    No ``runtime.activate``: it switches the process-wide profile and leaked into later tests
    (``cli health`` then probed the openrouter profile)."""
    from pipeline.limits import reset_run_usage, usage_summary

    reset_run_usage()
    db._record_usage(DECISIONS, {"input_tokens": 1234, "output_tokens": 0})
    summary = usage_summary()
    assert summary["prompt_tokens"] == 1234 and summary["calls"] == 1


def test_marker_subclass_takes_the_first_marker_in_order():
    block = db.load_question_set("reviewer_decisions_v2")["subclass"]["correspondence"]
    answers = {"marker__correspondence__notice": {"noul": 0.9}, "marker__correspondence__demand": {"noul": 0.7},
               "marker__correspondence__letter": {"noul": 0.2}}
    key, conf, _ = db.marker_subclass(block, answers, "correspondence")
    assert (key, conf) == ("demand", 0.7)   # demand precedes notice in the corpus order
    key, conf, _ = db.marker_subclass(block, {"marker__correspondence__letter": {"noul": 0.1}}, "correspondence")
    assert key == "email" and abs(conf - 0.9) < 1e-9


def test_v2_asks_marker_questions_for_correspondence():
    questions = db.decision_questions(db.load_question_set("reviewer_decisions_v2"))
    assert "subclass__correspondence" not in questions
    assert questions["marker__correspondence__memo"]["type"] == "noul"
    assert "subclass__contract" in questions


# --- 3.0.0: sorter handoff in the state and the verdict question -------------------------


def _v3_response(doc_type="contract", p=0.97, verdict="continue_sorter_correct"):
    class Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"model": DECISIONS,
                    "answers": {"doc_type": {"type": "choice", "choice": doc_type, "probabilities": {doc_type: p}},
                                "verdict": {"type": "choice", "choice": verdict,
                                            "probabilities": {verdict: 0.9, "route_to_human_review": 0.1}},
                                "subclass__contract": {"type": "choice", "choice": "supply", "probabilities": {"supply": 0.9}}},
                    "usage": {"input_tokens": 10, "output_tokens": 0}}
    return Resp()


def _decide_v3(monkeypatch, handoff, **resp):
    sent = {}

    def post(url, json, timeout, headers):
        sent.update(json)
        return _v3_response(**resp)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr("httpx.post", post)
    monkeypatch.setattr(db, "_record_usage", lambda model, usage: None)
    qset = db.load_question_set("reviewer_decisions_v3.0.0")
    out = db.decide("doc text", model=DECISIONS, questions=db.decision_questions(qset), qset=qset,
                    handoff=handoff, max_input_chars=1000)
    return sent, out


def test_v3_loads_with_verdict_and_handoff():
    qset = db.load_question_set("reviewer_decisions_v3.0.0")
    questions = db.decision_questions(qset)
    assert {"doc_type", "verdict", "subclass__contract"} <= set(questions)
    verdicts = set(qset["verdict"]["criteria"])
    assert {"continue_sorter_correct", "route_to_human_review", "reclassify"} <= verdicts
    assert set(qset["human_verdicts"]) <= verdicts


def test_v3_state_carries_the_sorter_handoff(monkeypatch):
    handoff = db.build_handoff("contract", "supply", 0.912345)
    sent, out = _decide_v3(monkeypatch, handoff)
    assert sent["state"] == {"document": "doc text", "sorter_handoff": handoff}
    assert handoff["sorter_confidence"] == 0.9123 and handoff["review_trigger"] == ["decision_class_review"]
    assert out["verdict"] == "continue_sorter_correct" and out["route_to_human"] is False
    assert out["confidence"] == 0.97


def test_v3_without_a_handoff_says_so(monkeypatch):
    sent, _ = _decide_v3(monkeypatch, None)
    assert sent["state"]["sorter_handoff"]["available"] is False


@pytest.mark.parametrize("verdict", ["route_to_human_review", "unreadable", "out_of_scope", "multiple_documents"])
def test_v3_human_verdict_gates_confidence_to_zero(monkeypatch, verdict):
    _, out = _decide_v3(monkeypatch, None, verdict=verdict)
    assert out["route_to_human"] is True and out["confidence"] == 0.0
    assert out["doc_type_probability"] == 0.97


def test_handoff_triggers():
    h = db.build_handoff("correspondence", None, 0.4, sorter_unsure=True, retried=True)
    assert h["review_trigger"] == ["decision_class_review", "sorter_below_low_band", "after_sorter_retry"]
    assert db.build_handoff("contract", None, "high")["sorter_confidence"] is None
    assert db.calibration_handoff(None) is None
    low = db.calibration_handoff({"sorter_doc_type": "contract", "sorter_doc_subclass": "supply", "sorter_confidence": 0.05})
    assert "sorter_below_low_band" in low["review_trigger"]


def test_sorter_handoff_map_reads_a_finished_run(tmp_path, monkeypatch):
    import json

    from mailroom_sandbox.job import preflight

    run = tmp_path / "sorter-run"
    run.mkdir()

    class Store:
        def __init__(self, path):
            self.path = path

        def read_checkpoint(self):
            return json.loads((self.path / "checkpoint.json").read_text())

        def load_items(self):
            return [json.loads(line) for line in (self.path / "items.jsonl").read_text().splitlines()]

    (run / "checkpoint.json").write_text(json.dumps({"state": "done"}))
    (run / "items.jsonl").write_text("\n".join(json.dumps(r) for r in [
        {"item_id": "a", "ok": True, "pred": {"doc_type": "contract", "contract_subtype": "supply", "confidence": 0.9}},
        {"item_id": "b", "ok": False, "error": "boom"},
    ]))
    monkeypatch.setattr("mailroom_sandbox.job.checkpoint.RunStore", Store)
    monkeypatch.setattr("mailroom_sandbox.job.spec.run_dir", lambda rid: tmp_path / rid)
    assert preflight.sorter_handoff_map("sorter-run") == {
        "a": {"sorter_doc_type": "contract", "sorter_doc_subclass": "supply", "sorter_confidence": 0.9}}
    (run / "checkpoint.json").write_text(json.dumps({"state": "running"}))
    with pytest.raises(ValueError, match="not a finished run"):
        preflight.sorter_handoff_map("sorter-run")


def test_sorter_handoff_map_merges_runs_and_accepts_a_cost_capped_run(tmp_path, monkeypatch):
    import json

    from mailroom_sandbox.job import preflight

    class Store:
        def __init__(self, path):
            self.path = path

        def read_checkpoint(self):
            return json.loads((self.path / "checkpoint.json").read_text())

        def load_items(self):
            return [json.loads(line) for line in (self.path / "items.jsonl").read_text().splitlines()]

    def make(rid, checkpoint, items):
        (tmp_path / rid).mkdir()
        (tmp_path / rid / "checkpoint.json").write_text(json.dumps(checkpoint))
        (tmp_path / rid / "items.jsonl").write_text("\n".join(json.dumps(i) for i in items))

    make("capped", {"state": "failed", "last_error": {"message": "api_cost_cap_usd=2.0 reached"}},
         [{"item_id": "a", "ok": True, "pred": {"doc_type": "contract", "confidence": 0.9}}])
    make("rest", {"state": "done"}, [{"item_id": "b", "ok": True, "pred": {"doc_type": "merger_agreement", "confidence": 1.0}}])
    make("broken", {"state": "failed", "last_error": {"message": "network"}}, [])
    monkeypatch.setattr("mailroom_sandbox.job.checkpoint.RunStore", Store)
    monkeypatch.setattr("mailroom_sandbox.job.spec.run_dir", lambda rid: tmp_path / rid)
    assert set(preflight.sorter_handoff_map(["capped", "rest"])) == {"a", "b"}
    with pytest.raises(ValueError, match="not a finished run"):
        preflight.sorter_handoff_map(["broken"])


def test_committed_handoff_file_matches_the_runs():
    from mailroom_sandbox.job import preflight
    from mailroom_sandbox.paths import repo_root

    path = "data/handoff/sorter-qwen3.7-flash/test.jsonl"
    if not (repo_root() / path).is_file():
        pytest.skip("saved sorter pass not present")
    handoff = preflight.sorter_handoff_map(path)
    assert len(handoff) == 323
    one = next(iter(handoff.values()))
    assert set(one) == {"sorter_doc_type", "sorter_doc_subclass", "sorter_confidence"}


# Subclasses the mailroom taxonomy supports (vendor/llm-mailroom/src/langchain_agents/
# doc_inventories.py). Every question set from 3.1.0 must offer each one, or the reviewer
# cannot answer a document of that subclass. Corpus conventions folded into another option
# are listed with where they go.
TAXONOMY = {
    "insurance_claim": ("pde", "inpatient", "outpatient", "carrier", "auto", "property",
                        "liability", "health", "life", "workers_comp", "other"),
    "corporate_record": ("articles_of_incorporation", "bylaws", "powers_of_attorney", "rights_instrument", "other"),
    "correspondence": ("email", "letter", "memo", "notice", "demand", "attorney_demand", "press_release",
                       "meeting_request"),
}


@pytest.mark.parametrize("stem", ["reviewer_decisions_v3.1.0"])
@pytest.mark.parametrize("cls", sorted(TAXONOMY))
def test_question_set_offers_every_taxonomy_subclass(stem, cls):
    block = db.load_question_set(stem)["subclass"][cls]
    missing = set(TAXONOMY[cls]) - set(block["criteria"])
    assert not missing, f"{stem} {cls} cannot answer {sorted(missing)}"


def test_taxonomy_table_matches_the_vendored_mailroom():
    inv = pytest.importorskip("langchain_agents.doc_inventories")
    assert set(TAXONOMY["insurance_claim"]) == set(inv.INSURANCE_CLAIM_TYPES)
    assert set(TAXONOMY["corporate_record"]) == set(inv.CORPORATE_RECORD_TYPES)
    assert set(TAXONOMY["correspondence"]) == set(inv.CORRESPONDENCE_TYPES)


def test_v3_1_asks_insurance_liability_and_workers_comp():
    q = db.decision_questions(db.load_question_set("reviewer_decisions_v3.1.0"))
    options = set(q["subclass__insurance_claim"]["criteria"])
    assert {"liability", "health", "life", "workers_comp", "other", db.NOT_THIS_CLASS} <= options


def test_saved_sorter_targets_are_consistent():
    """The patched targets (scripts/patch_sorter_handoff.py) never change the sorter input and
    only correct a label on two sources."""
    import json

    from mailroom_sandbox.paths import repo_root

    folder = repo_root() / "data" / "handoff" / "sorter-qwen3.7-flash"
    if not (folder / "train.targets.jsonl").is_file():
        pytest.skip("saved targets not present")
    for split, n in (("train", 2979), ("test", 323)):
        raw = {json.loads(x)["id"]: json.loads(x) for x in (folder / f"{split}.jsonl").read_text().split("\n") if x.strip()}
        rows = [json.loads(x) for x in (folder / f"{split}.targets.jsonl").read_text().split("\n") if x.strip()]
        assert len(rows) == len(raw) == n
        for r in rows:
            assert r["sorter_doc_type"] == raw[r["id"]]["sorter_doc_type"]
            assert r["target_status"] in {"label", "label_normalized", "corrected", "unannotated", "ambiguous", "disputed"}
            if r["target_status"] == "corrected":
                assert any("Decisions reviewer agrees" in e for e in r["target_evidence"])
            if r["target_status"] == "unannotated":
                assert r["target_doc_class"] == "merger_agreement" and r["target_subclass"] is None
                assert r["use_for_class"] and not r["use_for_subclass"]
            if r["target_status"] in ("ambiguous", "disputed"):
                # Neither is a target: kept as examples, never scored.
                assert r["target_doc_class"] is None and r["target_subclass"] is None
                assert not r["use_for_class"] and not r["use_for_subclass"] and r["sorter_class_correct"] is None
            if r["target_doc_class"] == "contract":
                assert r["target_subclass"] == r["target_subclass"].lower()


def test_decisions_backend_rejects_a_zero_cutoff():
    """A human verdict gates at 0.0, so a cutoff of 0 would never park it."""
    with pytest.raises(ValueError, match="cutoffs above 0 \\(contract\\)"):
        ReviewerSpec(backend="decisions", model=DECISIONS, questions="reviewer_decisions_v1",
                     classes={"contract": 0.0, "email": 0.5})
    ReviewerSpec(backend="decisions", model=DECISIONS, questions="reviewer_decisions_v1", classes={"contract": 0.01})


def test_a_gate_set_that_does_not_format_fails_at_load():
    """A field_instructions typo or a missing verdict instruction fails on load, not per row."""
    from mailroom_sandbox.decision_backends import _checked_gate_set

    qset = {"verdict": {"instructions": "Judge it.", "criteria": {"accept": "ok", "reject": "bad"}},
            "fields": {"contract": {"parties": "who signed"}},
            "field_instructions": "Is {field} supported? ({meaning})"}
    assert _checked_gate_set("t", qset) is qset
    with pytest.raises(ValueError, match="do not format for contract"):
        _checked_gate_set("t", {**qset, "field_instructions": "Is {field} supported? ({meanin})"})
    with pytest.raises(ValueError, match="verdict needs instructions"):
        _checked_gate_set("t", {**qset, "verdict": {"criteria": qset["verdict"]["criteria"]}})


def test_api_reviewer_may_share_the_sorter_model_on_a_calibration_run_only():
    """A sorter_reviewer run never calls the sorter, so a same-model chat reviewer is a valid comparison there;
    on a pipeline the reviewer would only repeat the sorter's answer."""
    from mailroom_sandbox.job.preflight import _api_reviewer_errors
    from mailroom_sandbox.job.spec import RunSpec

    reviewer = {"backend": "api", "model": "qwen/qwen3.7-flash", "allow_chat_model": True, "classes": {"contract": 0.9}}
    common = {"engine": {"kind": "openrouter", "model": "qwen/qwen3.7-flash"}, "reviewer": reviewer,
              "agent_routes": {"sorter_reviewer": {"provider": "openrouter", "model": "qwen/qwen3.7-flash"}}}
    assert _api_reviewer_errors(RunSpec(task="sorter_reviewer", **common)) == []
    errs = _api_reviewer_errors(RunSpec(task="pipeline", **common))
    assert any("different model from the sorter" in e for e in errs)
