#!/usr/bin/env python3
"""Refresh ``config/api_prices.yaml`` from OpenRouter's public model catalog.

Every model listed in the file is looked up in ``GET https://openrouter.ai/api/v1/models``
(no key needed) and its full price sheet is rewritten: base and long-prompt tiers
(``pricing.overrides``), input-cache read/write, context length and max completion tokens.
Prices are stored in USD per 1M tokens. ``--add MODEL`` adds a model to the list.

    python scripts/refresh_api_prices.py            # rewrite in place
    python scripts/refresh_api_prices.py --check    # exit 1 if the file is stale
    python scripts/refresh_api_prices.py --add qwen/qwen3.7-flash

Decisions-endpoint ids (``*-decisions``) are not in the catalog; they are kept as written.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

import yaml

from mailroom_sandbox.paths import repo_root

CATALOG_URL = "https://openrouter.ai/api/v1/models"
_FIELDS = {"prompt": "prompt", "completion": "completion",
           "input_cache_read": "cache_read", "input_cache_write": "cache_write"}


def _per_million(value) -> float:
    return round(float(value) * 1_000_000, 6)


def sheet_from_catalog(entry: dict) -> dict:
    """One ``config/api_prices.yaml`` model row from an OpenRouter ``/models`` entry."""
    pricing = entry.get("pricing") or {}
    tiers = []
    for minimum, block in [(0, pricing)] + [(int(o.get("min_prompt_tokens") or 0), o)
                                            for o in pricing.get("overrides") or []]:
        tier = {"min_prompt_tokens": minimum}
        tier.update({out: _per_million(block[src]) for src, out in _FIELDS.items() if block.get(src) is not None})
        tiers.append(tier)
    top = entry.get("top_provider") or {}
    return {"context_length": entry.get("context_length") or top.get("context_length"),
            "max_completion_tokens": top.get("max_completion_tokens"),
            "tiers": sorted(tiers, key=lambda t: t["min_prompt_tokens"])}


def fetch_catalog(url: str = CATALOG_URL) -> dict[str, dict]:
    if not url.startswith("https://"):
        raise ValueError(f"model catalog URL must be https: {url!r}")
    with urllib.request.urlopen(url, timeout=30) as resp:  # nosec B310 - https only, checked above
        return {m["id"]: m for m in json.load(resp)["data"]}


def refresh(doc: dict, catalog: dict[str, dict], *, today: str) -> tuple[dict, list[str]]:
    """The refreshed document and the ids that changed (or are missing from the catalog)."""
    changed = []
    models = dict(doc.get("models") or {})
    for model_id, row in models.items():
        if model_id not in catalog:
            # Decisions-API ids are not in the chat catalog: kept as written, never flagged.
            if not model_id.endswith("-decisions") and not (row or {}).get("endpoint"):
                changed.append(f"{model_id}: not in the OpenRouter catalog")
            continue
        new = {**(row or {}), **sheet_from_catalog(catalog[model_id])}
        if new != row:
            changed.append(model_id)
        models[model_id] = new
    out = {**doc, "models": models}
    if changed:
        out["checked"] = today
    return out, changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="report drift, write nothing")
    parser.add_argument("--add", action="append", default=[], metavar="MODEL")
    args = parser.parse_args()
    path = args.file or repo_root() / "config" / "api_prices.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {"models": {}}
    for model_id in args.add:
        doc.setdefault("models", {}).setdefault(model_id, {})
    new, changed = refresh(doc, fetch_catalog(), today=dt.date.today().isoformat())
    for line in changed:
        print(f"changed: {line}")
    if args.check:
        return 1 if changed else 0
    if changed:
        header = "".join(l + "\n" for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("#")) if path.exists() else ""
        path.write_text(header + yaml.safe_dump(new, sort_keys=False), encoding="utf-8")
        print(f"wrote {path}")
    else:
        print("up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
