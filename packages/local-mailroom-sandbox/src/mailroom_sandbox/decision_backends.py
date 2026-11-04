"""Decision-model backends for the Lane A reviewer.

A backend is a plain callable, ``backend(doc_text, doc_types, subclass_catalogs)
-> DecisionAnswer`` (``agents.decision_backend.DecisionBackend`` in the vendored
llm-mailroom). The graph never builds one; the sandbox does, and registers it.

* ``jev_backend`` asks Jev (TypeSafe, through Pydantic AI) two pick-one
  questions: ``doc_type`` and an optional ``doc_subclass``.
* ``local_backend`` runs the ``sorter_reviewer`` agent on the run's own serving
  route, so no document text leaves it.
* ``api_backend`` runs the same agent on a third-party API route, pinned to one
  model id.
* ``decisions_backend`` asks a Decisions-API model (``openai/gpt-6-luna-decisions``
  on OpenRouter) a question set from ``config/decisions``: one request per document,
  a probability for every option, no output tokens.
* ``mock_backend`` answers from a fixed table, for offline runs and tests.

Pydantic AI is an optional dependency (``pip install -e ".[decision]"``). It is
imported inside the call path, so offline installs keep working. The family
types (``DecisionAnswer``) are imported lazily too, after
``mailroom_sandbox.runtime.activate`` has put the mailroom source on ``sys.path``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, Iterable, Literal, Mapping, Optional

if TYPE_CHECKING:  # family types are imported lazily: activate() must run first
    from agents.decision_backend import DecisionBackend
    from pipeline.decision_review import DecisionAnswer

# Jev picks from at most this many options in one question; a 256th is a 400.
MAX_CHOICE_OPTIONS = 255

DEFAULT_MAX_INPUT_CHARS = 12000

# A tuned cutoff is tied to one model version, so only a versioned id is allowed.
_VERSIONED_JEV = re.compile(r"^jev-\d+(\.\d+)+$")

# OpenRouter's moving aliases (``~``, ``-latest``) and routing variants (``:floor``).
_PINNED_API = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$")

_GOAL = "Classify one document from its text."
_DOC_TYPE_QUESTION = "Which document type is this text?"
_DOC_SUBCLASS_QUESTION = "Which subclass of the document type best fits this text?"
_DOCUMENT_FORM_QUESTION = "What form is this document in, as an input to extraction?"


def _answer(
    doc_type: Optional[str], doc_subclass: Optional[str], confidence: Optional[float], model: str
) -> "DecisionAnswer":
    from pipeline.decision_review import DecisionAnswer

    return DecisionAnswer(doc_type, doc_subclass, confidence, model)


def mock_backend(answers: Mapping[str, tuple[str, float]]) -> "DecisionBackend":
    """Answer from ``{substring: (doc_type, confidence)}``; first match wins.

    A document matching no key gets ``("unknown", 0.0)``.
    """
    table = dict(answers)

    def backend(
        doc_text: str, doc_types: list[str], subclass_catalogs: dict[str, list[str]]
    ) -> "DecisionAnswer":
        for needle, (doc_type, confidence) in table.items():
            if needle in doc_text:
                return _answer(doc_type, None, confidence, "mock")
        return _answer("unknown", None, 0.0, "mock")

    return backend


def _checked_options(label: str, options: list[str]) -> list[str]:
    if len(options) > MAX_CHOICE_OPTIONS:
        raise ValueError(
            f"{label}: {len(options)} options exceeds the decision model's "
            f"{MAX_CHOICE_OPTIONS}-option limit for one question"
        )
    return options


def _output_model(doc_types: list[str], subclass_catalogs: Mapping[str, list[str]]) -> type:
    """Pydantic output model: ``doc_type`` pick-one, ``doc_subclass`` optional pick-one."""
    from pydantic import Field, create_model

    types = _checked_options("doc_type", list(dict.fromkeys(doc_types)))
    if len(types) < 2:
        raise ValueError("doc_type needs at least two options for a pick-one question")
    subclasses = _checked_options(
        "doc_subclass",
        list(dict.fromkeys(s for subs in subclass_catalogs.values() for s in subs)),
    )
    fields: dict[str, Any] = {
        "doc_type": (Literal[tuple(types)], Field(description=_DOC_TYPE_QUESTION)),
    }
    if subclasses:
        fields["doc_subclass"] = (
            Optional[Literal[tuple(subclasses)]],
            Field(description=_DOC_SUBCLASS_QUESTION),
        )
    return create_model("DocumentDecision", __doc__=_GOAL, **fields)


def _confidence(provider_details: Any, field: str) -> Optional[float]:
    """The per-field confidence Pydantic AI reports, or None when absent or not a number."""
    if not isinstance(provider_details, dict):
        return None
    by_field = provider_details.get("confidence")
    if not isinstance(by_field, dict):
        return None
    value = by_field.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def jev_backend(
    model: str = "jev-1.13.0", *, max_input_chars: int = DEFAULT_MAX_INPUT_CHARS
) -> "DecisionBackend":
    """Backend over TypeSafe's Jev via Pydantic AI (``TYPESAFE_API_KEY``).

    ``model`` must be a versioned id such as ``jev-1.13.0``; moving aliases
    (``jev-latest``, ``jev-preview``) are refused. The document is cut to
    ``max_input_chars`` before it is sent. The answer's confidence is the model's
    confidence in ``doc_type`` (``None`` when it reports none).
    """
    if not _VERSIONED_JEV.match(model):
        raise ValueError(
            f"{model!r} is not a pinned Jev version (expected e.g. 'jev-1.13.0'); "
            "moving aliases would silently change a tuned cutoff"
        )

    def backend(
        doc_text: str, doc_types: list[str], subclass_catalogs: dict[str, list[str]]
    ) -> "DecisionAnswer":
        try:
            from pydantic_ai import Agent
        except ImportError as exc:
            raise ImportError(
                'Jev backend needs Pydantic AI: pip install -e ".[decision]"'
            ) from exc

        output = _output_model(doc_types, subclass_catalogs)
        # The graph owns the retry budget: no SDK retries, no output retries.
        agent = Agent(
            f"typesafe:{model}",
            output_type=output,
            model_settings={"max_retries": 0},
            retries=0,
        )
        result = agent.run_sync(doc_text[:max_input_chars])
        picked = result.output
        return _answer(
            getattr(picked, "doc_type", None),
            getattr(picked, "doc_subclass", None),
            _confidence(result.response.provider_details, "doc_type"),
            model,
        )

    return backend


def local_backend(model: str) -> "DecisionBackend":
    """Backend over the ``sorter_reviewer`` agent, served in-house.

    ``model`` records which model answered; preflight proves the agent's route
    serves it and that it is not the sorter's own model. Provider errors
    propagate, so the graph's transient and failed-review handling applies.
    """

    def backend(
        doc_text: str, doc_types: list[str], subclass_catalogs: dict[str, list[str]]
    ) -> "DecisionAnswer":
        from agents.sorter_reviewer import SorterReviewerAgent

        picked = SorterReviewerAgent().review(
            doc_text, valid_doc_types=doc_types, doc_subclass_catalogs=subclass_catalogs
        )
        return _answer(picked.get("doc_type"), picked.get("doc_subclass"), picked.get("confidence"), model)

    return backend


def api_backend(model: str) -> "DecisionBackend":
    """Backend over the ``sorter_reviewer`` agent on a third-party API route.

    ``model`` must be an exact provider id such as ``openai/gpt-6-luna``, because a
    tuned cutoff is tied to one model; ``openrouter/*`` ids route dynamically. Preflight proves the agent's route serves it.
    """
    if not _PINNED_API.match(model) or model.endswith("-latest") or model.startswith("openrouter/"):
        raise ValueError(
            f"{model!r} is not a pinned API model id (expected e.g. 'openai/gpt-6-luna'); "
            "moving aliases would silently change a tuned cutoff"
        )
    return local_backend(model)


# ---------------------------------------------------------------------------
# Decisions API (OpenRouter alpha): typed answers with a probability per option.
# ---------------------------------------------------------------------------

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
DECISIONS_DIR_NAME = "decisions"
# Full documents fit: the largest train document is about 1.0M characters (~250k tokens),
# inside Luna Decisions' 1.05M-token context. The cap only guards against a runaway input.
DECISIONS_MAX_INPUT_CHARS = 2_000_000
_TRANSIENT = {408, 429, 500, 502, 503, 504, 524, 529}
NOT_THIS_CLASS = "not_this_class"
SUBCLASS_UNDETERMINED = "undetermined"
# The class-level abstain thresholds a question set may set (4.0.0+). Each one is optional.
ABSTAIN_KEYS = ("margin", "subclass_not_this_class_max", "unknown_max")
SUBCLASS_POLICIES = ("park", "keep_sorter")


def is_decisions_model(model: str | None) -> bool:
    """True for a Decisions-API model id (``openai/gpt-6-luna-decisions``), which has no chat route."""
    return bool(model) and str(model).split(":", 1)[0].endswith("-decisions")


# The decision models the reviewer lane supports, by backend. A model outside this list can
# still be frozen (the spec guards check its shape), but these are the ones calibrated here.
SUPPORTED_DECISION_MODELS: dict[str, tuple[str, ...]] = {
    "jev": ("jev-1.13.0",),
    "decisions": ("openai/gpt-6-luna-decisions",),
}


def frontrunner_question_set() -> str:
    """The question-set stem the lineage (config/decisions/LINEAGE.yaml) names as frontrunner."""
    import yaml

    lineage = yaml.safe_load((decisions_dir() / "LINEAGE.yaml").read_text(encoding="utf-8")) or {}
    front = str(lineage.get("frontrunner") or "")
    for entry in lineage.get("versions") or []:
        if str(entry.get("version")) == front:
            return str(entry["file"]).removesuffix(".yaml")
    raise ValueError(f"LINEAGE.yaml frontrunner {front!r} has no versions entry")


def decisions_dir() -> "Any":
    from mailroom_sandbox.paths import repo_root

    return repo_root() / "config" / DECISIONS_DIR_NAME


def load_question_set(stem: str) -> dict[str, Any]:
    """Parse ``config/decisions/<stem>.yaml`` and check its shape."""
    import yaml

    if not stem or "/" in stem or stem.startswith("."):
        raise ValueError(f"question set {stem!r} must be a plain stem under config/decisions/")
    path = decisions_dir() / f"{stem}.yaml"
    if not path.is_file():
        raise ValueError(f"question set {stem!r} not found at {path}")
    qset = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if qset.get("kind") == EXTRACTION_GATE:
        return _checked_gate_set(stem, qset)
    doc_type = qset.get("doc_type") or {}
    if not isinstance(doc_type.get("criteria"), dict) or len(doc_type["criteria"]) < 2:
        raise ValueError(f"{stem}: doc_type needs instructions and at least two criteria")
    verdict = qset.get("verdict")
    if verdict is not None:
        if not isinstance(verdict.get("criteria"), dict) or len(verdict["criteria"]) < 2:
            raise ValueError(f"{stem}: verdict needs instructions and at least two criteria")
        if set(qset.get("human_verdicts") or []) - set(verdict["criteria"]):
            raise ValueError(f"{stem}: human_verdicts must name verdict options")
    for cls, block in (qset.get("subclass") or {}).items():
        if not isinstance(block, dict) or not isinstance(block.get("criteria"), dict) or not block["criteria"]:
            raise ValueError(f"{stem}: subclass.{cls} needs instructions and criteria")
        if block.get("markers") is not None:
            markers, order = block["markers"], block.get("order") or []
            if not isinstance(markers, dict) or not markers or set(order) - set(markers):
                raise ValueError(f"{stem}: subclass.{cls}.order must name only keys of its markers")
    return qset


EXTRACTION_GATE = "extraction_gate"


def _checked_gate_set(stem: str, qset: dict[str, Any]) -> dict[str, Any]:
    verdict = qset.get("verdict") or {}
    if not isinstance(verdict.get("criteria"), dict) or "accept" not in verdict["criteria"] or len(verdict["criteria"]) < 2:
        raise ValueError(f"{stem}: an extraction gate needs a verdict with an accept option and at least one other")
    if set(qset.get("human_verdicts") or []) - set(verdict["criteria"]):
        raise ValueError(f"{stem}: human_verdicts must name verdict options")
    fields = qset.get("fields") or {}
    if not isinstance(fields, dict) or not fields or not all(isinstance(v, dict) and v for v in fields.values()):
        raise ValueError(f"{stem}: fields must map each gated class to {{field: meaning}}")
    if "{field}" not in str(qset.get("field_instructions") or ""):
        raise ValueError(f"{stem}: field_instructions must contain {{field}}")
    if not str(verdict.get("instructions") or "").strip():
        raise ValueError(f"{stem}: the verdict needs instructions")
    _checked_options("verdict", list(verdict["criteria"]))
    # Build every class's questions now: a format typo ({meanin}, a stray brace) fails at load,
    # not on each row of a paid run.
    for doc_type in fields:
        try:
            gate_questions(qset, doc_type)
        except (KeyError, IndexError, ValueError) as exc:
            raise ValueError(f"{stem}: field_instructions do not format for {doc_type}: {exc!r}") from exc
    return qset


def gate_questions(qset: Mapping[str, Any], doc_type: str, subclass: str | None = None) -> dict[str, Any]:
    """The gate request's questions: the verdict plus one yes/no per key field of ``doc_type``.

    1.3.0+: ``subclass_fields[doc_type][subclass]`` replaces the class rule of the fields it names,
    so the gate is asked only the rule of the document's own template. Unknown or missing
    subclass: the class rules.
    """
    instructions = str(qset["verdict"]["instructions"])
    scope = (qset["verdict"].get("class_scope") or {}).get(doc_type)
    if scope:  # 1.2.0+: the verdict judges only the class's key fields, named here
        instructions = f"{instructions} {scope}"
    questions: dict[str, Any] = {"verdict": {"type": "choice", "instructions": instructions,
                                             "criteria": dict(qset["verdict"]["criteria"])}}
    by_sub = (((qset.get("subclass_fields") or {}).get(doc_type) or {}).get(subclass or "") or {})
    for field, meaning in ((qset.get("fields") or {}).get(doc_type) or {}).items():
        meaning = by_sub.get(field, meaning)
        questions[f"field__{field}"] = {"type": "noul",
                                        "instructions": str(qset["field_instructions"]).format(field=field, meaning=meaning)}
    return questions


def key_field_score(field_support: Mapping[str, float], asked: Iterable[str] | None = None) -> float | None:
    """The gating score of a 1.2.0+ answer: the product of the key-field support probabilities.

    The verdict question is answered on its own and ignores the per-template field rules; on the
    1.3.0 calibration (1,591 labelled documents) this product separates extractions whose key
    fields are all right from the rest far better than ``accept_probability`` (AUROC 0.76 vs
    0.67 overall; corporate 0.89 vs 0.52, insurance 0.87 vs 0.78). None when no field was asked.

    ``asked`` names the fields the request asked about; an asked field with no numeric answer
    counts as support 0.0, so a missing answer can never raise the score.
    """
    import math

    if asked is None:
        values = [float(v) for v in field_support.values()]
    else:
        values = [float(field_support.get(f, 0.0)) for f in asked]
    return round(math.prod(values), 6) if values else None


def extraction_handoff(doc_type: str, extraction: Mapping[str, Any] | None,
                       doc_subclass: str | None = None) -> dict[str, Any]:
    """What the gate sees of a specialist's answer: the class it extracted for and the fields.

    ``doc_subclass`` is the sorter's subclass when the pipeline knows it (selects the 1.3.0+
    template rules). Underscore keys (parse diagnostics, raw text) are dropped; nothing of the
    scoring travels.
    """
    fields = {k: v for k, v in (extraction or {}).items() if not str(k).startswith("_")}
    out: dict[str, Any] = {"doc_type": doc_type, "fields": fields} if extraction else {"doc_type": doc_type, "available": False}
    if doc_subclass:
        out["doc_subclass"] = str(doc_subclass)
    return out


def extraction_gate_backend(model: str, qset: Mapping[str, Any]) -> Callable[[str, Mapping[str, Any]], dict[str, Any]]:
    """The pipeline gate registered with llm-mailroom (``agents.extraction_gate``).

    It answers ``gate(doc_text, handoff)`` with ``decide_extraction``. The subclass is
    the handoff's ``doc_subclass``, which is the **sorter's**, and there is no fallback to a
    labelled subclass: with none, the gate uses the class rules (1.2.0 behaviour). Pipeline
    gate numbers therefore include the sorter's subclass errors, unlike calibration runs.
    """
    if not is_decisions_model(model):
        raise ValueError(f"{model!r} is not a Decisions-API model")
    if qset.get("kind") != EXTRACTION_GATE:
        raise ValueError("the pipeline extraction gate needs an extraction_gate question set")
    version = str(qset.get("version") or "")

    def gate(doc_text: str, handoff: Mapping[str, Any]) -> dict[str, Any]:
        """Review one pipeline extraction."""
        subclass = handoff.get("doc_subclass")
        out = decide_extraction(doc_text, handoff, model=model, qset=qset,
                                subclass=str(subclass) if subclass else None)
        return {**out, "question_set": version, "model": model}

    return gate


def mock_extraction_gate_backend(model: str, qset: Mapping[str, Any]) -> Callable[[str, Mapping[str, Any]], dict[str, Any]]:
    """An offline gate for mock pipeline runs: a fixed neutral answer, no network call, no usage."""
    version = str((qset or {}).get("version") or "")

    def gate(doc_text: str, handoff: Mapping[str, Any]) -> dict[str, Any]:
        """Answer one extraction without calling the Decisions API."""
        return {"doc_type": handoff.get("doc_type"), "verdict": "accept", "accept_probability": 0.5,
                "human_review_probability": 0.0, "verdict_probabilities": {"accept": 0.5}, "field_support": {},
                "question_set": version, "model": model, "mock": True}

    return gate


def _post_decision(body: Mapping[str, Any], *, timeout: float, attempts: int) -> dict[str, Any]:
    """POST one Decisions request and return its JSON; the one retry loop for every caller.

    Transport errors and ``_TRANSIENT`` statuses are retried with backoff (``attempts`` in all);
    any other status, or a refusal, raises at once.
    """
    import os
    import time

    import httpx

    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Decisions backend needs OPENROUTER_API_KEY")
    last: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            resp = httpx.post(DECISIONS_URL, json=dict(body), timeout=timeout,
                              headers={"Authorization": f"Bearer {key}", "X-Title": "local-mailroom-sandbox"})
        except httpx.TransportError as exc:
            last = exc
        else:
            if resp.status_code == 200:
                return resp.json()
            last = RuntimeError(f"Decisions API {resp.status_code}: {resp.text[:300]}")
            if resp.status_code not in _TRANSIENT or "refused to answer" in resp.text:
                raise last
        time.sleep(2 ** attempt)
    raise last or RuntimeError("Decisions API failed")


def decide_extraction(doc_text: str, handoff: Mapping[str, Any], *, model: str, qset: Mapping[str, Any],
                      timeout: float = 120.0, attempts: int = 3, subclass: str | None = None) -> dict[str, Any]:
    """One extraction-gate request: ``{document, extraction_handoff}`` and the gate questions.

    Returns the verdict, ``accept_probability`` (the gating score), the human-review
    probability and one support probability per field. ``subclass`` (else the handoff's
    ``doc_subclass``) selects the template rules of a 1.3.0+ set.
    """
    if not is_decisions_model(model):
        raise ValueError(f"{model!r} is not a Decisions-API model")
    doc_type = str(handoff.get("doc_type") or "")
    limit = int((qset.get("max_input_chars_by_class") or {}).get(doc_type) or qset.get("max_input_chars")
                or DECISIONS_MAX_INPUT_CHARS)
    text = (doc_text or "")[:limit]
    body = {"model": model, "state": {"document": text if text.strip() else "(empty document)",
                                      "extraction_handoff": dict(handoff)},
            "questions": (questions := gate_questions(qset, doc_type, subclass or handoff.get("doc_subclass")))}
    # A whole long document (up to ~250k tokens) takes longer to read than the 120 s default allows.
    data = _post_decision(body, timeout=max(timeout, 60.0 + len(text) / 4_000), attempts=attempts)
    usage = data.get("usage") or {}
    _record_usage(model, usage, agent=EXTRACTION_GATE)
    answers = data.get("answers") or {}
    verdict = answers.get("verdict") or {}
    probs = {k: float(v) for k, v in (verdict.get("probabilities") or {}).items()}
    human = set(qset.get("human_verdicts") or [])
    fields = {}
    for key, answer in answers.items():
        value = (answer or {}).get("noul") if key.startswith("field__") else None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            fields[key.removeprefix("field__")] = float(value)
    return {
        "doc_type": doc_type,
        "doc_subclass": subclass or handoff.get("doc_subclass"),
        "input_chars": len(text),
        "truncated": len(doc_text or "") > limit,
        "verdict": verdict.get("choice"),
        "verdict_probabilities": probs,
        "accept_probability": probs.get("accept"),
        "human_review_probability": sum(v for k, v in probs.items() if k in human) if probs else None,
        "field_support": fields,
        "key_field_score": key_field_score(
            fields, [k.removeprefix("field__") for k in questions if k.startswith("field__")]),
        "confidence": probs.get("accept"),
        "served_model": data.get("model"),
        "usage": {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                  "cost": usage.get("cost")},
    }


def decision_questions(qset: Mapping[str, Any], doc_types: list[str] | None = None) -> dict[str, Any]:
    """The request's ``questions``: ``doc_type`` plus one ``subclass__<class>`` per class.

    ``doc_types`` (the live taxonomy) limits the doc_type options; an option with no
    criterion in the set gets its own name, so a new class is never silently dropped.
    """
    criteria = dict(qset["doc_type"]["criteria"])
    if doc_types:
        criteria = {cls: criteria.get(cls) or cls for cls in dict.fromkeys(doc_types)}
    _checked_options("doc_type", list(criteria))
    questions: dict[str, Any] = {
        "doc_type": {"type": "choice", "instructions": qset["doc_type"].get("instructions") or _DOC_TYPE_QUESTION,
                     "criteria": criteria},
    }
    if qset.get("verdict"):
        # 3.0.0+: the routing outcome against the sorter handoff, including the human-review cases.
        questions["verdict"] = {"type": "choice", "instructions": qset["verdict"]["instructions"],
                                "criteria": dict(qset["verdict"]["criteria"])}
    for cls, block in (qset.get("subclass") or {}).items():
        if doc_types and cls not in criteria:
            continue
        if block.get("markers"):
            # Marker classes: one yes/no question per marker; marker_subclass applies the order.
            for key, text in block["markers"].items():
                questions[f"marker__{cls}__{key}"] = {"type": "noul", "instructions": text}
            continue
        # Every subclass question is asked of every document, and the model refuses a question
        # with no option that fits; NOT_THIS_CLASS is that option. Only the chosen class's
        # answer is used.
        options = {**block["criteria"], NOT_THIS_CLASS: f"The document is not {cls}."}
        _checked_options(f"subclass.{cls}", list(options))
        questions[f"subclass__{cls}"] = {"type": "choice", "instructions": block.get("instructions") or _DOC_SUBCLASS_QUESTION,
                                         "criteria": options}
    return questions


def build_handoff(sorter_doc_type: Any, sorter_doc_subclass: Any, sorter_confidence: Any,
                  *, sorter_unsure: bool | None = None, retried: bool | None = None) -> dict[str, Any]:
    """The sorter handoff the reviewer sees, the same shape in the pipeline and in calibration.

    Every document of a decision class reaches the reviewer at any sorter confidence, so the
    trigger says that, plus whether the sorter ended below its class's low band.
    """
    triggers = ["decision_class_review"]
    if sorter_unsure:
        triggers.append("sorter_below_low_band")
    if retried:
        triggers.append("after_sorter_retry")
    confidence = sorter_confidence if isinstance(sorter_confidence, (int, float)) and not isinstance(sorter_confidence, bool) else None
    return {
        "sorter_doc_type": sorter_doc_type,
        "sorter_doc_subclass": sorter_doc_subclass,
        "sorter_confidence": round(float(confidence), 4) if confidence is not None else None,
        "review_trigger": triggers,
    }


def calibration_handoff(answer: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """A frozen sorter answer as the pipeline would hand it over (low band from the live taxonomy)."""
    if not answer:
        return None
    unsure = None
    try:
        from pipeline.config import get_confidence_thresholds

        conf = answer.get("sorter_confidence")
        if isinstance(conf, (int, float)):
            unsure = float(conf) < float(get_confidence_thresholds(answer.get("sorter_doc_type")).get("low", 0.70))
    except Exception:  # noqa: BLE001 - no mailroom config: leave the band unknown
        unsure = None
    return build_handoff(answer.get("sorter_doc_type"), answer.get("sorter_doc_subclass"),
                         answer.get("sorter_confidence"), sorter_unsure=unsure)


def marker_subclass(block: Mapping[str, Any], answers: Mapping[str, Any], cls: str) -> tuple[str | None, float | None, dict[str, float]]:
    """Subclass from yes/no marker answers: the first marker in ``order`` with p >= 0.5, else ``default``.

    The confidence is the chosen marker's probability, or for the default the probability
    that no earlier marker is present (the smallest of 1 - p).
    """
    probs: dict[str, float] = {}
    for key in block["markers"]:
        value = (answers.get(f"marker__{cls}__{key}") or {}).get("noul")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            probs[key] = float(value)
    for key in block.get("order") or list(block["markers"]):
        if probs.get(key, 0.0) >= 0.5:
            return key, probs[key], probs
    default = block.get("default")
    return default, (min((1.0 - p for p in probs.values()), default=None) if default else None), probs


def _record_usage(model: str, usage: Mapping[str, Any], *, agent: str = "sorter_reviewer") -> None:
    """Count the call in the run's usage accumulator, so job budgets and cost see it."""
    try:
        from pipeline.limits import record_usage
    except ImportError:
        return
    # prompt_/completion_ keys: record_usage reads ``output_tokens or completion_tokens``, so a
    # Decisions call's output_tokens=0 under the output_ key would read as missing and drop the call.
    record_usage({"prompt_tokens": int(usage.get("input_tokens") or 0), "completion_tokens": int(usage.get("output_tokens") or 0)},
                 model=model, agent=agent)


def decide(doc_text: str, *, model: str, questions: Mapping[str, Any], timeout: float = 120.0,
           attempts: int = 3, max_input_chars: int = DECISIONS_MAX_INPUT_CHARS,
           qset: Mapping[str, Any] | None = None, handoff: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """One Decisions request: the document as ``state``, every question at once.

    Returns ``{doc_type, doc_subclass, contract_subtype, confidence, probabilities,
    subclass_confidence, subclass_probabilities, served_model, usage}``. ``confidence`` is
    the probability the model gives the chosen doc_type. Transient HTTP errors are retried
    (``attempts`` in all); anything else raises.
    """
    if not is_decisions_model(model):
        raise ValueError(f"{model!r} is not a Decisions-API model")
    text = doc_text or ""
    if len(text) > max_input_chars:
        text = text[:max_input_chars]
    document = text if text.strip() else "(empty document)"
    state: Any = document
    if (qset or {}).get("handoff"):
        # 3.0.0+: the sorter's answer travels with the document as a claim to check.
        state = {"document": document,
                 "sorter_handoff": dict(handoff) if handoff else {"available": False, "note": "no sorter answer was passed"}}
    body = {"model": model, "state": state, "questions": dict(questions)}
    data = _post_decision(body, timeout=timeout, attempts=attempts)
    usage = data.get("usage") or {}
    _record_usage(model, usage)
    answers = data.get("answers") or {}
    top = answers.get("doc_type") or {}
    doc_type = top.get("choice")
    probs = top.get("probabilities") or {}
    confidence = probs.get(doc_type, top.get("confidence")) if doc_type else None
    block = ((qset or {}).get("subclass") or {}).get(doc_type) or {}
    sub: dict[str, Any] = {}
    if block.get("markers"):
        subclass, sub_conf, sub_probs = marker_subclass(block, answers, doc_type)
    else:
        sub = answers.get(f"subclass__{doc_type}") or {}
        subclass = sub.get("choice")
        sub_probs = {k: v for k, v in (sub.get("probabilities") or {}).items() if k != NOT_THIS_CLASS}
        if subclass == NOT_THIS_CLASS:
            # The subclass question disagrees with doc_type: report the best real subclass.
            subclass = max(sub_probs, key=sub_probs.get) if sub_probs else None
        sub_conf = sub_probs.get(subclass, sub.get("confidence")) if subclass else None
    verdict_answer = answers.get("verdict") or {}
    verdict = verdict_answer.get("choice")
    verdict_probs = verdict_answer.get("probabilities") or {}
    human = set((qset or {}).get("human_verdicts") or [])
    human_probability = sum(float(v) for k, v in verdict_probs.items() if k in human) if verdict_probs else None
    route_to_human = bool(verdict and verdict in human)
    doc_type_probability = float(confidence) if isinstance(confidence, (int, float)) else None
    # The gating confidence: the doc_type probability, or 0 when the verdict sends the document
    # to a person, so every cutoff parks it.
    gated = 0.0 if route_to_human else doc_type_probability
    return {
        "doc_type": doc_type,
        "doc_subclass": subclass,
        "doc_type_probability": doc_type_probability,
        "verdict": verdict,
        "verdict_probabilities": verdict_probs,
        "human_review_probability": human_probability,
        "route_to_human": route_to_human,
        "handoff": dict(handoff) if handoff else None,
        "contract_subtype": subclass if doc_type == "contract" else None,
        "confidence": gated,
        "probabilities": probs,
        "subclass_confidence": sub_conf,
        "subclass_probabilities": sub_probs,
        "served_model": data.get("model"),
        "usage": {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                  "cost": usage.get("cost")},
    }


def decisions_backend(model: str, questions: str | None = None, *, qset: Mapping[str, Any] | None = None) -> "DecisionBackend":
    """Backend over a Decisions-API model with a question set from ``config/decisions``."""
    if not is_decisions_model(model) or not _PINNED_API.match(model.split(":", 1)[0]):
        raise ValueError(f"{model!r} is not a pinned Decisions-API model id (expected e.g. 'openai/gpt-6-luna-decisions')")
    if qset is None and not questions:
        raise ValueError("decisions backend needs questions: <stem> (config/decisions/<stem>.yaml)")
    loaded: dict[str, Any] = {}

    def backend(doc_text: str, doc_types: list[str], subclass_catalogs: dict[str, list[str]],
                handoff: Mapping[str, Any] | None = None) -> "DecisionAnswer":
        if not loaded:
            loaded.update(qset if qset is not None else load_question_set(str(questions)))
        picked = decide(doc_text, model=model, questions=decision_questions(loaded, doc_types),
                        max_input_chars=int(loaded.get("max_input_chars") or DECISIONS_MAX_INPUT_CHARS), qset=loaded,
                        handoff=handoff)
        return _answer(picked["doc_type"], picked["doc_subclass"], picked["confidence"], model)

    return backend


def build_backend(name: str, model: str, *, questions: str | None = None) -> "DecisionBackend":
    """Backend by name: ``jev``, ``local``, ``api``, ``decisions`` (all use ``model``) or ``mock`` (empty table, all unknown)."""
    if name == "decisions":
        return decisions_backend(model, questions)
    if name == "jev":
        return jev_backend(model)
    if name == "local":
        return local_backend(model)
    if name == "mock":
        return mock_backend({})
    if name == "api":
        return api_backend(model)
    raise ValueError(f"unknown decision backend {name!r} (expected 'jev', 'local', 'api', 'decisions' or 'mock')")
