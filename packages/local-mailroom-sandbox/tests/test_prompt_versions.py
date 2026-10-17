"""Selecting ANY eval-environment prompt version (archived / frozen / mutation) per role.

The dojo lineage API (``llm_dojo_scoring.prompts.get_prompt_version``) is stubbed at
the seam's one dojo-facing function, ``prompt_versions.lookup_prompt_version``; the
vendored dojo's real texts are wired in phase 2. Nothing here is xfail or skipped.
"""

from __future__ import annotations

import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from mailroom_sandbox import prompt_versions as pv
from mailroom_sandbox import serving_groups
from mailroom_sandbox.cli import main
from mailroom_sandbox.eval import experiment_log, runners, scoring
from mailroom_sandbox.job import preflight, runner
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import DatasetSpec, FAMILY_HF_REVISION, RunSpec, run_dir, spec_hash
from mailroom_sandbox.prompt_registry import deactivate_runtime_overrides


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _v(key: str, role: str, text: str, lineage: str = "mutation") -> SimpleNamespace:
    return SimpleNamespace(
        key=key,
        role=role,
        version=int(key.rsplit("_v", 1)[1]),
        lineage=lineage,
        text=text,
        sha256=_sha(text),
        chars=len(text),
    )


STUB = {
    v.key: v
    for v in (
        _v("sorter_v1", "sorter", "EVAL-ENV sorter v1 {{doc_type_descriptions}}", "frozen"),
        _v("sorter_v2", "sorter", "EVAL-ENV sorter v2 {{doc_type_descriptions}}"),
        _v("sorter_v3", "sorter", "EVAL-ENV sorter v3 {{doc_type_descriptions}}"),
        _v("correspondence_specialist_v0", "correspondence_specialist", "EVAL-ENV corr v0", "archived"),
        _v("correspondence_specialist_v3", "correspondence_specialist", "EVAL-ENV corr v3"),
        _v("correspondence_specialist_v7", "correspondence_specialist", "EVAL-ENV corr v7"),
        _v("contracts_specialist_v2", "contracts_specialist", "EVAL-ENV contracts v2"),
        _v("pipeline_quality_v1", "pipeline_quality", "EVAL-ENV pipeline quality", "frozen"),
    )
}


@pytest.fixture
def stub_dojo(monkeypatch):
    seen: list[str] = []

    def lookup(key):
        seen.append(key)
        if key not in STUB:
            raise pv.PromptSelectionError(f"unknown eval-environment prompt version {key!r}: did you mean ...?")
        return STUB[key]

    monkeypatch.setattr(pv, "lookup_prompt_version", lookup)
    yield seen
    deactivate_runtime_overrides()


@pytest.fixture
def log_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    monkeypatch.setattr(scoring, "reports_dir", lambda: tmp_path / "reports")
    return log


def _records(log):
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


# ── parsing ──────────────────────────────────────────────────────────────────
def test_parse_role_equals_key_and_bare_key():
    got = pv.parse_selection(
        ["correspondence_specialist=correspondence_specialist_v3", "sorter_v3", "contracts_specialist_v2"]
    )
    assert got == {
        "contracts_specialist": "contracts_specialist_v2",
        "correspondence_specialist": "correspondence_specialist_v3",
        "sorter": "sorter_v3",
    }


def test_parse_mapping_and_idempotent_repeat():
    assert pv.parse_selection({"sorter": "sorter_v2"}) == {"sorter": "sorter_v2"}
    assert pv.parse_selection(["sorter_v2", "sorter=sorter_v2"]) == {"sorter": "sorter_v2"}
    assert pv.parse_selection(None) == {} and pv.parse_selection([]) == {}


def test_parse_hyphenated_role_is_inferred():
    assert pv.parse_selection(["judge-classification_v1"]) == {"judge-classification": "judge-classification_v1"}


@pytest.mark.parametrize(
    "bad,match",
    [
        (["sorter_v2", "sorter_v3"], "selected twice"),
        (["nonsense"], "cannot infer a role"),
        (["=sorter_v1"], "malformed"),
        (["sorter="], "malformed"),
        ([""], "empty"),
    ],
)
def test_parse_errors(bad, match):
    with pytest.raises(pv.PromptSelectionError, match=match):
        pv.parse_selection(bad)


# ── errors fail loudly ───────────────────────────────────────────────────────
def test_unknown_key_is_a_hard_error(stub_dojo):
    with pytest.raises(pv.PromptSelectionError, match="sorter_v99"):
        pv.resolve_selection(["sorter_v99"])


def test_key_role_mismatch_is_a_hard_error(stub_dojo):
    with pytest.raises(pv.PromptSelectionError, match="belongs to role 'sorter', not 'contracts_specialist'"):
        pv.resolve_selection(["contracts_specialist=sorter_v3"])


def test_role_the_pipeline_lacks_is_a_hard_error(stub_dojo):
    with pytest.raises(pv.PromptSelectionError, match="not a pipeline agent"):
        pv.resolve_selection(["pipeline_quality_v1"])


def test_dojo_sha_mismatch_is_a_hard_error(stub_dojo, monkeypatch):
    bad = _v("sorter_v3", "sorter", "text")
    bad.sha256 = "0" * 64
    monkeypatch.setattr(pv, "lookup_prompt_version", lambda key: bad)
    with pytest.raises(pv.PromptSelectionError, match="refusing to run text"):
        pv.resolve_prompt("sorter", "sorter_v3")


def test_missing_dojo_lineage_api_is_a_hard_error(monkeypatch):
    import llm_dojo_scoring.prompts as dojo_prompts

    monkeypatch.delattr(dojo_prompts, "get_prompt_version", raising=False)
    with pytest.raises(pv.PromptSelectionError, match="lineage API"):
        pv.lookup_prompt_version("sorter_v3")


def test_dojo_keyerror_becomes_selection_error(monkeypatch):
    import llm_dojo_scoring.prompts as dojo_prompts

    def boom(key):
        raise KeyError("no such key; did you mean sorter_v3?")

    monkeypatch.setattr(dojo_prompts, "get_prompt_version", boom, raising=False)
    with pytest.raises(pv.PromptSelectionError, match="did you mean sorter_v3"):
        pv.lookup_prompt_version("sorter_v33")


def test_resolve_prompt_returns_key_text_sha(stub_dojo):
    key, text, sha = pv.resolve_prompt("correspondence_specialist", "correspondence_specialist_v3")
    assert (key, text, sha) == ("correspondence_specialist_v3", "EVAL-ENV corr v3", _sha("EVAL-ENV corr v3"))


def test_default_is_the_current_simplified_stem_and_never_asks_the_dojo(stub_dojo):
    from mailroom_sandbox.prompts import load_variant

    key, text, sha = pv.resolve_prompt("correspondence_specialist")
    assert key == "correspondence_specialist_v7"
    assert text == load_variant("correspondence_specialist_simplified") and sha == _sha(text)
    assert pv.resolve_prompt("corporate_records_specialist")[0] == "corporate_records_specialist_v6"
    assert stub_dojo == []
    with pytest.raises(pv.PromptSelectionError, match="no sandbox default"):
        pv.resolve_prompt("sorter")


def test_archived_frozen_and_mutation_all_resolve(stub_dojo):
    sel = pv.resolve_selection(["correspondence_specialist_v0"])
    assert sel.prompts["correspondence_specialist"].lineage == "archived"
    assert pv.resolve_selection(["sorter_v1"]).prompts["sorter"].lineage == "frozen"
    assert pv.resolve_selection(["sorter_v3"]).prompts["sorter"].lineage == "mutation"


# ── sorter: eval-env keys collide by name with the mailroom registry ─────────
def test_sorter_v3_resolves_to_eval_env_text_not_the_mailroom_one(stub_dojo, monkeypatch):
    from mailroom_sandbox.runtime import resolve_mailroom_src

    monkeypatch.syspath_prepend(str(resolve_mailroom_src()))
    import langchain_agents.prompts as lc

    mailroom_v3 = lc.PROMPT_VERSIONS["sorter_v3"]
    assert mailroom_v3 != STUB["sorter_v3"].text  # same name, different text

    key, text, sha = pv.resolve_prompt("sorter", "sorter_v3")
    assert text == STUB["sorter_v3"].text and text != mailroom_v3
    assert stub_dojo == ["sorter_v3"]  # read from the dojo lineage, nowhere else

    # a key only the mailroom registry has is unknown to the seam
    assert "sorter_v14" in lc.PROMPT_VERSIONS
    with pytest.raises(pv.PromptSelectionError, match="sorter_v14"):
        pv.resolve_prompt("sorter", "sorter_v14")

    # and the text that reaches the live sorter lookup is the eval-env one
    pv.apply_selection(pv.resolve_selection(["sorter_v3"]))
    assert lc.get_prompt("sorter_v14") == STUB["sorter_v3"].text
    assert lc.get_prompt("sorter_v3") == STUB["sorter_v3"].text


def test_config_stem_sorter_v1_is_not_the_eval_env_sorter_v1(stub_dojo):
    from mailroom_sandbox.prompts import load_variant

    assert load_variant("sorter_v1") != STUB["sorter_v1"].text  # the stem is the mailroom text
    assert pv.resolve_prompt("sorter", "sorter_v1")[1] == STUB["sorter_v1"].text


# ── job spec + run lock ──────────────────────────────────────────────────────
def _spec(tmp_path, prompt, *, task="sorter", run_id="pv-run"):
    path = tmp_path / "f.jsonl"
    path.write_text(
        json.dumps({"id": "d0", "filename": "0.txt", "doc_text": "t", "expected": "contract", "expected_subclass": "service"}) + "\n",
        encoding="utf-8",
    )
    return RunSpec(
        run_id=run_id,
        task=task,
        prompt=prompt,
        dataset=DatasetSpec(local_path=f"file://{path}", limit=1),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job={"mock": True},
    )


def test_spec_accepts_mapping_or_list_and_normalizes(tmp_path):
    a = _spec(tmp_path, {"versions": {"sorter": "sorter_v3"}})
    b = _spec(tmp_path, {"versions": ["sorter_v3"]})
    assert a.prompt["versions"] == b.prompt["versions"] == {"sorter": "sorter_v3"}
    assert a.spec_hash() == b.spec_hash()


def test_spec_hash_differs_per_mutation_and_is_unchanged_without_versions(tmp_path):
    base = _spec(tmp_path, {})
    v2 = _spec(tmp_path, {"versions": {"sorter": "sorter_v2"}})
    v3 = _spec(tmp_path, {"versions": {"sorter": "sorter_v3"}})
    assert len({base.spec_hash(), v2.spec_hash(), v3.spec_hash()}) == 3
    assert base.spec_hash() == spec_hash(_spec(tmp_path, {"default": {"source": "code-default"}}))


def test_spec_versions_and_agents_for_one_role_conflict(tmp_path):
    with pytest.raises(ValueError, match="both set the prompt"):
        _spec(tmp_path, {"versions": {"sorter": "sorter_v3"}, "agents": {"sorter": {"source": "local", "file": "sorter_v1"}}})


def test_preflight_locks_key_sha_and_text(tmp_path, stub_dojo, job_data_dir):
    spec = _spec(tmp_path, {"versions": {"sorter": "sorter_v3"}})
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    store = RunStore(run_dir(report["run_id"]))
    lock = store.read_lock()
    sha = _sha(STUB["sorter_v3"].text)
    agent = lock["prompt"]["agents"]["sorter"]
    assert (agent["source"], agent["key"], agent["sha256"], agent["text"]) == (
        "eval-environment", "sorter_v3", sha, STUB["sorter_v3"].text,
    )
    assert lock["prompt_versions"] == {"sorter": {"key": "sorter_v3", "sha256": sha}}
    assert any(c["name"] == "prompt" and "sorter=sorter_v3" in c["detail"] for c in report["checks"])
    assert store.read_prompt_lock()["agents"]["sorter"]["key"] == "sorter_v3"


@pytest.mark.parametrize(
    "versions,match",
    [
        ({"sorter": "sorter_v99"}, "sorter_v99"),
        ({"contracts_specialist": "sorter_v3"}, "belongs to role"),
        ({"pipeline_quality": "pipeline_quality_v1"}, "not a pipeline agent"),
    ],
)
def test_preflight_fails_loudly_on_a_bad_selection(tmp_path, stub_dojo, job_data_dir, versions, match):
    report = preflight.preflight(_spec(tmp_path, {"versions": versions}), offline=True)
    assert report["status"] == "failed"
    assert report["checks"][0]["name"] == "prompt" and match in report["checks"][0]["detail"]


def test_a_different_mutation_drifts_the_lock(tmp_path, stub_dojo, job_data_dir):
    assert preflight.preflight(_spec(tmp_path, {"versions": {"sorter": "sorter_v2"}}), offline=True)["status"] == "prepared"
    again = preflight.preflight(_spec(tmp_path, {"versions": {"sorter": "sorter_v3"}}), offline=True)
    assert again["status"] == "drift_refused"


def test_job_records_are_stamped_with_the_locked_selection(tmp_path, stub_dojo, job_data_dir):
    spec = _spec(tmp_path, {"versions": {"sorter": "sorter_v3"}})
    report = preflight.preflight(spec, offline=True)
    store = RunStore(run_dir(report["run_id"]))
    rec = runner._build_record(store, "sorter", None, {}, mock=True)
    sha = _sha(STUB["sorter_v3"].text)
    assert rec["prompt_version"] == "sorter_v3" and rec["prompt_sha256"] == sha
    assert rec["eval_environment_prompt_key"] == "sorter_v3"
    assert rec["prompt_versions"] == {"sorter": {"key": "sorter_v3", "sha256": sha}}
    # run the job: the active selection is applied and the delegated record carries it
    runner.run_job(store, mock=True)
    assert pv.active_selection().keys == {"sorter": "sorter_v3"}


def test_job_without_a_selection_is_unchanged(tmp_path, job_data_dir):
    report = preflight.preflight(_spec(tmp_path, {}), offline=True)
    store = RunStore(run_dir(report["run_id"]))
    rec = runner._build_record(store, "sorter", None, {}, mock=True)
    assert "prompt_versions" not in rec and "eval_environment_prompt_key" not in rec
    assert "prompt_versions" not in store.read_lock()


# ── eval path + CLI ──────────────────────────────────────────────────────────
ROW = {"id": "d0", "filename": "d0.txt", "doc_text": "t", "expected": "contract", "expected_doc_class": "contract"}


def test_isolated_eval_record_carries_the_selected_identity(stub_dojo, log_env):
    pv.set_active_selection(pv.resolve_selection(["sorter_v3"]))
    result = runners.run_isolated_eval("sorter", mock=True, rows=[ROW])
    rec = result["record"]
    assert rec["prompt_version"] == "sorter_v3"
    assert rec["prompt_sha256"] == _sha(STUB["sorter_v3"].text)
    assert rec["eval_environment_prompt_key"] == "sorter_v3"
    assert rec["prompt_versions"]["sorter"]["key"] == "sorter_v3"


def test_default_eval_is_unchanged(stub_dojo, log_env):
    rec = runners.run_isolated_eval("sorter", mock=True, rows=[ROW])["record"]
    assert "prompt_versions" not in rec and rec["prompt_version"] != "sorter_v3"


def test_pipeline_record_logs_the_whole_selection(stub_dojo, log_env):
    pv.set_active_selection(pv.resolve_selection(["sorter_v3", "correspondence_specialist_v3"]))
    label, sha = pv.active_selection().label_for("pipeline")
    assert label == "correspondence_specialist_v3+sorter_v3" and len(sha) == 64
    rec = experiment_log.new_record(task="pipeline", prompt_version=label)
    assert rec["prompt_versions"].keys() == {"sorter", "correspondence_specialist"}
    assert "eval_environment_prompt_key" not in rec  # a pipeline is not one role
    # a role that was not selected keeps its own prompt
    assert pv.active_selection().label_for("contracts_specialist") is None


def test_cli_eval_prompt_version_end_to_end(stub_dojo, log_env, capsys):
    rc = main(["eval", "sorter", "--mock", "--prompt-version", "sorter_v3", "--name", "pv_cli"])
    assert rc == 0, capsys.readouterr().err
    (rec,) = [r for r in _records(log_env) if r.get("experiment_name") == "pv_cli"]
    assert rec["prompt_version"] == "sorter_v3"
    assert rec["prompt_sha256"] == _sha(STUB["sorter_v3"].text)


@pytest.mark.parametrize(
    "argv,match",
    [
        (["--prompt-version", "sorter_v99"], "unknown eval-environment prompt version 'sorter_v99'"),
        (["--prompt-version", "contracts_specialist=sorter_v3"], "belongs to role"),
        (["--prompt-version", "pipeline_quality_v1"], "not a pipeline agent"),
        (["--prompt-version", "sorter_v3", "--prompt", "sorter_local_v0"], "use one"),
        (["--prompt-version", "correspondence_specialist_v3"], "does not use the prompt"),
    ],
)
def test_cli_eval_errors_exit_nonzero_with_one_line(stub_dojo, log_env, capsys, argv, match):
    rc = main(["eval", "sorter", "--mock", *argv])
    err = capsys.readouterr().err
    assert rc == 1
    lines = [ln for ln in err.splitlines() if ln.startswith("error:")]
    assert len(lines) == 1 and match in lines[0]


def test_cli_eval_refuses_a_selection_the_task_would_ignore(stub_dojo, log_env, capsys):
    assert main(["eval", "legalbench", "--mock", "--prompt-version", "sorter_v3"]) == 1
    assert "does not use the prompt" in capsys.readouterr().err


def test_cli_run_merges_prompt_versions_into_the_spec(stub_dojo, tmp_path, capsys):
    from mailroom_sandbox.cli import _run_load_spec

    cfg = tmp_path / "run.yaml"
    cfg.write_text(
        "run_id: pv-cli\ntask: sorter\nprompt:\n  versions:\n    sorter: sorter_v2\n"
        "    correspondence_specialist: correspondence_specialist_v0\n",
        encoding="utf-8",
    )
    args = SimpleNamespace(config=str(cfg), prompt_versions=["sorter_v3"])
    spec, _ = _run_load_spec(args)
    assert spec.prompt["versions"] == {
        "correspondence_specialist": "correspondence_specialist_v0",
        "sorter": "sorter_v3",  # the flag wins for its role
    }
    plain, _ = _run_load_spec(SimpleNamespace(config=str(cfg), prompt_versions=[]))
    assert plain.prompt["versions"]["sorter"] == "sorter_v2" and plain.spec_hash() != spec.spec_hash()


# ── grouping: different mutations never pool ─────────────────────────────────
def _srv(kind, model, key, *, sha=None, ttft=0.3):
    profile, provider = {"local": ("ollama", "ollama"), "api": ("openrouter", "openrouter")}[kind]
    rec = {
        "profile": profile, "provider": provider, "model": model, "prompt_version": key, "task": "sorter",
        "dataset_fingerprint": "fp1", "dataset_revision": FAMILY_HF_REVISION, "ttft_seconds": ttft,
        "e2e_latency_seconds": 2.0, "prompt_tokens": 100, "completion_tokens": 40, "n": 5,
        "scores": {"exact_match": 1.0, "f1_macro": 1.0, "accuracy": 1.0},
    }
    if sha is not None:
        rec["prompt_sha256"] = sha
    return experiment_log.new_record(**rec)


def test_different_mutations_form_different_legs():
    sha = {k: _sha(v.text) for k, v in STUB.items()}
    rows = [
        _srv("local", "m", "sorter_v2", sha=sha["sorter_v2"]),
        _srv("local", "m", "sorter_v3", sha=sha["sorter_v3"]),
        _srv("local", "m", "sorter_v3", sha=sha["sorter_v3"], ttft=0.5),
    ]
    legs = serving_groups.group_legs(rows, lambda r: "local")
    assert sorted(len(leg.rows) for leg in legs) == [1, 2]
    assert {leg.identity["prompt_version"] for leg in legs} == {"sorter_v2", "sorter_v3"}


def test_same_label_with_different_bytes_never_pools():
    """Eval-env ``sorter_v1`` vs the mailroom-text stem logged under the same name."""
    rows = [
        _srv("local", "m", "sorter_v1", sha=_sha(STUB["sorter_v1"].text)),
        _srv("local", "m", "sorter_v1", sha="f" * 64),
        _srv("local", "m", "sorter_v1"),  # legacy row: hash unknown
    ]
    assert len(serving_groups.group_legs(rows, lambda r: "local")) == 3
    assert serving_groups.pooled_identity_conflict(rows) == ["prompt_sha256"]


def test_local_and_api_pair_only_on_the_same_prompt_bytes():
    s2, s3 = _sha(STUB["sorter_v2"].text), _sha(STUB["sorter_v3"].text)
    compared = scoring.compare_from_records(
        [
            _srv("local", "qwen3:8b", "sorter_v2", sha=s2),
            _srv("api", "qwen/qwen3.7-flash", "sorter_v2", sha=s2),
            _srv("local", "qwen3:8b", "sorter_v3", sha=s3),
            _srv("api", "qwen/qwen3.7-flash", "sorter_v3", sha=_sha("different bytes")),
        ]
    )
    assert len(compared["groups"]) == 1 and "sorter_v2" in compared["groups"][0]["label"]
    assert len(compared["unpaired"]) == 2
