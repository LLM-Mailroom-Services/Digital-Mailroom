"""eval-environment frozen v1 specialist prompt catalog (SAND-027-3).

The org-owned ``LLM-Mailroom-Services/eval-environment`` catalog is the
source of truth for specialist extraction prompts. Sandbox Modal + vLLM
runs pin the matching local stems under ``config/prompts/``; those files
must stay byte-identical to the frozen v1 sha256s.

Later frozen versions of a specialist (``frozen_successors`` in the lock, e.g.
the SAND-042 repaired insurance and merger stems frozen as eval-environment
``*_v4`` mutations) are byte-pinned the same way. They do not change the
default v1 stem a run gets; a run opts in by pinning the successor stem.

A specialist's default row may itself be a later eval-environment mutation
that corrected the original v1 text (dojo #30 re-freeze: the corporate-records
and correspondence stems carry ``*_v6`` / ``*_v7``). Such a row has a
``parent_key`` and a ``superseded`` block (the original v1 key, sha256, chars
and ``frozen_at``), so the v1 identity stays recoverable and is still checked
against a sibling checkout's manifest.

This module is hermetic: the sha256 lock lives in
``config/prompts/eval_environment_lineage.json``. A sibling eval-environment
checkout is optional (``EVAL_ENVIRONMENT_ROOT`` or ``../eval-environment``).
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.paths import prompts_dir, repo_root

CATALOG_NAME = "eval_environment_lineage.json"

# Vendor-mirror stems that are NOT the eval-environment frozen v1 surface.
VENDOR_MIRROR_STEMS: dict[str, str] = {
    "contracts_specialist_v33": "contracts_specialist",
    "merger_agreement_specialist_production": "merger_agreement_specialist",
    "corporate_records_specialist_production": "corporate_records_specialist",
    "correspondence_specialist_production": "correspondence_specialist",
    "insurance_claims_specialist_production": "insurance_claims_specialist",
}

_LOCAL_V0_SUFFIX = "_local_v0"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    path = prompts_dir() / CATALOG_NAME
    if not path.is_file():
        raise FileNotFoundError(f"missing eval-environment lineage lock {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("specialists"):
        raise ValueError(f"{path} must contain a specialists mapping")
    return data


def specialist_rows() -> dict[str, dict[str, Any]]:
    rows = load_catalog()["specialists"]
    return {str(agent): dict(row) for agent, row in rows.items()}


def successor_rows() -> list[dict[str, Any]]:
    """Frozen post-v1 specialist versions (eval-environment mutations), each with ``agent``."""
    rows = load_catalog().get("frozen_successors") or []
    return [dict(row) for row in rows]


def superseded_rows() -> list[dict[str, Any]]:
    """Original v1 identities (key, sha256, chars, frozen_at) of re-frozen default rows."""
    out: list[dict[str, Any]] = []
    for agent, row in specialist_rows().items():
        old = row.get("superseded")
        if isinstance(old, dict):
            out.append(dict(old, agent=agent, superseded_by=row.get("eval_environment_key")))
    return out


def _all_rows() -> list[dict[str, Any]]:
    v1 = [dict(row, agent=name) for name, row in specialist_rows().items()]
    return v1 + successor_rows()


def catalog_agents() -> tuple[str, ...]:
    return tuple(sorted(specialist_rows()))


def default_prompt_variant(agent: str) -> str | None:
    """Sandbox stem eval-environment froze as v1 for this specialist, if any."""
    row = specialist_rows().get(agent)
    if not row:
        return None
    stem = str(row.get("sandbox_stem") or "").strip()
    return stem or None


def lookup(
    *,
    agent: str | None = None,
    stem: str | None = None,
    key: str | None = None,
) -> dict[str, Any] | None:
    """Return the catalog row matching agent, sandbox stem, or eval-env key."""
    rows = specialist_rows()
    needle = stem or key
    if needle:
        for row in _all_rows():
            if needle in {
                str(row.get("sandbox_stem")),
                str(row.get("eval_environment_key")),
            }:
                if agent and agent != row["agent"]:
                    continue
                return row
        return None
    if agent and agent in rows:
        return dict(rows[agent], agent=agent)
    return None


def eval_environment_key_for(*, agent: str | None = None, stem: str | None = None) -> str | None:
    row = lookup(agent=agent, stem=stem)
    if not row:
        return None
    key = str(row.get("eval_environment_key") or "").strip()
    return key or None


def agents_for_variant(variant: str) -> list[str]:
    """Which pipeline agent(s) a local prompt stem should patch.

    Catalog stems map 1:1 onto their specialist. ``sorter_local_v0`` still
    covers sorter + sorter_reviewer (historical ``patch_managed_prompt``
    behaviour). Unknown stems fall back to the prefix before ``_local`` /
    ``_v``.
    """
    name = str(variant or "").strip()
    if not name:
        return []
    row = lookup(stem=name, key=name)
    if row:
        return [str(row["agent"])]
    vendor = VENDOR_MIRROR_STEMS.get(name)
    if vendor:
        return [vendor]
    if name.endswith(_LOCAL_V0_SUFFIX):
        target = name[: -len(_LOCAL_V0_SUFFIX)]
        if target == "sorter":
            return ["sorter", "sorter_reviewer"]
        return [target] if target else []
    if "_v" in name:
        return [name.split("_v", 1)[0]]
    return [name]


def assert_catalog_sha(agent: str, stem: str, text: str) -> None:
    """Refuse a catalog stem whose bytes drifted from its frozen lock row."""
    row = lookup(agent=agent, stem=stem)
    if not row:
        return
    if str(row.get("sandbox_stem")) != stem and str(row.get("eval_environment_key")) != stem:
        return
    expected = str(row.get("sha256") or "")
    actual = _sha(text)
    if expected and actual != expected:
        raise ValueError(
            f"eval-environment lineage drift for {agent}: stem={stem} "
            f"file_sha256={actual} catalog_sha256={expected} "
            f"(frozen key {row.get('eval_environment_key')}). "
            "Re-copy the eval-environment v1 text or update "
            f"config/prompts/{CATALOG_NAME} after a sanctioned re-freeze."
        )


def local_stem_sha256(stem: str) -> str:
    path = prompts_dir() / f"{stem}.txt"
    return _sha(path.read_text(encoding="utf-8"))


def verify_local_catalog(*, require_opening: bool = True) -> list[str]:
    """Return errors if sandbox catalog stems drifted from the JSON lock."""
    errors: list[str] = []
    for row in _all_rows():
        agent = row["agent"]
        stem = str(row["sandbox_stem"])
        path = prompts_dir() / f"{stem}.txt"
        if not path.is_file():
            errors.append(f"missing sandbox stem {path}")
            continue
        text = path.read_text(encoding="utf-8")
        actual = _sha(text)
        expected = str(row["sha256"])
        if actual != expected:
            errors.append(
                f"{agent}: {stem}.txt sha256={actual} != catalog {expected} "
                f"({row['eval_environment_key']})"
            )
        opening = str(row.get("opening") or "")
        if require_opening and opening and not text.startswith(opening):
            errors.append(
                f"{agent}: {stem}.txt does not start with eval-environment "
                f"designated stem {opening!r}"
            )
        expected_chars = row.get("chars")
        if expected_chars is not None and len(text) != int(expected_chars):
            errors.append(
                f"{agent}: {stem}.txt chars={len(text)} != catalog {expected_chars}"
            )
    return errors


def sibling_eval_environment_root() -> Path | None:
    env = os.environ.get("EVAL_ENVIRONMENT_ROOT")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    root = repo_root()
    candidates.extend(
        [
            root.parent / "eval-environment",
            root.parent.parent / "eval-environment",
        ]
    )
    for cand in candidates:
        manifest = cand / "prompts" / "manifest.json"
        if manifest.is_file():
            return cand.resolve()
    return None


def _md_body(path: Path) -> str:
    """Strip the leading markdown H1 that eval-environment mirrors wrap around the stem."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("#"):
        rest = text.split("\n", 1)[1] if "\n" in text else ""
        return rest.lstrip("\n")
    return text


def verify_sibling_catalog(sibling: Path | None = None) -> list[str]:
    """Compare sandbox stems to a sibling eval-environment checkout when present."""
    root = sibling if sibling is not None else sibling_eval_environment_root()
    if root is None:
        return []
    errors: list[str] = []
    manifest_path = root / "prompts" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read {manifest_path}: {exc}"]
    versions: Mapping[str, Any] = manifest.get("versions") or {}
    mutation_rows: list[dict[str, Any]] = []
    for agent, row in specialist_rows().items():
        row = dict(row, agent=agent)
        if row.get("parent_key"):
            # Default row is a later mutation: verify it (and its bytes) against
            # the sibling's mutations.json, and the superseded v1 identity
            # against the manifest.
            mutation_rows.append(row)
            old = row.get("superseded")
            if isinstance(old, dict):
                v1_meta = versions.get(str(old.get("eval_environment_key"))) if isinstance(versions, dict) else None
                if not isinstance(v1_meta, dict):
                    errors.append(f"{agent}: sibling manifest missing superseded {old.get('eval_environment_key')}")
                elif str(v1_meta.get("sha256") or "") != str(old.get("sha256")):
                    errors.append(
                        f"{agent}: superseded {old.get('eval_environment_key')} sha256={old.get('sha256')} "
                        f"!= sibling manifest sha256={v1_meta.get('sha256')}"
                    )
            continue
        key = str(row["eval_environment_key"])
        meta = versions.get(key) if isinstance(versions, dict) else None
        if not isinstance(meta, dict):
            errors.append(f"{agent}: sibling manifest missing {key}")
            continue
        sibling_sha = str(meta.get("sha256") or "")
        if sibling_sha and sibling_sha != str(row["sha256"]):
            errors.append(
                f"{agent}: sandbox catalog sha256={row['sha256']} "
                f"!= sibling {key} sha256={sibling_sha}"
            )
        md_path = root / "prompts" / f"{key}.md"
        if not md_path.is_file():
            errors.append(f"{agent}: missing sibling mirror {md_path}")
            continue
        md_sha = _sha(_md_body(md_path))
        local_sha = local_stem_sha256(str(row["sandbox_stem"]))
        if md_sha != local_sha:
            errors.append(
                f"{agent}: sibling {key}.md sha256={md_sha} "
                f"!= sandbox {row['sandbox_stem']}.txt sha256={local_sha}"
            )
    errors.extend(_verify_sibling_mutations(root, mutation_rows + successor_rows()))
    return errors


def _verify_sibling_successors(root: Path) -> list[str]:
    """Frozen-successor rows only (the SAND-042 ``*_v4`` stems)."""
    return _verify_sibling_mutations(root, successor_rows())


def _verify_sibling_mutations(root: Path, rows: list[dict[str, Any]]) -> list[str]:
    """Mutation rows (successors, re-frozen defaults) live in the sibling's ``prompts/mutations.json``."""
    if not rows:
        return []
    path = root / "prompts" / "mutations.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read {path}: {exc}"]
    registered = {str(m.get("key")): m for m in data.get("mutations") or []}
    errors: list[str] = []
    for row in rows:
        key = str(row["eval_environment_key"])
        meta = registered.get(key)
        if meta is None:
            errors.append(f"{row['agent']}: sibling mutations.json missing {key}")
            continue
        if str(meta.get("parent")) != str(row.get("parent_key")):
            errors.append(
                f"{row['agent']}: sibling {key} parent={meta.get('parent')} "
                f"!= catalog parent_key={row.get('parent_key')}"
            )
        if str(meta.get("sha256")) != str(row["sha256"]):
            errors.append(
                f"{row['agent']}: sandbox catalog sha256={row['sha256']} "
                f"!= sibling {key} sha256={meta.get('sha256')}"
            )
        # The recorded sha256 is metadata; the frozen bytes are ``text``.
        text = meta.get("text")
        if not isinstance(text, str):
            errors.append(f"{row['agent']}: sibling {key} has no mutation text")
        elif _sha(text) != str(row["sha256"]):
            errors.append(
                f"{row['agent']}: sibling {key} text sha256={_sha(text)} "
                f"!= sandbox catalog sha256={row['sha256']}"
            )
    return errors
