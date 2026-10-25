"""Offline fixture prep helpers (network-free)."""

from __future__ import annotations

import json

from pathlib import Path

from mailroom_sandbox.cli import main
from mailroom_sandbox.compose import VALID_PROFILES, compose_file
from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.prep import (
    clean_hf_rows,
    clean_legalbench_rows,
    clean_manifest_rows,
    environment_checklist,
    normalize_text,
    prepare_offline_datasets,
)


def test_normalize_text_collapses_noise():
    assert normalize_text("  a   b\r\n\r\n\r\nc  ") == "a b\n\nc"


def test_clean_manifest_and_prepare(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    rows, report = clean_manifest_rows()
    assert report.kept_rows >= 8
    assert report.dropped_empty == 0
    assert all(r["text"] and r["expected_doc_class"] for r in rows)

    hf_rows, hf_report = clean_hf_rows()
    assert hf_report.kept_rows >= 4
    lb_rows, lb_report = clean_legalbench_rows()
    assert lb_report.kept_rows >= 1
    assert all(r["answer"] in {"yes", "no"} for r in lb_rows)

    summary = prepare_offline_datasets()
    assert summary["counts"]["fixtures"] == report.kept_rows
    manifest = Path(summary["manifest"])
    if not manifest.is_absolute():
        manifest = repo_root() / manifest
    assert manifest.is_file()
    fixtures_rel = summary["artifacts"]["fixtures"]
    fixtures_path = Path(fixtures_rel)
    if not fixtures_path.is_absolute():
        fixtures_path = repo_root() / fixtures_path
    assert fixtures_path.is_file()
    first = json.loads(fixtures_path.read_text(encoding="utf-8").splitlines()[0])
    assert "text" in first and "expected_fields" in first


def test_environment_checklist_and_dockerfile():
    check = environment_checklist("ollama")
    assert check["dockerfile_ok"]
    assert check["compose_file_ok"]
    assert check["fixtures_manifest_ok"]
    assert check["activation_ok"]
    assert any(name.endswith("01_offline_environment_setup.ipynb") for name in check["notebooks"])
    assert any(name.endswith("02_load_clean_prepare_data.ipynb") for name in check["notebooks"])
    assert any(name.endswith("03_offline_sandbox_smoke.ipynb") for name in check["notebooks"])


def test_compose_includes_jupyter_service():
    raw = compose_file().read_text(encoding="utf-8")
    assert "jupyter:" in raw
    assert "deploy/Dockerfile" in raw
    assert "jupyter" in VALID_PROFILES
    assert (repo_root() / "deploy" / "Dockerfile").is_file()


def test_cli_datasets_prepare(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    assert main(["datasets", "prepare", "--profile", "ollama"]) == 0
