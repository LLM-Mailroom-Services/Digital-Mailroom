"""CLI wiring tests (DMR-027) — network-free."""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox.cli import main


def _write_run_yaml(tmp_path) -> str:
    import yaml

    path = tmp_path / "run.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "run_id": "cli-smoke",
                "task": "sorter",
                "dataset": {
                    "provider": "file",
                    "local_path": "file:///tmp/does-not-matter.jsonl",
                    "limit": 2,
                },
                "engine": {"kind": "vllm-local", "modal": None},
                "job": {"mock": True},
                "trace": {"sink": "none"},
            }
        ),
        encoding="utf-8",
    )
    return str(path)


def test_prompts_list(capsys):
    rc = main(["prompts", "list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "sorter" in out


def test_metrics_compare_requires_runs(capsys):
    with pytest.raises(SystemExit):
        main(["metrics", "compare"])


def test_run_parser_has_lifecycle(tmp_path, capsys):
    import json as _json

    # A config pointing at a non-existent dataset fails harmlessly under dry-run.
    path = tmp_path / "run.yaml"
    import yaml

    path.write_text(
        yaml.safe_dump(
            {
                "run_id": "cli-pf",
                "dataset": {"provider": "file", "local_path": "file:///tmp/nope.jsonl"},
                "engine": {"kind": "vllm-local", "modal": None},
                "trace": {"sink": "none"},
            }
        ),
        encoding="utf-8",
    )
    rc = main(["run", "preflight", "--config", str(path), "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"status": "prepared"' in out

pytestmark = pytest.mark.usefixtures("job_data_dir")
