"""Fixture catalog, tiny HF slices, and optional Hub pulls."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from mailroom_sandbox.paths import fixtures_dir, repo_root

MANIFEST_NAME = "manifest.csv"
HF_DATASET = "Lucius-Morningstar/mailroom-corpus"


def manifest_path() -> Path:
    return fixtures_dir() / MANIFEST_NAME


def load_manifest() -> list[dict[str, str]]:
    path = manifest_path()
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fixture_file(row: dict[str, str]) -> Path:
    return fixtures_dir() / row["subdir"] / row["filename"]


def parse_expected_fields(row: dict[str, str]) -> dict | None:
    raw = row.get("expected_fields") or ""
    if isinstance(raw, dict):
        return raw
    raw = str(raw).strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def dataset_fingerprint(rows: list[dict[str, str]]) -> str:
    """One canonical dataset fingerprint for records of the SAME rows.

    Covers id/filename/class/subclass/expected_fields so two same-id datasets
    with different GT content cannot collide; eval-run and job-run records
    share this function so ``pair_comparable_runs`` can pair them (DMR-049).
    """
    blob = json.dumps(
        [
            (
                r.get("id"),
                r.get("filename"),
                r.get("expected_doc_class"),
                r.get("expected_subclass"),
                json.dumps(r.get("expected_fields") or {}, sort_keys=True, default=str),
            )
            for r in rows
        ],
        sort_keys=True,
    )
    return hashlib.md5(blob.encode()).hexdigest()[:12]


def load_hf_fixtures() -> list[dict[str, Any]]:
    path = fixtures_dir() / "hf" / "docclass_mini.jsonl"
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


LEGALBENCH_FIXTURE = "legalbench/contract_qa.jsonl"
LEGALBENCH_TASKS = ("contract_qa", "family_classification")


def load_legalbench_fixtures(task: str | None = None) -> list[dict[str, Any]]:
    """Committed offline LegalBench fixture rows (the ``contract_qa`` smoke set).

    Raises when the fixture is missing — an empty fixture must never be scored
    as a 0-row eval (DMR-049 F2). ``task`` filters rows by their ``task`` key.
    """
    path = fixtures_dir() / LEGALBENCH_FIXTURE
    if not path.is_file():
        raise FileNotFoundError(f"legalbench fixture missing: {path}")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if task:
        rows = [r for r in rows if str(r.get("task") or "contract_qa") == task]
    return rows


def load_legalbench_suite_rows(task: str, *, sample: int, seed: int) -> list[dict[str, Any]]:
    """Seeded subset from the vendored llm-mailroom LegalBench suite.

    The real suite (``contract_qa``: 510 contracts x 41 categories = 20,910
    QA pairs; ``family_classification``: 200 labeled contracts) lives in
    llm-mailroom and needs its CUAD corpus on disk
    (``python scripts/fetch_full_cuad.py``). Rows are normalized to the
    sandbox keys (``question``/``document_text``/``answer``) so the runners
    consume either source identically.

    Raises ``FileNotFoundError`` when the suite is unavailable, and the
    suite's own ``CorpusUnavailable`` (naming the fetch command) when the
    corpus is missing — a live run never silently falls back to the toy
    fixture (DMR-049 F2/F4).
    """
    import sys

    from mailroom_sandbox.runtime import resolve_mailroom_src

    src = resolve_mailroom_src()
    if src is None:
        raise FileNotFoundError(
            "llm-mailroom source not found — run `sandbox fetch-deps` to vendor it"
        )
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from legalbench.tasks import get_task  # type: ignore
    except ModuleNotFoundError as exc:
        # The suite rides the vendored langchain_agents stack, which the
        # offline-first base install intentionally omits (DMR-058) — point
        # at the extra instead of leaking the import traceback.
        raise FileNotFoundError(
            f"legalbench suite needs the pipeline deps (missing {exc.name}) — "
            'pip install -e ".[pipeline]"'
        ) from exc

    task_obj = get_task(task)
    rows = task_obj.loader(sample, seed)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        document = str(row.get("document_text") or row.get("text") or "")
        normalized.append(
            {
                "id": str(row.get("qa_id") or row.get("row_id") or row.get("filename") or ""),
                "filename": str(row.get("filename") or row.get("qa_id") or row.get("row_id") or ""),
                "task": task,
                "question": row.get("question"),
                "document_text": document,
                "text": document,
                "answer": str(row.get("answer") or row.get("expected") or ""),
                "category": row.get("category"),
                "source_revision": f"legalbench:{task}:n={sample}:seed={seed}",
            }
        )
    return normalized


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def agent_fixture_path(agent: str) -> Path:
    return fixtures_dir() / "agents" / f"{agent}.jsonl"


def load_agent_fixtures(agent: str) -> list[dict[str, Any]]:
    return load_jsonl(agent_fixture_path(agent))


def serving_fixture_path() -> Path:
    return fixtures_dir() / "serving" / "local_vs_api.json"


def load_serving_fixtures() -> dict[str, Any]:
    """Synthetic local vs API serving records (no live LLM, no API key)."""
    path = serving_fixture_path()
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def intake_dir() -> Path:
    return fixtures_dir() / "intake"


def cache_dir() -> Path:
    path = repo_root() / "data" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def pull_hf_dataset(
    dataset_id: str = HF_DATASET,
    split: str = "test",
    max_rows: int = 50,
    revision: str = "",
    config: str = "ground_truth",
) -> Path:
    """LIVE-or-loud pinned Hub pull into data/cache (DMR-056).

    Routes through the SAME corpus loader the job preflight uses
    (``corpus.prepare_subset``): pinned revision (default
    ``FAMILY_HF_REVISION``), ``default``+``ground_truth`` merge on filename,
    ``content_sha256`` verification, GT-shard-absent refusal, deterministic
    subsetting (never first-N). ANY failure raises (the CLI maps it to exit
    1) — the old ``except Exception -> README marker -> exit 0`` silent no-op
    is gone, so a pull that fetched zero rows can never look successful.
    """
    from mailroom_sandbox.corpus import prepare_subset
    from mailroom_sandbox.job.spec import DatasetSpec, FAMILY_HF_REVISION

    rev = revision or FAMILY_HF_REVISION
    spec = DatasetSpec(
        provider="huggingface",
        repo=dataset_id,
        config=config,
        split=split,
        revision=rev,
        limit=max_rows,
    )
    dest = (
        cache_dir()
        / f"{dataset_id.replace('/', '__')}__{rev[:12]}"
        / f"{config or 'default'}_{split}_subset.jsonl"
    )
    result = prepare_subset(spec, dest)
    if not result.get("rows"):
        raise RuntimeError(
            f"pull returned 0 rows for {dataset_id}@{rev} "
            f"({config or 'default'}/{split}) — refusing to write an empty dataset"
        )
    print(
        f"pulled {result['rows']} row(s) from {dataset_id}@"
        f"{result.get('revision_resolved') or rev[:12]} ({config or 'default'}/{split}) "
        f"sha256={result['sha256'][:12]} -> {dest}"
    )
    return dest
