"""#85 M6e (#108): Tier-1 prior-scoped sorter lane tests.

Contracts pinned here (see the issue's definition of done):

- Tier-1 prior threading: a fast-path handoff with doc_type_pass=True and
  subclass_pass=False sends the verified-type prior through the EXISTING
  ``intake_prior=`` channel, doc_text intact, with the scoped completion
  budget (1024) applied.
- Tier-2 (doc_type not passed) emits NO BERT steer and keeps the full
  budget — the sorter stays full authority.
- Scoped success lands ``classification_method=bert_scoped`` (and the
  ``bert_scoped`` state flag); unscoped remains ``llm_sorter``.
- Overrule path: the sorter may flip the type with cited evidence — the
  BERT prior is advisory; the sorter's verdict wins unchanged.
- Scoped retries RETAIN the verified-type prior (the type is not
  re-litigated on the retry).
- Flag-off / lane-unavailable runs are byte-identical to pre-BERT
  (no prior block, no budget override, ``llm_sorter``).
- Agreement telemetry seam (bert_sorter_agreement, #106) with the drift
  rule documented.
"""

from unittest.mock import patch

import pytest

from graph.state import DocumentState

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _fast_path_handoff(doc_type: str = "contract", subclass: str = "binder",
                       doc_type_pass: bool = True, subclass_pass: bool = False,
                       route: str = "fast_path") -> dict:
    """A #98-shaped intake handoff; mirrors what bert_intake emits."""
    return {
        "available": True,
        "reason": "ok",
        "method": "bert",
        "routing_path": route,
        "route": route,
        "status": "success",
        "doc_type": doc_type,
        "subclass": subclass,
        "score": 0.93,
        "calibrated_confidence": 0.93,
        "subclass_confidence": 0.31,
        "n_windows": 1,
        "artifact_sha": "abc123",
        "guard_failures": [],
        "quality": {"messy": False,
                    "coverage": 1.0,
                    "context_fit": True,
                    "triage_vocab_ok": True,
                    "section_map_ok": True},
        "doc_type_pass": doc_type_pass,
        "subclass_pass": subclass_pass,
    }


def _state(**overrides) -> DocumentState:
    state: DocumentState = {
        "doc_id": "tier1-1",
        "matter_id": "TEST",
        "doc_text": "This is a binder of benefits summary for the group plan.",
        "doc_pages": None,
        "intake_prep": None,
        "bert_triage": None,
        "intake_handoff": None,
        "classification_attempts": 0,
        "retry_count": 0,
        "doc_type": "",
        "classification_confidence": 0.0,
        "extraction_confidence": 0.0,
        "escalation_reason": None,
        "messages": [],
    }
    state.update(overrides)
    return state


_SORTER_RETURN = {
    "doc_type": "contract",
    "contract_subtype": None,
    "doc_subclass": "binder",
    "confidence": 0.97,
    "reasoning": "evidence supports binder of benefits",
}

# ---------------------------------------------------------------------------
# format_bert_type_prior tier guards
# ---------------------------------------------------------------------------


class TestFormatBertTypePriorTierGuards:
    def test_fast_path_with_pass_emits_verified_prior(self):
        from agents.bert_intake import format_bert_type_prior

        handoff = _fast_path_handoff()
        prior = format_bert_type_prior(handoff)
        assert "[bert prior" in prior
        assert "primary class: contract" in prior
        assert "VERIFIED" in prior
        assert "type confidence: 0.93" in prior
        assert "UNVERIFIED" in prior  # subclass explicitly left to the sorter

    def test_doc_type_not_passed_emits_nothing(self):
        from agents.bert_intake import format_bert_type_prior

        handoff = _fast_path_handoff(doc_type_pass=False)
        assert format_bert_type_prior(handoff) == ""

    def test_clerk_only_route_emits_nothing(self):
        from agents.bert_intake import format_bert_type_prior

        handoff = _fast_path_handoff(route="clerk_only")
        assert format_bert_type_prior(handoff) == ""

    def test_no_triage_emits_nothing(self):
        from agents.bert_intake import format_bert_type_prior

        assert format_bert_type_prior(None) == ""


# ---------------------------------------------------------------------------
# classify_node tier behaviour
# ---------------------------------------------------------------------------


class TestClassifyNodeTierLadder:
    def test_tier1_prior_threaded_with_budget(self):
        from graph import build_graph as bg

        handoff = _fast_path_handoff()
        state = _state(bert_triage=dict(handoff), intake_handoff=dict(handoff))
        captured = {}

        def _fake(self, doc_text, pages=None, intake_prior=None, prefix=None,
                  max_tokens=None):
            captured["doc_text"] = doc_text
            captured["intake_prior"] = intake_prior
            captured["max_tokens"] = max_tokens
            return _SORTER_RETURN

        with patch("agents.sorter.SorterAgent.classify_json", _fake):
            result = bg.classify_node(state)

        # DoD: classify receives intake_prior containing the BERT class +
        # threshold marker; doc_text intact.
        assert captured["intake_prior"] is not None
        assert "[bert prior" in captured["intake_prior"]
        assert "primary class: contract" in captured["intake_prior"]
        assert "type confidence: 0.93" in captured["intake_prior"]
        assert captured["doc_text"].startswith("This is a binder")  # untruncated
        # scoped completion budget (2048 -> 1024)
        assert captured["max_tokens"] == 1024
        assert result["classification_method"] == "bert_scoped"
        assert result["bert_scoped"] is True
        assert result["doc_type"] == "contract"

    def test_tier2_no_prior_and_full_budget_when_type_not_passed(self):
        from graph import build_graph as bg

        handoff = _fast_path_handoff(doc_type_pass=False)
        state = _state(bert_triage=dict(handoff), intake_handoff=dict(handoff))
        captured = {}

        def _fake(self, doc_text, pages=None, intake_prior=None, prefix=None,
                  max_tokens=None):
            captured["intake_prior"] = intake_prior
            captured["max_tokens"] = max_tokens
            return _SORTER_RETURN

        with patch("agents.sorter.SorterAgent.classify_json", _fake):
            result = bg.classify_node(state)

        assert not captured["intake_prior"] or "[bert prior" not in captured["intake_prior"]
        assert captured["max_tokens"] is None  # full taxonomy.yaml budget
        assert result["classification_method"] == "llm_sorter"
        assert result["bert_scoped"] is False

    def test_unscoped_method_llm_sorter(self):
        from graph import build_graph as bg

        state = _state()  # no BERT at all
        captured = {}

        def _fake(self, doc_text, pages=None, intake_prior=None, prefix=None,
                  max_tokens=None):
            captured["intake_prior"] = intake_prior
            captured["max_tokens"] = max_tokens
            return _SORTER_RETURN

        with patch("agents.sorter.SorterAgent.classify_json", _fake):
            result = bg.classify_node(state)

        assert captured["max_tokens"] is None
        assert result["classification_method"] == "llm_sorter"
        assert result["bert_scoped"] is False

    def test_overrule_flips_type_with_evidence(self):
        """DoD overrule path: BERT is advisory — the sorter's cited flip wins."""
        from graph import build_graph as bg

        handoff = _fast_path_handoff(doc_type="contract")
        state = _state(bert_triage=dict(handoff), intake_handoff=dict(handoff))

        with patch(
            "agents.sorter.SorterAgent.classify_json",
            return_value={
                "doc_type": "claim",
                "contract_subtype": None,
                "doc_subclass": None,
                "confidence": 0.9,
                "reasoning": "Contract terms absent; this is a claim assertion "
                             "(cited clause 4.1 of the policy).",
            },
        ):
            result = bg.classify_node(state)

        assert result["doc_type"] == "claim"  # sorter authority, BERT overruled
        assert result["classification_method"] == "bert_scoped"  # lane stayed scoped
        assert result["bert_scoped"] is True


# ---------------------------------------------------------------------------
# retry_classify
# ---------------------------------------------------------------------------


class TestRetryClassifyTierScoped:
    def test_scoped_retry_retains_bert_prior(self):
        from graph import build_graph as bg

        handoff = _fast_path_handoff()
        state = _state(
            bert_triage=dict(handoff),
            intake_handoff=dict(handoff),
            doc_type="contract",
            classification_confidence=0.4,
            classification_attempts=1,
        )
        captured = {}

        def _fake(self, doc_text, pages=None, intake_prior=None, prefix=None,
                  max_tokens=None):
            captured["intake_prior"] = intake_prior
            captured["max_tokens"] = max_tokens
            captured["prefix"] = prefix
            return _SORTER_RETURN

        with patch("agents.sorter.SorterAgent.classify_json", _fake):
            result = bg.retry_classify_node(state)

        assert captured["intake_prior"] is not None
        assert "[bert prior" in captured["intake_prior"]  # type NOT re-litigated
        assert "RE-EVALUATION REQUESTED" in captured["prefix"]
        assert captured["max_tokens"] == 1024
        assert result["classification_method"] == "bert_scoped"
        assert result["retry_count"] == 1

    def test_unscoped_retry_byte_identical(self):
        from graph import build_graph as bg

        state = _state(doc_type="contract", classification_confidence=0.4,
                       classification_attempts=1)
        captured = {}

        def _fake(self, doc_text, pages=None, intake_prior=None, prefix=None,
                  max_tokens=None):
            captured["intake_prior"] = intake_prior
            captured["max_tokens"] = max_tokens
            return _SORTER_RETURN

        with patch("agents.sorter.SorterAgent.classify_json", _fake):
            result = bg.retry_classify_node(state)

        assert not captured["intake_prior"] or "[bert prior" not in captured["intake_prior"]
        assert captured["max_tokens"] is None
        assert result["classification_method"] == "llm_sorter"


# ---------------------------------------------------------------------------
# flag-off byte-identical regression (issue DoD, test_intake_agent area)
# ---------------------------------------------------------------------------


class TestFlagOffByteIdentical:
    def test_flag_off_classify_has_no_bert_trace(self):
        from graph import build_graph as bg

        # lane unavailable: flag_off handoff — the pre-BERT composition is
        # intake-prior only; nothing BERT may leak in.
        state = _state(
            intake_handoff={
                "available": False,
                "reason": "flag_off",
                "method": "bert",
                "routing_path": "clerk_only",
                "route": "clerk_only",
                "docs_url": None,
            },
        )
        captured = {}

        def _fake(self, doc_text, pages=None, intake_prior=None, prefix=None,
                  max_tokens=None):
            captured["intake_prior"] = intake_prior
            captured["max_tokens"] = max_tokens
            return _SORTER_RETURN

        with patch("agents.sorter.SorterAgent.classify_json", _fake):
            result = bg.classify_node(state)

        assert "[bert prior" not in (captured["intake_prior"] or "")
        assert captured["max_tokens"] is None
        assert result["classification_method"] == "llm_sorter"
        assert result["bert_scoped"] is False


# ---------------------------------------------------------------------------
# agreement telemetry seam (#106 bert_sorter_agreement)
# ---------------------------------------------------------------------------


class TestAgreementTelemetry:
    def test_agreement_value_true_false_none(self):
        from agents.bert_intake import bert_sorter_agreement_value

        handoff = _fast_path_handoff(doc_type="contract")
        assert bert_sorter_agreement_value(handoff, {
            "doc_type": "Contract",
        }) is True  # case-folded agree
        assert bert_sorter_agreement_value(handoff, {
            "doc_type": "claim",
        }) is False  # flip — drift rule input
        assert bert_sorter_agreement_value(handoff, {}) is None
        assert bert_sorter_agreement_value(None, {"doc_type": "x"}) is None
        assert bert_sorter_agreement_value({}, {}) is None

    def test_handoff_carries_per_head_pass_booleans(self, monkeypatch):
        from agents.bert_intake import run_bert_intake

        # The emission seam derives doc_type_pass from the route and keeps
        # subclass_pass conservative-False when the runner emits nothing.
        import types

        monkeypatch.setenv("MAILROOM_BERT_INTAKE", "1")

        def _fake_runner(doc_text, filename=None):
            return {
                "status": "success",
                "route": "fast_path",
                "doc_type": "contract",
                "subclass": "binder",
                "score": 0.93,
                "calibrated_confidence": 0.93,
                "subclass_confidence": 0.31,
                "agreement": True,
                "n_windows": 1,
                "artifact_sha": "abc123",
                "quality": {"messy": False, "coverage": 1.0},
                "guard_failures": [],
            }

        fake_module = types.SimpleNamespace(
            inference=types.SimpleNamespace(classify_document=_fake_runner)
        )
        with patch("agents.bert_intake._load_mailroom_ml",
                return_value=(fake_module, None)):
            handoff = run_bert_intake("doc text here", filename="x.txt")

        assert handoff["doc_type_pass"] is True  # route == fast_path
        assert handoff["subclass_pass"] is False  # runner silent -> conservative