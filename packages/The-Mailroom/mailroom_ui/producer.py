"""Pinned llm-mailroom import surface (distribution name: ``mailroom``).

The Langfuse display path never goes through this module. Operator helpers
(review resolve, the REVIEW-tray stub, the production-pilot locator) import
producer *contract* symbols when the ``[pipeline]`` extra or a sibling
checkout is available:

    pip install -e ".[pipeline]"

Pin: ``git+https://github.com/Exios66/llm-mailroom.git@2a212e76a62b`` (package
version 0.7.1 — tag ``v0.7.1``, corpus re-pin to the GT-closure revision).
Bump
``MAILROOM_GIT_SHA`` and the extra together.

In the mailroom-hub monorepo the workspace ``[pipeline]`` extra resolves
``mailroom`` to ``packages/llm-mailroom`` (editable), so the direct import
below wins; the sibling-checkout fallback also resolves to the same member
(``ROOT.parent / "llm-mailroom"``). Standalone checkouts keep the old
sibling/``MAILROOM_PIPELINE_ROOT`` behavior.

Never import ``api.main`` (watcher / embeddings / graph warm-up at import
time) or ``llm_dojo_scoring``.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import sys
from pathlib import Path
from typing import Any, Optional

# v0.7.1 tag 2a212e76a62b — "corpus re-pin to GT-closure revision 46a4d3c2"
MAILROOM_GIT_SHA = "2a212e76a62b"
MAILROOM_GIT_URL = "https://github.com/Exios66/llm-mailroom.git"
MAILROOM_DIST_NAME = "mailroom"
MAILROOM_DIST_VERSION = "0.7.1"
MAILROOM_PEP508 = (
    f"{MAILROOM_DIST_NAME} @ git+{MAILROOM_GIT_URL}@{MAILROOM_GIT_SHA}"
)

_FALLBACK_DISPOSITIONS = frozenset({"resume", "record", "requeue", "complete"})
_FALLBACK_DECISIONS = frozenset({"approved", "rejected"})

ROOT = Path(__file__).resolve().parent.parent


def pipeline_checkout() -> Optional[Path]:
    """Sibling / ``MAILROOM_PIPELINE_ROOT`` checkout, if present."""
    env = os.environ.get("MAILROOM_PIPELINE_ROOT")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend(
        [
            ROOT.parent / "llm-mailroom",
            Path("/home/ubuntu/src/llm-mailroom"),
            Path.home() / "src" / "llm-mailroom",
        ]
    )
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        src = resolved / "src"
        if (src / "pipeline" / "review_resolve.py").is_file():
            return resolved
        if (src / "graph" / "build_graph.py").is_file():
            return resolved
        if (src / "scripts" / "run_hf_pilot.py").is_file():
            return resolved
    return None


def _pin_cache_src() -> Path:
    return Path(os.environ.get("TMPDIR") or "/tmp") / f"the-mailroom-pin-{MAILROOM_GIT_SHA}" / "src"


def _materialize_git_pin(checkout: Path) -> Optional[Path]:
    """Extract ``pipeline`` + ``schemas`` at MAILROOM_GIT_SHA from a git checkout.

    The live sibling branch may not match the pin (and must not stay on
    ``sys.path`` — its ``scripts`` package would shadow this repo).
    """
    dest = _pin_cache_src()
    marker = dest / "pipeline" / "review_resolve.py"
    if marker.is_file():
        return dest
    try:
        import io
        import subprocess
        import tarfile

        proc = subprocess.run(
            [
                "git", "-C", str(checkout), "archive", MAILROOM_GIT_SHA,
                "src/pipeline", "src/schemas",
            ],
            capture_output=True,
            check=True,
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r:") as tar:
            try:
                tar.extractall(dest.parent, filter="data")
            except TypeError:
                tar.extractall(dest.parent)
    except Exception:
        return None
    return dest if marker.is_file() else None


def pipeline_src() -> Optional[Path]:
    """Importable producer ``src``: live tree, then git-archive of the pin."""
    checkout = pipeline_checkout()
    if checkout is None:
        cached = _pin_cache_src()
        if (cached / "pipeline" / "review_resolve.py").is_file():
            return cached
        return None
    live = checkout / "src"
    if (live / "pipeline" / "review_resolve.py").is_file():
        return live
    return _materialize_git_pin(checkout)


def _serialize_document_fallback(doc: Any) -> dict[str, Any]:
    """Catalog or manifest → JSON-safe lookup/tray payload (producer main)."""
    if doc is None:
        return {}
    if isinstance(doc, dict):
        stage = doc.get("stage")
        created = doc.get("created_at")
        updated = doc.get("updated_at")
        return {
            "doc_id": doc.get("doc_id"),
            "matter_id": doc.get("matter_id"),
            "original_filename": doc.get("original_filename"),
            "stage": getattr(stage, "value", stage),
            "doc_type": doc.get("doc_type"),
            "contract_subtype": doc.get("contract_subtype"),
            "doc_subclass": doc.get("doc_subclass"),
            "classification_confidence": doc.get("classification_confidence"),
            "extraction_confidence": doc.get("extraction_confidence"),
            "escalation_reason": doc.get("escalation_reason"),
            "trace_id": doc.get("trace_id"),
            "review_decision": doc.get("review_decision"),
            "extracted_data": doc.get("extracted_data"),
            "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
            "updated_at": updated.isoformat() if hasattr(updated, "isoformat") else updated,
        }
    stage = getattr(doc, "stage", None)
    if hasattr(stage, "value"):
        stage = stage.value
    updated = getattr(doc, "updated_at", None)
    created = getattr(doc, "created_at", None)
    return {
        "doc_id": getattr(doc, "doc_id", None),
        "matter_id": getattr(doc, "matter_id", None),
        "original_filename": getattr(doc, "original_filename", None),
        "stage": stage,
        "doc_type": getattr(doc, "doc_type", None),
        "contract_subtype": getattr(doc, "contract_subtype", None),
        "doc_subclass": getattr(doc, "doc_subclass", None),
        "classification_confidence": getattr(doc, "classification_confidence", None),
        "extraction_confidence": getattr(doc, "extraction_confidence", None),
        "escalation_reason": getattr(doc, "escalation_reason", None),
        "trace_id": getattr(doc, "trace_id", None),
        "review_decision": getattr(doc, "review_decision", None),
        "extracted_data": getattr(doc, "extracted_data", None),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
        "updated_at": updated.isoformat() if hasattr(updated, "isoformat") else updated,
    }


def _tray_actions_fallback(stage: Optional[str]) -> list[dict[str, str]]:
    stage = (stage or "").lower()
    actions = [
        {
            "disposition": "record",
            "decisions": "approved|rejected",
            "when": "Any stage — audit paper trail; file stays put",
        },
        {
            "disposition": "requeue",
            "decisions": "approved|rejected",
            "when": "Source file locatable — copy back to inbox for a fresh run",
        },
    ]
    if stage == "review":
        actions.insert(
            0,
            {
                "disposition": "resume",
                "decisions": "approved|rejected",
                "when": "Parked review — approve re-extracts; reject → failed bin",
            },
        )
        actions.append(
            {
                "disposition": "complete",
                "decisions": "approved",
                "when": "Parked review with human extracted_data — archive without LLM",
            },
        )
    return actions


def _origin_for(path: Path, *, via_src: bool) -> str:
    posix = path.as_posix()
    if f"the-mailroom-pin-{MAILROOM_GIT_SHA}" in posix:
        return "pin"
    if "llm-mailroom" in posix:
        return "checkout"
    return "checkout" if via_src else "installed"


def _import_contract() -> Optional[dict[str, Any]]:
    """Load ``pipeline.review_resolve`` without leaving sibling ``src`` on sys.path."""
    try:
        review = importlib.import_module("pipeline.review_resolve")
        manifest = importlib.import_module("schemas.manifest")
        path = Path(getattr(review, "__file__", "") or "")
        return {
            "origin": _origin_for(path, via_src=False),
            "review": review,
            "manifest": manifest,
            "path": str(path) if path else "",
        }
    except ImportError:
        pass
    src = pipeline_src()
    if src is None:
        return None
    inserted = str(src)
    already = inserted in sys.path
    if not already:
        sys.path.insert(0, inserted)
    try:
        # Drop a stale failed import so the checkout / pin can win.
        for name in (
            "pipeline.review_resolve",
            "pipeline",
            "schemas.manifest",
            "schemas",
        ):
            sys.modules.pop(name, None)
        review = importlib.import_module("pipeline.review_resolve")
        manifest = importlib.import_module("schemas.manifest")
        path = Path(getattr(review, "__file__", "") or "")
        return {
            "origin": _origin_for(path, via_src=True),
            "review": review,
            "manifest": manifest,
            "path": str(path) if path else "",
        }
    except ImportError:
        return None
    finally:
        if not already:
            try:
                sys.path.remove(inserted)
            except ValueError:
                pass


_LOADED = _import_contract()


def producer_available() -> bool:
    return _LOADED is not None


def installed_mailroom_version() -> Optional[str]:
    try:
        return importlib.metadata.version(MAILROOM_DIST_NAME)
    except importlib.metadata.PackageNotFoundError:
        return None


def producer_status() -> dict[str, Any]:
    """Machine-readable pin + import state (no secrets)."""
    origin = "fallback"
    path = ""
    if _LOADED is not None:
        origin = str(_LOADED.get("origin") or "installed")
        path = str(_LOADED.get("path") or "")
    return {
        "distribution": MAILROOM_DIST_NAME,
        "pin": MAILROOM_GIT_SHA,
        "version": MAILROOM_DIST_VERSION,
        "pep508": MAILROOM_PEP508,
        "imported": _LOADED is not None,
        "origin": origin,
        "installed_version": installed_mailroom_version(),
        "checkout": str(pipeline_checkout() or ""),
        "module": path,
    }


if _LOADED is not None:
    DISPOSITIONS: frozenset[str] = frozenset(_LOADED["review"].DISPOSITIONS)
    DECISIONS: frozenset[str] = frozenset(_LOADED["review"].DECISIONS)
    serialize_document = _LOADED["review"].serialize_document
    tray_actions_for = _LOADED["review"].tray_actions_for
    DocumentManifest = _LOADED["manifest"].DocumentManifest
    PipelineStage = _LOADED["manifest"].PipelineStage
else:
    DISPOSITIONS = _FALLBACK_DISPOSITIONS
    DECISIONS = _FALLBACK_DECISIONS
    serialize_document = _serialize_document_fallback
    tray_actions_for = _tray_actions_fallback
    DocumentManifest = None  # type: ignore[assignment]
    PipelineStage = None  # type: ignore[assignment]


def serialize_catalog_row(doc: Any) -> dict[str, Any]:
    """``serialize_document`` that also accepts a plain catalog dict."""
    if isinstance(doc, dict):
        if _LOADED is None:
            return _serialize_document_fallback(doc)
        from types import SimpleNamespace

        return serialize_document(SimpleNamespace(**doc))
    return serialize_document(doc)


def validate_operator_extraction(
    doc_type: str, extracted_data: dict[str, Any]
) -> dict[str, Any]:
    """Reject specialist-schema collisions before Complete (llm-mailroom #53).

    Prefer the live producer helper when the checkout or pin is new enough;
    fall back to the bundled field-map check so older imports still block
    foreign keys (e.g. correspondence ``sender`` on a contract).
    """
    review = (_LOADED or {}).get("review") if _LOADED else None
    live = getattr(review, "validate_operator_extraction", None)
    if callable(live):
        return live(doc_type, extracted_data)
    from mailroom_ui.pipeline_schema import (
        validate_operator_extraction as _bundled,
    )

    return _bundled(doc_type, extracted_data)
