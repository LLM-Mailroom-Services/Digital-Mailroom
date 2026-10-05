"""Dated specialist report tree (local-date / specialist / cell stem)."""

from __future__ import annotations

from datetime import datetime

import pytest
import yaml

from mailroom_sandbox.job import dated_reports
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.report_paths import (
    experiment_prefix,
    report_group_for_config,
    report_group_for_runbook,
)


def _specialist_store(
    tmp_path,
    *,
    mock: bool = False,
    run_id: str = "grid-20-merger-specialist-awq-1l4",
    replicas: int = 1,
) -> RunStore:
    """Build a locked specialist RunStore under tmp_path for path tests."""
    store = RunStore(tmp_path / run_id)
    store.write_lock(
        {
            "run_id": store.run_id,
            "task": "merger_agreement_specialist",
            "profile": "modal-vllm",
            "spec_hash": "abc",
            "engine": {
                "model": "Qwen/Qwen3-8B-AWQ",
                "modal": {"gpu": "L4", "max_containers": replicas, "min_containers": replicas},
            },
            "job": {"mock": mock, "concurrency": 8, "mode": "endpoint"},
            "dataset": {"limit": 20},
            "prompt": {"default": {"source": "local", "file": "merger_agreement_specialist_simplified"}},
        }
    )
    store.append_item(
        {
            "item_id": "DOC-1",
            "index": 0,
            "ok": True,
            "latency_ms": 110000.0,
            "prompt_tokens": 10000,
            "completion_tokens": 900,
            "ts": "2026-09-30T04:54:59.000+00:00",
            "score": {"overall_extraction_score": 0.04, "schema_valid": True},
        }
    )
    return store


def test_experiment_prefix_is_explicit_or_known_grid():
    """Named sweeps and cataloged runbooks resolve; unknown grids do not."""
    assert experiment_prefix("sand032-s3-corr50") == "SAND-32"
    assert experiment_prefix("sand39-1l4-n50") == "SAND-39"
    assert experiment_prefix("sand40-100-contracts-specialist-awq-2l4") == "SAND-40"
    assert experiment_prefix("grid-50-merger-specialist-awq-2l4") == "SAND-37"
    assert experiment_prefix("grid-external-experiment") is None
    assert experiment_prefix("run-20-merger-specialist-awq") is None
    assert experiment_prefix("run-20-merger-specialist-awq", {"runbook": "sand40"}) == "SAND-40"
    assert experiment_prefix("job-204", {"runbook_id": "grid-1l4"}) == "SAND-37"
    assert experiment_prefix("job-205", {"report_group": "SAND-123"}) == "SAND-123"


def test_report_groups_reject_duplicate_runbook_ids(tmp_path, monkeypatch):
    """A repeated runbook id in the catalog raises instead of last-key-wins."""
    from mailroom_sandbox import report_paths

    catalog = tmp_path / "report-groups.yaml"
    catalog.write_text(
        "schema: sandbox.report-groups/v1\n"
        "runbooks:\n"
        "  grid-1l4: SAND-37\n"
        "  grid-1l4: SAND-40\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(report_paths, "config_dir", lambda: tmp_path)

    with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key"):
        report_paths._report_groups()


@pytest.mark.parametrize("field, value", [
    ("runbooks", None),
    ("runbooks", []),
    ("runbooks", "grid-1l4"),
    ("runbooks", False),
    ("legacy_run_id_patterns", None),
    ("legacy_run_id_patterns", {}),
    ("legacy_run_id_patterns", "grid-.*"),
    ("legacy_run_id_patterns", False),
    ("legacy_run_id_patterns", [None]),
    ("legacy_run_id_patterns", ["grid-.*"]),
    ("legacy_run_id_patterns", [{"pattern": "grid-.*"}, []]),
])
def test_report_groups_reject_invalid_nested_shapes(tmp_path, monkeypatch, field, value):
    from mailroom_sandbox import report_paths

    data = {"schema": "sandbox.report-groups/v1", field: value}
    (tmp_path / "report-groups.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(report_paths, "config_dir", lambda: tmp_path)

    with pytest.raises(ValueError, match=field):
        report_paths._report_groups()


@pytest.mark.parametrize("fields", [
    {},
    {"runbooks": {}, "legacy_run_id_patterns": []},
    {"runbooks": {"grid-1l4": "SAND-37"}, "legacy_run_id_patterns": [
        {"pattern": "grid-.*", "report_group": "SAND-37"},
    ]},
])
def test_report_groups_accept_valid_nested_shapes(tmp_path, monkeypatch, fields):
    from mailroom_sandbox import report_paths

    data = {"schema": "sandbox.report-groups/v1", **fields}
    (tmp_path / "report-groups.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(report_paths, "config_dir", lambda: tmp_path)

    assert report_paths._report_groups() == data


def test_report_groups_reuse_runbooks_for_multiple_configs():
    """Several configs that share a runbook id map to the same report group."""
    assert report_group_for_runbook("grid-1l4") == "SAND-37"
    assert report_group_for_runbook("sand40") == "SAND-40"
    assert report_group_for_config(
        "config/runs/grid-20-correspondence-specialist-awq-1l4.yaml"
    ) == "SAND-37"
    assert report_group_for_config(
        "config/runs/sand40-100-contracts-specialist-awq-2l4.yaml"
    ) == "SAND-40"
    assert report_group_for_runbook("future-unknown") is None


def test_cell_stem_encodes_n_shape_concurrency(tmp_path):
    """Cell stems encode n, hardware shape, and concurrency."""
    store = _specialist_store(tmp_path)
    folder, stem = dated_reports.cell_stem(store)
    assert folder == "merger_agreement"
    assert stem == "RUN-20-MERGER-AWQ-1L4-C8"


def test_cell_stem_retry_suffix_does_not_clobber(tmp_path):
    store = RunStore(tmp_path / "grid-20-merger-specialist-awq-1l4-retry")
    store.write_lock(
        {
            "run_id": store.run_id,
            "task": "merger_agreement_specialist",
            "engine": {
                "model": "Qwen/Qwen3-8B-AWQ",
                "modal": {"gpu": "L4", "max_containers": 1},
            },
            "job": {"concurrency": 8},
            "dataset": {"limit": 20},
        }
    )
    folder, stem = dated_reports.cell_stem(store)
    assert folder == "merger_agreement"
    assert stem == "RUN-20-MERGER-AWQ-1L4-C8-RETRY"


def test_write_run_reports_lands_under_local_date(tmp_path):
    store = _specialist_store(tmp_path)
    now = datetime(2026, 9, 29, 23, 58)
    paths = dated_reports.write_run_reports(store, repo=tmp_path, now=now, wall_seconds=200.0)
    assert paths["report"].name == "RUN-20-MERGER-AWQ-1L4-C8-REPORT.md"
    assert paths["serving_md"].name == "RUN-20-MERGER-AWQ-1L4-C8-SERVING.md"
    assert paths["serving_json"].name == "RUN-20-MERGER-AWQ-1L4-C8.serving.json"
    assert paths["dir"] == tmp_path / "reports" / "SAND-37" / "2026-09-29" / "merger_agreement"
    text = paths["report"].read_text(encoding="utf-8")
    assert "grid-20-merger-specialist-awq-1l4" in text
    assert "Qwen/Qwen3-8B-AWQ" in text
    serving = paths["serving_md"].read_text(encoding="utf-8")
    assert "gpu_cost_per_document" in serving
    assert paths["tui_serving_json"] == (
        tmp_path / "reports" / "serving" / "SAND-37" / "1L4" / "n=20" / f"{store.run_id}.serving.json"
    )
    assert paths["tui_serving_json"].is_file()


def test_dated_and_serving_paths_follow_sweep_or_general_root(tmp_path):
    now = datetime(2026, 9, 29)
    ungrouped = _specialist_store(tmp_path, run_id="run-20-merger-specialist-awq-1l4")
    assert dated_reports.dated_cell_dir(ungrouped, repo=tmp_path, now=now) == (
        tmp_path / "reports" / "2026-09-29" / "merger_agreement"
    )
    assert dated_reports.serving_export_path(ungrouped, repo=tmp_path) == (
        tmp_path / "reports" / "serving" / dated_reports.local_report_date()
        / "merger_agreement" / f"{ungrouped.run_id}.serving.json"
    )

    sand40 = _specialist_store(
        tmp_path,
        run_id="sand40-20-merger-specialist-awq-2l4",
        replicas=2,
    )
    assert dated_reports.dated_cell_dir(sand40, repo=tmp_path, now=now) == (
        tmp_path / "reports" / "SAND-40" / "2026-09-29" / "merger_agreement"
    )
    assert dated_reports.serving_export_path(sand40, repo=tmp_path) == (
        tmp_path / "reports" / "serving" / "SAND-40" / "2L4" / "n=20"
        / f"{sand40.run_id}.serving.json"
    )

    probe = _specialist_store(
        tmp_path,
        run_id="sand40-probe-20-merger-specialist-awq-2l4-64k",
        replicas=2,
    )
    assert dated_reports.serving_export_path(probe, repo=tmp_path) == (
        tmp_path / "reports" / "serving" / "SAND-40" / "2L4" / "probes"
        / f"{probe.run_id}.serving.json"
    )


def test_default_serving_writer_uses_sweep_directory(tmp_path, monkeypatch):
    """Serving JSON for a grid lock lands under the cataloged sweep directory."""
    from mailroom_sandbox import report_paths
    from mailroom_sandbox.job import metrics

    config_root = report_paths.config_dir()
    monkeypatch.setattr("mailroom_sandbox.paths.repo_root", lambda: tmp_path)
    monkeypatch.setattr(report_paths, "config_dir", lambda: config_root)
    monkeypatch.setattr(dated_reports, "maybe_write_run_reports", lambda *args, **kwargs: {})
    store = _specialist_store(tmp_path)
    path = metrics.write_serving_json(store, wall_seconds=100.0)
    assert path == (
        tmp_path / "reports" / "serving" / "SAND-37" / "1L4" / "n=20"
        / f"{store.run_id}.serving.json"
    )
    assert path.is_file()


def test_mock_jobs_do_not_write_dated_tree(tmp_path):
    store = _specialist_store(tmp_path, mock=True)
    assert dated_reports.write_run_reports(store, repo=tmp_path) == {}
