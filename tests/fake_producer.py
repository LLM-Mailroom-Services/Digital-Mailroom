"""In-process llm-mailroom producer stub for REVIEW-tray demos and tests.

Mirrors producer ``origin/main`` (prefer ``/v1``): lookup, review resolve
(``override_doc_type``, dispositions resume|record|requeue|complete), audit,
health, inbox queue, ``POST /upload``. There is **no** ``GET /documents/{id}/source``
on this stub (older producer forks) so the visualizer source pane uses catalog
lookup fallback.

Display data still comes from Langfuse (FakeClient in the demo). This stub is
only the operator write-path the visualizer proxies to.
"""

from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from mailroom_ui.producer import DECISIONS, DISPOSITIONS, serialize_catalog_row

DEMO_TOKEN = "demo-review-token"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def demo_catalog() -> dict[str, dict[str, Any]]:
    """Catalog rows keyed by doc_id — aligned with ``scripts/demo_review_tray.py``."""
    return {
        "doc-merger-42": {
            "doc_id": "doc-merger-42",
            "matter_id": "review-tray-demo",
            "original_filename": "maud_merger_agreement_all_stock_42.pdf",
            "trace_id": "tray-review",
            "stage": "review",
            "doc_type": "merger_agreement",
            "doc_subclass": None,
            "contract_subtype": None,
            "classification_confidence": 0.93,
            "extraction_confidence": 0.61,
            "escalation_reason": "low extraction confidence (0.61) on indemnification clause",
            "review_decision": None,
            "extracted_data": {
                "parties": ["Helios Holdings Inc.", "Northwind Target LLC"],
                "consideration": "all-stock",
                "indemnification": None,
            },
            "created_at": _now(),
            "updated_at": _now(),
        },
        "doc-claim-fnol": {
            "doc_id": "doc-claim-fnol",
            "matter_id": "review-tray-demo",
            "original_filename": "insurance_claim_fnol_package_01.pdf",
            "trace_id": "tray-complete",
            "stage": "review",
            "doc_type": "insurance_claim",
            "doc_subclass": "fnol",
            "contract_subtype": None,
            "classification_confidence": 0.91,
            "extraction_confidence": 0.55,
            "escalation_reason": "partial FNOL extraction — operator can Complete with extracted_data",
            "review_decision": None,
            "extracted_data": {
                "claim_number": "CL-4419",
                "claimant": "Jordan Hale",
                "loss_date": "2026-03-12",
                "status": "open",
            },
            "created_at": _now(),
            "updated_at": _now(),
        },
        "doc-claim-miss": {
            "doc_id": "doc-claim-miss",
            "matter_id": "review-tray-demo",
            "original_filename": "insurance_claim_cms_synpuf_miss.pdf",
            "trace_id": "tray-reconsider",
            "stage": "archived",
            "doc_type": "insurance_claim",
            "doc_subclass": None,
            "contract_subtype": None,
            "classification_confidence": 0.99,
            "extraction_confidence": 0.97,
            "escalation_reason": "reconsider: judge verdict MISS",
            "review_decision": None,
            "extracted_data": {"claim_number": "CMS-0091"},
            "created_at": _now(),
            "updated_at": _now(),
        },
    }


class FakeProducerStore:
    """Mutable catalog + hash-chained audit + inbox queue."""

    def __init__(self, documents: Optional[dict[str, dict[str, Any]]] = None):
        self.documents = deepcopy(documents if documents is not None else demo_catalog())
        self.audit: dict[str, list[dict[str, Any]]] = {doc_id: [] for doc_id in self.documents}
        self.queued: list[dict[str, str]] = []
        self.inbox_pending = 1

    def serialize(self, doc: dict[str, Any]) -> dict[str, Any]:
        return serialize_catalog_row(doc)

    def find(self, *, doc_id: str = "", trace_id: str = "", filename: str = "") -> Optional[dict[str, Any]]:
        if doc_id and doc_id in self.documents:
            return self.documents[doc_id]
        if trace_id:
            for doc in self.documents.values():
                if doc.get("trace_id") == trace_id:
                    return doc
        if filename:
            for doc in self.documents.values():
                if doc.get("original_filename") == filename:
                    return doc
        return None

    def append_audit(self, doc_id: str, event: str, notes: str, detail: dict[str, Any]) -> None:
        chain = self.audit.setdefault(doc_id, [])
        prev = chain[-1]["hash"] if chain else "0" * 64
        payload = json.dumps({"event": event, "notes": notes, "detail": detail, "prev": prev},
                             sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        chain.append({
            "event": event,
            "notes": notes,
            "detail": detail,
            "prev_hash": prev,
            "hash": digest,
            "at": _now(),
        })

    def apply_override(self, doc: dict[str, Any], *, override_doc_type: Any,
                       doc_subclass: Any, contract_subtype: Any) -> None:
        from mailroom_ui.pipeline_schema import normalize_review_doc_type, normalize_review_subclass

        if override_doc_type:
            kind = normalize_review_doc_type(str(override_doc_type))
            if kind:
                doc["doc_type"] = kind
        if doc_subclass is not None and str(doc_subclass).strip():
            sub = str(doc_subclass).strip()
            try:
                sub = normalize_review_subclass(doc.get("doc_type"), sub) or sub
            except ValueError:
                pass
            doc["doc_subclass"] = sub
            if doc.get("doc_type") == "contract":
                doc["contract_subtype"] = sub
        elif contract_subtype is not None and str(contract_subtype).strip():
            sub = str(contract_subtype).strip()
            doc["contract_subtype"] = sub
            if not doc.get("doc_subclass"):
                doc["doc_subclass"] = sub
        doc["updated_at"] = _now()


def create_fake_producer(store: Optional[FakeProducerStore] = None, *, token: str = DEMO_TOKEN) -> FastAPI:
    store = store or FakeProducerStore()
    app = FastAPI(title="fake-llm-mailroom")

    def _require(request: Request) -> None:
        header = request.headers.get("authorization") or ""
        if header != f"Bearer {token}":
            raise HTTPException(401, "missing or invalid bearer token")

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "mailroom",
            "checks": {
                "watcher": "live",
                "watcher_heartbeat_seconds_ago": 0.2,
                "inbox_pending": store.inbox_pending,
                "ingestion_paused": False,
            },
        }

    @app.post("/upload")
    async def upload(request: Request):
        _require(request)
        form = await request.form()
        upload_file = form.get("file")
        if upload_file is None:
            raise HTTPException(400, "file is required")
        filename = getattr(upload_file, "filename", None) or "upload.bin"
        matter = str(form.get("matter_id") or "DEFAULT").strip() or "DEFAULT"
        upload_id = uuid.uuid4().hex[:12]
        store.queued.append({
            "file": filename,
            "matter_id": matter,
            "uploaded_at": _now(),
            "upload_id": upload_id,
        })
        store.inbox_pending = len(store.queued)
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "file": filename,
                "upload_id": upload_id,
                "matter_id": matter,
                "message": "File queued for processing — watcher will pick it up.",
            },
        )

    @app.get("/queue")
    async def queue(request: Request):
        _require(request)
        return {
            "queued": store.queued or [{
                "file": "inbox_scan_correspondence_07.pdf",
                "matter_id": "review-tray-demo",
                "uploaded_at": _now(),
            }],
            "processing": [],
        }

    @app.get("/lookup")
    async def lookup(
        request: Request,
        doc_id: str | None = Query(default=None),
        trace_id: str | None = Query(default=None),
        filename: str | None = Query(default=None),
    ):
        _require(request)
        if not (doc_id or trace_id or filename):
            raise HTTPException(400, "provide doc_id, trace_id, or filename")
        rec = store.find(doc_id=doc_id or "", trace_id=trace_id or "", filename=filename or "")
        if rec is None:
            raise HTTPException(404, "Document not found")
        return {"document": store.serialize(rec)}

    @app.get("/review/queue")
    async def review_queue(request: Request):
        _require(request)
        docs = [store.serialize(d) for d in store.documents.values() if d.get("stage") == "review"]
        return {
            "review_queue": len(docs),
            "documents": docs,
            "dispositions": sorted(DISPOSITIONS),
            "timestamp": _now(),
        }

    @app.post("/review/{doc_id}/resolve")
    async def resolve(doc_id: str, request: Request):
        _require(request)
        ctype = (request.headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            body = await request.json()
            if not isinstance(body, dict):
                raise HTTPException(400, "JSON body must be an object")
        else:
            form = await request.form()
            body = {k: form.get(k) for k in form.keys()}
            raw = body.get("extracted_data")
            if raw:
                body["extracted_data"] = json.loads(str(raw))

        decision = str(body.get("decision") or "").strip()
        notes = str(body.get("notes") or "")
        disposition = str(body.get("disposition") or "resume").strip() or "resume"
        if decision not in DECISIONS:
            raise HTTPException(400, "decision must be 'approved' or 'rejected'")
        if disposition not in DISPOSITIONS:
            raise HTTPException(400, "disposition must be 'resume', 'record', 'requeue', or 'complete'")
        rec = store.documents.get(doc_id)
        if rec is None:
            raise HTTPException(404, f"Manifest not found for doc_id: {doc_id}")
        try:
            store.apply_override(
                rec,
                override_doc_type=body.get("override_doc_type"),
                doc_subclass=body.get("doc_subclass"),
                contract_subtype=body.get("contract_subtype"),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

        if disposition == "record":
            rec["review_decision"] = decision
            if notes:
                prior = rec.get("escalation_reason") or ""
                rec["escalation_reason"] = f"{prior}; [review:{decision}] {notes}".strip("; ")
            store.append_audit(doc_id, "review_recorded", notes,
                               {"decision": decision, "disposition": "record", "stage": rec.get("stage")})
            return {"status": "ok", "doc_id": doc_id, "decision": decision,
                    "disposition": "record", "notes": notes}

        if disposition == "requeue":
            name = rec.get("original_filename") or f"{doc_id}.bin"
            dest = f"{name.rsplit('.', 1)[0]}-requeue.{name.rsplit('.', 1)[-1]}" if "." in name else f"{name}-requeue"
            store.queued.append({"file": dest, "matter_id": rec.get("matter_id") or "DEFAULT",
                                 "uploaded_at": _now()})
            store.inbox_pending = len(store.queued)
            store.append_audit(doc_id, "review_requeued", notes,
                               {"decision": decision, "inbox_file": dest})
            return {"status": "ok", "doc_id": doc_id, "decision": decision,
                    "disposition": "requeue", "notes": notes, "inbox_file": dest}

        if rec.get("stage") != "review":
            raise HTTPException(
                400,
                f"Document is not in review (current stage: {rec.get('stage')}); "
                "use disposition=record or disposition=requeue",
            )

        if disposition == "complete":
            if decision != "approved":
                raise HTTPException(400, "disposition=complete requires decision=approved")
            extracted = body.get("extracted_data")
            if not isinstance(extracted, dict) or not extracted:
                raise HTTPException(400, "disposition=complete requires extracted_data object")
            kind = rec.get("doc_type")
            if kind:
                try:
                    from mailroom_ui.pipeline_schema import validate_operator_extraction

                    extracted = validate_operator_extraction(str(kind), extracted)
                except ValueError as exc:
                    raise HTTPException(400, str(exc)) from exc
            rec["extracted_data"] = extracted
            rec["stage"] = "archived"
            rec["review_decision"] = "approved"
            store.append_audit(doc_id, "review_completed", notes,
                               {"disposition": "complete", "stage": "archived"})
            return {
                "status": "ok", "doc_id": doc_id, "decision": decision,
                "disposition": "complete", "notes": notes,
                "complete": {"stage": "archived"},
            }

        if decision == "rejected":
            rec["review_decision"] = "rejected"
            rec["stage"] = "failed"
            store.append_audit(doc_id, "review_rejected", notes, {"disposition": "resume"})
            return {"status": "ok", "doc_id": doc_id, "decision": decision,
                    "disposition": "resume", "notes": notes}

        rec["review_decision"] = "approved"
        rec["stage"] = "archived"
        store.append_audit(doc_id, "review_approved", notes,
                           {"disposition": "resume", "resumed_stage": "extract"})
        return {
            "status": "ok", "doc_id": doc_id, "decision": decision,
            "disposition": "resume", "notes": notes,
            "resume": {"stage": "extract", "doc_type": rec.get("doc_type")},
        }

    @app.get("/audit/{doc_id}")
    async def audit(doc_id: str, request: Request):
        _require(request)
        if doc_id not in store.documents:
            raise HTTPException(404, "Document not found")
        entries = store.audit.get(doc_id) or []
        return {"doc_id": doc_id, "entries": entries, "valid": True, "count": len(entries)}

    def _mount_v1() -> None:
        from fastapi.routing import APIRoute

        wanted = {
            "/health", "/upload", "/queue", "/lookup", "/review/queue",
            "/review/{doc_id}/resolve", "/audit/{doc_id}",
        }
        for route in list(app.router.routes):
            if not isinstance(route, APIRoute) or route.path not in wanted:
                continue
            methods = sorted(m for m in route.methods if m not in {"HEAD"})
            app.add_api_route(
                "/v1" + route.path,
                route.endpoint,
                methods=methods,
                dependencies=route.dependencies,
                name=f"v1_{route.name}",
                tags=["v1"],
            )

    _mount_v1()
    app.state.store = store
    app.state.token = token
    return app


def pick_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def serve_in_thread(app: FastAPI, *, host: str = "127.0.0.1", port: int = 0):
    """Run a uvicorn server in a daemon thread. Returns (server, port)."""
    import uvicorn

    if port <= 0:
        port = pick_port(host)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True, name="fake-producer")
    thread.start()
    deadline = time.time() + 8.0
    while time.time() < deadline:
        if getattr(server, "started", False):
            return server, port, thread
        time.sleep(0.05)
    raise RuntimeError(f"fake producer failed to start on {host}:{port}")


def stop_server(server) -> None:
    server.should_exit = True
