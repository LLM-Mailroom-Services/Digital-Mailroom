"""SAND-032 reports read grouped serving artifacts for metrics and cost."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml


def test_load_uses_grouped_serving_records_for_metrics_and_cost(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts" / "sand032" / "report.py"
    monkeypatch.syspath_prepend(str(script.parent))
    spec = importlib.util.spec_from_file_location("sand032_report", script)
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)

    serving_path = tmp_path / report.SERVING.relative_to(report.ROOT)
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(report, "RUNS", tmp_path / "data" / "runtime" / "runs")
    monkeypatch.setattr(report, "RT", tmp_path / "data" / "runtime" / "sand032")
    monkeypatch.setattr(report, "SERVING", serving_path)

    run_id = "sand032-l0-baseline"
    configs = tmp_path / "config" / "runs"
    configs.mkdir(parents=True)
    (configs / f"{run_id}.yaml").write_text(yaml.safe_dump({
        "engine": {"modal": {"max_containers": 2}},
        "job": {"concurrency": 8},
    }), encoding="utf-8")
    run = report.RUNS / run_id
    run.mkdir(parents=True)
    (run / "items.jsonl").write_text(json.dumps({"item_id": "DOC-1", "ok": True}) + "\n")
    serving = {"wall_seconds": 3600, "tokens_per_second": 12}
    grouped = tmp_path / "reports" / "serving" / "SAND-32"
    grouped.mkdir(parents=True)
    (grouped / f"{run_id}.serving.json").write_text(json.dumps(serving))

    data = report.load(run_id)
    assert data["serving"] == serving
    metrics = report.metrics(data)
    assert metrics["wall"] == 3600
    assert metrics["tps"] == 12
    assert metrics["busy_usd"] == pytest.approx(1.60)
    assert metrics["usd_doc"] == pytest.approx(1.60)
