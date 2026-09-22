"""#85 M5/M6 (#90/#91): gate wiring completion — terminal gate outcome.

Contracts pinned here (remaining DoD items after #99/#100/#108):

- ``BERT_INTAKE_MODE=verify`` exercises the gate WITHOUT skipping the
  sorter: fast-path docs still route to ``classify``, gate-failed docs to
  the reviewer guard, and the terminal manifest records the verify-mode
  verdict computed against the REAL sorter/reviewer results (P6/P7).
- The terminal manifest records ``classification_method`` and the
  ``intake.bert.gate_outcome`` block (``verdict``/``mode``/``failures``/
  ``failed_checks``/``eligible_for_sorter_skip``/``recommended_action``).
- Fail-open: a missing mailroom-ml package or a raising gate NEVER blocks
  the manifest or the run; an intake/BERT problem can never alone mark a
  run FAILED (#91).
- Reviewer blindness: the gate consumes sorter/reviewer verdicts as inputs;
  no triage labels flow the reverse direction.
"""

from unittest.mock import patch

import pytest

from graph.state import DocumentState

import sys
import types as _types


class _FakeMailroomML:
    """Injects a fake `mailroom_ml.routing` into sys.modules so the LAZY
    import seam in the gate callers resolves (the sibling package is not
    installed in this venv)."""

    def __init__(self, gate_fn):
        self.module = _types.ModuleType("mailroom_ml")
        self.routing = _types.ModuleType("mailroom_ml.routing")
        self.routing.evaluate_intake_gate = gate_fn
        self.routing.GATE_ALLOWLISTED_START = ("contract",)

    def __enter__(self):
        self._saved = {}
        for name in ("mailroom_ml", "mailroom_ml.routing"):
            self._saved[name] = sys.modules.get(name)
            sys.modules[name] = self.module if name == "mailroom_ml" else self.routing
        return self

    def __exit__(self, *exc):
        for name, mod in self._saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod
        return False


def _fast_path_handoff(doc_type: str = "contract") -> dict:
    return {
        "available": True,
        "reason": "ok",
        "method": "bert",
        "routing_path": "fast_path",
        "route": "fast_path",
        "status": "success",
        "doc_type": doc_type,
        "subclass": "binder",
        "score": 0.93,
        "calibrated_confidence": 0.93,
        "subclass_confidence": 0.31,
        "n_windows": 1,
        "artifact_sha": "abc123",
        "quality": {"messy": False, "coverage": 1.0},
        "doc_type_pass": True,
        "subclass_pass": False,
    }


def _gate_fail_handoff() -> dict:
    return {
        "available": True,
        "reason": "ok",
        "method": "bert",
        "routing_path": "clerk_only",
        "route": "clerk_only",
        "status": "success",
        "doc_type": "contract",
        "subclass": None,
        "score": 0.31,
        "calibrated_confidence": 0.31,
        "n_windows": 1,
        "artifact_sha": "abc123",
        "quality": {"messy": True, "coverage": 0.5},
        "doc_type_pass": False,
        "subclass_pass": False,
    }


def _state(**overrides) -> DocumentState:
    state: DocumentState = {
        "doc_id": "g-1",
        "matter_id": "TEST",
        "doc_text": "Letter text for gate tests.",
        "doc_pages": None,
        "intake_prep": None,
        "bert_triage": None,
        "intake_handoff": None,
        "intake_meta": None,
        "classification_attempts": 0,
        "retry_count": 0,
        "doc_type": "",
        "classification_confidence": 0.0,
        "extraction_confidence": 0.0,
        "escalation_reason": None,
        "review_decision": None,
        "messages": [],
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# verify mode exercises the gate without skipping
# ---------------------------------------------------------------------------


class TestVerifyModeExercisesGate:
    def test_verify_fast_path_routes_to_classify_not_extract(self, monkeypatch):
        """Verify = sorter still runs; only skip may bypass (#90 DoD)."""
        from graph.routing import after_intake

        monkeypatch.setenv("BERT_INTAKE_MODE", "verify")
        handoff = _fast_path_handoff()
        assert after_intake(_state(intake_handoff=dict(handoff))) == "classify"

    def test_verify_gate_fail_routes_to_reviewer_guard(self, monkeypatch):
        from graph.routing import after_intake

        monkeypatch.setenv("BERT_INTAKE_MODE", "verify")
        handoff = _gate_fail_handoff()
        assert after_intake(_state(intake_handoff=handoff)) == "review_classify"

    def test_skip_fast_path_allowlisted_eligible_extracts(self, monkeypatch):
        from graph.routing import after_intake

        monkeypatch.setenv("BERT_INTAKE_MODE", "skip")
        handoff = _fast_path_handoff()
        gate = _FakeGate({"eligible_for_sorter_skip": True})
        with _FakeMailroomML(gate):
            assert after_intake(_state(intake_handoff=dict(handoff))) == "extract"
        assert gate.calls[0]["mode"] == "skip"


# ---------------------------------------------------------------------------
# terminal manifest: method + gate outcome
# ---------------------------------------------------------------------------


class _FakeGate:
    """Records the exact arguments the gate received."""

    def __init__(self, verdict: dict):
        self.calls: list[dict] = []
        self._verdict = verdict

    def __call__(self, handoff, sorter_result=None, reviewer_result=None, *,
                 mode=None) -> dict:
        self.calls.append({
            "handoff": handoff,
            "sorter_result": sorter_result,
            "reviewer_result": reviewer_result,
            "mode": mode,
        })
        return self._verdict


class TestTerminalManifestGateOutcome:
    def test_archive_records_verify_verdict_with_real_results(self, monkeypatch):
        """Verify-mode gate_outcome computed against sorter+reviewer inputs."""
        from graph.build_graph import _attach_gate_outcome

        monkeypatch.setenv("BERT_INTAKE_MODE", "verify")
        fake_gate = _FakeGate({
            "verdict": "FAIL",
            "mode": "verify",
            "failures": ["F5"],
            "failed_checks": {"P6": "sorter disagreed with BERT"},
            "eligible_for_sorter_skip": False,
            "recommended_action": "force_llm_sorter",
        })
        state = _state(
            intake_meta={"bert": _fast_path_handoff()},
            doc_type="claim",
            classification_confidence=0.9,
            classification_attempts=1,
            review_decision="reviewer_agrees",
        )
        with _FakeMailroomML(fake_gate):
            meta = _attach_gate_outcome(state["intake_meta"], state)

        outcome = meta["bert"]["gate_outcome"]
        assert outcome["verdict"] == "FAIL"
        assert outcome["mode"] == "verify"
        assert outcome["failures"] == ["F5"]
        assert outcome["eligible_for_sorter_skip"] is False
        # the gate received the REAL sorter/reviewer results (P6/P7 inputs)
        call = fake_gate.calls[0]
        assert call["sorter_result"] == {"doc_type": "claim", "confidence": 0.9}
        assert call["reviewer_result"] == {"doc_type": "reviewer_agrees"}
        assert call["mode"] == "verify"

    def test_archive_skip_mode_records_verdict(self, monkeypatch):
        from graph.build_graph import _attach_gate_outcome

        monkeypatch.setenv("BERT_INTAKE_MODE", "skip")
        fake_gate = _FakeGate({
            "verdict": "PASS",
            "mode": "skip",
            "failures": [],
            "failed_checks": {},
            "eligible_for_sorter_skip": True,
            "recommended_action": "accept_bert",
        })
        state = _state(
            intake_meta={"bert": _fast_path_handoff()},
            classification_attempts=0,  # skip mode: sorter never ran
        )
        with _FakeMailroomML(fake_gate):
            meta = _attach_gate_outcome(state["intake_meta"], state)

        assert meta["bert"]["gate_outcome"]["verdict"] == "PASS"
        assert fake_gate.calls[0]["sorter_result"] is None

    def test_no_bert_lane_leaves_meta_untouched(self):
        from graph.build_graph import _attach_gate_outcome

        state = _state(intake_meta=None)
        assert _attach_gate_outcome(None, state) == {}

        state2 = _state(intake_meta={"prep": {"section_count": 1}},
                        intake_handoff={"available": False, "reason": "flag_off"})
        meta = _attach_gate_outcome(state2["intake_meta"], state2)
        assert "gate_outcome" not in meta
        assert meta["prep"]["section_count"] == 1

    def test_missing_package_and_raising_gate_fail_open(self):
        """#91: an intake/gate problem can never mark a run FAILED."""
        from graph.build_graph import _attach_gate_outcome

        state = _state(intake_meta={"bert": _fast_path_handoff()})
        # no mailroom_ml importable (undeclared sibling absent) -> no outcome
        meta = _attach_gate_outcome(state["intake_meta"], state)
        assert "gate_outcome" not in meta["bert"]
        assert meta["bert"]["available"] is True  # handoff survives

        # raising gate -> no outcome, no exception
        def _boom(*a, **k):
            raise RuntimeError("gate exploded")

        with _FakeMailroomML(_boom):
            meta = _attach_gate_outcome(state["intake_meta"], state)
        assert "gate_outcome" not in meta["bert"]


class TestTerminalManifestMethod:
    def test_archive_manifest_carries_classification_method(self, temp_base_dir):
        """#91 DoD: manifest records the method + the gate outcome."""
        from graph.build_graph import _attach_gate_outcome, archive_node
        from pipeline.bins import load_manifest, save_manifest

        gate = _FakeGate({
            "verdict": "PASS",
            "mode": "skip",
            "failures": [],
            "failed_checks": {},
            "eligible_for_sorter_skip": True,
            "recommended_action": "accept_bert",
        })

        def _fake_archive(manifest, file_path, prev_audit_hash=""):
            save_manifest(manifest)  # mirror the real archivist contract
            return (str(file_path) + ".json", {"hash": "aabb" * 8})

        with _FakeMailroomML(gate):
            with patch("graph.build_graph._catalog_upsert"):
                with patch("agents.archivist.archive_document", _fake_archive):
                    with patch("graph.build_graph._latest_audit_hash",
                               return_value=""):
                        with patch("graph.build_graph._write_audit_log"):
                            doc = temp_base_dir / "pipeline" / "inbox" / "letter.txt"
                            doc.write_text("letter")
                            state = _state(
                                file_path=str(doc),
                                doc_type="contract",
                                classification_confidence=0.9,
                                classification_attempts=1,
                                classification_method="bert_scoped",
                                intake_meta={"bert": _fast_path_handoff()},
                            )
                            result = archive_node(state)

        assert result["stage"] == "archived"
        manifest = load_manifest(state["doc_id"])
        assert manifest is not None
        assert manifest.classification_method == "bert_scoped"
        # terminal record carries the enriched (not raw) intake block
        assert manifest.intake["bert"]["gate_outcome"]["verdict"] == "PASS"
        _attach_gate_outcome  # (referenced so the import is used)


# ---------------------------------------------------------------------------
# intake never alone marks a run FAILED (fail-soft, all failure shapes)
# ---------------------------------------------------------------------------


class TestIntakeNeverFailsRun:
    def test_berror_intake_state_flows_to_classify(self):
        """A broken classifier degrades to the clerk + sorter — never FAIL."""
        from agents.bert_intake import FLAG_OFF
        from graph.routing import after_intake

        # lane unavailable -> today's path (byte-identical pre-BERT)
        assert after_intake(_state(intake_handoff={
            "available": False, "reason": FLAG_OFF, "method": "bert",
        })) == "classify"
        # classifier itself errored -> fail-soft to the sorter
        assert after_intake(_state(intake_handoff={
            "available": False, "reason": "error", "method": "bert",
            "status": "failure",
        })) == "classify"

    def test_intake_stage_never_returns_failed(self, temp_base_dir):
        """The intake stage state carries no FAILED marker on any shape."""
        from graph.build_graph import _ensure_dirs, intake_node

        _ensure_dirs()
        inbox = temp_base_dir / "pipeline" / "inbox"

        broken_handoffs = [
            {"available": False, "reason": "flag_off", "method": "bert"},
            {"available": False, "reason": "no_package", "method": "bert"},
            {"available": False, "reason": "error", "method": "bert",
             "status": "failure"},
            {"available": False, "reason": "no_model", "method": "bert"},
        ]
        for handoff in broken_handoffs:
            with patch("agents.bert_intake.run_bert_intake",
                       return_value=dict(handoff)):
                doc = inbox / f"g-{handoff['reason'].replace('/', '_')}.txt"
                doc.write_text("letter for the intake shape sweep")
                out = intake_node(_state(doc_text="letter", file_path=str(doc)))
            assert "FAILED" not in str(out.get("stage", ""))
            assert out.get("intake_handoff", {}).get("available") is False
        # every shape still carries an always-emitted handoff
        doc = inbox / "g-final.txt"
        doc.write_text("letter for the intake shape sweep")
        with patch("agents.bert_intake.run_bert_intake",
                   return_value=dict(broken_handoffs[0])):
            out = intake_node(_state(doc_text="letter", file_path=str(doc)))
        assert out["intake_handoff"]["available"] is False