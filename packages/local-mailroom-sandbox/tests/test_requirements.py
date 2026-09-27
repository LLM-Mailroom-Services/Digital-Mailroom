"""Requirements files stay in sync with pyproject.toml (DMR-078)."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_sync():
    path = ROOT / "scripts" / "sync_requirements.py"
    spec = importlib.util.spec_from_file_location("sync_requirements", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sync_requirements_check_clean():
    mod = _load_sync()
    assert mod.sync(check=True) == 0


def test_pipeline_extra_declares_aiosqlite_and_pdf_stack():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r"^pipeline\s*=\s*\[(.*?)\]", text, flags=re.M | re.S)
    assert m, "pipeline extra missing from pyproject.toml"
    block = m.group(1).lower()
    for needle in (
        "sqlalchemy",
        "aiosqlite",
        "greenlet",
        "pypdf",
        "pdfplumber",
        "pillow",
        "langchain-core",
        "langgraph",
    ):
        assert needle in block, f"pipeline extra missing {needle!r}"


def test_modal_job_image_lists_pipeline_deps():
    app = (ROOT / "deploy" / "modal_job.py").read_text(encoding="utf-8")
    for needle in (
        "aiosqlite",
        "sqlalchemy",
        "numpy",
        "pandas",
        "langchain-core",
        "langgraph",
        "pypdf",
        "pillow",
        "langfuse",
        "greenlet",
        "pdfplumber",
    ):
        assert needle in app, f"modal_job uv_pip_install missing {needle!r}"


def test_requirements_pipeline_file_lists_aiosqlite():
    text = (ROOT / "requirements" / "pipeline.txt").read_text(encoding="utf-8")
    assert "aiosqlite" in text
    assert "-r base.txt" in text


def test_root_requirements_shim_points_at_dev():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "-r requirements/dev.txt" in text


def test_modal_job_requirements_mirror_covers_image_packages():
    """Every package string in modal_job.uv_pip_install appears in modal-job.txt or base."""
    app = (ROOT / "deploy" / "modal_job.py").read_text(encoding="utf-8")
    start = app.index(".uv_pip_install(")
    # End at the first line that is only `    )` after the call opens — avoid
    # matching `)` inside comments above the package list.
    end = app.index("\n    )", start)
    block = app[start:end]
    pkgs = re.findall(r'"([^"]+)"', block)
    assert pkgs, "no packages in uv_pip_install"
    req_text = (ROOT / "requirements" / "modal-job.txt").read_text(encoding="utf-8")
    base_text = (ROOT / "requirements" / "base.txt").read_text(encoding="utf-8")
    combined = req_text + "\n" + base_text
    for pkg in pkgs:
        name = re.split(r"[<=>!~\[]", pkg, maxsplit=1)[0].strip().lower()
        assert name in combined.lower(), (
            f"{pkg!r} not represented in requirements/modal-job.txt"
        )
