"""SAND-026: default vendor sync cannot clobber simplified experiment pins."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_sync():
    path = ROOT / "scripts" / "sync_specialist_prompts.py"
    spec = importlib.util.spec_from_file_location("sync_specialist_prompts", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_experiment_stems_are_not_in_default_exports():
    sync = _load_sync()
    export_stems = {stem for stem, _kind in sync.EXPORTS}
    assert export_stems.isdisjoint(sync.EXPERIMENT_STEMS)
    for vendor_stem, experiment_stem in sync.EXPERIMENT_FROM_VENDOR.items():
        assert vendor_stem in export_stems
        assert experiment_stem in sync.EXPERIMENT_STEMS
        assert (ROOT / "config" / "prompts" / f"{experiment_stem}.txt").is_file()
        assert (ROOT / "config" / "prompts" / f"{vendor_stem}.txt").is_file()


def test_refuse_experiment_write_without_opt_in():
    sync = _load_sync()
    for stem in sync.EXPERIMENT_STEMS:
        msg = sync._refuse_experiment_write(stem, overwrite_experiment=False)
        assert msg and "--overwrite-experiment" in msg
        assert sync._refuse_experiment_write(stem, overwrite_experiment=True) is None


def test_default_sync_leaves_simplified_files_untouched(tmp_path, monkeypatch):
    sync = _load_sync()
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    # Seed vendor + experiment files.
    vendor_body = "VENDOR TEXT\n"
    experiment_body = "SIMPLIFIED EXPERIMENT TEXT\n"
    mapping = dict(sync.EXPERIMENT_FROM_VENDOR)
    for vendor_stem, experiment_stem in mapping.items():
        (prompts / f"{vendor_stem}.txt").write_text(vendor_body, encoding="utf-8")
        (prompts / f"{experiment_stem}.txt").write_text(experiment_body, encoding="utf-8")
    monkeypatch.setattr(sync, "PROMPTS", prompts)
    monkeypatch.setattr(
        sync,
        "_load_texts",
        lambda: {vendor: "VENDOR TEXT" for vendor in mapping},
    )
    assert sync.sync(check=False, overwrite_experiment=False) == 0
    for vendor_stem, experiment_stem in mapping.items():
        assert (prompts / f"{experiment_stem}.txt").read_text(encoding="utf-8") == experiment_body
        assert (prompts / f"{vendor_stem}.txt").read_text(encoding="utf-8") == vendor_body


def test_check_passes_on_repo_pins():
    pytest.importorskip("langchain_core")
    sync = _load_sync()
    assert sync.sync(check=True) == 0


def test_check_fails_when_simplified_matches_vendor(tmp_path, monkeypatch):
    sync = _load_sync()
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    vendor_text = "same text for both\n"
    mapping = dict(sync.EXPERIMENT_FROM_VENDOR)
    for vendor_stem, experiment_stem in mapping.items():
        (prompts / f"{vendor_stem}.txt").write_text(vendor_text, encoding="utf-8")
        (prompts / f"{experiment_stem}.txt").write_text(vendor_text, encoding="utf-8")
    monkeypatch.setattr(sync, "PROMPTS", prompts)
    monkeypatch.setattr(
        sync,
        "_load_texts",
        lambda: {vendor: "same text for both" for vendor in mapping},
    )
    assert sync.sync(check=True) == 1


def test_overwrite_experiment_is_opt_in(tmp_path, monkeypatch):
    sync = _load_sync()
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    mapping = dict(sync.EXPERIMENT_FROM_VENDOR)
    for vendor_stem, experiment_stem in mapping.items():
        (prompts / f"{vendor_stem}.txt").write_text("old vendor\n", encoding="utf-8")
        (prompts / f"{experiment_stem}.txt").write_text("keep me\n", encoding="utf-8")
    monkeypatch.setattr(sync, "PROMPTS", prompts)
    monkeypatch.setattr(
        sync,
        "_load_texts",
        lambda: {vendor: "NEW VENDOR" for vendor in mapping},
    )
    assert sync.sync(check=False, overwrite_experiment=True) == 0
    for experiment_stem in mapping.values():
        assert (prompts / f"{experiment_stem}.txt").read_text(encoding="utf-8") == "NEW VENDOR\n"
