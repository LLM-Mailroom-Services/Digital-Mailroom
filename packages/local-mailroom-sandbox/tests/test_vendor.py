"""DMR-057 self-containment regression tests.

The sandbox must be fully operational from a fresh checkout: the pipeline
(llm-mailroom@v0.6.0) and scoring engine (llm-dojo-scoring@v0.12.2) ship as
TRACKED snapshots under ``vendor/`` and are put on ``sys.path`` at package
import. No pip git pins, no ``sandbox fetch-deps`` step, no env tricks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mailroom_sandbox.paths import repo_root, vendored_dojo_src, vendored_mailroom_src
from mailroom_sandbox.runtime import resolve_dojo_src, resolve_mailroom_src

MAILROOM_PIN = "v0.6.0"
MAILROOM_COMMIT = "3cf9fb921f0048a10d9a15760e2b4d825831a344"
DOJO_PIN = "v0.12.2"
DOJO_COMMIT = "6dab61bd0782835cfab33faeae8fc457e119ea62"


def test_vendored_trees_are_tracked_and_pinned():
    for name, pin, commit in (
        ("llm-mailroom", MAILROOM_PIN, MAILROOM_COMMIT),
        ("llm-dojo-scoring", DOJO_PIN, DOJO_COMMIT),
    ):
        tree = repo_root() / "vendor" / name
        assert (tree / "VENDOR.md").is_file(), f"vendor/{name}/VENDOR.md missing"
        md = (tree / "VENDOR.md").read_text(encoding="utf-8")
        assert pin in md and commit in md
        assert not (tree / ".git").exists(), "vendored tree must not carry .git"


def test_resolution_prefers_vendored_snapshots():
    assert resolve_mailroom_src() == vendored_mailroom_src()
    assert resolve_dojo_src() == vendored_dojo_src()


def test_vendored_srcs_are_on_sys_path_at_import():
    for src in (vendored_mailroom_src(), vendored_dojo_src()):
        assert src is not None
        assert str(src.resolve()) in sys.path


def test_dojo_resolves_from_vendored_tree():
    import llm_dojo_scoring

    vendor = vendored_dojo_src()
    assert str(Path(llm_dojo_scoring.__file__).resolve()).startswith(str(vendor.resolve()))


def test_agent_prompt_names_merge_vendor_templates_and_static_roster():
    from mailroom_sandbox.prompt_registry import agent_prompt_names

    names = agent_prompt_names()
    # Vendored template keys (v0.6.0 surface)…
    assert "sorter_reviewer" in names
    assert "judge-classification" in names
    # …and the sandbox-only static roster entries v0.6.0 does not template.
    assert "relations" in names
    assert "gmail_triage" in names
    assert "intake" in names


@pytest.mark.parametrize(
    "module",
    [
        "pipeline.config",
        "llm.prompts",
        "legalbench.tasks",
        "observability.scores",
        "graph.build_graph",
        "agents.sorter",
        "llm_dojo_scoring.serving",
        "llm_dojo_scoring.experiment",
    ],
)
def test_vendored_modules_import(module):
    import importlib

    importlib.import_module(module)


def test_no_git_pip_pins_in_manifest():
    pyproject = (repo_root() / "pyproject.toml").read_text(encoding="utf-8")
    assert "llm-dojo-scoring.git@" not in pyproject
    assert "llm-mailroom.git@" not in pyproject
    assert "llm-entity-extraction.git@" not in pyproject
    assert "[tool.uv.sources]" not in pyproject


def test_modal_worker_bundles_vendor_and_skips_git_pins():
    app = (repo_root() / "deploy" / "modal_job.py").read_text(encoding="utf-8")
    assert "mailroom @ git+" not in app  # no pip install of the mailroom dist
    assert "llm-dojo-scoring @" not in app
    assert 'vendor" / "llm-mailroom"' in app
    assert 'vendor" / "llm-dojo-scoring"' in app


def test_legalbench_suite_bridge_still_loud_without_cuad_corpus():
    # The vendored legalbench suite must raise the corpus fetch command, never
    # silently fall back to the toy fixture (data/cuad stays pruned).
    from mailroom_sandbox.datasets import load_legalbench_suite_rows

    with pytest.raises(Exception) as excinfo:
        load_legalbench_suite_rows("contract_qa", sample=2, seed=1)
    assert "fetch_full_cuad" in str(excinfo.value)