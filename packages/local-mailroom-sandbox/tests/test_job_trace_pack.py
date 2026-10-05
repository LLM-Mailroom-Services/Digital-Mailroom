"""Local-first span mirror + trace pack/verify/prune — network-free."""
from __future__ import annotations

import json
import zipfile

import pytest

pytest.importorskip("opentelemetry.sdk")

from mailroom_sandbox.job import otel, preflight, runner, trace_pack
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import DatasetSpec, RunSpec, run_dir


@pytest.fixture(autouse=True)
def _isolated_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))


def _prepped_store(tmp_path, rows=4, run_id="run-t1", job=None):
    path = tmp_path / "f.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(rows):
            fh.write(json.dumps({"id": f"d{i}", "filename": f"{i}.txt", "doc_text": f"t{i}", "expected": "contract"}) + "\n")
    spec = RunSpec(
        run_id=run_id,
        task="sorter",
        dataset=DatasetSpec(local_path=f"file://{path}", limit=rows),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job=job or {"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    return RunStore(run_dir(report["run_id"]))


def _traced_run(tmp_path, rows=6, concurrency=3):
    store = _prepped_store(tmp_path, rows=rows, job={"mock": True, "concurrency": concurrency})
    mirror = tmp_path / "traces" / f"{store.run_id}.spans.jsonl.gz"
    tracer = otel.configure_tracing(otel.resolve_sink(sink="none", run_id=store.run_id), local_path=mirror)
    assert tracer is not None
    with otel.job_span(tracer, "job.run", run_id=store.run_id):
        summary = runner.run_job(store, mock=None, tracer=tracer)
    otel.flush_tracer(tracer)
    return store, mirror, summary


def test_local_mirror_nests_item_spans_under_run(tmp_path):
    store, mirror, summary = _traced_run(tmp_path)
    assert summary["state"] == "done"
    spans = trace_pack.read_spans(mirror)
    roots = [s for s in spans if s["name"] == "job.run"]
    items = [s for s in spans if s["name"] == "job.item"]
    assert len(roots) == 1 and len(items) == 6
    # Items run on worker threads yet still hang off the run span.
    assert {s["parent_span_id"] for s in items} == {roots[0]["span_id"]}
    assert {s["trace_id"] for s in spans} == {roots[0]["trace_id"]}
    assert all(s["attributes"]["job.ok"] is True for s in items)
    assert roots[0]["resource"]["sandbox.run_id"] == store.run_id


def test_no_sink_and_no_mirror_is_noop():
    assert otel.configure_tracing(otel.resolve_sink(sink="none"), local_path=None) is None


def test_local_trace_path_env_toggle(monkeypatch, tmp_path):
    assert otel.local_trace_path("r1") == tmp_path / "traces" / "r1.spans.jsonl.gz"
    monkeypatch.setenv(otel.LOCAL_TRACE_ENV, "0")
    assert otel.local_trace_path("r1") is None


def test_pack_writes_parquet_zip_with_manifest(tmp_path):
    store, mirror, _ = _traced_run(tmp_path, rows=4, concurrency=2)
    result = trace_pack.pack(store.run_id, experiment="SAND-041", runner="claude", date="2026-10-01", spans_path=mirror)
    assert result["zip"].endswith(f"2026-10-01/claude_SAND-041_{store.run_id}.zip")
    assert result["span_count"] == 5 and result["trace_count"] == 1
    assert result["uploaded"] is None and result["verified"] is False
    with zipfile.ZipFile(result["zip"]) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["table"] in zf.namelist()
    if manifest["table"] == "spans.parquet":
        import io

        import pyarrow.parquet as pq

        with zipfile.ZipFile(result["zip"]) as zf:
            table = pq.read_table(io.BytesIO(zf.read("spans.parquet")))
        assert table.num_rows == 5
        assert {"run_id", "span_id", "duration_ms", "attr.job.ok"} <= set(table.column_names)


def test_pack_upload_verify_then_prune(tmp_path):
    store, mirror, _ = _traced_run(tmp_path, rows=3, concurrency=1)
    dest = tmp_path / "Drive" / "LOGS"
    result = trace_pack.pack(store.run_id, runner="axios", dest=dest, date="2026-10-01", spans_path=mirror)
    assert result["verified"] is True
    assert result["uploaded"] == str(dest / "2026-10-01" / f"axios_run_{store.run_id}.zip")
    removed = trace_pack.prune(result)
    assert set(removed) == {str(mirror), result["zip"]}
    assert not mirror.exists()
    assert (dest / "2026-10-01" / f"axios_run_{store.run_id}.zip").is_file()


def test_prune_refuses_without_verified_upload(tmp_path):
    store, mirror, _ = _traced_run(tmp_path, rows=2, concurrency=1)
    result = trace_pack.pack(store.run_id, spans_path=mirror)
    with pytest.raises(RuntimeError):
        trace_pack.prune(result)
    assert mirror.exists()


def test_prune_refuses_when_upload_changed(tmp_path):
    store, mirror, _ = _traced_run(tmp_path, rows=2, concurrency=1)
    result = trace_pack.pack(store.run_id, dest=tmp_path / "up", spans_path=mirror)
    with open(result["uploaded"], "ab") as fh:
        fh.write(b"x")
    with pytest.raises(RuntimeError):
        trace_pack.prune(result)
    assert mirror.exists()


def test_endpoint_tracer_mirrors_even_with_sink_none(tmp_path):
    from mailroom_sandbox import cli

    tracer = cli._endpoint_tracer("r-endpoint", {"trace": {"sink": "none", "otlp": False}})
    assert tracer is not None
    assert tracer.sandbox_local_path == tmp_path / "traces" / "r-endpoint.spans.jsonl.gz"
    with otel.job_span(tracer, "job.run", run_id="r-endpoint"):
        pass
    otel.flush_tracer(tracer)
    assert len(trace_pack.read_spans(tracer.sandbox_local_path)) == 1
