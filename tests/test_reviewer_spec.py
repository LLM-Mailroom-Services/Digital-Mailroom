"""The decision reviewer is frozen in the run spec (network-free)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from mailroom_sandbox.decision_backends import SUPPORTED_DECISION_MODELS
from mailroom_sandbox.job import preflight
from mailroom_sandbox.job.spec import DatasetSpec, ReviewerSpec, RunSpec, spec_core
from mailroom_sandbox.runtime import activate

# Computed with the spec implementation at 48c3f8f, before reviewer existed.
# Pin the model and use a Hub request: local /tmp resolves differently on macOS.
PRE_REVIEWER_HASH = "0b474bf41250f04433674038acc55a3e03326be20863bbf0fc0f74506837efd2"


def _reviewer(**overrides) -> dict:
    base = {"backend": "jev", "model": "jev-1.13.0", "classes": {"contract": 0.9}}
    base.update(overrides)
    if base["backend"] == "api":
        # A chat model as decision reviewer is an explicit opt-in (test_decisions_backend.py).
        base.setdefault("allow_chat_model", True)
    if base["backend"] == "decisions":
        base.setdefault("questions", "reviewer_decisions_v3.1.0")
    return base


def _spec(**overrides) -> RunSpec:
    base = dict(
        task="sorter",
        dataset=DatasetSpec(repo="example/corpus", revision="a" * 40),
        engine={"kind": "vllm-local", "model": "Qwen/Qwen3-8B", "modal": None},
    )
    base.update(overrides)
    return RunSpec(**base)


def test_hash_unchanged_without_reviewer():
    spec = _spec()
    assert spec.reviewer is None
    assert "reviewer" not in spec_core(spec)
    assert spec.spec_hash() == PRE_REVIEWER_HASH


def test_hash_changes_with_reviewer_and_cutoff():
    plain = _spec().spec_hash()
    low = _spec(reviewer=_reviewer(classes={"contract": 0.8})).spec_hash()
    high = _spec(reviewer=_reviewer(classes={"contract": 0.9})).spec_hash()
    assert len({plain, low, high}) == 3
    assert _spec(reviewer=_reviewer()).spec_hash() == high


def test_hash_changes_with_cutoff():
    a = _spec(reviewer=_reviewer(classes={"contract": 0.8}))
    b = _spec(reviewer=_reviewer(classes={"contract": 0.85}))
    assert a.spec_hash() != b.spec_hash()


def test_core_freezes_backend_model_and_cutoffs():
    core = spec_core(_spec(reviewer=_reviewer(classes={"contract": 0.9, "insurance_claim": 0.7})))
    assert core["reviewer"] == {
        "backend": "jev",
        "model": "jev-1.13.0",
        "classes": {"contract": 0.9, "insurance_claim": 0.7},
    }


@pytest.mark.parametrize(("backend", "model"), [("jev", "jev-1.13.0"), ("api", "openai/gpt-6-luna"),
                                              ("decisions", "openai/gpt-6-luna-decisions")])
def test_third_party_backends_may_review_correspondence(backend, model):
    spec = _spec(reviewer=_reviewer(backend=backend, model=model, classes={"correspondence": 0.9}))
    assert spec.reviewer.classes == {"correspondence": 0.9}


@pytest.mark.parametrize("model", ["~openai/gpt-luna-latest", "openai/gpt-luna-latest", "openai/gpt-6-luna:batch", "gpt-6-luna", "openrouter/auto"])
def test_api_backend_refuses_a_moving_model_id(model):
    with pytest.raises(ValidationError, match="pinned API model"):
        _spec(reviewer=_reviewer(backend="api", model=model))


def _api_errors(route=None, model="openai/gpt-6-luna", **job):
    routes = {"sorter_reviewer": route} if route else {}
    spec = _spec(reviewer=_reviewer(backend="api", model=model, classes={"contract": 0.9}), agent_routes=routes)
    spec.job = spec.job.model_copy(update={"mock": False, **job})
    return " ".join(preflight._api_reviewer_errors(spec))


def test_api_reviewer_needs_an_openrouter_route_serving_its_model():
    assert "agent_routes.sorter_reviewer" in _api_errors()
    assert "provider openrouter" in _api_errors({"provider": "vllm", "model": "openai/gpt-6-luna", "base_url": "http://127.0.0.1:8000/v1"})
    assert "differs" in _api_errors({"provider": "openrouter", "model": "openai/gpt-5.6-luna"})
    assert _api_errors({"provider": "openrouter", "model": "openai/gpt-6-luna"}) == ""


def test_local_backend_may_use_correspondence():
    spec = _spec(reviewer=_reviewer(backend="local", model="Org/Second", classes={"correspondence": 0.9}))
    assert spec.reviewer.classes == {"correspondence": 0.9}


def _local_errors(model="Org/Second", route=None, mock=False, agent_models=None, sorter_route=None):
    routes = {"sorter_reviewer": route} if route else {}
    if sorter_route:
        routes["sorter"] = sorter_route
    spec = _spec(reviewer=_reviewer(backend="local", model=model, classes={"correspondence": 0.9}),
                 agent_routes=routes, job={"mock": mock}, agent_models=agent_models or {})
    return " ".join(preflight._local_reviewer_errors(spec))


def test_local_reviewer_needs_a_second_model():
    assert "different model" in _local_errors(model="Qwen/Qwen3-8B", mock=True)


def test_local_reviewer_needs_a_route_serving_its_model():
    assert "agent_routes.sorter_reviewer" in _local_errors()
    route = {"provider": "vllm", "model": "Org/Other", "base_url": "http://10.0.0.1:8000/v1"}
    assert "effective model 'Org/Other'" in _local_errors(route=route)
    assert _local_errors(route={**route, "model": "Org/Second"}) == ""


PRIVATE_ROUTE = {"provider": "vllm", "model": "Org/Second", "base_url": "http://10.0.0.1:8000/v1"}


def test_local_reviewer_checks_the_overridden_reviewer_model():
    # agent_models wins over the route pin at activation, so preflight must check it.
    errors = _local_errors(route=PRIVATE_ROUTE, agent_models={"sorter_reviewer": "Qwen/Qwen3-8B"})
    assert "effective model 'Qwen/Qwen3-8B'" in errors and "different model" in errors


def test_local_reviewer_checks_the_effective_sorter_model():
    sorter = {"provider": "vllm", "model": "Org/Second", "base_url": "http://10.0.0.2:8000/v1"}
    assert "different model" in _local_errors(route=PRIVATE_ROUTE, sorter_route=sorter)
    assert "different model" in _local_errors(route=PRIVATE_ROUTE, agent_models={"sorter": "Org/Second"})


@pytest.mark.parametrize("url", ["https://api.example.com/v1", "http://8.8.8.8:8000/v1",
                                 "https://other--app.modal.run/v1"])
def test_local_reviewer_refuses_a_vllm_route_outside_the_run(url, monkeypatch):
    monkeypatch.setenv("MODAL_WORKSPACE", "mine")
    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
    assert "not a loopback/private address" in _local_errors(route={**PRIVATE_ROUTE, "base_url": url})


@pytest.mark.parametrize("url", ["http://localhost:8001/v1", "http://127.0.0.1:8001/v1",
                                 "https://mine--reviewer.modal.run/v1", "https://engine.internal.test/v1"])
def test_local_reviewer_accepts_a_vllm_route_the_run_controls(url, monkeypatch):
    monkeypatch.setenv("MODAL_WORKSPACE", "mine")
    monkeypatch.setenv("VLLM_BASE_URL", "https://engine.internal.test/v1")
    assert _local_errors(route={**PRIVATE_ROUTE, "base_url": url}) == ""


def test_local_reviewer_refuses_a_vllm_route_to_an_openrouter_engine_host():
    # An OpenRouter engine's host is a third party: matching it proves nothing.
    spec = _spec(engine={"kind": "openrouter", "model": "qwen/qwen3.5-9b", "modal": None},
                 profile="openrouter", job={"mock": False},
                 reviewer=_reviewer(backend="local", model="Org/Second", classes={"correspondence": 0.9}),
                 agent_routes={"sorter_reviewer": {**PRIVATE_ROUTE, "base_url": "https://openrouter.ai/api/v1"}})
    assert "not a loopback/private address" in " ".join(preflight._local_reviewer_errors(spec))


def test_local_reviewer_refuses_a_third_party_route():
    route = {"provider": "openrouter", "model": "Org/Second"}
    assert "third party" in _local_errors(route=route)


def test_mock_backend_may_use_correspondence_offline():
    spec = _spec(reviewer=_reviewer(backend="mock", model="mock", classes={"correspondence": 0.9}))
    assert spec.reviewer.classes == {"correspondence": 0.9}


@pytest.mark.parametrize("cutoff", [-0.01, 1.01, float("nan"), float("inf"), True])
def test_rejects_cutoff_outside_unit_interval(cutoff):
    with pytest.raises(ValidationError):
        _spec(reviewer=_reviewer(classes={"contract": cutoff}))


def test_accepts_unit_interval_ends():
    spec = _spec(reviewer=_reviewer(classes={"contract": 0.0, "insurance_claim": 1.0}))
    assert spec.reviewer.classes == {"contract": 0.0, "insurance_claim": 1.0}


def test_rejects_empty_classes():
    with pytest.raises(ValidationError):
        _spec(reviewer=_reviewer(classes={}))


@pytest.mark.parametrize("model", ["jev-latest", "jev-preview", "jev-1", "gpt-4o"])
def test_rejects_unpinned_jev_model(model):
    with pytest.raises(ValidationError, match="pinned|Jev"):
        _spec(reviewer=_reviewer(model=model))


def test_rejects_unknown_backend():
    with pytest.raises(ValidationError):
        _spec(reviewer=_reviewer(backend="gpt"))


def test_rejects_unknown_reviewer_field():
    with pytest.raises(ValidationError):
        _spec(reviewer=_reviewer(extra=1))


def _file_spec(tmp_path, **overrides) -> RunSpec:
    path = tmp_path / "f.jsonl"
    path.write_text(
        json.dumps({"id": "d0", "filename": "0.txt", "doc_text": "t0",
                    "expected": "contract", "expected_subclass": "service"}) + "\n",
        encoding="utf-8",
    )
    return RunSpec(
        run_id=overrides.pop("run_id", "rv-1"),
        task="sorter",
        dataset=DatasetSpec(local_path=f"file://{path}", limit=1),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        **overrides,
    )


def _failed_detail(report) -> str:
    assert report["status"] == "failed", report
    return " ".join(c["detail"] for c in report["checks"] if not c["ok"])


def test_preflight_requires_typesafe_key_for_jev(tmp_path, job_data_dir, monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.runtime._load_dotenv", lambda: None)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    spec = _file_spec(tmp_path, reviewer=_reviewer(), job={"mock": False})
    detail = _failed_detail(preflight.preflight(spec, offline=True))
    assert "TYPESAFE_API_KEY" in detail and "backend mock" in detail


def test_preflight_refuses_jev_in_a_mock_run(tmp_path, job_data_dir, monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.runtime._load_dotenv", lambda: None)
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-secret-value")
    spec = _file_spec(tmp_path, run_id="rv-jev-mock", reviewer=_reviewer(), job={"mock": True})
    detail = _failed_detail(preflight.preflight(spec, offline=True))
    assert "mock run" in detail and "backend mock" in detail
    assert "ts-secret-value" not in detail


def test_preflight_refuses_unknown_reviewer_class(tmp_path, job_data_dir, monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.runtime._load_dotenv", lambda: None)
    spec = _file_spec(tmp_path, run_id="rv-typo", reviewer=_reviewer(backend="mock", model="mock", classes={"contrat": 0.9}))
    detail = _failed_detail(preflight.preflight(spec, offline=True))
    assert "contrat" in detail and "contract" in detail


def test_preflight_passes_with_key_and_never_echoes_it(tmp_path, job_data_dir, monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.runtime._load_dotenv", lambda: None)
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-secret-value")
    spec = _file_spec(tmp_path, run_id="rv-key", reviewer=_reviewer(), job={"mock": False})
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    assert "ts-secret-value" not in json.dumps(report)


def test_preflight_mock_backend_needs_no_key(tmp_path, job_data_dir, monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.runtime._load_dotenv", lambda: None)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    spec = _file_spec(tmp_path, run_id="rv-mock", reviewer=_reviewer(backend="mock", model="mock"))
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"


def test_lock_freezes_the_reviewer(tmp_path, job_data_dir, monkeypatch):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    monkeypatch.setattr("mailroom_sandbox.runtime._load_dotenv", lambda: None)
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-secret-value")
    spec = _file_spec(tmp_path, run_id="rv-lock", reviewer=_reviewer(), job={"mock": False})
    report = preflight.preflight(spec, offline=True)
    lock = RunStore(run_dir(report["run_id"])).read_lock()
    assert lock["reviewer"] == spec.reviewer.model_dump()
    assert "ts-secret-value" not in json.dumps(lock)


@pytest.fixture
def registry():
    from agents import decision_backend

    activate("ollama", load_env_file=False)  # puts the mailroom source on sys.path
    decision_backend.register_decision_backend(None)
    yield decision_backend
    decision_backend.register_decision_backend(None)
    activate("ollama", load_env_file=False)  # rewrite the reviewer block back to all-llm


def test_activate_registers_backend_and_class_modes(registry):
    reviewer = ReviewerSpec(backend="mock", model="mock", classes={"contract": 0.85})
    activate("ollama", load_env_file=False, reviewer=reviewer)

    assert registry.get_decision_backend() is not None
    from pipeline.config import get_review_mode, get_reviewer_config

    assert get_review_mode("contract") == "decision_only"
    assert get_review_mode("insurance_claim") == "llm"
    cfg = get_reviewer_config()
    assert cfg["default_mode"] == "llm"
    assert cfg["by_class"] == {"contract": {"mode": "decision_only", "cutoff": 0.85}}


def test_llm_only_spec_registers_nothing(registry):
    activate("ollama", load_env_file=False)
    assert registry.get_decision_backend() is None
    from pipeline.config import get_review_mode, get_reviewer_config

    assert get_reviewer_config()["by_class"] == {}
    assert get_review_mode("contract") == "llm"


def test_llm_only_activate_after_reviewer_run_clears_everything(registry):
    reviewer = ReviewerSpec(backend="mock", model="mock", classes={"contract": 0.85})
    activate("ollama", load_env_file=False, reviewer=reviewer)
    assert registry.get_decision_backend() is not None

    activate("ollama", load_env_file=False)

    assert registry.get_decision_backend() is None
    from pipeline.config import get_review_mode

    assert get_review_mode("contract") == "llm"


def test_locked_runtime_activates_the_frozen_reviewer(registry):
    from mailroom_sandbox.runtime import locked_runtime

    lock = {"profile": "ollama", "reviewer": _reviewer(backend="mock", model="mock", classes={"contract": 0.7})}
    with locked_runtime(lock, {}):
        activate(
            "ollama", load_env_file=False,
            reviewer=ReviewerSpec(backend="mock", model="mock", classes={"insurance_claim": 0.5}),
        )
    from pipeline.config import get_review_mode

    assert registry.get_decision_backend() is not None
    assert get_review_mode("contract") == "decision_only"
    assert get_review_mode("insurance_claim") == "llm"  # the argument is ignored under a lock


def test_activate_does_not_log_the_api_key(registry, monkeypatch, caplog):
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-secret-value")
    with caplog.at_level("DEBUG"):
        activate(
            "ollama", load_env_file=False,
            reviewer=ReviewerSpec(backend="jev", model="jev-1.13.0", classes={"contract": 0.9}),
        )
    assert "ts-secret-value" not in caplog.text


@pytest.fixture
def create_experiment(tmp_path):
    from mailroom_sandbox import cli

    source = tmp_path / "docs.jsonl"
    source.write_text("".join(
        json.dumps({"id": f"c{i}", "doc_text": "Email from Jane to John.", "expected_doc_class": "contract",
                    "expected_subclass": "nda", "expected_stage": "archived",
                    "expected_fields": {"cuad_clause_labels": ["nda"]}}) + "\n"
        for i in range(3)
    ))

    def create(*options):
        root = tmp_path / ("exp-" + str(len(list(tmp_path.glob("exp-*")))))
        args = ["experiment", "create", root.name, "--doc-class", "contract", "--samples", "3",
                "--local-dataset", str(source), "--trace-sink", "none", "--mock", "--output", str(root), *options]
        return cli.main(args), root

    return create


def test_experiment_create_freezes_the_reviewer(create_experiment):
    from mailroom_sandbox.job.spec import load_run_spec

    code, root = create_experiment(
        "--decision-reviewer", "jev:jev-1.13.0",
        "--decision-class", "contract=0.9", "--decision-class", "insurance_claim=0.75",
    )
    assert code == 0
    spec = load_run_spec(next((root / "runs").glob("*.yaml")))
    assert spec.reviewer.model_dump() == {
        "backend": "jev", "model": "jev-1.13.0", "classes": {"contract": 0.9, "insurance_claim": 0.75},
    }


def test_experiment_create_freezes_the_luna_decisions_reviewer(create_experiment):
    from mailroom_sandbox.job.spec import load_run_spec

    code, root = create_experiment(
        "--decision-reviewer", "decisions:openai/gpt-6-luna-decisions", "--decision-class", "contract=0.78",
    )
    assert code == 0
    spec = load_run_spec(next((root / "runs").glob("*.yaml")))
    assert spec.reviewer.model_dump() == {
        "backend": "decisions", "model": "openai/gpt-6-luna-decisions", "classes": {"contract": 0.78},
        "questions": "reviewer_decisions_v3.1.0",
    }


def test_experiment_create_without_flags_has_no_reviewer(create_experiment):
    from mailroom_sandbox.job.spec import load_run_spec

    code, root = create_experiment()
    assert code == 0
    assert load_run_spec(next((root / "runs").glob("*.yaml"))).reviewer is None


@pytest.mark.parametrize("options", [
    ["--decision-reviewer", "jev:jev-1.13.0"],
    ["--decision-class", "contract=0.9"],
    ["--decision-reviewer", "jev-1.13.0", "--decision-class", "contract=0.9"],
    ["--decision-reviewer", "jev:jev-latest", "--decision-class", "contract=0.9"],
    ["--decision-reviewer", "jev:jev-1.13.0", "--decision-class", "contract"],
    ["--decision-reviewer", "jev:jev-1.13.0", "--decision-class", "contract=high"],
    ["--decision-reviewer", "jev:jev-1.13.0", "--decision-class", "contract=1.5"],
    ["--decision-reviewer", "jev:jev-1.13.0", "--decision-class", "contrat=0.9"],
    ["--decision-reviewer", "mock:mock", "--decision-class", "contract=0.9", "--decision-class", "contract=0.8"],
])
def test_experiment_create_refuses_bad_reviewer_flags(create_experiment, options, tmp_path):
    code, _ = create_experiment(*options)
    assert code == 1
    assert not list(tmp_path.glob("exp-*/experiment.yaml"))


def test_experiment_create_names_bad_key_and_valid_classes(create_experiment, capsys):
    code, _ = create_experiment("--decision-reviewer", "mock:mock", "--decision-class", "contrat=0.9")
    err = capsys.readouterr().err
    assert code == 1 and "contrat" in err and "contract" in err and "insurance_claim" in err


@pytest.mark.parametrize("key", [None, "local-secret"])
@pytest.mark.parametrize("mock", [False, True])
def test_jev_modal_job_rejected_before_key_check(monkeypatch, key, mock):
    if key is None:
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    else:
        monkeypatch.setenv("TYPESAFE_API_KEY", key)
    spec = _spec(reviewer=_reviewer(), job={"mode": "modal", "mock": mock})
    errors = preflight._engine_errors(spec)
    assert len(errors) == 1
    assert ("mock run" if mock else "modal jobs") in errors[0]
    assert "TYPESAFE_API_KEY" not in errors[0]


@pytest.mark.parametrize(("backend", "model"), [(b, m) for b, ms in SUPPORTED_DECISION_MODELS.items() for m in ms])
def test_every_supported_decision_model_freezes(backend, model):
    spec = _spec(reviewer=_reviewer(backend=backend, model=model, classes={"contract": 0.78, "correspondence": 0.64}))
    core = spec_core(spec)["reviewer"]
    assert core["backend"] == backend and core["model"] == model
    if backend == "decisions":
        assert core["questions"] == "reviewer_decisions_v3.1.0"


def test_supported_list_names_jev_and_luna_decisions():
    assert "jev-1.13.0" in SUPPORTED_DECISION_MODELS["jev"]
    assert "openai/gpt-6-luna-decisions" in SUPPORTED_DECISION_MODELS["decisions"]


def test_decisions_reviewer_hash_changes_with_question_set():
    a = _spec(reviewer=_reviewer(backend="decisions", model="openai/gpt-6-luna-decisions", questions="reviewer_decisions_v2"))
    b = _spec(reviewer=_reviewer(backend="decisions", model="openai/gpt-6-luna-decisions", questions="reviewer_decisions_v3.1.0"))
    assert a.spec_hash() != b.spec_hash()


def test_frontrunner_question_set_matches_the_lineage():
    import yaml

    from mailroom_sandbox.decision_backends import decisions_dir, frontrunner_question_set, load_question_set

    lineage = yaml.safe_load((decisions_dir() / "LINEAGE.yaml").read_text())
    stem = frontrunner_question_set()
    assert stem == "reviewer_decisions_v3.1.0"
    assert load_question_set(stem)["version"] == lineage["frontrunner"] == "3.1.0"
    assert [v for v in lineage["versions"] if v["status"] == "frontrunner"] == [
        v for v in lineage["versions"] if v["version"] == lineage["frontrunner"]]


def test_a_paid_reviewer_route_on_a_local_engine_needs_a_reviewer_block():
    """The sorter_reviewer's own openrouter route bills tokens even when the engine is local."""
    local = _spec(task="sorter_reviewer")
    assert not preflight._reviewer_route_bills_tokens(local)
    paid = _spec(task="sorter_reviewer",
                 agent_routes={"sorter_reviewer": {"provider": "openrouter", "model": "openai/gpt-6-luna"}})
    assert preflight._reviewer_route_bills_tokens(paid)
    paid.job = paid.job.model_copy(update={"mock": False})
    assert any("needs a reviewer block" in e for e in preflight._engine_errors(paid))


def test_a_live_extraction_gate_run_needs_a_decisions_reviewer():
    """Without one, every row would raise in _live_extraction_gate."""
    spec = _spec(task="extraction_gate")
    spec.job = spec.job.model_copy(update={"mock": False})
    assert any("live extraction_gate run needs a reviewer block" in e for e in preflight._engine_errors(spec))
    spec.job = spec.job.model_copy(update={"mock": True})
    assert not any("extraction_gate" in e for e in preflight._engine_errors(spec))
