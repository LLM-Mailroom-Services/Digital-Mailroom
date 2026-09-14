"""DMR-057 self-containment regression tests.

The sandbox must be fully operational from a fresh checkout: the pipeline
(llm-mailroom@v0.7.1) and scoring engine (llm-dojo-scoring@v0.14.0) ship as
TRACKED snapshots under ``vendor/`` and are put on ``sys.path`` at package
import. No pip git pins, no ``sandbox fetch-deps`` step, no env tricks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mailroom_sandbox.paths import repo_root, vendored_dojo_src, vendored_mailroom_src
from mailroom_sandbox.runtime import resolve_dojo_src, resolve_mailroom_src

MAILROOM_PIN = "v0.7.1"
MAILROOM_COMMIT = "2a212e76a62b98f6eba451ff6f3c5bc96039ae37"
DOJO_PIN = "v0.14.0"
DOJO_COMMIT = "5298d7036652c04467be4150028453edbbcd4a38"


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
    # Vendored template keys (v0.7.1 surface)…
    assert "sorter_reviewer" in names
    assert "judge-classification" in names
    # …and the sandbox-only static roster entries v0.7.1 does not template.
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


def test_refresh_locates_package_src_for_each_vendored_layout(tmp_path):
    # DMR-058 regression: fetch-deps must map BOTH upstream layouts — llm-
    # mailroom's src/ AND llm-dojo-scoring's root-level llm_dojo_scoring/ —
    # and must refuse (None) anything unrecognized instead of half-wiping the
    # tracked tree (the old `work / name` fallback crashed after rmtree).
    from mailroom_sandbox.cli import _package_src_dir

    mailroom = tmp_path / "mailroom"
    (mailroom / "src" / "pipeline").mkdir(parents=True)
    assert _package_src_dir(mailroom) == mailroom / "src"

    dojo = tmp_path / "dojo"
    (dojo / "llm_dojo_scoring").mkdir(parents=True)
    assert _package_src_dir(dojo) == dojo / "llm_dojo_scoring"

    weird = tmp_path / "weird"
    weird.mkdir()
    assert _package_src_dir(weird) is None

def test_docs_claim_current_vendored_pins():
    """hub#54: no non-vendor tracked file may claim the OLD vendored pins
    (v0.6.0 / v0.12.2) as the current surface — the docs must name the
    shipped snapshot pins. Historical release-note entries (CHANGELOG
    released sections) are allowed to describe the old pins as history."""
    root = repo_root()
    # Intentional old-pin references: this test's own string, the
    # test_live_or_loud assertion that the OLD git-pin form is absent from the
    # htcondor script, and the run_batch_eval.sh line-142 historical note.
    allow_substrings = (
        "test_vendor.py",
        "test_live_or_loud.py",
        "the old mailroom@v0.6.0 / llm-dojo-scoring@v0.12.2",
    )
    stale = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".py", ".md", ".yaml", ".yml", ".sh"}:
            continue
        rel = path.relative_to(root)
        if "vendor" in rel.parts or "__pycache__" in rel.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "v0.6.0" in text or "v0.12.2" in text:
            if any(s in str(rel) or s in text for s in allow_substrings):
                continue
            # CHANGELOG.md is history by definition — released AND in-flight
            # entries legitimately describe the old pins (HUB-era notes). The
            # live docs/source surface is what the sweep guards.
            if rel.name == "CHANGELOG.md":
                continue
            stale.append(str(rel))
    assert not stale, f"stale vendored-pin claims: {stale}"


def test_offline_image_bundles_vendor_and_readmes_match_surface():
    """hub#55: the offline Dockerfile must COPY vendor/ (vendored evals run
    in-image; a read-only image cannot fetch-deps), .dockerignore must not
    exclude it, and the boilerplate READMEs must reference the real module
    surface so following them cannot yield ImportError/FileNotFoundError."""
    root = repo_root()

    dockerfile = (root / "deploy" / "Dockerfile").read_text()
    assert "COPY vendor ./vendor" in dockerfile
    assert ".[dev,notebooks,hf,pipeline]" in dockerfile  # pipeline extra baked

    dockerignore = (root / ".dockerignore").read_text()
    assert "vendor/*" not in dockerignore.splitlines()

    src_readme = (root / "src" / "README.md").read_text()
    assert "SandboxPipeline" not in src_readme
    assert "mailroom_sandbox.activate()" in src_readme

    eval_readme = (root / "src" / "mailroom_sandbox" / "eval" / "README.md").read_text()
    assert "from mailroom_sandbox.eval import run_evaluation" not in eval_readme
    assert "runners.run_isolated_eval" in eval_readme

    config_readme = (root / "config" / "README.md").read_text()
    assert "taxonomy.yaml" not in config_readme.split("##")[0] or "mailroom.taxonomy.base.yaml" in config_readme
    assert "SANDBOX_PROFILE" in config_readme

    profiles_readme = (root / "config" / "profiles" / "README.md").read_text()
    assert "MAILROOM_ENV" not in profiles_readme
    assert "SANDBOX_PROFILE" in profiles_readme
    assert "ollama.yaml" in profiles_readme and "vllm-remote.yaml" in profiles_readme
