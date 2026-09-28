from pathlib import Path

from agent_mailroom.config.loader import confidence
from agent_mailroom.pipeline.routing import after_arbiter, after_classify, after_extract, after_judge
from agent_mailroom.pipeline.state import RunState


def _state(**kwargs) -> RunState:
    base = RunState(doc_id="x", matter_id="M", original_filename="f.txt", file_path=Path("f.txt"))
    for key, value in kwargs.items():
        setattr(base, key, value)
    return base


def test_severity_gates_match_v060():
    global_cfg = confidence()
    assert global_cfg["retry_max"] == 2
    assert global_cfg["arbiter_retry_max"] == 2
    assert global_cfg["judge_max_passes"] == 3
    contract = confidence("contract")
    assert contract["high"] == 0.98
    assert contract["judge_band_high"] == 0.97
    correspondence = confidence("correspondence")
    assert correspondence["high"] == 0.95
    assert correspondence["low"] == 0.85


def test_high_confidence_classify_goes_to_extract():
    nxt = after_classify(_state(doc_type="contract", classification_confidence=0.99, classification_attempts=1))
    assert nxt == "extract"


def test_medium_band_retries_then_lane_a():
    # correspondence medium band: [0.85, 0.95)
    first = after_classify(_state(doc_type="correspondence", classification_confidence=0.88, classification_attempts=1))
    assert first == "retry_classify"
    second = after_classify(
        _state(doc_type="correspondence", classification_confidence=0.88, classification_attempts=2),
        retry=True,
    )
    assert second == "review_classify"


def test_unknown_goes_to_review():
    nxt = after_classify(_state(doc_type="unknown", classification_confidence=0.4, classification_attempts=1))
    assert nxt == "human_review"


def test_extract_judge_band():
    # contract Lane B: [0.90, 0.97)
    nxt = after_extract(
        _state(doc_type="contract", extraction_confidence=0.93, extraction_attempts=1)
    )
    assert nxt == "judge_verify"


def test_extract_high_skips_judge():
    nxt = after_extract(
        _state(doc_type="contract", extraction_confidence=0.98, extraction_attempts=1)
    )
    assert nxt == "compile_report"


def test_conflict_goes_to_boss():
    nxt = after_extract(
        _state(doc_type="contract", conflict_detected=True, extraction_confidence=0.98, extraction_attempts=1)
    )
    assert nxt == "boss_escalation"


def test_judge_partial_to_arbiter():
    nxt = after_judge(_state(judge_verdict="partial", judge_pass_count=1))
    assert nxt == "arbiter"


def test_arbiter_retry_bound_is_two():
    first = after_arbiter(_state(arbiter_decision="retry_extraction", arbiter_retry_count=1))
    assert first == "retry_extract"
    second = after_arbiter(_state(arbiter_decision="retry_extraction", arbiter_retry_count=2))
    assert second == "retry_extract"
    spent = after_arbiter(_state(arbiter_decision="retry_extraction", arbiter_retry_count=3))
    assert spent == "human_review"


def test_mock_classify_rules_are_well_formed():
    """Every mock rule is (doc_type, conf, needles); a bare (conf, needles)
    tuple left behind by a taxonomy removal made every contract/merger
    document fall through to `unknown` and park in review."""
    from agent_mailroom.config.loader import extractable_types
    from agent_mailroom.llm import mock

    msa = "MASTER SERVICES AGREEMENT\nNOW, THEREFORE ...\nGoverning Law.\nIN WITNESS WHEREOF"
    assert mock.classify(msa)["doc_type"] == "contract"
    filing = "FORM 10-K\nSecurities and Exchange Commission\nItem 1A. Risk Factors"
    assert mock.classify(filing)["doc_type"] == "unknown"
    for text in (msa, "agreement and plan of merger; surviving corporation"):
        assert mock.classify(text)["doc_type"] in extractable_types()


def test_sorter_exception_stays_visible_in_escalation_reason(monkeypatch):
    """A crashing sorter must not masquerade as a genuine unknown document."""
    from pathlib import Path

    from agent_mailroom.pipeline import nodes
    from agent_mailroom.pipeline.state import RunState

    def boom(agent, text):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(nodes, "run_agent", boom)
    state = RunState(doc_id="x", matter_id="M", original_filename="a.txt", file_path=Path("a.txt"))
    state.doc_text = "anything"
    out = nodes.node_classify(state)
    assert out.doc_type == "unknown"
    assert "unknown_or_invalid_type" in out.escalation_reason
    assert "sorter failed: provider exploded" in out.escalation_reason
