"""Constellation repo browser for the mailroom-tui REPL.

The LLM-Mailroom constellation is the set of standalone ``Exios66/*`` repos
mirrored by the monorepo ``mailroom-hub``.  Each entry ships a bundled blurb
(the source of truth when offline) and can be enriched with live GitHub API
metadata (description / stars / updated) — fail-soft, cached, never blocking.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import webbrowser
from typing import Any, Optional

GITHUB_ORG = "Exios66"
# Name -> (role, dist, bundled blurb, homepage).
CONSTELLATION: dict[str, dict[str, str]] = {
    "llm-mailroom": {
        "role": "pipeline",
        "dist": "mailroom",
        "blurb": "Multi-agent pipeline: ingests high-volume legal documents, "
                 "classifies them, routes them to specialist agents for "
                 "extraction, compiles matter records, and archives everything "
                 "with a full audit trail.",
        "homepage": "",
    },
    "The-Mailroom": {
        "role": "visualizer",
        "dist": "the-mailroom",
        "blurb": "Pixel-art visual engine for the llm-mailroom pipeline — this "
                 "package. Every displayed value is derived from Langfuse "
                 "traces.",
        "homepage": "https://exios66.github.io/The-Mailroom/",
    },
    "llm-dojo-scoring": {
        "role": "scoring",
        "dist": "llm-dojo-scoring",
        "blurb": "Dedicated scoring, error-analysis, visualization, and "
                 "interpretation suite for LLM document pipelines — a single "
                 "importable library replacing project-local scoring code.",
        "homepage": "",
    },
    "llm-entity-extraction": {
        "role": "eval",
        "dist": "llm-entity-extraction",
        "blurb": "Training & evaluation environment to identify strong LLM "
                 "candidates for legal document entity extraction, "
                 "classification, and summarization.",
        "homepage": "",
    },
    "agent-mailroom": {
        "role": "pipeline",
        "dist": "agent-mailroom",
        "blurb": "Self-contained legal-document mailroom: one state machine per "
                 "document, specialist agents at desks, a hash-chained audit "
                 "log, and a pixel floor where envelopes fly from reception to "
                 "the boss.",
        "homepage": "",
    },
    "local-mailroom-sandbox": {
        "role": "sandbox",
        "dist": "mailroom-sandbox",
        "blurb": "Sandbox for developing & testing the LLM mailroom pipeline "
                 "with offline/localized models.",
        "homepage": "",
    },
    "Enron-Evaluation-Environment": {
        "role": "corpus",
        "dist": "enron-evaluation-environment",
        "blurb": "Exploratory data analysis of the CMU classic Enron email "
                 "corpus and the production of a pipeline-ready correspondence "
                 "dataset for the pipeline.",
        "homepage": "",
    },
    "claims-data-eda": {
        "role": "corpus",
        "dist": "claims-data-eda",
        "blurb": "Exploratory data analysis of real insurance-claim samples "
                 "from the mailroom-dataset (carrier / inpatient / outpatient / "
                 "PDE strata).",
        "homepage": "",
    },
    "llm-mailroom-graph": {
        "role": "derived",
        "dist": "llm-mailroom-graph",
        "blurb": "Interactive graphify knowledge graph of llm-mailroom — a "
                 "derived artifact site rebuilt from the source repo.",
        "homepage": "https://exios66.github.io/llm-mailroom-graph/",
    },
    "mailroom-corpus-eda": {
        "role": "corpus",
        "dist": "mailroom-corpus-eda",
        # Upstream repo keeps the capitalized casing; the monorepo package
        # (and the sync cursor) use the lowercase name.
        "repo": "Mailroom-Corpus-EDA",
        "blurb": "Dedicated repository for the full HF LLM-Mailroom corpus "
                 "exploratory data analysis + the centralized Hub upload "
                 "helpers (mailroom-dataset dataset family).",
        "homepage": "",
    },
    "mailroom-dev": {
        "role": "hub",
        "dist": "mailroom-hub",
        "blurb": "The monorepo of the LLM-Mailroom project (this workspace) — "
                 "one uv workspace, one lockfile, all feeder repositories "
                 "mirrored as packages. Canonical hub URL: "
                 "https://github.com/Exios66/mailroom-dev.",
        "homepage": "",
    },
    "mailroom-hub": {
        "role": "hub",
        "dist": "mailroom-hub",
        "blurb": "Monorepo mirror of Exios66/mailroom-dev under the "
                 "mailroom-hub release name (CHANGELOG + release chain + "
                 "vX.Y.Z tags).",
        "homepage": "",
    },
    "LLM-Postal": {
        "role": "hub",
        "dist": "mailroom-hub",
        "blurb": "Monorepo mirror of the LLM-Mailroom constellation — one "
                 "checkout, one virtualenv, ten packages, zero cross-repo "
                 "import friction.",
        "homepage": "",
    },
    "mailroom-dev-graph": {
        "role": "derived",
        "dist": "mailroom-dev-graph",
        "blurb": "Interactive graphify knowledge graph of the mailroom-dev "
                 "monorepo — 4,870 code symbols, 16,161 edges, 325 communities "
                 "across 9 packages.",
        "homepage": "https://exios66.github.io/mailroom-dev-graph/",
    },
    "llm-entity-extraction-graph": {
        "role": "derived",
        "dist": "llm-entity-extraction-graph",
        "blurb": "Interactive graphify knowledge graph of llm-entity-extraction "
                 "— a derived artifact site.",
        "homepage": "",
    },
}

GH_API = "https://api.github.com/repos"
CACHE_TTL = float(os.environ.get("MAILROOM_REPOS_TTL", "3600"))


def repo_url(name: str) -> str:
    meta = CONSTELLATION.get(name, {})
    repo = meta.get("repo", name)
    return f"https://github.com/{GITHUB_ORG}/{repo}"


def all_repos() -> list[dict[str, str]]:
    """Constellation entries with GitHub URLs attached, stable order."""
    out = []
    for name, meta in CONSTELLATION.items():
        out.append({"name": name, **meta, "url": repo_url(name)})
    return out


def _fetch_gh(name: str) -> Optional[dict[str, Any]]:
    url = f"{GH_API}/{GITHUB_ORG}/{name}"
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": "mailroom-tui"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return None


# {name: (fetched_at, payload)} — GitHub API is unauthenticated-rate-limited
# (60 req/h); every call is cached for CACHE_TTL so a browsing session never
# burns the budget.
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def live_meta(name: str, force: bool = False) -> Optional[dict[str, Any]]:
    """Live GitHub metadata for one repo; None when unreachable/unenriched."""
    now = time.monotonic()
    hit = _CACHE.get(name)
    if hit and not force and now - hit[0] < CACHE_TTL:
        return hit[1]
    payload = _fetch_gh(name)
    if payload is None:
        if hit:
            return hit[1]
        return None
    slim = {
        "description": payload.get("description") or "",
        "stars": payload.get("stargazers_count"),
        "language": payload.get("language"),
        "updated_at": (payload.get("updated_at") or "")[:10],
        "homepage": payload.get("homepage") or "",
        "archived": bool(payload.get("archived")),
        "fork": bool(payload.get("fork")),
        "html_url": payload.get("html_url") or repo_url(name),
    }
    _CACHE[name] = (now, slim)
    return slim


def open_repo(name: str) -> bool:
    """Open a repo's GitHub page in the default browser. False on failure."""
    try:
        return webbrowser.open(repo_url(name))
    except Exception:
        return False


def lookup(name: str) -> Optional[dict[str, str]]:
    """Match a repo name, tolerating an ``Exios66/`` org prefix."""
    needle = name.strip().lower()
    if needle.startswith("exios66/"):
        needle = needle[len("exios66/"):]
    for repo in all_repos():
        if repo["name"].lower() == needle:
            return repo
    return None