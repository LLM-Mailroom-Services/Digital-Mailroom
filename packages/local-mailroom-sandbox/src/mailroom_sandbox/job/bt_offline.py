"""SAND-032: Braintrust-Experiment-shaped rows, written OFFLINE (no upload).

Rows live under ``data/runtime/bt_experiments/`` (gitignored). Reports are
built from them and committed; then the rows are disposed. ``dispose``
refuses until the report is tracked in git, so evidence cannot vanish
before it is recorded.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from mailroom_sandbox.job.checkpoint import RunStore


def _numeric_scores(score: dict | None) -> dict[str, float]:
    return {
        k: v
        for k, v in (score or {}).items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    }


def write_experiment(store: RunStore, *, out_root: Path, git_commit: str) -> Path:
    lock = store.read_lock() or {}
    run_id = str(lock.get("run_id") or store.dir.name)
    out = Path(out_root) / run_id
    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": run_id,
        "project": "mailroom-sandbox-offline",
        "metadata": {
            "engine": lock.get("engine") or {},
            "dataset": lock.get("dataset") or {},
            "prompt": lock.get("prompt") or {},
            "git_commit": git_commit,
        },
    }
    (out / "experiment.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8"
    )
    lines = []
    for item in store.load_items():
        latency = item.get("latency_ms")
        score = item.get("score") or {}
        lines.append(
            json.dumps(
                {
                    "id": item.get("item_id"),
                    "input": {"doc_id": item.get("item_id")},
                    "output": item.get("pred"),
                    "expected": score.get("expected"),
                    "scores": _numeric_scores(score),
                    "metrics": {
                        "latency_seconds": (
                            None if latency is None else round(float(latency) / 1000.0, 6)
                        ),
                        "prompt_tokens": item.get("prompt_tokens"),
                        "completion_tokens": item.get("completion_tokens"),
                    },
                    "metadata": {"ok": item.get("ok"), "error": item.get("error")},
                },
                default=str,
            )
        )
    (out / "rows.jsonl").write_text(
        "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
    )
    return out


def git_tracked(path: Path) -> bool:
    res = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], capture_output=True, text=True
    )
    return res.returncode == 0


def dispose(
    run_id: str,
    *,
    out_root: Path,
    report: Path,
    is_tracked: Callable[[Path], bool] = git_tracked,
) -> bool:
    if not is_tracked(Path(report)):
        raise RuntimeError(
            f"report {report} is not tracked in git — commit it before disposing {run_id}"
        )
    target = Path(out_root) / run_id
    if target.exists():
        shutil.rmtree(target)
        return True
    return False
