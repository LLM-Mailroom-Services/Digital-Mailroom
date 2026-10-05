"""Operator write-path to llm-mailroom human review.

Document *display* stays Langfuse-only. These helpers proxy approve / reject /
record / requeue / complete to the producer API when ``MAILROOM_PIPELINE_URL``
and a token are set. Missing config is a clear error — never a fabricated
catalog row.

Producer contract (llm-mailroom ``origin/main``): prefer ``/v1`` aliases;
resolve body uses ``override_doc_type`` (not ``doc_type``); lookup returns
``{"document": serialize_document(...)}`` with ``original_filename``. Producer main now ships ``GET /documents/{id}/source`` and ``POST /upload``;
older forks may 404 the source route — the visualizer falls back to lookup.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from .pipeline_ops import _token, pipeline_base_url, producer_url
from .pipeline_schema import normalize_review_doc_type, normalize_review_subclass
from .producer import (
    DECISIONS,
    DISPOSITIONS,
    tray_actions_for,
    validate_operator_extraction,
)

log = logging.getLogger("mailroom.review_actions")

VALID_DISPOSITIONS = DISPOSITIONS


class ReviewActionError(Exception):
    """Producer call failed. ``status`` is the HTTP status to surface."""

    def __init__(self, message: str, status: int = 502, detail: Any = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.detail = detail


def pipeline_configured() -> bool:
    return bool(pipeline_base_url() and _token())


def _http_error(exc: urllib.error.HTTPError) -> ReviewActionError:
    raw = ""
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception as read_exc:  # body already consumed / socket closed
        log.debug("producer error body unreadable: %s", read_exc)
    detail: Any = raw[:400] if raw else (exc.reason or str(exc))
    try:
        parsed = json.loads(raw) if raw else {}
        if isinstance(parsed, dict):
            detail = parsed.get("detail") or parsed.get("error") or parsed
    except ValueError:
        pass  # non-JSON error body: keep the raw text as detail
    return ReviewActionError(str(detail)[:400], status=int(exc.code), detail=detail)


def _open(req: urllib.request.Request, timeout: float) -> tuple[bytes, Any]:
    """Send one producer request; every failure becomes ReviewActionError.

    HTTPError/URLError were the only mapped cases — a read timeout
    (``TimeoutError``) or a dropped connection escaped as a bare 500.
    """
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.headers
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise ReviewActionError("producer timed out", status=504) from exc
        raise ReviewActionError(f"producer unreachable: {exc.reason}", status=502) from exc
    except TimeoutError as exc:  # socket.timeout is an alias on 3.10+
        raise ReviewActionError("producer timed out", status=504) from exc
    except OSError as exc:  # connection reset mid-read, etc.
        raise ReviewActionError(f"producer connection failed: {exc}", status=502) from exc


def _json_payload(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        snippet = raw[:120].decode("utf-8", errors="replace")
        raise ReviewActionError(
            f"producer returned non-JSON body: {snippet!r}", status=502,
        ) from exc
    return payload if isinstance(payload, dict) else {"data": payload}


def disposition_filename(header: str) -> str:
    """Filename from a Content-Disposition header (RFC 6266 / 5987 aware)."""
    if not header:
        return ""
    import re

    star = re.search(r"filename\*\s*=\s*([^']*)'[^']*'([^;]+)", header, re.I)
    if star:
        try:
            name = urllib.parse.unquote(star.group(2).strip().strip('"'), encoding=star.group(1) or "utf-8")
            return os.path.basename(name.replace("\\", "/")).strip()
        except (LookupError, UnicodeDecodeError):
            pass
    from email.message import Message

    msg = Message()
    msg["content-disposition"] = header
    name = msg.get_filename() or ""
    return os.path.basename(name.replace("\\", "/")).strip()


def content_disposition(name: str, *, disposition: str = "attachment") -> str:
    """Header-safe Content-Disposition for an arbitrary (unicode) filename.

    Interpolating the raw name broke on quotes and raised
    UnicodeEncodeError (HTTP 500) for any non-latin-1 character.
    """
    base = os.path.basename((name or "").replace("\\", "/")).strip() or "download"
    ascii_name = "".join(
        ch if 32 <= ord(ch) < 127 and ch not in '"\\;' else "_" for ch in base
    )
    quoted = urllib.parse.quote(base, safe="")
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quoted}"


def _request_json(
    method: str,
    url: str,
    *,
    token: str = "",
    body: Optional[dict[str, Any]] = None,
    timeout: float = 8.0,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    raw, _headers = _open(req, timeout)
    return _json_payload(raw)


_MAX_UPLOAD_BYTES = 32 * 1024 * 1024


def _safe_upload_name(name: str) -> str:
    base = os.path.basename((name or "").replace("\\", "/").strip()) or "upload.bin"
    return base.replace('"', "").replace("\r", "").replace("\n", "")


def _request_multipart(
    url: str,
    *,
    token: str = "",
    fields: Optional[dict[str, str]] = None,
    files: Optional[list[tuple[str, str, str, bytes]]] = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST multipart/form-data (producer ``POST /v1/upload``)."""
    boundary = f"----MailroomBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in (fields or {}).items():
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    for field, filename, content_type, data in files or []:
        safe = _safe_upload_name(filename)
        ctype = (content_type or "application/octet-stream").split(";")[0].strip()
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        chunks.append(
            f'Content-Disposition: form-data; name="{field}"; filename="{safe}"\r\n'.encode("utf-8")
        )
        chunks.append(f"Content-Type: {ctype}\r\n\r\n".encode("utf-8"))
        chunks.append(data)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    body = b"".join(chunks)
    headers = {
        "Accept": "application/json",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    raw, _headers = _open(req, timeout)
    return _json_payload(raw)


def _request_bytes(
    method: str,
    url: str,
    *,
    token: str = "",
    timeout: float = 8.0,
) -> tuple[bytes, str, str]:
    """GET bytes from the producer. Returns (body, content_type, filename)."""
    headers = {"Accept": "*/*"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method=method)
    data, resp_headers = _open(req, timeout)
    content_type = resp_headers.get("Content-Type") or "application/octet-stream"
    filename = disposition_filename(resp_headers.get("Content-Disposition") or "")
    return data, content_type, filename


def _require_pipeline() -> tuple[str, str]:
    base = pipeline_base_url()
    token = _token()
    if not base:
        raise ReviewActionError(
            "MAILROOM_PIPELINE_URL is not set — review resolve needs the llm-mailroom API",
            status=503,
        )
    if not token:
        raise ReviewActionError(
            "MAILROOM_PIPELINE_TOKEN (or MAILROOM_API_TOKEN) is not set",
            status=503,
        )
    return base, token


def _normalize_producer_document(document: dict[str, Any]) -> dict[str, Any]:
    """Alias producer ``original_filename`` so older UI keys still resolve."""
    out = dict(document)
    filename = (
        out.get("original_filename")
        or out.get("file")
        or out.get("filename")
        or ""
    )
    if filename:
        out.setdefault("original_filename", filename)
        out.setdefault("file", filename)
        out.setdefault("filename", filename)
    return out


def _unwrap_document(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    document = data.get("document") if isinstance(data.get("document"), dict) else None
    if document is None:
        return None
    return _normalize_producer_document(document)


def lookup_document(
    *,
    trace_id: str = "",
    filename: str = "",
    doc_id: str = "",
    timeout: float = 8.0,
) -> dict[str, Any]:
    """GET /v1/lookup on the producer. Raises ReviewActionError on failure."""
    _require_pipeline()
    token = _token()
    params: dict[str, str] = {}
    if doc_id:
        params["doc_id"] = doc_id
    if trace_id:
        params["trace_id"] = trace_id
    if filename:
        params["filename"] = filename
    if not params:
        raise ReviewActionError("provide trace_id, filename, or doc_id", status=400)
    qs = urllib.parse.urlencode(params)
    data = _request_json("GET", producer_url(f"/lookup?{qs}"), token=token, timeout=timeout)
    document = _unwrap_document(data)
    if document is None:
        raise ReviewActionError("Document not found", status=404)
    return document


def fetch_audit(doc_id: str, *, timeout: float = 8.0) -> dict[str, Any]:
    _require_pipeline()
    token = _token()
    return _request_json(
        "GET",
        producer_url(f"/audit/{urllib.parse.quote(doc_id)}"),
        token=token,
        timeout=timeout,
    )


def _lookup_or_id(
    *,
    trace_id: str = "",
    filename: str = "",
    doc_id: str = "",
    timeout: float = 8.0,
) -> tuple[str, Optional[dict[str, Any]]]:
    """Resolve a producer doc_id, returning the catalog row when lookup hits."""
    resolved = (doc_id or "").strip()
    document: Optional[dict[str, Any]] = None
    try:
        document = lookup_document(
            trace_id=trace_id, filename=filename, doc_id=resolved, timeout=timeout,
        )
        resolved = str(document.get("doc_id") or resolved)
    except ReviewActionError as exc:
        if not resolved or exc.status not in (404,):
            raise
    if not resolved:
        raise ReviewActionError(
            "could not resolve a producer doc_id from this trace", status=404,
        )
    return resolved, document


def _source_from_catalog(document: dict[str, Any], resolved: str) -> dict[str, Any]:
    """Build a viewer payload from GET /lookup when /documents/{id}/source 404s.

    llm-mailroom main has no parked-file source route. The catalog row may still
    carry ``extracted_data`` / ``escalation_reason`` / ``original_filename``.
    """
    filename = (
        document.get("original_filename")
        or document.get("file")
        or document.get("filename")
        or resolved
    )
    chunks: list[str] = []
    text = document.get("extracted_text") or document.get("text")
    if isinstance(text, str) and text.strip():
        chunks.append(text.strip())
    extracted = document.get("extracted_data")
    if extracted not in (None, {}, []):
        dumped = json.dumps(extracted, indent=2, default=str)
        if chunks:
            chunks.append("--- extracted_data ---\n" + dumped)
        else:
            chunks.append(dumped)
    reason = document.get("escalation_reason")
    if isinstance(reason, str) and reason.strip():
        chunks.append("--- escalation ---\n" + reason.strip())
    body = "\n\n".join(chunks).strip() if chunks else None
    if not body:
        body = (
            "This producer has no GET /documents/{doc_id}/source. "
            f"Catalog lookup for {filename} returned no extracted_data or text."
        )
    has_content = bool(chunks)
    return {
        "configured": True,
        "status": "ok",
        "doc_id": document.get("doc_id") or resolved,
        "filename": filename,
        "content_type": "application/json; charset=utf-8" if extracted not in (None, {}, []) and not (
            isinstance(text, str) and text.strip()
        ) else "text/plain; charset=utf-8",
        "text": body,
        "truncated": False,
        "readable": has_content,
        "bytes": len(body.encode("utf-8")),
        "source": "lookup",
        "error": None if has_content else (
            "llm-mailroom main has no GET /documents/{doc_id}/source"
        ),
    }


def _lookup_miss_payload(filename: str = "") -> dict[str, Any]:
    """Producer catalog has no record for this trace — an honest per-item state.

    The REVIEW tray probes every parked run; a hard HTTP 404 for each one trips
    the UI's global fetch-error banner. A 200 payload with ``readable: false``
    lets each row show "no catalog record" inline. Never fabricates content.
    """
    return {
        "configured": True,
        "status": "missing",
        "doc_id": None,
        "filename": filename or None,
        "content_type": "text/plain; charset=utf-8",
        "text": None,
        "truncated": False,
        "readable": False,
        "bytes": 0,
        "source": "lookup-miss",
        "error": (
            "llm-mailroom has no catalog record for this document (lookup 404) "
            "— parked text is unavailable from the producer."
        ),
    }


def fetch_source(
    *,
    trace_id: str = "",
    filename: str = "",
    doc_id: str = "",
    timeout: float = 8.0,
) -> dict[str, Any]:
    """Parked-file JSON. Tries producer source, then catalog lookup fallback.

    A producer-catalog miss on a trace/filename probe (no explicit doc_id)
    returns the 200 lookup-miss payload instead of raising 404 — the tray
    renders per-item state rather than a global error. Explicit doc_id misses
    still raise so downloads stay honest 404s.
    """
    if not pipeline_configured():
        return {
            "configured": False,
            "text": None,
            "error": (
                "Set MAILROOM_PIPELINE_URL and MAILROOM_PIPELINE_TOKEN to "
                "view parked document text from llm-mailroom."
            ),
        }
    try:
        resolved, document = _lookup_or_id(
            trace_id=trace_id, filename=filename, doc_id=doc_id, timeout=timeout,
        )
    except ReviewActionError as exc:
        if exc.status == 404 and not (doc_id or "").strip():
            return _lookup_miss_payload(filename)
        raise
    token = _token()
    try:
        data = _request_json(
            "GET",
            producer_url(f"/documents/{urllib.parse.quote(resolved)}/source"),
            token=token,
            timeout=timeout,
        )
        data["configured"] = True
        data["error"] = None
        data.setdefault("source", "producer")
        # The producer's source payload doesn't carry `readable`; the UIs gate
        # on it, so real text rendered as "(empty document text)".
        if "readable" not in data:
            text = data.get("text")
            data["readable"] = isinstance(text, str) and bool(text.strip())
        return data
    except ReviewActionError as exc:
        if exc.status != 404:
            raise
        if document is None:
            try:
                document = lookup_document(doc_id=resolved, timeout=timeout)
            except ReviewActionError:
                document = {"doc_id": resolved}
        return _source_from_catalog(document, resolved)


def fetch_source_download(
    *,
    trace_id: str = "",
    filename: str = "",
    doc_id: str = "",
    timeout: float = 30.0,
) -> tuple[bytes, str, str]:
    """GET /documents/{doc_id}/source?download=1 — original bytes.

    llm-mailroom main does not expose this route. A 404 is returned honestly
    rather than synthesizing a file from catalog JSON.
    """
    resolved, _document = _lookup_or_id(
        trace_id=trace_id, filename=filename, doc_id=doc_id, timeout=min(timeout, 8.0),
    )
    token = _token()
    try:
        data, content_type, name = _request_bytes(
            "GET",
            producer_url(f"/documents/{urllib.parse.quote(resolved)}/source?download=1"),
            token=token,
            timeout=timeout,
        )
    except ReviewActionError as exc:
        if exc.status == 404:
            raise ReviewActionError(
                "Producer has no GET /documents/{doc_id}/source — cannot download "
                "the original file. Use the text pane (catalog lookup fallback) "
                "or fetch the file from the review bin on the producer host.",
                status=404,
                detail=exc.detail,
            ) from exc
        raise
    return data, content_type, name or filename or resolved


def _class_override_body(
    doc_type: str = "",
    doc_subclass: str = "",
    override_doc_type: str = "",
) -> dict[str, str]:
    """Map visualizer ``doc_type`` onto producer ``override_doc_type``."""
    extra: dict[str, str] = {}
    try:
        kind = normalize_review_doc_type(override_doc_type or doc_type)
    except ValueError as exc:
        raise ReviewActionError(str(exc), status=400) from exc
    if kind:
        extra["override_doc_type"] = kind
    try:
        subclass = normalize_review_subclass(kind or doc_type or None, doc_subclass)
    except ValueError:
        # Producer main does not catalog-gate subclass; a parked token like
        # insurance "fnol" must still resolve. Canonicalize when we can.
        subclass = (doc_subclass or "").strip() or None
    if subclass:
        extra["doc_subclass"] = subclass
        if kind == "contract" or (not kind and (doc_type or "") == "contract"):
            extra["contract_subtype"] = subclass
    return extra


def _coerce_extracted_data(extracted_data: Any) -> Optional[dict[str, Any]]:
    if extracted_data is None or extracted_data == "":
        return None
    if isinstance(extracted_data, str):
        try:
            extracted_data = json.loads(extracted_data)
        except json.JSONDecodeError as exc:
            raise ReviewActionError("extracted_data must be a JSON object", status=400) from exc
    if not isinstance(extracted_data, dict):
        raise ReviewActionError("extracted_data must be a JSON object", status=400)
    return extracted_data


def review_context(
    *,
    trace_id: str = "",
    filename: str = "",
    doc_id: str = "",
    timeout: float = 8.0,
) -> dict[str, Any]:
    """Probe producer + optional catalog/audit for the REVIEW desk.

    Unconfigured returns HTTP-200-shaped payload (``configured: false``) so
    the UI can show setup copy instead of a hard error.
    """
    if not pipeline_configured():
        return {
            "configured": False,
            "document": None,
            "audit": None,
            "tray_actions": None,
            "error": (
                "Set MAILROOM_PIPELINE_URL and MAILROOM_PIPELINE_TOKEN to "
                "approve, reject, record, or requeue against llm-mailroom."
            ),
        }
    out: dict[str, Any] = {
        "configured": True,
        "document": None,
        "audit": None,
        "tray_actions": None,
        "error": None,
    }
    if not (trace_id or filename or doc_id):
        return out
    try:
        document = lookup_document(
            trace_id=trace_id, filename=filename, doc_id=doc_id, timeout=timeout,
        )
        out["document"] = document
        out["tray_actions"] = tray_actions_for(document.get("stage"))
        resolved = str(document.get("doc_id") or doc_id or "")
        if resolved:
            try:
                out["audit"] = fetch_audit(resolved, timeout=timeout)
            except ReviewActionError as exc:
                log.info("review audit unavailable: %s", exc.message)
    except ReviewActionError as exc:
        if exc.status == 404:
            out["error"] = "Document not found in the producer catalog"
        else:
            out["error"] = exc.message
    return out


def resolve_review(
    *,
    decision: str,
    disposition: str = "resume",
    notes: str = "",
    trace_id: str = "",
    filename: str = "",
    doc_id: str = "",
    doc_type: str = "",
    doc_subclass: str = "",
    override_doc_type: str = "",
    extracted_data: Any = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST /v1/review/{doc_id}/resolve on the producer (JSON body)."""
    decision = (decision or "").strip()
    disposition = (disposition or "resume").strip() or "resume"
    if decision not in DECISIONS:
        raise ReviewActionError("decision must be 'approved' or 'rejected'", status=400)
    if disposition not in VALID_DISPOSITIONS:
        raise ReviewActionError(
            "disposition must be 'resume', 'record', 'requeue', or 'complete'",
            status=400,
        )
    extra = _class_override_body(doc_type, doc_subclass, override_doc_type)
    extracted = _coerce_extracted_data(extracted_data)
    _require_pipeline()
    token = _token()
    resolved, document = _lookup_or_id(
        trace_id=trace_id, filename=filename, doc_id=doc_id, timeout=min(timeout, 8.0),
    )
    if disposition == "complete" and extracted:
        kind = extra.get("override_doc_type") or (document or {}).get("doc_type")
        if kind:
            try:
                extracted = validate_operator_extraction(str(kind), extracted)
            except ValueError as exc:
                raise ReviewActionError(str(exc), status=400) from exc
    body: dict[str, Any] = {
        "decision": decision,
        "notes": notes or "",
        "disposition": disposition,
        **extra,
    }
    if extracted is not None:
        body["extracted_data"] = extracted
    return _request_json(
        "POST",
        producer_url(f"/review/{urllib.parse.quote(resolved)}/resolve"),
        token=token,
        body=body,
        timeout=timeout,
    )


INBOX_SETUP = (
    "Set MAILROOM_PIPELINE_URL and MAILROOM_PIPELINE_TOKEN to "
    "queue documents into llm-mailroom."
)
INBOX_FILE_REQUIRED = (
    "file is required — POST multipart field `file` (or JSON content_base64) "
    "to /api/inbox/enqueue"
)


def enqueue_inbox(
    *,
    filename: str = "",
    matter_id: str = "",
    content_type: str = "",
    file_bytes: Optional[bytes] = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Proxy a file to producer ``POST /v1/upload``.

    Unconfigured → HTTP 503 with setup copy (no fabricated queue row).
    Missing bytes → HTTP 400. Producer errors pass through.
    """
    if not pipeline_configured():
        raise ReviewActionError(INBOX_SETUP, status=503, detail={"configured": False})
    if not file_bytes:
        raise ReviewActionError(
            INBOX_FILE_REQUIRED,
            status=400,
            detail={"configured": True, "filename": filename or None},
        )
    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        raise ReviewActionError(
            f"file exceeds {_MAX_UPLOAD_BYTES} byte visualizer limit",
            status=413,
        )
    _require_pipeline()
    token = _token()
    fields: dict[str, str] = {}
    if (matter_id or "").strip():
        fields["matter_id"] = matter_id.strip()
    data = _request_multipart(
        producer_url("/upload"),
        token=token,
        fields=fields,
        files=[(
            "file",
            filename or "upload.bin",
            content_type or "application/octet-stream",
            file_bytes,
        )],
        timeout=timeout,
    )
    data.setdefault("configured", True)
    return data
