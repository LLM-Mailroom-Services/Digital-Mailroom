"""Pack a run's local span mirror for upload, verify the copy, then prune.

Local-first tracing: ``otel.configure_tracing`` mirrors every span of a run to
``data/traces/<run_id>.spans.jsonl.gz``. ``pack`` turns that mirror into one
zip (``spans.parquet`` zstd, or ``spans.csv.gz`` without pyarrow, plus a
``manifest.json``), named ``<runner>_<experiment>_<run_id>.zip`` under
``data/runtime/exports/<YYYY-MM-DD>/``. With a destination (a synced Drive
folder such as ``.../LLM-MAILROOM 📮/LOGS``) the zip is copied to
``<dest>/<YYYY-MM-DD>/`` and re-hashed there; ``prune`` deletes the local
mirror and the local zip only after that copy verified.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mailroom_sandbox.job.otel import local_trace_path
from mailroom_sandbox.paths import runtime_dir

UPLOAD_DIR_ENV = "SANDBOX_TRACE_UPLOAD_DIR"
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def default_runner() -> str:
    return "claude" if os.environ.get("CLAUDECODE") else "axios"


def _slug(value: str) -> str:
    return _SAFE.sub("-", value).strip("-") or "run"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_spans(path: Path) -> list[dict[str, Any]]:
    """All span records from a (multi-member) gzip JSONL mirror."""
    spans: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                spans.append(json.loads(line))
    return spans


def _iso(ns: Any) -> str | None:
    if not isinstance(ns, int):
        return None
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat(timespec="microseconds")


def _scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, default=str)


def flatten(record: dict[str, Any], run_id: str) -> dict[str, Any]:
    """One span as a tidy row; attributes become ``attr.<key>`` columns."""
    start, end = record.get("start_time_unix_nano"), record.get("end_time_unix_nano")
    resource = record.get("resource") or {}
    row: dict[str, Any] = {
        "run_id": resource.get("sandbox.run_id") or run_id,
        "trace_id": record.get("trace_id"),
        "span_id": record.get("span_id"),
        "parent_span_id": record.get("parent_span_id"),
        "name": record.get("name"),
        "kind": record.get("kind"),
        "start_time_utc": _iso(start),
        "end_time_utc": _iso(end),
        "duration_ms": round((end - start) / 1e6, 3) if isinstance(start, int) and isinstance(end, int) else None,
        "status_code": record.get("status_code"),
        "status_description": record.get("status_description"),
        "service_name": resource.get("service.name"),
        "events_json": json.dumps(record["events"], default=str) if record.get("events") else None,
    }
    for key, value in sorted((record.get("attributes") or {}).items()):
        row[f"attr.{key}"] = _scalar(value)
    return row


def _write_table(rows: list[dict[str, Any]]) -> tuple[str, bytes]:
    """Serialize rows as zstd Parquet when pyarrow is present, else gzip CSV."""
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, columns)
        writer.writeheader()
        writer.writerows(rows)
        return "spans.csv.gz", gzip.compress(buf.getvalue().encode("utf-8"), mtime=0)
    arrays = {}
    for col in columns:
        values = [row.get(col) for row in rows]
        try:
            arrays[col] = pa.array(values)
        except (pa.ArrowInvalid, pa.ArrowTypeError, TypeError):
            # Mixed types across spans (e.g. an attribute that is sometimes int, sometimes str).
            arrays[col] = pa.array([None if v is None else str(v) for v in values], type=pa.string())
    table = pa.table(arrays)
    sink = io.BytesIO()
    pq.write_table(table, sink, compression="zstd")
    return "spans.parquet", sink.getvalue()


def pack(
    run_id: str,
    *,
    experiment: str | None = None,
    runner: str | None = None,
    dest: Path | None = None,
    date: str | None = None,
    spans_path: Path | None = None,
) -> dict[str, Any]:
    """Zip the run's span mirror; copy and verify it at ``dest`` when given."""
    source = spans_path or local_trace_path(run_id)
    if source is None or not Path(source).is_file():
        raise FileNotFoundError(f"no local span mirror for {run_id!r} (expected {source})")
    source = Path(source)
    records = read_spans(source)
    rows = [flatten(r, run_id) for r in records]
    table_name, table_bytes = _write_table(rows)

    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    runner = _slug(runner or default_runner())
    experiment = _slug(experiment or run_id.split("-", 1)[0])
    name = f"{runner}_{experiment}_{_slug(run_id)}.zip"
    starts = [r["start_time_utc"] for r in rows if r.get("start_time_utc")]
    manifest = {
        "schema": "sandbox.trace-pack/v1",
        "run_id": run_id,
        "runner": runner,
        "experiment": experiment,
        "span_count": len(rows),
        "trace_count": len({r.get("trace_id") for r in rows}),
        "first_span_utc": min(starts) if starts else None,
        "last_span_utc": max(starts) if starts else None,
        "table": table_name,
        "source": str(source),
        "source_sha256": sha256_file(source),
        "packed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    out_dir = runtime_dir() / "exports" / date
    out_dir.mkdir(parents=True, exist_ok=True)
    local_zip = out_dir / name
    with zipfile.ZipFile(local_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        # Parquet/gzip payloads are already compressed; store them as-is.
        zf.writestr(table_name, table_bytes, compress_type=zipfile.ZIP_STORED)
    result: dict[str, Any] = {
        **manifest,
        "zip": str(local_zip),
        "zip_bytes": local_zip.stat().st_size,
        "zip_sha256": sha256_file(local_zip),
        "uploaded": None,
        "verified": False,
    }
    if dest is not None:
        result.update(_copy_and_verify(local_zip, Path(dest) / date, result["zip_sha256"]))
    return result


def _copy_and_verify(local_zip: Path, target_dir: Path, expected_sha: str) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / local_zip.name
    shutil.copyfile(local_zip, target)
    with open(target, "rb") as fh:
        os.fsync(fh.fileno())
    copy_sha = sha256_file(target)
    with zipfile.ZipFile(target) as zf:
        bad_member = zf.testzip()
    return {
        "uploaded": str(target),
        "uploaded_sha256": copy_sha,
        "verified": copy_sha == expected_sha and bad_member is None,
    }


def prune(result: dict[str, Any]) -> list[str]:
    """Delete the local mirror and local zip, only after a verified upload."""
    if not result.get("verified") or not result.get("uploaded"):
        raise RuntimeError("refusing to prune: no verified uploaded copy")
    if not Path(result["uploaded"]).is_file() or sha256_file(Path(result["uploaded"])) != result["zip_sha256"]:
        raise RuntimeError(f"refusing to prune: uploaded copy changed or vanished ({result['uploaded']})")
    removed: list[str] = []
    uploaded = Path(result["uploaded"]).resolve()
    for key in ("source", "zip"):
        path = Path(result[key])
        if path.resolve() == uploaded:
            continue
        if path.is_file():
            path.unlink()
            removed.append(str(path))
    return removed
