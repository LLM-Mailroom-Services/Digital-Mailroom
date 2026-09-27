"""eval-environment frozen v1 specialist prompt catalog (SAND-027-3).

The org-owned ``LLM-Mailroom-Services/eval-environment`` catalog is the
source of truth for specialist extraction prompts. Sandbox Modal + vLLM
runs pin the matching local stems under ``config/prompts/``; those files
must stay byte-identical to the frozen v1 sha256s.

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
        for name, row in rows.items():
            if needle in {
                str(row.get("sandbox_stem")),
                str(row.get("eval_environment_key")),
            }:
                if agent and agent != name:
                    continue
                return dict(row, agent=name)
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
    """Refuse a catalog stem whose bytes drifted from the frozen v1 lock."""
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
    for agent, row in specialist_rows().items():
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
    for agent, row in specialist_rows().items():
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
    return errors
