#!/usr/bin/env python3
"""Score Langfuse ``document-pipeline`` traces against HF docclass ground truth.

Mirrors the entity-extraction eval runners (manifest + deterministic scorers
+ JSON/markdown report) but reads **Langfuse** as the sole run log — the same
contract The-Mailroom displays. Classification is scored two ways:

- **exact** — predicted ``doc_type`` == HF ``expected``
- **aligned** — exact match after extract-alias collapse (v0.6.0:
  ``merger_agreement`` is a live MAUD class, not aligned with ``contract``)

Usage:
    python scripts/eval_pipeline.py --session pilot-hf-...
    python scripts/eval_pipeline.py --since 86400 --environment pilot
    python scripts/eval_pipeline.py --check   # no network: print scorer contract
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from mailroom_ui.hf_corpus import (  # noqa: E402
    corpus_id,
    corpus_revision,
    fetch_rows,
    gt_config,
)
from mailroom_ui.intake_normalize import deterministic_normalize, looks_messy  # noqa: E402
from mailroom_ui.pipeline_eval import (  # noqa: E402
    aligned as _aligned,
    classify_failure,
    predicted_subclass_token,
    score_rows,
    subclass_ok,
)

DATASET_ID = corpus_id()


def _basic_auth() -> str:
    import base64

    pk = os.environ.get("LANGFUSE_PUBLIC_KEY") or ""
    sk = os.environ.get("LANGFUSE_SECRET_KEY") or ""
    if not pk or not sk:
        raise SystemExit("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY missing (.env)")
    return base64.b64encode(f"{pk}:{sk}".encode()).decode()


def _lf_get(path: str) -> dict:
    host = (os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
            or "https://us.cloud.langfuse.com").rstrip("/")
    req = urllib.request.Request(
        host + path,
        headers={"Authorization": f"Basic {_basic_auth()}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode())


def fetch_traces(*, session: str | None, since: int, environment: str, limit: int) -> list[dict]:
    traces: list[dict] = []
    page = 1
    while len(traces) < limit:
        q = [f"limit={min(50, limit - len(traces))}", "name=document-pipeline", f"page={page}"]
        if session:
            q.append(f"sessionId={urllib.parse.quote(session)}")
        if environment:
            # v4 filter: some deployments ignore this; we also filter client-side
            q.append(f"environment={urllib.parse.quote(environment)}")
        data = _lf_get("/api/public/traces?" + "&".join(q))
        batch = data.get("data") or []
        if not batch:
            break
        traces.extend(batch)
        meta = data.get("meta") or {}
        if page >= int(meta.get("totalPages") or 1):
            break
        page += 1
        time.sleep(0.2)
    cutoff = None
    if since:
        cutoff = datetime.now(timezone.utc).timestamp() - since

    def _ts(t):
        raw = t.get("timestamp") or t.get("createdAt") or ""
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    out = []
    for t in traces:
        if cutoff and _ts(t) < cutoff:
            continue
        env = t.get("environment") or (t.get("metadata") or {}).get("environment")
        if environment and env and env != environment:
            continue
        if session:
            sid = t.get("sessionId") or t.get("session_id")
            if sid != session:
                continue
        out.append(t)
        if len(out) >= limit:
            break
    return out


def _pick(d: dict, *keys):
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return None


def _as_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _score_map(scores: list[dict]) -> dict:
    """Latest value per score name (Langfuse returns newest-first)."""
    out = {}
    for score in scores or []:
        if not isinstance(score, dict):
            continue
        name = score.get("name")
        if name and name not in out:
            out[name] = score.get("value")
    return out


def _ground_truth_blob(*sources) -> dict:
    for src in sources:
        if isinstance(src, dict) and isinstance(src.get("ground_truth"), dict):
            return src["ground_truth"]
    return {}


def _expected_class(gt: dict, *fallbacks) -> str | None:
    for blob in (gt, *fallbacks):
        if not isinstance(blob, dict):
            continue
        for key in ("expected_hf_class", "expected_doc_class", "expected"):
            val = blob.get(key)
            if val:
                return val
    return None


def _expected_subclass(gt: dict, *fallbacks) -> str | None:
    for blob in (gt, *fallbacks):
        if not isinstance(blob, dict):
            continue
        val = blob.get("expected_subclass")
        if val:
            return val
    return None


def _predicted_subclass_from(out: dict, *payloads) -> str | None:
    for blob in (out, _as_dict(out.get("sorter")) if isinstance(out, dict) else {}, *payloads):
        if not isinstance(blob, dict):
            continue
        token = blob.get("doc_subclass") or blob.get("contract_subtype")
        if token:
            return token
    return None


def _stamp_subclass(row: dict) -> None:
    predicted = predicted_subclass_token(row)
    if predicted and not row.get("predicted_subclass"):
        row["predicted_subclass"] = predicted
    expected = row.get("expected_subclass")
    if expected:
        row["subclass_ok"] = subclass_ok(expected, predicted_subclass_token(row))


def traces_to_rows(traces: list[dict]) -> list[dict]:
    rows = []
    for t in traces:
        inp = t.get("input") if isinstance(t.get("input"), dict) else {}
        out = t.get("output") if isinstance(t.get("output"), dict) else {}
        meta = t.get("metadata") if isinstance(t.get("metadata"), dict) else {}
        filename = inp.get("filename") or meta.get("filename")
        scores = _score_map(t.get("scores") or [])
        sorter = _as_dict(out.get("sorter"))
        predicted = out.get("doc_type") or sorter.get("doc_type")
        gt = _ground_truth_blob(out, inp, meta)
        expected = _expected_class(gt, meta, inp, out)
        expected_sub = _expected_subclass(gt, meta, inp, out)
        predicted_sub = _predicted_subclass_from(out)
        started = t.get("timestamp") or t.get("createdAt")
        ended = t.get("updatedAt") or t.get("updated_at")
        seconds = None
        try:
            if started and ended:
                t0 = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
                seconds = round((t1 - t0).total_seconds(), 2)
        except Exception:
            seconds = None
        row = {
            "trace_id": t.get("id"),
            "filename": filename,
            "expected": expected,
            "predicted": predicted,
            "exact_ok": bool(expected and predicted and expected == predicted),
            "aligned_ok": _aligned(expected, predicted) if expected else False,
            "expected_subclass": expected_sub,
            "predicted_subclass": predicted_sub,
            "doc_subclass": predicted_sub,
            "contract_subtype": sorter.get("contract_subtype") or out.get("contract_subtype"),
            "stage": out.get("stage"),
            "class_conf": out.get("classification_confidence"),
            "extract_conf": out.get("extraction_confidence"),
            "extracted_data": out.get("extracted_data"),
            "error": out.get("error_message") or out.get("error"),
            "cost_usd": scores.get("estimated_cost_usd") or t.get("totalCost"),
            "total_tokens": scores.get("total_tokens"),
            "verdict": scores.get("mailroom-pipeline-judge"),
            "quality": scores.get("mailroom-pipeline-quality"),
            "session": t.get("sessionId") or t.get("session_id"),
            "environment": t.get("environment"),
            "tags": t.get("tags"),
            # Trace.updatedAt also moves when asynchronous evaluators attach
            # scores, so it is not pipeline latency. Prefer the explicit
            # end-to-end score emitted before the trace closes.
            "seconds": scores.get("run_duration_seconds") or seconds,
            "intake_changed": False,
            "intake_messy": False,
        }
        _stamp_subclass(row)
        rows.append(row)
    return rows


def enrich_intake(rows: list[dict]) -> list[dict]:
    """Pull ``normalize-intake`` observation output onto each row."""
    for row in rows:
        tid = row.get("trace_id")
        if not tid:
            continue
        try:
            detail = _lf_get(f"/api/public/traces/{urllib.parse.quote(str(tid))}")
        except Exception:
            continue
        out = detail.get("output") if isinstance(detail.get("output"), dict) else {}
        meta = detail.get("metadata") if isinstance(detail.get("metadata"), dict) else {}
        inp = detail.get("input") if isinstance(detail.get("input"), dict) else {}
        gt = (
            (out.get("ground_truth") if isinstance(out.get("ground_truth"), dict) else None)
            or (inp.get("ground_truth") if isinstance(inp.get("ground_truth"), dict) else None)
            or {}
        )
        for obs in detail.get("observations") or []:
            if not isinstance(obs, dict):
                continue
            name = obs.get("name") or ""
            obs_out = _as_dict(obs.get("output"))
            if name == "normalize-intake":
                row["intake_messy"] = bool(obs_out.get("messy"))
                row["intake_changed"] = bool(
                    obs_out.get("collapsed_blank_runs") or obs_out.get("hyphen_unwraps") or obs_out.get("changed")
                )
                row["intake_method"] = obs_out.get("method")
                row["intake_chars"] = obs_out.get("chars")
            if name == "pipeline-result":
                if not gt:
                    gt = obs_out.get("ground_truth") if isinstance(obs_out.get("ground_truth"), dict) else {}
                if not row.get("extracted_data"):
                    row["extracted_data"] = obs_out.get("extracted_data")
            if name in ("classify-document", "classify", "pipeline-result",
                        "write-catalog", "compile-report"):
                if not row.get("predicted_subclass"):
                    token = obs_out.get("doc_subclass") or obs_out.get("contract_subtype")
                    nested = _as_dict(obs_out.get("sorter"))
                    token = token or nested.get("doc_subclass") or nested.get("contract_subtype")
                    if token:
                        row["predicted_subclass"] = token
                        row["doc_subclass"] = row.get("doc_subclass") or token
                        if obs_out.get("contract_subtype") or nested.get("contract_subtype"):
                            row["contract_subtype"] = (
                                obs_out.get("contract_subtype") or nested.get("contract_subtype")
                            )
        expected = (
            row.get("expected")
            or gt.get("expected_hf_class")
            or meta.get("expected_hf_class")
            or gt.get("expected_doc_class")
        )
        if not row.get("expected_subclass"):
            row["expected_subclass"] = (
                gt.get("expected_subclass")
                or meta.get("expected_subclass")
                or inp.get("expected_subclass")
            )
        if expected:
            row["expected"] = expected
            pred = row.get("predicted") or out.get("doc_type")
            row["exact_ok"] = expected == pred
            row["aligned_ok"] = _aligned(expected, pred)
        if not row.get("predicted"):
            row["predicted"] = out.get("doc_type")
            if row.get("expected"):
                row["exact_ok"] = row["expected"] == row.get("predicted")
                row["aligned_ok"] = _aligned(row["expected"], row.get("predicted"))
        if not row.get("predicted_subclass"):
            token = _predicted_subclass_from(out)
            if token:
                row["predicted_subclass"] = token
                row["doc_subclass"] = row.get("doc_subclass") or token
        _stamp_subclass(row)
        if not row.get("stage"):
            row["stage"] = out.get("stage")
        if not row.get("error"):
            row["error"] = out.get("error_message") or out.get("error")
        if row.get("extracted_data") is None:
            row["extracted_data"] = out.get("extracted_data")
        scores = _score_map(detail.get("scores") or [])
        if scores.get("estimated_cost_usd") is not None:
            row["cost_usd"] = scores["estimated_cost_usd"]
        if scores.get("total_tokens") is not None:
            row["total_tokens"] = scores["total_tokens"]
        if scores.get("run_duration_seconds") is not None:
            row["seconds"] = scores["run_duration_seconds"]
        if scores.get("mailroom-pipeline-judge") is not None:
            row["verdict"] = scores["mailroom-pipeline-judge"]
        if scores.get("mailroom-pipeline-quality") is not None:
            row["quality"] = scores["mailroom-pipeline-quality"]
    return rows


def attach_hf_labels(rows: list[dict], split: str = "train") -> list[dict]:
    """Fill missing ``expected`` from pinned mailroom-dataset GT, joined on filename."""
    need = [r for r in rows if r.get("filename") and not r.get("expected")]
    if not need:
        return rows
    labels: dict[str, str] = {}
    revision = corpus_revision()
    for sp in (split, "test", "train"):
        batch = fetch_rows(
            dataset=DATASET_ID,
            config=gt_config(),
            split=sp,
            revision=revision,
        )
        for row in batch:
            expected = row.get("expected")
            fn = row.get("filename")
            if not fn or expected is None:
                continue
            labels[fn] = expected
            # sanitized local names used as Langfuse input.filename
            stem = Path(str(fn).replace("/", "_").replace(":", "_")).name
            if stem:
                labels.setdefault(stem, expected)
                labels.setdefault(stem + ".txt", expected)
        if labels:
            break
    for r in rows:
        if not r.get("expected") and r.get("filename") in labels:
            r["expected"] = labels[r["filename"]]
            r["exact_ok"] = r["expected"] == r.get("predicted")
            r["aligned_ok"] = _aligned(r["expected"], r.get("predicted"))
    return rows


def attach_manifest(rows: list[dict], path: str | None) -> list[dict]:
    """Join expected labels from a hf_pilot ``manifest.json`` or ``report.json``."""
    if not path:
        return rows
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    items = payload.get("samples") if isinstance(payload, dict) else payload
    by_local: dict[str, str] = {}
    by_orig: dict[str, str] = {}
    by_trace: dict[str, str] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        expected = item.get("expected")
        if item.get("local_filename") and expected:
            by_local[item["local_filename"]] = expected
        if item.get("filename") and expected:
            by_orig[item["filename"]] = expected
        if item.get("trace_id") and expected:
            by_trace[str(item["trace_id"])] = expected
    for r in rows:
        if r.get("expected"):
            continue
        expected = (
            by_trace.get(str(r.get("trace_id") or ""))
            or by_local.get(r.get("filename") or "")
            or by_orig.get(r.get("filename") or "")
        )
        if expected:
            r["expected"] = expected
            r["exact_ok"] = expected == r.get("predicted")
            r["aligned_ok"] = _aligned(expected, r.get("predicted"))
    return rows


def render_markdown(summary: dict, rows: list[dict], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"- n = **{summary['n']}**",
        f"- exact accuracy = **{summary['exact_accuracy']:.3f}**",
        f"- aligned accuracy = **{summary['aligned_accuracy']:.3f}**",
        f"- cost USD = {summary['cost_usd_sum']}",
        f"- tokens = {summary['tokens_sum']}",
        f"- mean latency s = {summary.get('latency_s_mean', 0)}",
        f"- intake changed / messy = {summary['intake_changed']} / {summary['intake_messy']}",
        "",
        "## Failure modes",
        "",
        "| mode | n |",
        "|---|---|",
    ]
    for mode, n in sorted((summary.get("failure_modes") or {}).items()):
        lines.append(f"| {mode} | {n} |")
    lines += ["", "## Per class", "", "| class | n | exact | aligned |", "|---|---|---|---|"]
    for cls, stats in sorted((summary.get("by_class") or {}).items()):
        lines.append(f"| {cls} | {stats['n']} | {stats['exact']} | {stats['aligned']} |")
    lines += ["", "## Confusion (expected \\ predicted)", ""]
    preds = sorted({p for cells in (summary.get("confusion") or {}).values() for p in cells})
    if preds:
        lines.append("| expected | " + " | ".join(preds) + " |")
        lines.append("|---|" + "|".join(["---"] * len(preds)) + "|")
        for exp, cells in sorted((summary.get("confusion") or {}).items()):
            lines.append("| " + exp + " | " + " | ".join(str(cells.get(p, 0)) for p in preds) + " |")
    lines += ["", "## Samples", "", "| file | expected | predicted | stage | mode |", "|---|---|---|---|---|"]
    for r in rows:
        fn = (r.get("filename") or r.get("trace_id") or "")[:48]
        lines.append(
            f"| {fn} | {r.get('expected')} | {r.get('predicted')} | "
            f"{r.get('stage')} | {classify_failure(r)} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", help="Langfuse session id (pilot-hf-...)")
    parser.add_argument("--environment", default="pilot")
    parser.add_argument("--since", type=int, default=86400, help="seconds lookback")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--split", default="train", help="HF split used to join labels")
    parser.add_argument("--manifest", help="hf_pilot manifest.json or report.json for GT join")
    parser.add_argument("--out", help="write JSON report here")
    parser.add_argument("--md", help="write markdown report here")
    parser.add_argument("--check", action="store_true",
                        help="run the scorer on a fixture; no Langfuse/HF calls")
    args = parser.parse_args()

    if args.check:
        fixture = [
            {"expected": "contract", "predicted": "contract", "stage": "archived", "exact_ok": True, "aligned_ok": True},
            {"expected": "merger_agreement", "predicted": "merger_agreement", "stage": "archived", "exact_ok": True, "aligned_ok": True},
            {"expected": "merger_agreement", "predicted": "contract", "stage": "archived", "exact_ok": False, "aligned_ok": False},
            {"expected": "correspondence", "predicted": "contract", "stage": "archived", "exact_ok": False, "aligned_ok": False},
            {"expected": "corporate_record", "predicted": "corporate_record", "stage": "failed", "error": "x", "exact_ok": True, "aligned_ok": True},
        ]
        for r in fixture:
            r["filename"] = (r["expected"] or "x") + ".txt"
        summary = score_rows(fixture)
        assert summary["n"] == 5
        assert abs(summary["exact_accuracy"] - 0.6) < 1e-9
        assert abs(summary["aligned_accuracy"] - 0.6) < 1e-9
        assert classify_failure(fixture[2]) == "wrong_class"
        assert classify_failure(fixture[3]) == "wrong_class"
        assert classify_failure(fixture[4]) == "failed"
        messy, stats = deterministic_normalize("A\n\n\n\nB-\nC")
        assert looks_messy("x\n" * 30, None)
        print("check ok", json.dumps(summary))
        return 0

    traces = fetch_traces(
        session=args.session, since=args.since,
        environment=args.environment, limit=args.limit,
    )
    rows = attach_manifest(
        enrich_intake(attach_hf_labels(traces_to_rows(traces), split=args.split)),
        args.manifest,
    )
    summary = score_rows(rows)
    title = f"Pipeline eval — {args.session or args.environment} ({datetime.now(timezone.utc).date()})"
    md = render_markdown(summary, rows, title)
    print(md)
    payload = {"summary": summary, "samples": rows, "session": args.session,
               "environment": args.environment, "dataset": DATASET_ID}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(md, encoding="utf-8")
        print(f"wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
