"""Modal+vLLM model/GPU swap from ``config/models.yaml`` ``modal_models``.

One place to resolve deploy knobs. Default experiment path stays
``Qwen/Qwen3-8B`` on ``L4`` (specialist 5×30 suite). Alternate rows are
applied by exporting ``MODAL_VLLM_*`` then recreating the Modal app::

    eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"
    modal run deploy/modal_vllm.py::download_model
    modal deploy deploy/modal_vllm.py --strategy recreate

Does not mutate run-30 YAMLs — those stay Qwen+L4. For an alternate
benchmark, copy a run YAML and edit ``engine.model`` / ``engine.modal.gpu``.
"""

from __future__ import annotations

from typing import Any

from mailroom_sandbox.paths import config_dir
from mailroom_sandbox.overlay import load_yaml
from mailroom_sandbox.job.spec import KNOWN_GPUS

# Default specialist / cost-eval posture (docs/benchmark-l4.md).
DEFAULT_MODAL_MODEL = "Qwen/Qwen3-8B"
DEFAULT_MODAL_GPU = "L4"

# Env keys written by ``env_exports`` (deploy/modal_vllm.py reads these).
MATRIX_ENV_KEYS = (
    "MODAL_VLLM_MODEL",
    "MODAL_VLLM_GPU",
    "MODAL_VLLM_QUANTIZATION",
    "MODAL_VLLM_MAX_MODEL_LEN",
    "MODAL_VLLM_TP_SIZE",
)


def modal_models() -> dict[str, dict[str, Any]]:
    raw = load_yaml(config_dir() / "models.yaml").get("modal_models") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}


def list_modal_models() -> list[dict[str, Any]]:
    rows = []
    for model_id, row in sorted(modal_models().items()):
        rows.append(
            {
                "model": model_id,
                "gpu": row.get("gpu", DEFAULT_MODAL_GPU),
                "quantization": row.get("quantization") or "",
                "max_model_len": row.get("max_model_len"),
                "tp_size": row.get("tp_size", 1),
                "default": model_id == DEFAULT_MODAL_MODEL,
                "notes": (row.get("notes") or "").strip(),
            }
        )
    return rows


def resolve_modal_row(
    model_id: str | None = None,
    *,
    gpu_override: str | None = None,
) -> dict[str, Any]:
    """Resolve one matrix row (+ optional GPU override) into deploy knobs."""
    mid = (model_id or DEFAULT_MODAL_MODEL).strip()
    catalog = modal_models()
    if mid not in catalog:
        known = ", ".join(sorted(catalog)[:12])
        more = "…" if len(catalog) > 12 else ""
        raise KeyError(
            f"model {mid!r} not in config/models.yaml modal_models "
            f"(have: {known}{more}). Add a row or pass a catalog id."
        )
    row = catalog[mid]
    gpu = (gpu_override or row.get("gpu") or DEFAULT_MODAL_GPU).strip()
    base = gpu.split(":")[0]
    if base not in KNOWN_GPUS:
        raise ValueError(
            f"gpu {gpu!r} not in known classes {sorted(KNOWN_GPUS)}"
        )
    tp = row.get("tp_size")
    if ":" in gpu:
        tp = int(gpu.split(":")[1])
    elif tp is None:
        tp = 1
    quant = row.get("quantization") or ""
    max_len = int(row.get("max_model_len") or 16384)
    return {
        "model": mid,
        "gpu": gpu,
        "quantization": str(quant),
        "max_model_len": max_len,
        "tp_size": int(tp),
        "notes": (row.get("notes") or "").strip(),
        "is_default": mid == DEFAULT_MODAL_MODEL and gpu.split(":")[0] == DEFAULT_MODAL_GPU,
        "env": {
            "MODAL_VLLM_MODEL": mid,
            "MODAL_VLLM_GPU": gpu,
            "MODAL_VLLM_QUANTIZATION": str(quant),
            "MODAL_VLLM_MAX_MODEL_LEN": str(max_len),
            "MODAL_VLLM_TP_SIZE": str(int(tp)),
        },
    }


def env_exports(
    model_id: str | None = None,
    *,
    gpu_override: str | None = None,
    shell: str = "bash",
) -> str:
    """Shell snippet suitable for ``eval "$(sandbox modal-matrix env …)"``."""
    resolved = resolve_modal_row(model_id, gpu_override=gpu_override)
    lines = [
        f"# modal-matrix: {resolved['model']} on {resolved['gpu']} "
        f"(default_posture={resolved['is_default']})",
    ]
    for key, val in resolved["env"].items():
        if shell == "fish":
            lines.append(f"set -gx {key} {val!r}")
        else:
            # Safe for bash/zsh eval — values are HF ids / short tokens.
            lines.append(f"export {key}={_shell_quote(val)}")
    lines.append(
        "# then: modal run deploy/modal_vllm.py::download_model && "
        "modal deploy deploy/modal_vllm.py --strategy recreate"
    )
    return "\n".join(lines) + "\n"


def _shell_quote(value: str) -> str:
    if value == "":
        return '""'
    if all(c.isalnum() or c in "/._-:+" for c in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def cutover_hints(resolved: dict[str, Any]) -> list[str]:
    """Operator notes after a matrix swap (run YAML still defaults to L4)."""
    hints = [
        "Deploy knobs come ONLY from MODAL_VLLM_* at `modal deploy` time.",
        "Specialist run-30 YAMLs stay Qwen/Qwen3-8B + L4 — do not edit them "
        "for one-off swaps; copy to config/runs/<name>.yaml if needed.",
        "After recreate: export VLLM_BASE_URL from the new modal.run URL and "
        "sandbox cutover --profile modal-vllm && sandbox health --profile modal-vllm",
    ]
    if not resolved.get("is_default"):
        hints.append(
            f"ALTERNATE posture: {resolved['model']} on {resolved['gpu']} — "
            "not the default 30-doc specialist cost-eval path "
            "(docs/benchmark-l4.md)."
        )
    return hints
