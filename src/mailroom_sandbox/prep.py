"""Load / clean / prepare offline fixtures for notebook and CLI use.

Writes prepared artifacts under ``data/runtime/prepared/`` (gitignored via
``data/runtime/``). Network is never required for the offline path.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mailroom_sandbox.datasets import (
    dataset_fingerprint,
    fixture_file,
    load_agent_fixtures,
    load_hf_fixtures,
    load_legalbench_fixtures,
    load_manifest,
    parse_expected_fields,
)
from mailroom_sandbox.paths import fixtures_dir, repo_root, runtime_dir

_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")


@dataclass
class CleanReport:
    source: str
    input_rows: int
    kept_rows: int
    dropped_empty: int = 0
    dropped_missing_fields: int = 0
    repaired_fields: int = 0
    issues: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def prepared_dir() -> Path:
    path = runtime_dir() / "prepared"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _display_path(path: Path) -> str:
    """Prefer a repo-relative path; fall back to absolute when outside the tree."""
    try:
        return str(path.resolve().relative_to(repo_root()))
    except ValueError:
        return str(path.resolve())


def normalize_text(text: str) -> str:
    """Collapse whitespace noise while preserving paragraph breaks."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _WS_RE.sub(" ", cleaned)
    cleaned = _BLANK_RE.sub("\n\n", cleaned)
    return cleaned.strip()


def _require_keys(row: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    return [k for k in keys if not str(row.get(k) or "").strip()]


def clean_manifest_rows(rows: list[dict[str, str]] | None = None) -> tuple[list[dict[str, Any]], CleanReport]:
    """Load the fixture catalog, read each file, normalize text, attach gold."""
    rows = rows if rows is not None else load_manifest()
    report = CleanReport(source="manifest", input_rows=len(rows), kept_rows=0)
    prepared: list[dict[str, Any]] = []
    for row in rows:
        missing = _require_keys(row, ("id", "subdir", "filename", "expected_doc_class"))
        if missing:
            report.dropped_missing_fields += 1
            report.issues.append(f"{row.get('id', '?')}: missing {missing}")
            continue
        path = fixture_file(row)
        if not path.is_file():
            report.dropped_missing_fields += 1
            report.issues.append(f"{row['id']}: missing file {path}")
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        text = normalize_text(raw)
        if not text:
            report.dropped_empty += 1
            report.issues.append(f"{row['id']}: empty after clean")
            continue
        fields = parse_expected_fields(row)
        if fields is None and (row.get("expected_fields") or "").strip():
            report.repaired_fields += 1
            report.issues.append(f"{row['id']}: expected_fields was not valid JSON; dropped")
            fields = {}
        elif fields is None:
            fields = {}
        prepared.append(
            {
                "id": row["id"],
                "subdir": row["subdir"],
                "filename": row["filename"],
                "path": str(path.relative_to(repo_root())),
                "expected_doc_class": row["expected_doc_class"],
                "expected_stage": row.get("expected_stage") or "",
                "size_tier": row.get("size_tier") or "",
                "dataset": row.get("dataset") or "sandbox-fixtures",
                "expected_fields": fields,
                "text": text,
                "char_count": len(text),
                "source": row.get("source") or "",
                "license": row.get("license") or "",
            }
        )
    report.kept_rows = len(prepared)
    return prepared, report


def clean_hf_rows(rows: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], CleanReport]:
    rows = rows if rows is not None else load_hf_fixtures()
    report = CleanReport(source="hf", input_rows=len(rows), kept_rows=0)
    prepared: list[dict[str, Any]] = []
    for row in rows:
        text = normalize_text(str(row.get("text") or ""))
        doc_type = str(row.get("doc_type") or row.get("expected_hf_class") or "").strip()
        row_id = str(row.get("id") or "").strip()
        if not row_id or not doc_type:
            report.dropped_missing_fields += 1
            report.issues.append(f"{row_id or '?'}: missing id/doc_type")
            continue
        if not text:
            report.dropped_empty += 1
            report.issues.append(f"{row_id}: empty text")
            continue
        prepared.append(
            {
                "id": row_id,
                "doc_type": doc_type,
                "expected_hf_class": row.get("expected_hf_class") or doc_type,
                "filename": row.get("filename") or f"{row_id}.txt",
                "split": row.get("split") or "test",
                "text": text,
                "char_count": len(text),
            }
        )
    report.kept_rows = len(prepared)
    return prepared, report


def clean_legalbench_rows(
    rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], CleanReport]:
    rows = rows if rows is not None else load_legalbench_fixtures()
    report = CleanReport(source="legalbench", input_rows=len(rows), kept_rows=0)
    prepared: list[dict[str, Any]] = []
    for row in rows:
        row_id = str(row.get("id") or "").strip()
        question = normalize_text(str(row.get("question") or row.get("text") or ""))
        answer = str(row.get("answer") or row.get("label") or "").strip().lower()
        if not row_id or not question:
            report.dropped_missing_fields += 1
            report.issues.append(f"{row_id or '?'}: missing id/question")
            continue
        if answer not in {"yes", "no"}:
            report.dropped_missing_fields += 1
            report.issues.append(f"{row_id}: answer must be yes/no, got {answer!r}")
            continue
        prepared.append(
            {
                "id": row_id,
                "question": question,
                "text": normalize_text(str(row.get("text") or row.get("document_text") or "")),
                "answer": answer,
                "task": row.get("task") or "contract_qa",
                "char_count": len(question),
            }
        )
    report.kept_rows = len(prepared)
    return prepared, report


def clean_agent_rows(agent: str) -> tuple[list[dict[str, Any]], CleanReport]:
    rows = load_agent_fixtures(agent)
    report = CleanReport(source=f"agents/{agent}", input_rows=len(rows), kept_rows=0)
    prepared: list[dict[str, Any]] = []
    for row in rows:
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            report.dropped_missing_fields += 1
            report.issues.append("row missing id")
            continue
        out = dict(row)
        out["id"] = row_id
        if "expected_fields" in out and isinstance(out["expected_fields"], str):
            try:
                out["expected_fields"] = json.loads(out["expected_fields"])
                report.repaired_fields += 1
            except json.JSONDecodeError:
                report.issues.append(f"{row_id}: expected_fields not JSON")
                out["expected_fields"] = {}
        # Attach normalized fixture text when a catalog path is present.
        subdir = out.get("subdir")
        filename = out.get("filename")
        if subdir and filename:
            path = fixtures_dir() / str(subdir) / str(filename)
            if path.is_file():
                out["text"] = normalize_text(path.read_text(encoding="utf-8", errors="replace"))
                out["char_count"] = len(out["text"])
                if not out["text"]:
                    report.dropped_empty += 1
                    report.issues.append(f"{row_id}: empty fixture text")
                    continue
            else:
                report.issues.append(f"{row_id}: fixture file missing ({path.name})")
        prepared.append(out)
    report.kept_rows = len(prepared)
    return prepared, report


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return path


def prepare_offline_datasets(*, agents: list[str] | None = None) -> dict[str, Any]:
    """Clean all offline corpora and write JSONL + a prep manifest."""
    out_dir = prepared_dir()
    agents = agents or ["judge", "arbiter", "boss", "intake", "pdf_transcriber", "image_extractor"]
    reports: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}

    manifest_rows, report = clean_manifest_rows()
    path = write_jsonl(out_dir / "fixtures_prepared.jsonl", manifest_rows)
    artifacts["fixtures"] = _display_path(path)
    reports.append(report.as_dict())

    hf_rows, report = clean_hf_rows()
    path = write_jsonl(out_dir / "hf_prepared.jsonl", hf_rows)
    artifacts["hf"] = _display_path(path)
    reports.append(report.as_dict())

    lb_rows, report = clean_legalbench_rows()
    path = write_jsonl(out_dir / "legalbench_prepared.jsonl", lb_rows)
    artifacts["legalbench"] = _display_path(path)
    reports.append(report.as_dict())

    agent_artifacts: dict[str, str] = {}
    for agent in agents:
        rows, report = clean_agent_rows(agent)
        if report.input_rows == 0 and report.kept_rows == 0:
            reports.append(report.as_dict())
            continue
        path = write_jsonl(out_dir / "agents" / f"{agent}_prepared.jsonl", rows)
        agent_artifacts[agent] = _display_path(path)
        reports.append(report.as_dict())
    artifacts["agents"] = agent_artifacts  # type: ignore[assignment]

    # Lightweight class-balanced view for sorter pilots (one row per doc class).
    by_class: dict[str, dict[str, Any]] = {}
    for row in manifest_rows:
        cls = row["expected_doc_class"]
        by_class.setdefault(cls, row)
    balanced = list(by_class.values())
    path = write_jsonl(out_dir / "sorter_pilot_balanced.jsonl", balanced)
    artifacts["sorter_pilot_balanced"] = _display_path(path)

    agent_counts: dict[str, int] = {}
    for agent, rel in agent_artifacts.items():
        artifact = Path(rel)
        if not artifact.is_absolute():
            artifact = repo_root() / artifact
        agent_counts[agent] = sum(
            1 for line in artifact.read_text(encoding="utf-8").splitlines() if line.strip()
        )

    summary = {
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": dataset_fingerprint(
            [
                {
                    "id": r["id"],
                    "filename": r["filename"],
                    "expected_doc_class": r["expected_doc_class"],
                }
                for r in manifest_rows
            ]
        ),
        "counts": {
            "fixtures": len(manifest_rows),
            "hf": len(hf_rows),
            "legalbench": len(lb_rows),
            "agents": agent_counts,
            "sorter_pilot_balanced": len(balanced),
        },
        "artifacts": artifacts,
        "reports": reports,
    }

    manifest_path = out_dir / "prep_manifest.json"
    manifest_path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    summary["manifest"] = _display_path(manifest_path)
    return summary


def environment_checklist(profile: str = "ollama") -> dict[str, Any]:
    """Inspect whether the offline sandbox can activate without guessing."""
    root = repo_root()
    env_candidates = [root / ".env", root / "config" / ".env", root / "config" / ".env.example"]
    env_found = next((p for p in env_candidates if p.is_file()), None)
    fixtures_ok = (fixtures_dir() / "manifest.csv").is_file()
    compose_ok = (root / "deploy" / "docker-compose.yml").is_file()
    dockerfile_ok = (root / "deploy" / "Dockerfile").is_file()
    notebooks = sorted((root / "notebooks").glob("*.ipynb")) if (root / "notebooks").is_dir() else []

    from mailroom_sandbox.overlay import list_profiles
    from mailroom_sandbox.runtime import activate, resolve_mailroom_src

    profiles = list_profiles()
    activation = None
    activation_error = None
    try:
        activation = activate(profile, load_env_file=True)
    except Exception as exc:  # noqa: BLE001 — surface to notebook operators
        activation_error = f"{type(exc).__name__}: {exc}"

    mailroom = resolve_mailroom_src()
    return {
        "repo_root": str(root),
        "profile": profile,
        "profiles_available": profiles,
        "env_file": str(env_found.relative_to(root)) if env_found else None,
        "fixtures_manifest_ok": fixtures_ok,
        "compose_file_ok": compose_ok,
        "dockerfile_ok": dockerfile_ok,
        "notebooks": [str(p.relative_to(root)) for p in notebooks],
        "mailroom_src": str(mailroom) if mailroom else None,
        "runtime_taxonomy": str(activation.taxonomy_path.relative_to(root)) if activation else None,
        "agent_count": len(activation.assignments) if activation else 0,
        "activation_ok": activation is not None,
        "activation_error": activation_error,
        "prepared_dir": str(prepared_dir().relative_to(root)),
        "offline_ready": bool(
            fixtures_ok and compose_ok and dockerfile_ok and activation is not None and env_found is not None
        ),
    }


def ensure_dotenv_from_example() -> Path | None:
    """Copy config/.env.example → .env when missing (never overwrite)."""
    root = repo_root()
    dest = root / ".env"
    if dest.is_file():
        return dest
    src = root / "config" / ".env.example"
    if not src.is_file():
        return None
    shutil.copyfile(src, dest)
    return dest
