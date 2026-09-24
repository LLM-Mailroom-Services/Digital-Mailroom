"""Local mailroom-ml ModernBERT feeder (path contract, no weight copies).

Resolves the sibling ``mailroom-ml`` checkout and a calibrated checkpoint
directory so sorter-vs-ModernBERT comparisons can load real weights without
vendoring multi-hundred-MB safetensors into this sandbox.

Env contract (any one of the model path vars is enough)::

    MAILROOM_ML_SRC=/Users/…/Cold_Storage/mailroom-ml
    MODERNBERT_MODEL_PATH=$MAILROOM_ML_SRC/artifacts/run2-published
    # aliases accepted by mailroom-ml itself:
    ML_MODEL_DIR=$MODERNBERT_MODEL_PATH

Resolution order for the checkpoint (first hit with ``labels.json`` wins):

1. ``MODERNBERT_MODEL_PATH`` / ``ML_MODEL_DIR``
2. ``$MAILROOM_ML_SRC/artifacts/run2-published`` (calibrated published bundle)
3. ``…/artifacts/pytorch/model`` then ``…/artifacts/onnx/model``

Live eval shells out to mailroom-ml's ``training/eval_modernbert.py`` so the
sandbox does not need torch/onnxruntime as hard deps.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.job.metrics import MODERNBERT_DEFAULT_COST_PER_DOC_USD
from mailroom_sandbox.paths import repo_root

_log = logging.getLogger("mailroom_sandbox.modernbert")

# Published Hub id (weights live locally; this is the serving record label).
MODERNBERT_MODEL_ID = "Lucius-Morningstar/mailroom-modernbert-classifier"

__all__ = [
    "MODERNBERT_MODEL_ID",
    "resolve_mailroom_ml_src",
    "resolve_modernbert_model_path",
    "ensure_mailroom_ml_on_path",
    "feeder_status",
    "run_modernbert_eval",
    "serving_record_from_eval",
]


def resolve_mailroom_ml_src() -> Path | None:
    """Root of the mailroom-ml checkout (contains ``src/mailroom_ml``)."""
    env = (os.environ.get("MAILROOM_ML_SRC") or "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    # Sibling under Cold_Storage (canonical local layout) + one level up.
    root = repo_root()
    candidates.extend(
        [
            root.parent / "mailroom-ml",
            root.parent.parent / "mailroom-ml",
            Path.home() / "Desktop" / "Cold_Storage" / "mailroom-ml",
        ]
    )
    seen: set[Path] = set()
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "src" / "mailroom_ml" / "__init__.py").is_file():
            return resolved
    return None


def _bundle_ok(path: Path) -> bool:
    return path.is_dir() and (path / "labels.json").is_file()


def resolve_modernbert_model_path() -> Path | None:
    """Calibrated ModernBERT artifact dir (prefer run2-published)."""
    for key in ("MODERNBERT_MODEL_PATH", "ML_MODEL_DIR"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            p = Path(raw).expanduser()
            if _bundle_ok(p):
                return p.resolve()
            _log.warning("%s=%s is set but labels.json is missing", key, raw)

    ml = resolve_mailroom_ml_src()
    if ml is None:
        return None
    for rel in (
        Path("artifacts") / "run2-published",
        Path("artifacts") / "pytorch" / "model",
        Path("artifacts") / "onnx" / "model",
    ):
        cand = ml / rel
        if _bundle_ok(cand):
            return cand.resolve()
    return None


def ensure_mailroom_ml_on_path() -> Path:
    """Prepend mailroom-ml ``src`` to ``sys.path``; raise if unresolved."""
    ml = resolve_mailroom_ml_src()
    if ml is None:
        raise FileNotFoundError(
            "mailroom-ml not found — set MAILROOM_ML_SRC to the checkout root "
            "(expected sibling …/Cold_Storage/mailroom-ml with src/mailroom_ml/)"
        )
    src = ml / "src"
    resolved = str(src.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)
    return ml


def feeder_status() -> dict[str, Any]:
    """Loud path inventory for ``sandbox modernbert status``."""
    ml = resolve_mailroom_ml_src()
    model = resolve_modernbert_model_path()
    eval_cli = (ml / "training" / "eval_modernbert.py") if ml else None
    out: dict[str, Any] = {
        "mailroom_ml_src": str(ml) if ml else None,
        "modernbert_model_path": str(model) if model else None,
        "eval_entrypoint": str(eval_cli) if eval_cli and eval_cli.is_file() else None,
        "model_id": MODERNBERT_MODEL_ID,
        "ok": bool(ml and model and eval_cli and eval_cli.is_file()),
        "env": {
            "MAILROOM_ML_SRC": os.environ.get("MAILROOM_ML_SRC") or None,
            "MODERNBERT_MODEL_PATH": os.environ.get("MODERNBERT_MODEL_PATH") or None,
            "ML_MODEL_DIR": os.environ.get("ML_MODEL_DIR") or None,
        },
        "hint": (
            "export MAILROOM_ML_SRC=…/mailroom-ml && "
            "export MODERNBERT_MODEL_PATH=$MAILROOM_ML_SRC/artifacts/run2-published"
            if not (ml and model)
            else "sandbox modernbert eval --sample 50 --json"
        ),
    }
    if model is not None:
        out["has_temperatures"] = (model / "temperatures.json").is_file()
        out["has_onnx"] = (model / "model.onnx").is_file()
        out["has_safetensors"] = (model / "model.safetensors").is_file()
    return out


def run_modernbert_eval(
    *,
    sample: int = 50,
    seed: int = 42,
    checkpoint: Path | str | None = None,
    timeout_s: int = 1800,
) -> dict[str, Any]:
    """Run mailroom-ml's eval CLI; return the JSON report.

    Uses the mailroom-ml ``.venv`` interpreter when present so torch/onnx
    deps resolve without installing them into the sandbox venv.
    """
    ml = ensure_mailroom_ml_on_path()
    ckpt = Path(checkpoint) if checkpoint else resolve_modernbert_model_path()
    if ckpt is None or not _bundle_ok(ckpt):
        raise FileNotFoundError(
            "ModernBERT checkpoint missing — set MODERNBERT_MODEL_PATH to a "
            "bundle with labels.json (prefer artifacts/run2-published)"
        )
    script = ml / "training" / "eval_modernbert.py"
    if not script.is_file():
        raise FileNotFoundError(f"eval entrypoint missing: {script}")

    venv_py = ml / ".venv" / "bin" / "python"
    python = str(venv_py) if venv_py.is_file() else sys.executable
    cmd = [
        python,
        str(script),
        "--checkpoint",
        str(ckpt),
        "--sample",
        str(int(sample)),
        "--seed",
        str(int(seed)),
        "--json",
    ]
    env = os.environ.copy()
    env.setdefault("ML_MODEL_DIR", str(ckpt))
    env.setdefault("MAILROOM_ML_SRC", str(ml))
    # Prefer mailroom-ml src on PYTHONPATH for the child.
    src = str((ml / "src").resolve())
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not prev else f"{src}{os.pathsep}{prev}"

    _log.info("modernbert eval: %s", " ".join(cmd))
    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(ml),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        raise RuntimeError(
            f"modernbert eval failed (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '')[:800]}"
        )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"modernbert eval returned non-JSON stdout: {proc.stdout[:400]!r}"
        ) from exc
    if not isinstance(report, dict):
        raise RuntimeError("modernbert eval JSON was not an object")
    report["_sandbox_wall_seconds"] = round(elapsed, 3)
    report["_checkpoint"] = str(ckpt)
    return report


def serving_record_from_eval(report: Mapping[str, Any]) -> dict[str, Any]:
    """Build a dojo-compatible serving record from an eval_modernbert report.

    ``cost_per_document`` uses the ONNX-CPU floor unless overridden via env
    ``MODERNBERT_COST_PER_DOC_USD``.
    """
    n = int(report.get("n_docs") or 0)
    cpd_raw = (os.environ.get("MODERNBERT_COST_PER_DOC_USD") or "").strip()
    try:
        cpd = float(cpd_raw) if cpd_raw else MODERNBERT_DEFAULT_COST_PER_DOC_USD
    except ValueError:
        cpd = MODERNBERT_DEFAULT_COST_PER_DOC_USD

    wall = report.get("_sandbox_wall_seconds")
    e2e = None
    if wall is not None and n > 0:
        e2e = float(wall) / n
    elif n > 0:
        # Eval report has no per-doc latency; leave absent rather than invent.
        e2e = None

    rec: dict[str, Any] = {
        "serving_kind": "modernbert",
        "provider": "onnx-cpu" if report.get("model_kind", "").startswith("onnx") else "pytorch",
        "profile": "modernbert",
        "model": MODERNBERT_MODEL_ID,
        "task": "sorter",
        "classifier": "modernbert",
        "dataset_fingerprint": (
            f"modernbert-eval-n{n}-seed{report.get('seed', 42)}-"
            f"{report.get('artifact_sha') or 'sha-unknown'}"
        ),
        "n": n,
        "cost_per_document": cpd,
        "estimated_cost_usd": round(cpd * n, 8) if n else None,
        "scores": {
            "accuracy": report.get("doc_type_accuracy"),
            "exact_match": report.get("doc_type_accuracy"),
            "doc_type_accuracy": report.get("doc_type_accuracy"),
            "subclass_accuracy": report.get("subclass_accuracy_conditional"),
        },
        "checkpoint": report.get("_checkpoint") or report.get("checkpoint"),
        "model_kind": report.get("model_kind"),
        "artifact_sha": report.get("artifact_sha"),
    }
    if e2e is not None:
        rec["e2e_latency_seconds"] = e2e
    return {k: v for k, v in rec.items() if v is not None}
