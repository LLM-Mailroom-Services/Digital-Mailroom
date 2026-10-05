"""Resolve report grouping from a run ID or its locked experiment metadata."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from mailroom_sandbox.paths import config_dir, repo_root

_SAND_TOKEN = re.compile(r"(?:^|[^A-Za-z0-9])SAND[-_]?0*(\d+)(?!\d)", re.IGNORECASE)
_REPORT_GROUP = re.compile(r"^SAND-(\d+)$", re.IGNORECASE)
_SWEEP_FIELDS = ("experiment", "experiment_id", "sweep", "sweep_id", "runbook", "runbook_id", "config", "config_path")


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """``yaml.safe_load`` keeps the last duplicate mapping key; reject instead."""

    def construct_mapping(self, node, deep=False):
        """Build a mapping and raise if a key is repeated."""
        if isinstance(node, yaml.nodes.MappingNode):
            self.flatten_mapping(node)
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _canonical_group(value: Any) -> str | None:
    """Return ``SAND-N`` when ``value`` is a canonical report-group token."""
    match = _REPORT_GROUP.fullmatch(str(value or "").strip())
    return f"SAND-{int(match.group(1))}" if match else None


def _report_groups() -> dict[str, Any]:
    """Load the report-group catalog, rejecting duplicates and invalid shapes."""
    path = config_dir() / "report-groups.yaml"
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeySafeLoader) or {}
    if not isinstance(data, Mapping) or data.get("schema") != "sandbox.report-groups/v1":
        raise ValueError(f"{path}: unsupported or invalid report-group catalog")
    if "runbooks" in data and not isinstance(data["runbooks"], Mapping):
        raise ValueError(f"{path}: runbooks must be a mapping")
    if "legacy_run_id_patterns" in data:
        patterns = data["legacy_run_id_patterns"]
        if not isinstance(patterns, list) or any(not isinstance(row, Mapping) for row in patterns):
            raise ValueError(f"{path}: legacy_run_id_patterns must be a list of mappings")
    return dict(data)


def report_group_for_runbook(runbook_id: str | None) -> str | None:
    """Map a cataloged runbook id to its report group, or ``None``."""
    if not runbook_id:
        return None
    groups = _report_groups().get("runbooks") or {}
    return _canonical_group(groups.get(str(runbook_id).strip())) if isinstance(groups, Mapping) else None


def report_group_for_config(config_path: str | Path | None) -> str | None:
    """Resolve a run YAML path through the catalog to a single report group."""
    if not config_path:
        return None
    path = Path(config_path).expanduser()
    if not path.is_absolute():
        path = repo_root() / path
    try:
        relative = path.resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return None

    from mailroom_sandbox.job.runbooks import load_catalog

    configured_runbooks = _report_groups().get("runbooks") or {}
    rows = load_catalog().get("runbooks") or {}
    matches = {
        _canonical_group(configured_runbooks.get(str(runbook_id)))
        for runbook_id, row in rows.items()
        if relative in {str(item) for item in (row or {}).get("configs") or []}
    }
    matches.discard(None)
    if len(matches) > 1:
        raise ValueError(f"config {relative!r} belongs to runbooks with different report groups: {sorted(matches)}")
    return next(iter(matches), None)


def report_group_for_legacy_run_id(run_id: str | None) -> str | None:
    """Match a locked run id against catalog legacy patterns."""
    candidate = str(run_id or "").strip()
    if not candidate:
        return None
    for row in _report_groups().get("legacy_run_id_patterns") or []:
        if re.fullmatch(str(row.get("pattern") or ""), candidate, re.IGNORECASE):
            return _canonical_group(row.get("report_group"))
    return None


def experiment_prefix(run_id: str | None, metadata: Mapping[str, Any] | None = None) -> str | None:
    """Return ``SAND-NN`` only when the run is associated with a named sweep."""
    if isinstance(metadata, Mapping):
        group = _canonical_group(metadata.get("report_group"))
        if group:
            return group
        for key in ("runbook_id", "runbook"):
            group = report_group_for_runbook(str(metadata.get(key) or "").strip())
            if group:
                return group

    candidates = [str(run_id or "")]
    if isinstance(metadata, Mapping):
        candidates.extend(str(metadata.get(key) or "") for key in _SWEEP_FIELDS)

    for candidate in candidates:
        match = _SAND_TOKEN.search(candidate)
        if match:
            return f"SAND-{int(match.group(1))}"

    return report_group_for_legacy_run_id(run_id)
