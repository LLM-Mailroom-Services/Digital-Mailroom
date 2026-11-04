"""DMR-091: offline lifecycle proofs against real stores, CLI and runners.

Only Modal/OpenAI SDK transport is replaced. Expected counts are hand derived.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest
import yaml

from mailroom_sandbox.job import preflight, runner
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import DatasetSpec, RunSpec, run_dir

from test_generation_protocol import modal_fs  # noqa: F401 - pytest fixture

pytestmark = pytest.mark.usefixtures("job_data_dir")


def prepare(tmp_path, *, count=3, concurrency=1, mock=True, task="sorter", run_id="lifecycle", prompt=None, agent_models=None):
    source = tmp_path / "input.jsonl"
    source.write_text("".join(json.dumps({"id": f"d{i}", "filename": f"d{i}.txt",
        "doc_text": "Dear Alice, Please pay invoice 42. Regards Bob.",
        "expected": "correspondence", "question": "Is payment due?", "answer": "Yes"}) + "\n"
        for i in range(count)))
    run_id += "-" + __import__("hashlib").sha256(str(tmp_path).encode()).hexdigest()[:8]
    spec = RunSpec(run_id=run_id, task=task, profile="ollama", prompt=prompt or {}, agent_models=agent_models or {},
        dataset=DatasetSpec(provider="file", local_path=str(source)),
        engine={"kind": "vllm-local", "model": "locked-model", "modal": None},
        job={"mock": mock, "max_retries": 0, "concurrency": concurrency}, trace={"sink": "none"})
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    return spec, RunStore(run_dir(run_id))


def snapshot(store):
    return {p.name: p.read_bytes() for p in store.dir.iterdir() if p.is_file() and p.name not in {"run.lock", "cancel.lock"}}


def test_repeated_preflight_preserves_remote_generation_and_artifacts(tmp_path, monkeypatch, modal_fs):
    spec, store = prepare(tmp_path)
    store.append_item({"index": 0, "item_id": "d0", "predicted": "correspondence", "ok": True})
    store.write_checkpoint(state="running", cursor=1, total=3,
        remote={"call_id": "fc-ALIVE", "fired_at": "2026-10-23T00:00:00+00:00"})
    store.write_cold_boot({"cold_boot_seconds": 7.0})
    before = snapshot(store)
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    assert snapshot(store) == before
    assert store.read_checkpoint()["remote"]["call_id"] == "fc-ALIVE"
    from mailroom_sandbox.job import remote
    import shutil

    # An actual old checkpoint has only call ID/time. Prove its full remote
    # lock via the filesystem-backed CLI boundary before reattaching.
    shutil.copytree(store.dir, modal_fs.volume / store.run_id)
    modal_fs.calls["fc-ALIVE"] = "RUNNING"
    assert remote.ensure_running(store) == {"action": "attached", "call_id": "fc-ALIVE"}
    assert modal_fs.spawned == []
    assert not any(cmd[2] == "put" for cmd in modal_fs.transfers)



@pytest.mark.parametrize("artifact", ["dataset.jsonl", "prompt.lock.json", "checkpoint.json"])
def test_repeat_refuses_missing_generation_artifact(tmp_path, artifact):
    spec, store = prepare(tmp_path)
    (store.dir / artifact).unlink()
    before = snapshot(store)
    assert preflight.preflight(spec, offline=True)["status"] == "failed"
    assert snapshot(store) == before


def test_repeat_refuses_dataset_drift_without_repairing_it(tmp_path):
    spec, store = prepare(tmp_path)
    store.dataset_path.write_text('{"id":"different"}\n')
    before = snapshot(store)
    assert preflight.preflight(spec, offline=True)["status"] == "failed"
    assert snapshot(store) == before


@pytest.mark.parametrize("remote", [None, {"call_id": "fc-ALIVE"}])
def test_force_refuses_running_generation(tmp_path, remote):
    spec, store = prepare(tmp_path)
    store.write_checkpoint(state="running", cursor=0, total=3, remote=remote)
    before = snapshot(store)
    assert preflight.preflight(spec, offline=True, force=True)["status"] == "busy_refused"
    assert snapshot(store) == before


def test_force_refuses_held_writer_even_if_checkpoint_is_prepared(tmp_path):
    spec, store = prepare(tmp_path)
    # A separate process owns the advisory writer lock, like an endpoint run.
    code = "import fcntl,sys; f=open(sys.argv[1],'a+'); fcntl.flock(f,fcntl.LOCK_EX); print('ready',flush=True); sys.stdin.read()"
    proc = subprocess.Popen([sys.executable, "-B", "-c", code, str(store.flock_path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert proc.stdout.readline().strip() == "ready"
        result = subprocess.run([sys.executable, "-B", "-c",
            "import json,sys; from mailroom_sandbox.job.preflight import preflight; from mailroom_sandbox.job.spec import RunSpec; print(json.dumps(preflight(RunSpec(**json.loads(sys.argv[1])),force=True,offline=True)))",
            spec.model_dump_json()], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout.splitlines()[-1])["status"] == "busy_refused"
    finally:
        proc.communicate("", timeout=10)


def test_force_archives_paused_generation_and_control_artifacts(tmp_path):
    spec, store = prepare(tmp_path)
    store.write_checkpoint(state="paused", cursor=0, total=3)
    store.write_cold_boot({"cold_boot_seconds": 7})
    (store.dir / "experiment_log.jsonl").write_text('{"run_id":"old-generation"}\n')
    # Exact names are part of the on-disk cancellation protocol.
    for name in ("cancel.request.json", "cancel.ack.json"):
        (store.dir / name).write_text('{"token":"old"}')
    before = snapshot(store)
    out = preflight.preflight(spec, offline=True, force=True)
    assert out["status"] == "prepared"
    archive = Path(out["archived"])
    assert {p.name: p.read_bytes() for p in archive.iterdir()} == before
    assert not store.cold_boot_path.exists()
    assert not (store.dir / "cancel.request.json").exists()
    assert store.read_checkpoint()["cursor"] == 0


@pytest.mark.parametrize("text", ["plain", "é — 東京"])
def test_valid_unterminated_jsonl_tail_can_append(tmp_path, text):
    store = RunStore(tmp_path / "tail")
    first = {"index": 0, "ok": True, "text": text}
    store.items_path.write_text(json.dumps(first, ensure_ascii=False), encoding="utf-8")
    assert store.load_items() == [first]
    with store.acquire():
        store.append_item({"index": 1, "ok": True})
    assert store.load_items() == [first, {"index": 1, "ok": True}]
    assert len(store.items_path.read_text().splitlines()) == 2


def test_resume_reports_run_wide_errors_and_scored_denominator(tmp_path):
    _, store = prepare(tmp_path)
    store.append_item({"index": 0, "item_id": "d0", "ok": False,
        "expected": "correspondence", "predicted": "", "error": "ValueError: earlier failure"})
    store.write_checkpoint(state="paused", cursor=1, total=3)
    out = runner.run_job(store)
    assert (out["ok"], out["errors"], out["cursor"]) == (2, 1, 3)
    assert out["last_error"] == "ValueError: earlier failure"
    assert out["scores"]["error_count"] == 1
    assert out["scores"]["n"] == 2
    assert out["record"]["scores"]["error_count"] == 1
    assert store.summary()["errors"] == 1


@pytest.mark.parametrize("concurrency", [1, 2])
def test_endpoint_cancel_drains_inflight_then_resumes(tmp_path, monkeypatch, concurrency):
    _, store = prepare(tmp_path, count=5, concurrency=concurrency, mock=False, task="sorter")
    entered = []
    entered_lock = threading.Lock()
    barrier = threading.Barrier(concurrency) if concurrency > 1 else None
    release = threading.Event()

    def predict(task, row, **kwargs):
        # A live endpoint call: the first `concurrency` items block until the
        # operator's cancel has been recorded, so cancel must drain them.
        with entered_lock:
            number = len(entered)
            entered.append(number)
        if number < concurrency:
            if barrier:
                barrier.wait(timeout=10)
            if number > 0:
                assert release.wait(timeout=10)
        return "correspondence", {"prompt_tokens": 3, "completion_tokens": 1, "llm_calls": 1}

    monkeypatch.setattr(runner, "_predict_row", predict)
    immediate = []
    def progress(event):
        if event["cursor"] == 1:
            # Two independent operators can cancel while the run holds its
            # writer lock. Neither may block on that long lock or lose a write.
            commands = [subprocess.Popen([sys.executable, "-B", "-c",
                "import sys; from mailroom_sandbox.cli import main; raise SystemExit(main(['run','cancel','--run-id',sys.argv[1]]))",
                store.run_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for _ in range(2)]
            for cancel in commands:
                stdout, stderr = cancel.communicate(timeout=10)
                assert cancel.returncode == 0, stdout + stderr
                assert '"state": "cancel_requested"' in stdout
            immediate.append((store.read_checkpoint() or {})["state"])
            release.set()
    with store.acquire():
        out = runner.run_job(store, on_event=progress)
    assert out["state"] == "paused"
    assert immediate == ["running"]  # no false acknowledgement before draining
    assert len(entered) == concurrency
    assert sorted(i["index"] for i in store.load_items()) == list(range(concurrency))
    assert store.read_checkpoint()["state"] == "paused"
    with store.acquire():
        resumed = runner.run_job(store)
    assert resumed["state"] == "done"
    assert (resumed["ok"], resumed["errors"], resumed["cursor"]) == (5, 0, 5)
    assert sorted(i["index"] for i in store.load_items()) == [0, 1, 2, 3, 4]
    assert len(entered) == 5


@pytest.mark.parametrize("drift", ["model", "prompt", "dataset"])
def test_api_eval_rejects_spec_drift_before_reusing_terminal_record(tmp_path, monkeypatch, drift):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api-evals"))
    from api_evals.invoke import run_task
    from mailroom_sandbox.eval import experiment_log
    spec, store = prepare(tmp_path)
    store.write_checkpoint(state="done", cursor=3, total=3)
    experiment_log.append({"run_id": store.run_id, "experiment_name": f"sandbox_sorter_{store.run_id}",
        "spec_hash": spec.spec_hash(), "model": "locked-model", "n": 3, "scores": {"n": 3}})
    if drift == "model":
        spec.engine.model = "changed-model"
    elif drift == "prompt":
        spec.prompt = {"agents": {"sorter": {"source": "local", "file": "sorter_local_v0"}}}
    else:
        spec.dataset.limit = 1
    path = tmp_path / "api.yaml"
    path.write_text(yaml.safe_dump(spec.model_dump(mode="json")))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    before = snapshot(store)
    with pytest.raises(RuntimeError, match="drift_refused"):
        run_task(path, prices=(1.0, 2.0))
    assert snapshot(store) == before


@pytest.mark.parametrize("identity", ["substring", "wrong_hash", "wrong_run"])
def test_api_eval_terminal_record_requires_exact_identity(tmp_path, monkeypatch, identity):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api-evals"))
    from api_evals.invoke import run_task
    from mailroom_sandbox.eval import experiment_log
    spec, store = prepare(tmp_path)
    store.write_checkpoint(state="done", cursor=3, total=3)
    record = {"run_id": store.run_id, "experiment_name": f"sandbox_sorter_{store.run_id}",
        "spec_hash": spec.spec_hash(), "model": "locked-model", "n": 3}
    if identity == "substring":
        record.pop("run_id")
        record["experiment_name"] += "-other"
    elif identity == "wrong_hash":
        record["spec_hash"] = "wrong"
    else:
        record["run_id"] = "other"
    experiment_log.append(record)
    path = tmp_path / "api.yaml"
    path.write_text(yaml.safe_dump(spec.model_dump(mode="json")))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="matching terminal record"):
        run_task(path, prices=(1.0, 2.0))


def test_api_eval_exact_terminal_reuse_needs_no_key(tmp_path, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api-evals"))
    from api_evals.invoke import run_task
    from mailroom_sandbox.eval import experiment_log
    spec, store = prepare(tmp_path)
    store.write_checkpoint(state="done", cursor=3, total=3)
    from mailroom_sandbox.job.checkpoint import generation_identity

    experiment_log.append({"run_id": store.run_id, "spec_hash": spec.spec_hash(),
        "run_generation": generation_identity(store.read_lock()), "run_state": "done", "task": spec.task,
        "model": "locked-model", "n": 3, "scores": {"n": 3}, "prompt_tokens": 30, "completion_tokens": 6})
    path = tmp_path / "api.yaml"
    path.write_text(yaml.safe_dump(spec.model_dump(mode="json")))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    out = run_task(path, prices=(1.0, 2.0))
    assert out["resumed"] is True
    assert out["spec_hash"] == spec.spec_hash()
    assert out["cost"]["cost_usd"] == pytest.approx(0.000042)


# Fresh interpreter: no submitting-process activation can accidentally satisfy
# the sorter guard. The real graph reaches an OpenAI SDK MockTransport.
_COLD_PROCESS = r'''
import importlib.util, json, os, sys, types
from pathlib import Path
import httpx, openai, yaml
from mailroom_sandbox import runtime
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job import runner
store = RunStore(Path(sys.argv[1]))
assert runtime.active() is None
requests = []
real_openai = openai.OpenAI
payload = {"doc_type":"correspondence", "confidence":0.99, "reasoning":"Offline transport fixture",
    "communication_type":"email", "intent":"payment_demand", "subject_matter":"unpaid invoice",
    "sender":"Bob", "recipient":"Alice", "keywords":["invoice"], "completeness":1.0,
    "completeness_label":"complete", "decision":"approved", "fields_to_fix":[]}
def transport(request):
    body = json.loads(request.content)
    requests.append(body)
    assert runtime.active() is not None, "cold process did not activate the lock"
    return httpx.Response(200,json={"id":"offline","object":"chat.completion","created":0,
        "model":body["model"],"choices":[{"index":0,"message":{"role":"assistant",
        "content":json.dumps(payload)},"finish_reason":"stop"}],
        "usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}})
def client(*args,**kwargs):
    kwargs["http_client"] = httpx.Client(transport=httpx.MockTransport(transport))
    return real_openai(*args,**kwargs)
openai.OpenAI = client
# Native vendor imports this constructor by name; this is the SDK boundary.
import llm.client
llm.client.OpenAI = client
if sys.argv[2] == "worker":
    class Image:
        @classmethod
        def debian_slim(cls,**kwargs): return cls()
        def add_local_python_source(self,*args,**kwargs): return self
        def add_local_dir(self,*args,**kwargs): return self
        def uv_pip_install(self,*args,**kwargs): return self
        def env(self,*args,**kwargs): return self
    class Volume:
        @classmethod
        def from_name(cls,*args,**kwargs): return cls()
        def commit(self): pass
    class Dict:
        values={}
        @classmethod
        def from_name(cls,*args,**kwargs): return cls()
        def put(self,key,value): self.values[key]=value
    class App:
        def __init__(self,*args,**kwargs): pass
        def function(self,*args,**kwargs): return lambda fn:fn
        def local_entrypoint(self,*args,**kwargs): return lambda fn:fn
    modal=types.ModuleType("modal")
    modal.Image,modal.Volume,modal.Dict,modal.App=Image,Volume,Dict,App
    modal.Secret=types.SimpleNamespace(from_dict=lambda values:values)
    sys.modules["modal"]=modal
    path=Path(sys.argv[3])
    spec=importlib.util.spec_from_file_location("cold_modal_job",path)
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    worker.RUNS_MOUNT=str(store.dir.parent)
    worker.SANDBOX_ROOT=os.environ["SANDBOX_ROOT"]
    out=worker.run_job({"run_id":store.run_id})
    values = list(Dict.values.values())
    assert len(values) == 1 and values[0]["state"] == "done", out
    from mailroom_sandbox.job.checkpoint import generation_identity
    assert values[0]["run_generation"] == generation_identity(store.read_lock())
else:
    from mailroom_sandbox.cli import main
    rc=main(["run","resume","--run-id",store.run_id])
    assert rc==0,(rc,store.summary())
assert store.read_checkpoint()["state"] == "done",store.load_items()
assert requests,"real live sorter never reached SDK transport"
assert runtime.active().profile_name == "ollama"
assert runtime.active().agent_models == {"judge":"locked-judge"}
assert runtime.active().agent_knobs == {"sorter":{"max_tokens":321,"max_input_chars":9876,
    "chunk_chars":2345,"temperature":0.2,"model":"locked-sorter"}}
assert requests[0]["model"] == "locked-sorter",requests[0]
assert requests[0].get("max_tokens",requests[0].get("max_completion_tokens")) == 321,requests[0]
assert "LOCKED SORTER SENTINEL" in json.dumps(requests[0]["messages"])
print("COLD_PROOF="+json.dumps({"requests":len(requests),"state":"done"}))
'''


@pytest.mark.parametrize("entry", ["worker", "resume"])
def test_cold_execution_activates_locked_runtime_at_sdk_boundary(tmp_path, monkeypatch, entry):
    import shutil

    original = Path(os.environ["SANDBOX_ROOT"])
    root = tmp_path / "sandbox"
    shutil.copytree(original / "config", root / "config")
    (root / "vendor").symlink_to(original / "vendor", target_is_directory=True)
    monkeypatch.setenv("SANDBOX_ROOT", str(root))
    text = (root / "config/prompts/sorter_local_v0.txt").read_text()
    (root / "config/prompts/cold_lifecycle.txt").write_text(text + "\nLOCKED SORTER SENTINEL\n")
    monkeypatch.setenv("SANDBOX_AGENT_KNOBS", json.dumps({"sorter": {
        "max_tokens": 321, "max_input_chars": 9876, "chunk_chars": 2345,
        "temperature": 0.2, "model": "locked-sorter"}}))
    _, store = prepare(tmp_path, count=1, mock=False, agent_models={"judge": "locked-judge"},
        prompt={"agents": {"sorter": {"source": "local", "file": "cold_lifecycle"}}})
    env = dict(os.environ, SANDBOX_AGENT_KNOBS='{"sorter":{"max_tokens":1}}')
    result = subprocess.run([sys.executable, "-B", "-c", _COLD_PROCESS, str(store.dir), entry,
        str(Path(__file__).resolve().parents[1] / "deploy/modal_job.py")],
        env=env, capture_output=True, text=True, timeout=50)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"state": "done"' in result.stdout


def test_explicit_agent_models_are_locked_and_hashed(tmp_path):
    spec, _ = prepare(tmp_path)
    original_hash = spec.spec_hash()
    spec = RunSpec.model_validate({**spec.model_dump(), "run_id": "explicit-models",
        "agent_models": {"judge": "locked-judge", "sorter": "locked-sorter"}})
    assert spec.spec_hash() != original_hash
    assert preflight.preflight(spec, offline=True)["status"] == "prepared"
    assert RunStore(run_dir(spec.run_id)).read_lock()["agent_models"] == {
        "judge": "locked-judge", "sorter": "locked-sorter"}


def test_whole_run_reactivation_keeps_knobs_models_and_prompt_selection(tmp_path):
    # Existing isolated eval calls activate a second time; this must not erase
    # ANY locked generation knob or replace the dojo prompt selection.
    from mailroom_sandbox import runtime, prompt_versions
    spec, store = prepare(tmp_path, count=1, task="judge", prompt={"versions": {"judge": "judge_v1"}})
    lock = store.read_lock()
    lock["agent_models"] = {"judge": "locked-judge"}
    lock["agent_knobs"] = {"judge": {"max_tokens": 321, "max_input_chars": 9876,
        "chunk_chars": 2345, "temperature": 0.2, "model": "knob-model",
        "reasoning_effort": "low", "top_p": 0.8, "top_k": 20,
        "presence_penalty": 0.1, "length_retries": 2}}
    store.lock_path.write_text(json.dumps(lock))
    prompt_versions.set_active_selection(prompt_versions.resolve_selection(["sorter_v1"]))
    out = runner.run_job(store)
    assert out["state"] == "done"
    assert prompt_versions.active_selection().keys == {"judge": "judge_v1"}
    assert out["result"]["record"]["prompt_versions"]["judge"]["key"] == "judge_v1"
    assert runtime.active().agent_models == {"judge": "locked-judge"}
    assert runtime.active().agent_knobs == {"judge": {"max_tokens": 321, "max_input_chars": 9876,
        "chunk_chars": 2345, "temperature": 0.2, "model": "knob-model",
        "reasoning_effort": "low", "top_p": 0.8, "top_k": 20,
        "presence_penalty": 0.1, "length_retries": 2}}
    taxonomy = yaml.safe_load(runtime.active().taxonomy_path.read_text())
    assert taxonomy["agents"]["judge"]["model"] == "locked-judge"
    assert taxonomy["agents"]["judge"]["max_tokens"] == 321
    assert taxonomy["agents"]["judge"]["temperature"] == 0.2


@pytest.mark.parametrize("override", [
    ["--model", "different-model"],
    ["--agent-model", "judge=different-model"],
    ["--prompt-version", "sorter=sorter_v1"],
])
def test_run_id_resume_refuses_runtime_override_drift(tmp_path, override):
    from mailroom_sandbox.cli import main

    _, store = prepare(tmp_path)
    before = snapshot(store)
    argv = (["run", "resume", "--run-id", store.run_id, *override]
            if override[0] == "--prompt-version"
            else ["run", *override, "resume", "--run-id", store.run_id])
    assert main(argv) == 3
    assert snapshot(store) == before



def test_start_freezes_explicit_model_overrides(tmp_path):
    from mailroom_sandbox.cli import main

    spec, _ = prepare(tmp_path)
    spec.run_id = "start-overrides"
    path = tmp_path / "start.yaml"
    path.write_text(yaml.safe_dump(spec.model_dump(mode="json")))
    assert main(["run", "--model", "cli-model", "--agent-model", "judge=cli-judge",
        "start", "--config", str(path), "--offline"]) == 0
    lock = RunStore(run_dir(spec.run_id)).read_lock()
    assert lock["engine"]["model"] == "cli-model"
    assert lock["agent_models"] == {"judge": "cli-judge"}
    assert lock["spec_core"]["agent_models"] == {"judge": "cli-judge"}
