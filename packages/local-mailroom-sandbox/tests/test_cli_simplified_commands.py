"""Exit codes and output branches of CLI commands whose redundant returns were collapsed.

These handlers used to return the same success value on every path; the refactor
must leave their exit codes and printed output unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mailroom_sandbox import cli


def _row(package: str, *, error: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        package=package,
        dest_root=Path("/dest") / package,
        materialized=2,
        sync_written=1,
        skipped=False,
        error=error,
    )


def _propagate_result(*rows: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(source_root=Path("/src"), monorepo_root=None, packages=list(rows))


@pytest.mark.parametrize(
    ("rows", "expected_rc"),
    [
        ((_row("a"), _row("b")), 0),
        ((_row("a"), _row("b", error="boom")), 1),
    ],
)
def test_subagents_propagate_exit_code_follows_package_errors(monkeypatch, capsys, rows, expected_rc):
    monkeypatch.setattr(
        "mailroom_sandbox.subagents.propagate_family_checkouts",
        lambda **kw: _propagate_result(*rows),
    )
    args = argparse.Namespace(monorepo_root=None, packages=None, dry_run=True)
    assert cli._cmd_subagents_propagate(args) == expected_rc
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True and payload["monorepo_root"] is None
    assert [p["package"] for p in payload["packages"]] == [r.package for r in rows]
    assert [p["error"] for p in payload["packages"]] == [r.error for r in rows]


@pytest.mark.parametrize(
    ("pid", "message"),
    [(None, "no recorded tunnel for profile 'vllm-remote'"), (4242, "tunnel down: killed pid 4242")],
)
def test_tunnel_down_reports_and_exits_zero(monkeypatch, capsys, pid, message):
    monkeypatch.setattr(cli, "_tunnel_spec", lambda args: SimpleNamespace(profile="vllm-remote"))
    monkeypatch.setattr("mailroom_sandbox.tunnel.terminate", lambda spec: pid)
    assert cli._cmd_tunnel_down(argparse.Namespace(profile="vllm-remote")) == 0
    assert message in capsys.readouterr().out


def test_modal_matrix_list_table_and_json(capsys):
    assert cli.main(["modal-matrix", "list"]) == 0
    text = capsys.readouterr().out
    assert text.startswith("default  gpu")
    # SAND-077: the star is the app default; the frozen cost-eval posture is Qwen3-8B.
    starred = [line for line in text.splitlines() if line.startswith("*  ")]
    assert len(starred) == 1 and starred[0].endswith(" Qwen/Qwen3.5-9B")
    assert "* = app default Qwen/Qwen3.5-9B" in text and "Qwen/Qwen3-8B (sandbox runbook show l4-qwen3-8b)" in text

    assert cli.main(["modal-matrix", "list", "--json"]) == 0
    models = json.loads(capsys.readouterr().out)["models"]
    assert models and all("model" in row for row in models)
    assert sum(1 for row in models if row.get("default")) == 1


def test_modal_matrix_show_text_and_json(capsys):
    assert cli.main(["modal-matrix", "show", "Qwen/Qwen3-8B"]) == 0
    text = capsys.readouterr().out
    for label in ("model:", "gpu:", "max_model_len:", "env:", "hints:"):
        assert label in text
    assert "  export " in text and "  - " in text

    assert cli.main(["modal-matrix", "show", "Qwen/Qwen3-8B", "--json"]) == 0
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["model"] == "Qwen/Qwen3-8B"
    assert resolved["hints"] and set(resolved["env"])
