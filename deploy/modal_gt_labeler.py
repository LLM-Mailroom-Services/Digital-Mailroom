"""Modal app for chunked v9.1 ground-truth labeling (SAND-045).

``modal deploy deploy/modal_gt_labeler.py`` publishes ``sandbox-vllm-gt-labeler``.
The app scale-to-zeros (``min_containers=0``). It does not label the corpus
by itself. Run one chunk at a time through ``mailroom_sandbox.gt_labeler``:
at most 40 documents and a projected bill of $2 on two L4s.

Posture: ``Qwen/Qwen3-14B-AWQ``, two L4 replicas, ``max_num_seqs=8`` and
``max_inputs=8`` per replica (16 in flight), fp8 KV, prefix caching, thinking
off, structured outputs (async scheduling off).

Stop the app when a chunk's queue drains::

    modal app stop sandbox-vllm-gt-labeler
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mailroom_sandbox.gt_labeler import (  # noqa: E402
    APP_NAME,
    POSTURE,
    apply_posture_env,
    assert_posture,
)


def _invoked_by_modal() -> bool:
    joined = " ".join(sys.argv)
    return "modal_gt_labeler.py" in joined and any(
        token in sys.argv for token in ("deploy", "run", "serve")
    )


def _export_lines() -> str:
    lines = [f"export {key}={value}" for key, value in POSTURE.items()]
    return "\n".join(lines) + "\n"


def _hydrate():
    """Apply the posture, refuse a drifted shell, then load the shared vLLM app."""
    apply_posture_env()
    assert_posture()
    spec = importlib.util.spec_from_file_location(
        "sandbox_gt_labeler_vllm",
        Path(__file__).with_name("modal_vllm.py"),
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load deploy/modal_vllm.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.APP_NAME != APP_NAME:
        raise RuntimeError(
            f"hydrated app {module.APP_NAME!r} != {APP_NAME!r}"
        )
    return module


if __name__ == "__main__" and "--export" in sys.argv:
    sys.stdout.write(_export_lines())
elif __name__ == "__main__" and "--check" in sys.argv:
    apply_posture_env()
    assert_posture()
    print(f"ok {APP_NAME} {POSTURE['MODAL_VLLM_MODEL']} x{POSTURE['MODAL_VLLM_MAX_CONTAINERS']} L4")
elif _invoked_by_modal():
    _vllm = _hydrate()
    app = _vllm.app
    serve = _vllm.serve
    download_model = _vllm.download_model
    main = _vllm.main
