#!/usr/bin/env python3
"""build_a100_manifest.py — S1: per-leg A100 run manifest (DMR-078).

Standalone, stdlib-only. Reads ONLY from the staged inputs tree
    C:/Users/grant/Digital Mailroom/wt-manifest/_a100_inputs/
and writes two artifacts flat into the local-mailroom-sandbox package's
reports/ directory:

    reports/a100-run-manifest.md
    reports/a100-run-manifest.csv

One row per A100 run *leg*, i.e. one row per job record under
_a100_inputs/jobs/ whose job_id contains the token "a100". That count
(32) is treated as authoritative: the script asserts
    (#A100 job records) == (#manifest rows)
and additionally asserts that every row's run_store directory exists
(_a100_inputs/run_store/<run_id>). Any mismatch fails loudly (non-zero exit).

Field provenance (faithful — blank when there is genuinely no source):
  run_id        job record job_id (== job filename stem == run_store dir name)
  gpu           1x/2x parsed from the job_id token; blank when absent
  doc_class     parsed from the run_id class token
  n             job record `total` (fallback `done`) = documents in the leg
  driver_or_runner  the series runner the inputs name for that run_id family
                    (scripts/run_a100_*.py); blank when no runner is identified
  config_spec   run-spec yaml filename cited by that series runner
                (inferable from the run_id arm); blank when not inferable
  run_dir       matched _a100_inputs/run_store/<run_id> (must exist)
  score         no per-A100-leg score exists in the inputs -> blank
  errors        job record `errors`
  gpu_cost_usd  A100-Research-Report.md GPU $/100 docs x n/100 (base legs only)
  cost_per_doc  A100-Research-Report.md GPU $/100 docs / 100 (base legs only)
  dataset_fingerprint  no per-A100-leg fingerprint exists in the inputs -> blank
  notes         short provenance / caveat string

Deterministic: rows are sorted by run_id, no timestamps, fixed float
formatting, LF line terminators. Two runs are byte-identical.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

# --- fixed roots -------------------------------------------------------------
INPUT_ROOT = Path("C:/Users/grant/Digital Mailroom/wt-manifest/_a100_inputs")
JOBS_DIR = INPUT_ROOT / "jobs"
RUN_STORE = INPUT_ROOT / "run_store"
CONFIGS_DIR = INPUT_ROOT / "configs"
REPORTS_DIR = INPUT_ROOT / "reports"
CARDS_DIR = INPUT_ROOT / "cards"

# package reports/ dir: <worktree>/packages/local-mailroom-sandbox/reports
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PACKAGE_ROOT / "reports"

A100_TOKEN = "a100"

# --- A100 report basis (cards/A100-Research-Report.md "Adapting to a bigger
# GPU" table; identical numbers reproduced in cards/make_a100_figures.py) -----
# canonical class -> (cost_per_100_docs_1x, cost_per_100_docs_2x, report_n)
A100_COST_PER_100 = {
    "correspondence":   {"1x": 0.188, "2x": 0.219, "n": 300},
    "insurance_claim":  {"1x": 0.237, "2x": 0.273, "n": 300},
    "corporate_record": {"1x": 0.163, "2x": 0.170, "n": 300},
    "contract":         {"1x": 0.516, "2x": 0.690, "n": 150},
    "merger":           {"1x": 0.400, "2x": 0.548, "n": 100},
}

# class token -> canonical key (longest first so "merger" never shadows nothing
# longer; "corporate_record" before any "corporate").
_CLASS_TOKENS = [
    ("insurance_claim", "insurance_claim"),
    ("corporate_record", "corporate_record"),
    ("correspondence", "correspondence"),
    ("contract", "contract"),
    ("merger", "merger"),
]

# base allclass matrix leg: qwen3-8b-a100-<class>-a100-<1x|2x>-<class>-<N>
_BASE_LEG_RE = re.compile(
    r"^qwen3-8b-a100-(?P<c1>contract|corporate_record|correspondence|insurance_claim|merger)"
    r"-a100-(?P<gpu>1x|2x)-"
    r"(?P<c2>contract|corporate_record|correspondence|insurance_claim|merger)-(?P<n>\d+)$"
)

# v3 legs documented verbatim by scripts/run_a100_v3_finish.py
_V3_LEG_RE = re.compile(r"^qwen3-8b-a100-v3-(?P<cls>contract|merger)$")

_GPU_RE = re.compile(r"(?:^|-)1x(?:-|$)|(?:^|-)2x(?:-|$)")


def classify_doc(run_id: str) -> str:
    for token, canonical in _CLASS_TOKENS:
        if token in run_id:
            return canonical
    return ""


def parse_gpu(run_id: str) -> str:
    m = _GPU_RE.search(run_id)
    if not m:
        return ""
    return m.group(0).strip("-")


def runner_for(run_id: str) -> str:
    """The series runner the inputs name for this run_id family, else ''."""
    if _BASE_LEG_RE.match(run_id):
        return "scripts/run_a100_matrix.py"
    if "-a100-v2-" in run_id:
        return "scripts/run_a100_v2.py"
    m = _V3_LEG_RE.match(run_id)
    if m and m.group("cls") in ("contract", "merger"):
        return "scripts/run_a100_v3_finish.py"
    return ""


def config_spec_for(run_id: str, gpu: str) -> str:
    """Run-spec yaml filename the series runner cites, inferable from the arm."""
    if _BASE_LEG_RE.match(run_id):
        return {"1x": "a100_1x_allclass.yaml", "2x": "a100_2x_allclass.yaml"}.get(gpu, "")
    if "-a100-v2-" in run_id:
        return {"1x": "a100_v2_1x_allclass.yaml", "2x": "a100_v2_2x_allclass.yaml"}.get(gpu, "")
    m = _V3_LEG_RE.match(run_id)
    if m:
        return {"contract": "a100_v3_extract_contract.yaml",
                "merger": "a100_v3_extract_merger.yaml"}[m.group("cls")]
    return ""


def load_a100_jobs() -> list[dict]:
    if not JOBS_DIR.is_dir():
        raise SystemExit(f"FATAL: jobs dir not found: {JOBS_DIR}")
    jobs = []
    for path in sorted(JOBS_DIR.glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        job_id = rec.get("job_id") or path.stem
        if A100_TOKEN in job_id:
            jobs.append(rec)
    return sorted(jobs, key=lambda r: r.get("job_id", ""))


def build_rows(jobs: list[dict]) -> list[dict]:
    rows = []
    for rec in jobs:
        run_id = rec.get("job_id") or ""
        gpu = parse_gpu(run_id)
        doc_class = classify_doc(run_id)
        n = rec.get("total")
        if n is None:
            n = rec.get("done")
        errors = rec.get("errors")

        # run_store dir must exist for this run_id
        run_dir_path = RUN_STORE / run_id
        if not run_dir_path.is_dir():
            raise SystemExit(
                f"FATAL: no run_store match for run_id={run_id!r} "
                f"(expected dir {run_dir_path})"
            )

        driver = runner_for(run_id)
        config_spec = config_spec_for(run_id, gpu)

        # cost: only the base allclass legs have a per-class/per-arm number in
        # the A100 report basis (and only at the report's own sample size).
        gpu_cost_usd = ""
        cost_per_doc = ""
        notes = []
        m = _BASE_LEG_RE.match(run_id)
        cost_note = ""
        if m and m.group("c1") == m.group("c2") == doc_class and gpu in ("1x", "2x"):
            basis = A100_COST_PER_100.get(doc_class)
            if basis and n is not None and int(n) == basis["n"]:
                per100 = basis[gpu]
                gpu_cost_usd = f"{per100 * (int(n) / 100.0):.6f}"
                cost_per_doc = f"{per100 / 100.0:.6f}"
                cost_note = (
                    f"cost from A100-Research-Report.md (GPU ${per100:.3f}/100 docs"
                    f" x n={int(n)}/100)"
                )

        if gpu == "":
            notes.append("gpu not encoded in run_id")
        if cost_note:
            notes.append(cost_note)
        else:
            notes.append("no per-leg score/fingerprint/cost source in inputs")
        if n is None:
            notes.append("n absent from job record")
        else:
            done = rec.get("done")
            if done is not None and int(done) != int(n):
                notes.append(f"done={done}/total={n}")
        if driver == "":
            notes.append("runner not identified in inputs")

        rows.append({
            "run_id": run_id,
            "gpu": gpu,
            "doc_class": doc_class,
            "n": "" if n is None else int(n),
            "driver_or_runner": driver,
            "config_spec": config_spec,
            "run_dir": run_id,
            "score": "",
            "errors": "" if errors is None else int(errors),
            "gpu_cost_usd": gpu_cost_usd,
            "cost_per_doc": cost_per_doc,
            "dataset_fingerprint": "",
            "notes": "; ".join(notes),
        })
    rows.sort(key=lambda r: r["run_id"])
    return rows


COLUMNS = [
    "run_id", "gpu", "doc_class", "n", "driver_or_runner", "config_spec",
    "run_dir", "score", "errors", "gpu_cost_usd", "cost_per_doc",
    "dataset_fingerprint", "notes",
]


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _md_cell(v) -> str:
    s = "" if v is None else str(v)
    return s.replace("|", "\\|")


def write_md(rows: list[dict], path: Path, n_jobs: int) -> None:
    lines = []
    lines.append("# A100 run manifest — per-leg 1x/2x cost-per-token evidence")
    lines.append("")
    lines.append("Generated by `scripts/build_a100_manifest.py` (S1, DMR-078). "
                 "One row per A100 run leg.")
    lines.append("")
    lines.append(f"- A100 job records (job_id contains `a100`): **{n_jobs}**")
    lines.append(f"- Manifest rows: **{len(rows)}**")
    lines.append("- Source of record: `_a100_inputs/jobs/*.json` (identity, n, errors), "
                 "`_a100_inputs/cards/A100-Research-Report.md` (base-leg GPU cost basis), "
                 "`_a100_inputs/run_store/<run_id>/` (matched dataset dir).")
    lines.append("- Fields left blank carry no per-A100-leg source in the staged "
                 "inputs (`score`, `dataset_fingerprint`); blanks are not zeros.")
    lines.append("")
    lines.append("| " + " | ".join(COLUMNS) + " |")
    lines.append("|" + "|".join(["---"] * len(COLUMNS)) + "|")
    for r in rows:
        lines.append("| " + " | ".join(_md_cell(r[c]) for c in COLUMNS) + " |")
    lines.append("")
    lines.append("## Provenance notes")
    lines.append("")
    lines.append("- `gpu` (1x/2x) is parsed from the `job_id` token; blank when the "
                 "id does not encode a GPU count.")
    lines.append("- `n` is the job record `total` (the leg's document count); "
                 "`done!=total` is flagged in `notes`.")
    lines.append("- `driver_or_runner` names the series runner the inputs attribute "
                 "to that run_id family (`scripts/run_a100_matrix.py`, "
                 "`scripts/run_a100_v2.py`, `scripts/run_a100_v3_finish.py`); blank "
                 "where no runner is identifiable.")
    lines.append("- `config_spec` is the run-spec yaml the series runner cites, "
                 "inferable from the run_id arm; blank where not inferable.")
    lines.append("- `gpu_cost_usd` / `cost_per_doc` are taken from the "
                 "A100-Research-Report.md base matrix (GPU $ per 100 docs) for the "
                 "ten base allclass legs only; all other legs have no per-run cost "
                 "source in the inputs.")
    lines.append("- `score` and `dataset_fingerprint` are blank throughout: the "
                 "staged `experiment_log_head.jsonl` and `reports/*.serving.json` "
                 "carry only non-A100 (L4 / sand032 / sorter) legs, and "
                 "`cards/A100-MASTER-SCORE-COST-CARD.md` is absent from the inputs.")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    jobs = load_a100_jobs()
    n_jobs = len(jobs)
    rows = build_rows(jobs)

    # ASSERTION: A100 job-record count is authoritative and must equal rows.
    if n_jobs != len(rows):
        raise SystemExit(
            f"FATAL: {n_jobs} A100 job records but {len(rows)} manifest rows "
            "(must be 1:1)"
        )
    # (per-row run_store existence already asserted in build_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "a100-run-manifest.csv"
    md_path = OUT_DIR / "a100-run-manifest.md"
    write_csv(rows, csv_path)
    write_md(rows, md_path, n_jobs)

    print(f"A100 job records : {n_jobs}")
    print(f"manifest rows    : {len(rows)}")
    print(f"rows == jobs     : {n_jobs == len(rows)}")
    print(f"run_store matched: {sum(1 for r in rows if (RUN_STORE / r['run_dir']).is_dir())}/{len(rows)}")
    print(f"wrote            : {md_path}")
    print(f"wrote            : {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
