"""Append-only sandbox experiment log (JSONL + markdown summary)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from llm_dojo_scoring.experiment import append_experiment, git_snapshot, load_records, utc_now

from mailroom_sandbox.paths import reports_dir

JSONL_NAME = "experiment_log.jsonl"
MD_NAME = "experiment_log.md"

#: Provider/GPU identity extras a run may record for a Modal self-hosted leg
#: (GPU billing rate, warm span, scale-to-zero window, weight pin, image tag,
#: vLLM serving knobs). The vendored dojo ``IDENTITY_FIELDS`` does not carry
#: them, so they pass through to the JSONL row verbatim (never normalized away).
PROVIDER_IDENTITY_KEYS = (
    "gpu_hourly_usd",
    "warm_span_seconds",
    "scaledown_seconds",
    "revision",
    "image_tag",
    "gpu_memory_utilization",
    "max_num_seqs",
)


def jsonl_path() -> Path:
    return reports_dir() / JSONL_NAME


def md_path() -> Path:
    return reports_dir() / MD_NAME


def new_record(
    *,
    identity: Mapping[str, Any] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Build a JSONL row; ``identity`` carries provider/GPU serving extras.

    Extras (see ``PROVIDER_IDENTITY_KEYS``) are merged into the row so they
    survive to the JSONL log. ``fields`` may also carry them directly — both
    paths are backward-compatible and nothing is stripped here.
    """
    record = {
        "timestamp": utc_now(),
        "sandbox": True,
        "git": git_snapshot(),
    }
    record.update(fields)
    if identity:
        for key, value in identity.items():
            if value is not None:
                record[key] = value
    from mailroom_sandbox.eval.scoring import attach_serving_identity

    return attach_serving_identity(record)


def append(record: dict[str, Any], path: Path | None = None) -> Path:
    dest = path or jsonl_path()
    written = append_experiment(record, dest)
    regenerate_markdown(dest)
    return written


def regenerate_markdown(jsonl: Path | None = None) -> Path:
    src = jsonl or jsonl_path()
    dest = src.with_suffix(".md") if src.name.endswith(".jsonl") else md_path()
    records = load_records(src) if src.is_file() else []
    lines = [
        "# Sandbox experiment log",
        "",
        "Local-variant runs only. Not a mirror of llm-entity-extraction.",
        "",
        f"{len(records)} record(s).",
        "",
    ]
    for rec in records:
        name = rec.get("experiment_name") or rec.get("name") or "(unnamed)"
        scores = rec.get("scores") or {}
        headline = scores.get("exact_match")
        if headline is None:
            headline = scores.get("overall_extraction_score")
        if headline is None:
            headline = scores.get("accuracy")
        lines.append(
            f"- `{name}` · profile={rec.get('profile')} · "
            f"provider={rec.get('provider')} · serving={rec.get('serving_kind')} · "
            f"model={rec.get('model')} · "
            f"prompt={rec.get('prompt_version')} · score={headline} · "
            f"backend={rec.get('tracing_backend')}"
        )
        card = rec.get("serving_markdown")
        if not card:
            nested = rec.get("local_vs_api") or {}
            card = nested.get("markdown") if isinstance(nested, dict) else None
        if card:
            lines.extend(["", str(card).rstrip(), ""])
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def load() -> list[dict[str, Any]]:
    path = jsonl_path()
    if not path.is_file():
        return []
    return load_records(path)
