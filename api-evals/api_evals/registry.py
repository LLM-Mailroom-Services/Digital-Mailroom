"""api_evals — task registry for OpenRouter API eval comparisons.

Mirrors the org-owned ``LLM-Mailroom-Services/eval-environment`` task-registry
pattern (one registry of registered tasks, a case loader, a live invoker, and a
cost/scoring layer), but scoped to THIS sandbox repo and coded for OpenRouter:

* every task pins a run-spec YAML under ``api-evals/config/runs/`` that is
  COMPARABLE to the sandbox Modal run YAMLs — same strata draw (split=all,
  class bucket count N, ``sample_seed: 42``, pinned ``FAMILY_HF_REVISION``),
  same local prompt stem (``contracts_specialist_v33_simplified`` /
  ``correspondence_specialist_simplified``);
* the only difference is ``profile: openrouter`` + ``engine.model:
  qwen/qwen3.7-flash`` (the OpenRouter champion the sandbox maps the Modal
  ``Qwen/Qwen3-8B`` row onto).
* real API cost is computed from per-item tokens x the LIVE OpenRouter list
  price (never invented), with a cross-check against the response's own
  ``usage.cost`` where available.

The registry is the ONE-FILE extension point: register a task by adding a
``config/runs/<run_id>.yaml`` and (optionally) an entry here for metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PACKAGE_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _PACKAGE_DIR.parent  # api-evals/
CONFIG_DIR = _ROOT_DIR / "config"
RUNS_DIR = CONFIG_DIR / "runs"
DATA_DIR = _ROOT_DIR / "data"
REPORTS_DIR = _ROOT_DIR / "reports"
BLANK_DIR = _ROOT_DIR / "blank"

#: The OpenRouter champion id used by every api-evals task — the id the
#: sandbox's ``config/models.yaml`` maps the Modal ``Qwen/Qwen3-8B`` workhorse
#: onto, so API cost numbers are like-for-like against the Modal runs.
DEFAULT_API_MODEL = "qwen/qwen3.7-flash"

#: Expected OpenRouter list prices for the champion (USD per 1M tokens),
#: refreshed at run time from ``GET /api/v1/models``; these are the fallback
#: when the live refresh is unavailable (offline / no key). Verified against
#: the live /models payload on 2026-09-25 and against a real response's
#: ``usage.cost`` (17 prompt x 0.03 + 5 completion x 0.13 = 1.16e-6 USD).
DEFAULT_LIST_PRICES: dict[str, tuple[float, float]] = {
    "qwen/qwen3.7-flash": (0.03, 0.13),
}


@dataclass(frozen=True)
class Task:
    """One api-evals task: a run-spec YAML + resolved metadata."""

    run_id: str
    task: str
    doc_class: str
    n: int
    model: str
    prompt_stem: str
    yaml_path: Path


def task_yamls() -> list[Path]:
    return sorted(RUNS_DIR.glob("*.yaml"))


def load_task(yaml_path: Path | str) -> Task:
    """Load one run-spec YAML and lift its reproducible metadata."""
    from mailroom_sandbox.job.spec import load_run_spec

    path = Path(yaml_path)
    spec = load_run_spec(path)
    if spec.profile != "openrouter":
        raise ValueError(
            f"{path.name}: api-evals tasks must use profile=openrouter "
            f"(got {spec.profile!r})"
        )
    if spec.engine.kind != "openrouter":
        raise ValueError(
            f"{path.name}: api-evals tasks must use engine.kind=openrouter "
            f"(got {spec.engine.kind!r})"
        )
    buckets = ((spec.dataset.strata or {}).get("buckets") or [])
    doc_class = ""
    if buckets and isinstance(buckets[0], dict):
        doc_class = str(buckets[0].get("doc_class") or "")
    agents = (spec.prompt.get("agents") or {})
    prompt_stem = ""
    for ref in agents.values():
        if isinstance(ref, dict) and ref.get("source") == "local" and ref.get("file"):
            prompt_stem = str(ref["file"])
            break
    run_id = spec.run_id or path.stem
    return Task(
        run_id=run_id,
        task=str(spec.task),
        doc_class=doc_class,
        n=int(spec.dataset.limit or 0),
        model=str(spec.engine.model),
        prompt_stem=prompt_stem,
        yaml_path=path,
    )


def tasks() -> list[Task]:
    return [load_task(p) for p in task_yamls()]


def task_by_run_id(run_id: str) -> Task:
    for t in tasks():
        if t.run_id == run_id:
            return t
    raise KeyError(f"no api-evals task with run_id={run_id!r}; have {sorted(t.run_id for t in tasks())}")


def registered() -> dict[str, Any]:
    """Registry manifest (for CLI ``list`` and the report header)."""
    return {
        "provider": "openrouter",
        "model": DEFAULT_API_MODEL,
        "tasks": [
            {
                "run_id": t.run_id,
                "task": t.task,
                "doc_class": t.doc_class,
                "n": t.n,
                "prompt_stem": t.prompt_stem,
                "yaml": str(t.yaml_path),
            }
            for t in tasks()
        ],
    }
