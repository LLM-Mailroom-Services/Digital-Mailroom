"""DMR-091 generation residuals: real CLI/graph/SDK, offline transport only."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types

import pytest
import yaml

from mailroom_sandbox import runtime
from mailroom_sandbox.cli import main
from mailroom_sandbox.eval import experiment_log
from mailroom_sandbox.job import preflight, runner
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import RunSpec, run_dir

pytestmark = pytest.mark.usefixtures("job_data_dir")
KNOBS = {"sorter": {"model": "env-sorter-model", "max_tokens": 137,
                     "temperature": 0.27, "max_input_chars": 5000}}


@pytest.fixture
def source_root(tmp_path, monkeypatch):
    archive = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(archive / "api-evals"))
    root = tmp_path / "sandbox"
    shutil.copytree(archive / "config", root / "config")
    (root / "vendor").symlink_to(archive / "vendor", target_is_directory=True)
    monkeypatch.setenv("SANDBOX_ROOT", str(root))
    return root


def spec_file(tmp_path, source_root, *, count=1, task="sorter"):
    source = tmp_path / "input.jsonl"
    source.write_text("".join(json.dumps({"id": f"d{i}", "filename": f"d{i}.txt",
        "doc_text": "Dear Alice, Please pay invoice 42. Regards Bob.",
        "expected": "correspondence", "question": "Is payment due?", "answer": "Yes"}) + "\n"
        for i in range(count)))
    prompt = source_root / "config/prompts/generation_residual.txt"
    prompt.write_text((prompt.parent / "sorter_local_v0.txt").read_text() + "\nGENERATION ONE SENTINEL\n")
    spec = RunSpec(run_id="generation-residual", task=task, profile="ollama",
        prompt={"agents": {"sorter": {"source": "local", "file": "generation_residual"}}},
        dataset={"provider": "file", "local_path": str(source)},
        engine={"kind": "vllm-local", "model": "engine-model", "modal": None},
        job={"mock": False, "max_retries": 0, "concurrency": 1}, trace={"sink": "none"})
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(spec.model_dump(mode="json")))
    return spec, path, RunStore(run_dir(spec.run_id)), prompt


# These are real OpenAI clients. Only their HTTP transport is substituted.
SDK_SETUP = r'''
import mailroom_sandbox  # Bootstrap vendored imports in fresh subprocesses.
import json, httpx, openai
requests = []
fail_provider = False
cancel_run = None
payload = {"doc_type":"correspondence","confidence":0.99,"reasoning":"offline fixture",
    "communication_type":"email","intent":"payment_demand","subject_matter":"invoice",
    "sender":"Bob","recipient":"Alice","keywords":["invoice"],"completeness":1.0,
    "completeness_label":"complete","decision":"approved","fields_to_fix":[]}
real_client = openai.OpenAI
def transport(request):
    body = json.loads(request.content)
    requests.append(body)
    if cancel_run and len(requests) == 2:
        import subprocess, sys
        out = subprocess.run([sys.executable,"-B","-c",
            "import sys; from mailroom_sandbox.cli import main; raise SystemExit(main(['run','cancel','--run-id',sys.argv[1]]))",
            cancel_run], capture_output=True, text=True, timeout=15)
        assert out.returncode == 0, out.stdout + out.stderr
    if fail_provider:
        return httpx.Response(400,json={"error":{"message":"generation failure fixture","type":"bad_request"}})
    return httpx.Response(200,json={"id":"offline","object":"chat.completion","created":0,
        "model":body["model"],"choices":[{"index":0,"message":{"role":"assistant",
        "content":json.dumps(payload)},"finish_reason":"stop"}],
        "usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}})
def client(*args,**kwargs):
    kwargs["http_client"] = httpx.Client(transport=httpx.MockTransport(transport))
    return real_client(*args,**kwargs)
openai.OpenAI = client
import llm.client
llm.client.OpenAI = client
'''


@pytest.fixture
def sdk(monkeypatch):
    import openai
    import llm.client
    # Restore the two constructor bindings after the genuine SDK boundary fixture.
    monkeypatch.setattr(openai, "OpenAI", openai.OpenAI)
    monkeypatch.setattr(llm.client, "OpenAI", llm.client.OpenAI)
    state = {}
    exec(SDK_SETUP, state)
    return state


def assert_wire(requests):
    assert len(requests) == 2
    for body in requests:
        assert body["model"] == "env-sorter-model"
        assert body.get("max_tokens", body.get("max_completion_tokens")) == 137
        assert body["temperature"] == 0.27
    assert "GENERATION ONE SENTINEL" in json.dumps(requests[0]["messages"])


def test_initial_cli_knobs_survive_cold_resume(tmp_path, source_root, sdk, monkeypatch):
    spec, path, store, _ = spec_file(tmp_path, source_root, count=2)
    monkeypatch.setenv("SANDBOX_AGENT_KNOBS", json.dumps(KNOBS))
    sdk["cancel_run"] = spec.run_id
    assert main(["run", "start", "--config", str(path), "--offline"]) == 2
    assert store.state() == "paused"
    assert store.read_checkpoint()["cursor"] == 1
    assert store.read_lock()["agent_knobs"] == KNOBS
    assert_wire(sdk["requests"])
    code = SDK_SETUP + r'''
import sys
from mailroom_sandbox import runtime
from mailroom_sandbox.cli import main
assert runtime.active() is None
assert main(["run","resume","--run-id",sys.argv[1]]) == 0
print("WIRE=" + json.dumps(requests))
'''
    # A fresh process has a hostile later override; it must replay frozen knobs.
    env = dict(os.environ, SANDBOX_AGENT_KNOBS='{"sorter":{"model":"ambient-later","max_tokens":1,"temperature":0.9}}')
    out = subprocess.run([sys.executable, "-B", "-c", code, spec.run_id],
                         env=env, capture_output=True, text=True, timeout=50)
    assert out.returncode == 0, out.stdout + out.stderr
    assert_wire(json.loads(next(line[5:] for line in out.stdout.splitlines() if line.startswith("WIRE="))))
    assert store.state() == "done"
    assert [row["index"] for row in store.load_items()] == [0, 1]


def test_api_refuses_old_success_after_same_ref_reset_fails(tmp_path, source_root, sdk, monkeypatch):
    from api_evals.invoke import run_task
    spec, path, store, prompt = spec_file(tmp_path, source_root)
    assert main(["run", "start", "--config", str(path), "--offline"]) == 0
    old = experiment_log.load()[-1]
    assert old["scores"]["accuracy"] == 1.0
    old_lock = store.read_lock()
    prompt.write_text(prompt.read_text().replace("GENERATION ONE SENTINEL", "GENERATION TWO SENTINEL"))
    assert preflight.preflight(spec, offline=True, force=True)["status"] == "prepared"
    assert store.read_lock()["spec_hash"] == old_lock["spec_hash"]
    assert store.read_lock()["dataset"]["sha256"] == old_lock["dataset"]["sha256"]
    assert store.read_lock()["prompt_text_sha"] != old_lock["prompt_text_sha"]
    sdk["fail_provider"] = True
    with store.acquire():
        assert runner.run_job(store)["state"] == "failed"
    count = len(sdk["requests"])
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="failed|matching terminal record"):
        run_task(path, prices=(1.0, 2.0))
    assert len(sdk["requests"]) == count
    assert store.state() == "failed"


def test_run_id_resume_refuses_missing_prompt_before_activation(tmp_path, source_root, sdk):
    spec, _, store, _ = spec_file(tmp_path, source_root)
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    store.prompt_lock_path.unlink()
    before = runtime.active()
    # CLI must give a nonzero refusal, preserving the generation and making no calls.
    assert main(["run", "resume", "--run-id", store.run_id]) == 1
    assert sdk["requests"] == []
    assert runtime.active() is before
    assert store.state() == "prepared"


def worker_body(monkeypatch, store):
    """Use the real deployed function body behind inert Modal SDK objects."""
    class Image:
        @classmethod
        def debian_slim(cls, **kwargs): return cls()
        def add_local_python_source(self, *args, **kwargs): return self
        def add_local_dir(self, *args, **kwargs): return self
        def uv_pip_install(self, *args, **kwargs): return self
        def env(self, *args, **kwargs): return self
    class Volume:
        @classmethod
        def from_name(cls, *args, **kwargs): return cls()
        def commit(self): pass
    class Dict:
        @classmethod
        def from_name(cls, *args, **kwargs): return cls()
        def put(self, key, value): pass
    class App:
        def __init__(self, *args, **kwargs): pass
        def function(self, *args, **kwargs): return lambda fn: fn
        def local_entrypoint(self, *args, **kwargs): return lambda fn: fn
    modal = types.ModuleType("modal")
    modal.Image, modal.Volume, modal.Dict, modal.App = Image, Volume, Dict, App
    modal.Secret = types.SimpleNamespace(from_dict=lambda values: values)
    monkeypatch.setitem(sys.modules, "modal", modal)
    path = Path(__file__).resolve().parents[1] / "deploy/modal_job.py"
    spec = importlib.util.spec_from_file_location("residual_worker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RUNS_MOUNT = str(store.dir.parent)
    return module.run_job


@pytest.mark.parametrize("entry", ["runner", "resume", "start", "worker", "api"])
@pytest.mark.parametrize("damage", ["missing_prompt", "changed_prompt", "missing_dataset",
    "changed_dataset", "missing_checkpoint", "corrupt_checkpoint", "wrong_checkpoint_generation"])
def test_all_execution_entries_refuse_damage_without_activation_or_calls(
        tmp_path, source_root, sdk, monkeypatch, entry, damage):
    from api_evals.invoke import run_task
    spec, path, store, _ = spec_file(tmp_path, source_root)
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    if damage.startswith("missing_"):
        {"missing_prompt": store.prompt_lock_path, "missing_dataset": store.dataset_path,
         "missing_checkpoint": store.checkpoint_path}[damage].unlink()
    elif damage == "changed_prompt":
        prompt = store.read_prompt_lock()
        prompt["agents"]["sorter"]["text"] += "\nMUTATED ARTIFACT\n"
        store.write_prompt_lock(prompt)
    elif damage == "changed_dataset":
        store.dataset_path.write_text('{"id":"foreign-dataset"}\n')
    elif damage == "corrupt_checkpoint":
        store.checkpoint_path.write_text('{"state":')
    else:
        cp = store.read_checkpoint()
        cp["generation_id"] = "foreign-generation"
        store.checkpoint_path.write_text(json.dumps(cp))
    before = {p.name: p.read_bytes() for p in store.dir.iterdir() if p.is_file()
              and p.name not in {"run.lock", "cancel.lock"}}
    activation = runtime.active()
    if entry == "resume":
        assert main(["run", "resume", "--run-id", spec.run_id]) == 1
    elif entry == "start":
        assert main(["run", "start", "--config", str(path), "--offline"]) == 1
    else:
        if entry == "runner":
            invoke = lambda: runner.run_job(store)
        elif entry == "worker":
            worker = worker_body(monkeypatch, store)
            invoke = lambda: worker({"run_id": spec.run_id})
        else:
            monkeypatch.setenv("OPENROUTER_API_KEY", "offline-fixture")
            invoke = lambda: run_task(path, prices=(1.0, 2.0))
        with pytest.raises(RuntimeError, match="generation|prompt|dataset|checkpoint|preflight"):
            invoke()
    assert sdk["requests"] == []
    assert runtime.active() is activation
    assert {p.name: p.read_bytes() for p in store.dir.iterdir() if p.is_file()
            and p.name not in {"run.lock", "cancel.lock"}} == before


@pytest.mark.parametrize("entry", ["worker", "resume"])
def test_intact_generation_replays_frozen_prompt_after_stem_changes(
        tmp_path, source_root, sdk, monkeypatch, entry):
    spec, _, store, prompt = spec_file(tmp_path, source_root)
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    prompt.write_text(prompt.read_text().replace("GENERATION ONE SENTINEL", "LATER STEM SENTINEL"))
    if entry == "worker":
        worker_body(monkeypatch, store)({"run_id": spec.run_id})
        assert store.state() == "done"
    else:
        assert main(["run", "resume", "--run-id", spec.run_id]) == 0
    assert len(sdk["requests"]) == 2
    assert "GENERATION ONE SENTINEL" in json.dumps(sdk["requests"][0]["messages"])
    assert "LATER STEM SENTINEL" not in json.dumps(sdk["requests"])


def test_exact_keyless_reuse_ignores_wrong_generation_and_status(tmp_path, source_root, sdk, monkeypatch):
    from api_evals.invoke import run_task
    spec, path, store, _ = spec_file(tmp_path, source_root)
    assert main(["run", "start", "--config", str(path), "--offline"]) == 0
    original = experiment_log.load()[-1]
    assert original["run_state"] == "done"
    identity = original["run_generation"]
    assert identity["dataset_sha256"] == store.read_lock()["dataset"]["sha256"]
    assert identity["prompt_text_sha"] == store.read_lock()["prompt_text_sha"]
    for field in ("lock_sha256", "dataset_sha256", "prompt_text_sha", "run_state", "task"):
        wrong = json.loads(json.dumps(original))
        if field == "run_state":
            wrong[field] = "failed"
        elif field == "task":
            wrong[field] = "unrelated-agent"
        else:
            wrong["run_generation"][field] = "foreign"
        wrong["scores"] = {"accuracy": -99}
        experiment_log.append(wrong)
    count = len(sdk["requests"])
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = run_task(path, prices=(1.0, 2.0))
    assert result["resumed"] is True
    assert result["record"] == original
    assert result["scores"]["accuracy"] == 1.0
    assert result["cost"]["cost_usd"] == pytest.approx(0.00004)
    assert len(sdk["requests"]) == count


def test_legacy_reuse_requires_time_content_and_unreset_generation(tmp_path, source_root, sdk, monkeypatch):
    from api_evals.invoke import run_task
    spec, path, store, _ = spec_file(tmp_path, source_root)
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    # Construct an actual old-format generation, then execute it normally.
    # Neither old empty agent_models nor the new knobs stamp alters spec_hash.
    lock = store.read_lock()
    lock.pop("generation_id")
    store.lock_path.write_text(json.dumps(lock))
    store.write_checkpoint(state="prepared", cursor=0, total=1)
    with store.acquire():
        assert runner.run_job(store)["state"] == "done"
    record = experiment_log.load()[-1]
    record.pop("run_generation")
    record.pop("run_state")
    # Historical per-item records could omit timestamp; that cannot prove reuse.
    record["timestamp"] = store.read_checkpoint()["updated_at"]
    experiment_log.jsonl_path().write_text(json.dumps(record) + "\n")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert run_task(path, prices=(1.0, 2.0))["resumed"] is True
    for field, value in [("timestamp", "1999-01-01T00:00:00+00:00"),
                         ("prompt_sha256", "foreign"), ("dataset_fingerprint", "foreign")]:
        wrong = dict(record, **{field: value})
        experiment_log.jsonl_path().write_text(json.dumps(wrong) + "\n")
        with pytest.raises(RuntimeError, match="matching terminal record"):
            run_task(path, prices=(1.0, 2.0))
    experiment_log.jsonl_path().write_text(json.dumps(record) + "\n")
    (store.dir / "archive-prior-generation").mkdir()
    with pytest.raises(RuntimeError, match="matching terminal record"):
        run_task(path, prices=(1.0, 2.0))


def test_force_reset_isolates_cancel_identity_even_with_same_spec(tmp_path, source_root):
    spec, _, store, _ = spec_file(tmp_path, source_root)
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    previous = store.request_cancel()
    generation = store.read_lock()["generation_id"]
    store.write_checkpoint(state="paused", cursor=0, total=1)
    assert preflight.preflight(spec, offline=True, force=True)["status"] == "prepared"
    assert store.read_lock()["generation_id"] != generation
    store.cancel_path.write_text(json.dumps(previous))
    assert store.pending_cancel() is None
    current = store.request_cancel()
    store.acknowledge_cancel(previous)
    assert store.pending_cancel()["token"] == current["token"]
    store.acknowledge_cancel(current)
    assert store.pending_cancel() is None


def test_old_empty_hash_and_empty_knob_replay_remain_compatible(tmp_path, source_root, monkeypatch, sdk):
    assert RunSpec().spec_hash() == "c9f10813c1da4c634a5100a59ff484d6f7342a598688ab62934efa35593015ee"
    assert RunSpec(agent_models={}).spec_hash() == "c9f10813c1da4c634a5100a59ff484d6f7342a598688ab62934efa35593015ee"
    spec, _, store, _ = spec_file(tmp_path, source_root)
    monkeypatch.delenv("SANDBOX_AGENT_KNOBS", raising=False)
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    assert store.read_lock()["agent_knobs"] == {}
    monkeypatch.setenv("SANDBOX_AGENT_KNOBS", json.dumps(KNOBS))
    assert main(["run", "resume", "--run-id", spec.run_id]) == 0
    assert len(sdk["requests"]) == 2
    assert sdk["requests"][0]["model"] == "engine-model"
    assert sdk["requests"][0].get("max_tokens", sdk["requests"][0].get("max_completion_tokens")) == 2048
    assert sdk["requests"][0]["temperature"] == 0.1


def test_whole_run_global_record_is_stamped_before_append(tmp_path, source_root, monkeypatch):
    from api_evals.invoke import run_task
    spec, path, store, _ = spec_file(tmp_path, source_root, task="judge")
    spec.job.mock = True
    spec.prompt = {"versions": {"judge": "judge_v1"}}
    path.write_text(yaml.safe_dump(spec.model_dump(mode="json")))
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    with store.acquire():
        result = runner.run_job(store)
    assert result["state"] == "done"
    global_record = experiment_log.load()[-1]
    assert global_record["run_generation"] == result["result"]["record"]["run_generation"]
    assert global_record["run_state"] == "done"
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert run_task(path, prices=(1.0, 2.0))["record"] == global_record
