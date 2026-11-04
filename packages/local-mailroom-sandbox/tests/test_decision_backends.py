"""Decision backends: the Jev adapter and the offline mock (network-free)."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from typing import Any

import pytest

from mailroom_sandbox.decision_backends import build_backend, jev_backend, mock_backend

DOC_TYPES = ["contract", "correspondence", "insurance_claim"]
CATALOGS = {
    "contract": ["nda", "msa"],
    "correspondence": ["letter", "memo"],
    "insurance_claim": ["msa"],  # shared name: the union must dedupe
}


class _FakeAgentState:
    """What the fake Agent saw, and what it answers."""

    def __init__(self) -> None:
        self.init_args: tuple[Any, ...] = ()
        self.init_kwargs: dict[str, Any] = {}
        self.prompts: list[Any] = []
        self.output = SimpleNamespace(doc_type="contract", doc_subclass="nda")
        self.provider_details: dict[str, Any] | None = {
            "confidence": {"doc_type": 0.91, "doc_subclass": 0.4}
        }


@pytest.fixture
def fake_agent(monkeypatch):
    """Stand in for ``pydantic_ai.Agent`` so no model, key or network is touched."""
    state = _FakeAgentState()

    class FakeAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            state.init_args = args
            state.init_kwargs = kwargs

        def run_sync(self, prompt: Any, **_: Any) -> Any:
            state.prompts.append(prompt)
            response = SimpleNamespace(provider_details=state.provider_details)
            return SimpleNamespace(output=state.output, response=response)

    module = types.ModuleType("pydantic_ai")
    module.Agent = FakeAgent  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pydantic_ai", module)
    return state


def test_mock_backend_matches_text():
    backend = mock_backend({"master services": ("contract", 0.97), "dear sir": ("correspondence", 0.8)})
    answer = backend("this is a master services agreement", DOC_TYPES, CATALOGS)
    assert (answer.doc_type, answer.confidence, answer.model) == ("contract", 0.97, "mock")
    assert answer.doc_subclass is None
    assert backend("dear sir, we write", DOC_TYPES, CATALOGS).doc_type == "correspondence"


def test_mock_backend_unmatched_is_unknown_zero():
    answer = mock_backend({"needle": ("contract", 0.9)})("haystack", DOC_TYPES, CATALOGS)
    assert (answer.doc_type, answer.confidence) == ("unknown", 0.0)


def test_jev_rejects_moving_aliases():
    for alias in ("jev-latest", "jev-preview", "jev", "gpt-6"):
        with pytest.raises(ValueError):
            jev_backend(alias)


def test_jev_accepts_versioned_id_without_importing_pydantic_ai(monkeypatch):
    # Construction must not need the optional dependency; only the call does.
    monkeypatch.setitem(sys.modules, "pydantic_ai", None)
    jev_backend("jev-1.13.0")


def test_jev_maps_field_confidence(fake_agent):
    backend = jev_backend("jev-1.13.0")
    answer = backend("some text", DOC_TYPES, CATALOGS)
    assert answer.doc_type == "contract"
    assert answer.doc_subclass == "nda"
    assert answer.confidence == 0.91
    assert answer.model == "jev-1.13.0"
    assert fake_agent.init_args == ("typesafe:jev-1.13.0",)


def test_jev_builds_pick_one_output_and_zero_retries(fake_agent):
    jev_backend("jev-1.13.0")("some text", DOC_TYPES, CATALOGS)
    kwargs = fake_agent.init_kwargs
    assert kwargs["model_settings"] == {"max_retries": 0}
    assert kwargs["retries"] == 0
    schema = kwargs["output_type"].model_json_schema()
    props = schema["properties"]
    assert props["doc_type"]["enum"] == DOC_TYPES
    sub_options = [o for o in props["doc_subclass"]["anyOf"] if "enum" in o]
    assert sub_options[0]["enum"] == ["nda", "msa", "letter", "memo"]
    assert any(o.get("type") == "null" for o in props["doc_subclass"]["anyOf"])
    assert set(schema["required"]) == {"doc_type", "doc_subclass"}


def test_jev_truncates_to_input_cap(fake_agent):
    jev_backend("jev-1.13.0", max_input_chars=10)("x" * 50, DOC_TYPES, CATALOGS)
    assert fake_agent.prompts == ["x" * 10]


def test_jev_default_cap_is_12000(fake_agent):
    jev_backend("jev-1.13.0")("y" * 13000, DOC_TYPES, CATALOGS)
    assert len(fake_agent.prompts[0]) == 12000


def test_jev_missing_confidence_returns_none(fake_agent):
    backend = jev_backend("jev-1.13.0")
    for details in (None, {}, {"confidence": {}}, {"confidence": {"doc_subclass": 0.5}}):
        fake_agent.provider_details = details
        assert backend("t", DOC_TYPES, CATALOGS).confidence is None


def test_jev_non_numeric_confidence_returns_none(fake_agent):
    fake_agent.provider_details = {"confidence": {"doc_type": "high"}}
    assert jev_backend("jev-1.13.0")("t", DOC_TYPES, CATALOGS).confidence is None


def test_jev_no_subclass_catalog_omits_the_field(fake_agent):
    fake_agent.output = SimpleNamespace(doc_type="contract")
    answer = jev_backend("jev-1.13.0")("t", DOC_TYPES, {})
    assert answer.doc_subclass is None
    assert "doc_subclass" not in fake_agent.init_kwargs["output_type"].model_json_schema()["properties"]


def test_jev_subclass_none_stays_none(fake_agent):
    fake_agent.output = SimpleNamespace(doc_type="contract", doc_subclass=None)
    assert jev_backend("jev-1.13.0")("t", DOC_TYPES, CATALOGS).doc_subclass is None


def test_jev_refuses_over_255_options(fake_agent):
    backend = jev_backend("jev-1.13.0")
    with pytest.raises(ValueError, match="255"):
        backend("t", [f"type_{i}" for i in range(256)], {})
    with pytest.raises(ValueError, match="255"):
        backend("t", DOC_TYPES, {"contract": [f"sub_{i}" for i in range(256)]})
    assert fake_agent.prompts == []


def test_jev_needs_two_doc_types(fake_agent):
    with pytest.raises(ValueError):
        jev_backend("jev-1.13.0")("t", ["contract"], {})


def test_build_backend_names():
    assert build_backend("mock", "ignored")("zzz", DOC_TYPES, CATALOGS).doc_type == "unknown"
    assert callable(build_backend("jev", "jev-1.13.0"))
    with pytest.raises(ValueError):
        build_backend("luna", "x")
    with pytest.raises(ValueError):
        build_backend("jev", "jev-latest")


def test_jev_against_real_pydantic_ai(monkeypatch):
    """Drive the real Agent over a stubbed Jev transport: no key, no network."""
    pytest.importorskip("pydantic_ai")
    pytest.importorskip("typesafe_sdk")
    import pydantic_ai
    from pydantic_ai.models.decision import ChoiceAnswer, DecisionResponse
    from pydantic_ai.models.typesafe import TypeSafeModel
    from pydantic_ai.providers.typesafe import TypeSafeProvider
    from pydantic_ai.usage import RequestUsage

    seen: dict[str, Any] = {}

    class StubJev(TypeSafeModel):
        def __init__(self, name: str) -> None:
            super().__init__(name, provider=TypeSafeProvider(api_key="unused"))

        async def decide(self, request, model_settings):
            seen["state"] = request.state
            seen["max_retries"] = model_settings.get("max_retries")
            seen["questions"] = sorted(request.questions)
            answers = {
                "doc_type": ChoiceAnswer(
                    choice="contract", confidence=0.88, probabilities={"contract": 0.88}
                ),
                "doc_subclass": ChoiceAnswer(
                    choice="nda", confidence=0.7, probabilities={"nda": 0.7}
                ),
            }
            return DecisionResponse(
                answers=answers,
                model_name=self._model_name,
                usage=RequestUsage(input_tokens=1, output_tokens=0),
            )

    real_agent = pydantic_ai.Agent

    def agent_with_stub(model, **kwargs):
        assert model == "typesafe:jev-1.13.0"
        return real_agent(StubJev("jev-1.13.0"), **kwargs)

    monkeypatch.setattr(pydantic_ai, "Agent", agent_with_stub)
    answer = jev_backend("jev-1.13.0")("hello world", DOC_TYPES, CATALOGS)
    assert (answer.doc_type, answer.doc_subclass, answer.confidence) == ("contract", "nda", 0.88)
    assert seen["max_retries"] == 0
    assert seen["questions"] == ["doc_subclass", "doc_type"]


def test_local_backend_answers_from_the_in_house_reviewer(monkeypatch):
    from mailroom_sandbox.decision_backends import local_backend
    from mailroom_sandbox.runtime import activate

    activate("ollama", load_env_file=False)
    calls = []

    def review(self, doc_text, **kwargs):
        calls.append((doc_text, kwargs))
        return {"doc_type": "correspondence", "doc_subclass": "memo", "confidence": 0.81}

    monkeypatch.setattr("agents.sorter_reviewer.SorterReviewerAgent.review", review)
    answer = local_backend("Org/Second")("text", DOC_TYPES, CATALOGS)
    assert (answer.doc_type, answer.doc_subclass, answer.confidence, answer.model) == (
        "correspondence", "memo", 0.81, "Org/Second")
    assert calls == [("text", {"valid_doc_types": DOC_TYPES, "doc_subclass_catalogs": CATALOGS})]


def test_build_backend_names_the_local_backend():
    assert callable(build_backend("local", "Org/Second"))
