"""Experiment-log prompt labels (issue #39 / DMR-053 / SAND-027-3)."""

from __future__ import annotations

from typing import Any


def _agent_ref(prompt_lock: dict[str, Any] | None, task: str) -> dict[str, Any] | None:
    if not prompt_lock:
        return None
    agents = prompt_lock.get("agents") or {}
    ref = agents.get(task)
    return ref if isinstance(ref, dict) else None


def _local_stem(ref: dict[str, Any]) -> str | None:
    if ref.get("source") != "local":
        return None
    stem = str(ref.get("file") or ref.get("stem") or "").strip()
    return stem or None


def _bound_prompt_for_task(task: str) -> str | None:
    try:
        from llm.prompts import _bound_prompt_versions

        versions = _bound_prompt_versions()
        if task in versions:
            return str(versions[task])
    except Exception:
        return None
    return None


def _catalog_identity(label: str | None, *, task: str) -> tuple[str | None, str | None, str | None]:
    """eval-environment key, sandbox stem, catalog sha256 when this is a frozen v1 pin."""
    del task  # identity is the stem/key; task is accepted for call-site symmetry
    if not label:
        return None, None, None
    from mailroom_sandbox.eval_environment_lineage import lookup

    row = lookup(stem=label, key=label)
    if row is None:
        return None, None, None
    return (
        str(row.get("eval_environment_key") or "") or None,
        str(row.get("sandbox_stem") or "") or None,
        str(row.get("sha256") or "") or None,
    )


def resolve_logged_prompt_version(
    prompt_version: str | None,
    *,
    task: str,
    prompt_lock: dict[str, Any] | None = None,
) -> tuple[str, str | None]:
    """Label (+ optional sha256) written to experiment / serving records.

    When the lock or explicit variant is an eval-environment frozen v1
    specialist stem, the label is the catalog key (``contracts_specialist_v1``)
    so Modal records pair with eval-environment ``prompt_key``.
    """
    stem: str | None = None
    sha: str | None = None
    if prompt_version:
        ref = _agent_ref(prompt_lock, task)
        sha = str(ref["sha256"]) if ref and ref.get("sha256") else None
        stem = prompt_version
        label = prompt_version
    else:
        ref = _agent_ref(prompt_lock, task)
        if ref:
            stem = _local_stem(ref)
            if stem:
                sha = str(ref["sha256"]) if ref.get("sha256") else None
                label = stem
            else:
                label = None
        else:
            label = None
        if not label:
            default = (prompt_lock or {}).get("default") or {}
            if isinstance(default, dict):
                stem = _local_stem(default)
                if stem:
                    sha = str(default["sha256"]) if default.get("sha256") else None
                    label = stem
                elif default.get("source"):
                    label = str(default["source"])
        if not label:
            bound = _bound_prompt_for_task(task)
            if bound:
                return bound, None
            return "mailroom-default", None

    env_key, catalog_stem, catalog_sha = _catalog_identity(stem or label, task=task)
    if env_key and (stem or label) in {env_key, catalog_stem}:
        return env_key, sha or catalog_sha
    return label, sha


def stamp_prompt_provenance(record: dict[str, Any], label: str, sha256: str | None) -> None:
    record["prompt_version"] = label
    if sha256:
        record["prompt_sha256"] = sha256
    env_key, stem, catalog_sha = _catalog_identity(label, task=str(record.get("task") or ""))
    if env_key:
        record["eval_environment_prompt_key"] = env_key
        if stem:
            record.setdefault("prompt_stem", stem)
        if catalog_sha and not record.get("prompt_sha256"):
            record["prompt_sha256"] = catalog_sha
