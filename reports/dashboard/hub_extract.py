"""Source-verified extraction for the Mailroom reports hub.

Every figure is read out of a tracked file (a markdown table cell, a sentence
or a JSON key) and recorded with repo, commit and quote. Cross-checks compare
per-document tables with the run-level figures each report states; a mismatch
aborts the build unless it is a documented entry in ``KNOWN``.

Sources:
- this repo (``local-mailroom-sandbox``): ``reports/`` — read live every build
- ``LLM-Mailroom-Services/eval-environment`` and ``LLM-Mailroom-Services/mailroom-ml``:
  read from sibling checkouts by ``build_hub.py sync`` into the committed
  snapshot ``external_snapshot.json`` (figures + provenance at a pinned SHA),
  so the page rebuilds offline.
"""

from __future__ import annotations

import json
import math
import pathlib
import re
import statistics
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
SANDBOX = HERE.parent.parent

KNOWN = {
    "sand032-s5-merger50-maud.summary_usd": (
        "The SAND-032 program summary lists the MAUD-prompt merger run at ${got}/doc; its run report "
        "gives ${want}/doc. The summary row used the serving export, which also bills the run's 122.8 s "
        "cold boot (0.251214 vs 0.196653 USD over 46 docs); every other row is busy-window only. "
        "This page uses the busy-window figure."
    ),
    "sand032-s6-sorter1000.usd_basis": (
        "The S6 sorter report gives ${got}/doc. That is the serving export's billed figure, which includes "
        "the run's {boot:.1f} s cold boot; every other SAND-032 $/doc is busy-window only. On that basis "
        "S6 costs ${want}/doc, which this page uses."
    ),
    "api.qwen_merger_model": (
        "eval-environment files the merger leg under Qwen3-8B, but the logged model is {model}. "
        "It is shown here as its own model."
    ),
    "api.deepseek_cls_wall": (
        "The DeepSeek-V4.1-Flash n=100 classification run logs a {wall} s wall time but a {p95:.1f} s p95 "
        "call latency, which cannot both be true. Its runtime is not charted."
    ),
    "mb.armB.coverage_field": (
        "mailroom-ml Arm B eval JSON: selective_risk.coverage is {top}, which is the last sweep row "
        "(threshold 0.99, coverage {last}), not the recommended {pick} threshold ({row}). The page reads "
        "the recommended row."
    ),
    "mb.run3.coverage_field": (
        "mailroom-ml run-3 eval JSON has the same exporter defect: coverage {top} is the 0.99 row; at the "
        "recommended {pick} threshold coverage is {row}."
    ),
    "mb.plus_invalid": (
        "The held-out-plus eval (1,323 docs, doc_type accuracy {acc}) is invalid: on the {n} canonical test "
        "documents it contains, it gets {plus} right where the same checkpoint's canonical run gets {base}. "
        "Its slice table also assigns all docs to the canonical slice. It is excluded from the charts."
    ),
}

NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?:e-?\d+)?")
L4_USD_PER_HOUR = 0.80


class SourceError(RuntimeError):
    pass


def git_sha(root: pathlib.Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001 — provenance only
        return "unknown"


class Ledger:
    """Collects provenance, known-issue hits and cross-check results."""

    def __init__(self, known: dict[str, str]):
        self.known = known
        self.prov: dict[str, dict] = {}
        self.issues: list[dict] = []
        self.checks = 0

    def record(self, key, value, repo, sha, path, quote):
        self.prov[key] = {"key": key, "value": value, "repo": repo, "sha": sha, "source": path, "quote": str(quote).strip()[:240]}
        return value

    def check(self, cond: bool, msg: str, key: str | None = None, **fmt):
        self.checks += 1
        if key in self.known:
            if cond:
                raise SourceError(f"known issue {key!r} no longer reproduces — remove it from KNOWN")
            self.issues.append({"key": key, "note": self.known[key].format(**fmt)})
            return
        if not cond:
            raise SourceError(f"cross-check failed: {msg}")


class Repo:
    def __init__(self, name: str, root: pathlib.Path, ledger: Ledger, sub: str = ""):
        self.name, self.root, self.L = name, root, ledger
        self.base = root / sub if sub else root
        self.sub = sub
        self.sha = git_sha(root)

    def rel(self, path: str) -> str:
        return f"{self.sub}/{path}" if self.sub else path

    def text(self, path: str) -> str:
        return (self.base / path).read_text()

    def _num(self, s: str, idx: int = 0) -> float:
        found = NUM.findall(s.replace("**", ""))
        if len(found) <= idx:
            raise SourceError(f"no number #{idx} in {s!r}")
        return float(found[idx].replace(",", ""))

    def cell(self, key, path, row, col, idx=0):
        hits = [ln for ln in self.text(path).splitlines() if ln.strip().startswith(row)]
        if not hits or len(set(hits)) != 1:
            raise SourceError(f"{self.name}:{path}: expected one row starting {row!r}, found {len(hits)}")
        cells = [c.strip() for c in hits[0].strip().strip("|").split("|")]
        return self.L.record(key, self._num(cells[col], idx), self.name, self.sha, self.rel(path), hits[0])

    def rx(self, key, path, pattern, group=1, number=True):
        flat = re.sub(r"\s+", " ", self.text(path))
        m = re.search(pattern, flat)
        if not m:
            raise SourceError(f"{self.name}:{path}: pattern {pattern!r} not found")
        val = self._num(m.group(group)) if number else m.group(group)
        return self.L.record(key, val, self.name, self.sha, self.rel(path), m.group(0))

    def jload(self, path):
        p = self.base / path
        if p.suffix == ".jsonl":
            return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
        return json.loads(p.read_text())

    def jkey(self, key, path, *keys, doc=None):
        node = doc if doc is not None else self.jload(path)
        for k in keys:
            node = node[k]
        return self.L.record(key, node, self.name, self.sha, self.rel(path), f"{'.'.join(map(str, keys))} = {json.dumps(node)[:120]}")

    def table(self, path, section: str, first_header: str) -> list[dict]:
        """Rows of the first markdown table under ``## section`` whose header starts with ``first_header``."""
        lines = self.text(path).splitlines()
        try:
            start = next(i for i, ln in enumerate(lines) if ln.startswith("## ") and ln[3:].startswith(section))
        except StopIteration as exc:
            raise SourceError(f"{self.name}:{path}: no section {section!r}") from exc
        rows, header = [], None
        for ln in lines[start + 1:]:
            if ln.startswith("## "):
                break
            if not ln.startswith("|"):
                if header is not None and rows:
                    break
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if header is None:
                if cells[0].startswith(first_header):
                    header = cells
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            rows.append(dict(zip(header, cells)))
        if header is None:
            raise SourceError(f"{self.name}:{path}: no table headed {first_header!r} under {section!r}")
        return rows


def fnum(s: str):
    s = (s or "").replace("**", "").strip()
    if s in ("", "None", "—", "-"):
        return None
    m = NUM.search(s)
    return float(m.group(0).replace(",", "")) if m else None


def median(xs):
    return statistics.median(xs)


# ------------------------------------------------------------------ SAND-032
SAND032 = {
    # run id: (report path, class key, metric kind)
    "sand032-s3-corr50": ("SAND-32/correspondence/SAND032-S3-CORR50-REPORT.md", "correspondence", "extraction"),
    "sand032-s3-corr50-repeat": ("SAND-32/correspondence/SAND032-S3-CORR50-REPEAT-REPORT.md", "correspondence", "extraction"),
    "sand032-s3-insurance50": ("SAND-32/insurance/SAND032-S3-INSURANCE50-REPORT.md", "insurance_claim", "extraction"),
    "sand032-s3-corporate50": ("SAND-32/corporate/SAND032-S3-CORPORATE50-REPORT.md", "corporate_record", "extraction"),
    "sand032-s3-contracts50": ("SAND-32/contract/SAND032-S3-CONTRACTS50-REPORT.md", "contract", "cuad"),
    "sand032-s3-merger50": ("SAND-32/merger/SAND032-S3-MERGER50-REPORT.md", "merger_agreement", "maud"),
    "sand032-s5-merger50-maud": ("SAND-32/merger/SAND032-S5-MERGER50-MAUD-REPORT.md", "merger_agreement", "maud"),
    "sand032-s2a-corr100-1rep": ("SAND-32/correspondence/SAND032-S2A-CORR100-1REP-REPORT.md", "correspondence", "extraction"),
    "sand032-s2b-corr100-2rep": ("SAND-32/correspondence/SAND032-S2B-CORR100-2REP-REPORT.md", "correspondence", "extraction"),
    "sand032-s4-corr20-bf16": ("SAND-32/correspondence/SAND032-S4-CORR20-BF16-REPORT.md", "correspondence", "extraction"),
    "sand032-l0-baseline": ("SAND-32/correspondence/SAND032-L0-BASELINE-REPORT.md", "correspondence", "extraction"),
    "sand032-l1-nothink": ("SAND-32/correspondence/SAND032-L1-NOTHINK-REPORT.md", "correspondence", "extraction"),
    "sand032-l2-marlin": ("SAND-32/correspondence/SAND032-L2-MARLIN-REPORT.md", "correspondence", "extraction"),
    "sand032-l5-graphs": ("SAND-32/correspondence/SAND032-L5-GRAPHS-REPORT.md", "correspondence", "extraction"),
}
SUMMARY = "serving/QWEN3-L4-LADDER-SUMMARY.md"
LADDER = "serving/SAND-32/SAND032-LADDER.md"


def sand032_run(R: Repo, rid: str) -> dict:
    path, cls, kind = SAND032[rid]
    L = R.L
    k = f"sand032.{rid}"
    ok = R.cell(f"{k}.ok", path, "| docs ok / total |", 1, 0)
    n = R.cell(f"{k}.n", path, "| docs ok / total |", 1, 1)
    overall = R.cell(f"{k}.overall", path, "| **overall_extraction_score** |", 1)
    schema = R.cell(f"{k}.schema", path, "| schema_valid_rate |", 1)
    wall = R.cell(f"{k}.wall", path, "| wall (runner busy interval) |", 1)
    p50 = R.cell(f"{k}.p50", path, "| latency p50 / p95 / max |", 1, 0)
    p95 = R.cell(f"{k}.p95", path, "| latency p50 / p95 / max |", 1, 1)
    lmax = R.cell(f"{k}.max", path, "| latency p50 / p95 / max |", 1, 2)
    ptok = R.cell(f"{k}.prompt_tokens", path, "| prompt / completion tokens |", 1, 0)
    ctok = R.cell(f"{k}.completion_tokens", path, "| prompt / completion tokens |", 1, 1)
    tps = R.cell(f"{k}.tps", path, "| throughput |", 1)
    per_doc_usd = R.cell(f"{k}.usd_per_doc", path, "| **$ per doc (busy)** |", 1)
    gpu_usd = R.rx(f"{k}.gpu_usd", path, r"\| GPU \$ over busy wall \([^)]*\) \| ([\d.]+) \|")
    conc = R.cell(f"{k}.conc", path, "| concurrency |", 1)
    speed = R.rx(f"{k}.speedup", path, r"= \*\*([\d.]+)×\*\* effective parallelism")

    rows = R.table(path, "Per-document scores", "#")
    docs = []
    for r in rows:
        docs.append({
            "doc": r["doc id"].strip("`"), "subclass": r["subclass"], "overall": fnum(r["overall"]),
            "schema": r.get("schema") == "✓", "latency": fnum(r["latency s"]),
            "prompt": fnum(r["prompt tok"]), "completion": fnum(r["compl tok"]),
            "error": (r.get("error") or "").strip() or None,
        })
    okd = [d for d in docs if not d["error"]]
    L.check(len(docs) == n, f"{rid}: {len(docs)} rows vs n={n}")
    L.check(len(okd) == ok, f"{rid}: {len(okd)} ok rows vs stated {ok}")
    scored = [d for d in okd if d["overall"] is not None]
    mean_ok = sum(d["overall"] for d in scored) / len(scored)
    L.check(abs(mean_ok - overall) < 0.0006, f"{rid}: per-doc mean {mean_ok:.4f} vs headline {overall}")
    L.check(sum(d["prompt"] for d in okd) == ptok, f"{rid}: prompt token sum")
    L.check(sum(d["completion"] for d in okd) == ctok, f"{rid}: completion token sum")
    lat = [d["latency"] for d in okd]
    L.check(abs(median(lat) - p50) < 0.11, f"{rid}: p50 {median(lat):.2f} vs {p50}")
    L.check(abs(max(lat) - lmax) < 0.06, f"{rid}: max latency")
    L.check(abs(gpu_usd / ok - per_doc_usd) < 2e-6, f"{rid}: $/doc = GPU $ / completed docs")
    L.check(abs(sum(d["schema"] for d in okd) / len(okd) - schema) < 0.011, f"{rid}: schema rate", key=f"{rid}.schema_rate",
            got=f"{sum(d['schema'] for d in okd)}/{len(okd)}", want=schema)
    by = {}
    for d in scored:
        by.setdefault(d["subclass"], []).append(d["overall"])
    strata = R.table(path, "Strata", "subclass")
    for s in strata:
        name = s["subclass"].replace("**", "")
        if name == "total":
            continue
        L.check(name in by and int(fnum(s["n"])) == len(by[name]), f"{rid}: stratum {name} n")
        L.check(abs(sum(by[name]) / len(by[name]) - fnum(s["mean overall"])) < 0.0006, f"{rid}: stratum {name} mean")

    out = {
        "run": rid, "cls": cls, "kind": kind, "n": int(n), "ok": int(ok), "overall": overall, "schema": schema,
        "wall": wall, "p50": p50, "p95": p95, "max": lmax, "tps": tps, "usd_per_doc": per_doc_usd, "gpu_usd": gpu_usd,
        "conc": int(conc), "speedup": speed, "prompt_per_doc": ptok / ok, "compl_per_doc": ctok / ok, "docs": docs,
        # math.fsum: correctly rounded on every Python (3.12's sum() compensates, 3.11's does not)
        "strata": [{"subclass": s, "n": len(v), "mean": math.fsum(v) / len(v)}
                   for s, v in sorted(by.items(), key=lambda kv: -math.fsum(kv[1]) / len(kv[1]))],
    }
    if kind == "cuad":
        out["headline"] = R.cell(f"{k}.cuad_f1", path, "| micro precision / recall / F1 |", 1, 2)
        out["cuad_p"] = R.cell(f"{k}.cuad_p", path, "| micro precision / recall / F1 |", 1, 0)
        out["cuad_r"] = R.cell(f"{k}.cuad_r", path, "| micro precision / recall / F1 |", 1, 1)
        out["scored_docs"] = R.cell(f"{k}.cuad_docs", path, "| docs with CUAD labels (scored) |", 1, 0)
        out["metric"] = "CUAD clause-detection micro F1"
        L.check(out["scored_docs"] == len(scored), f"{rid}: CUAD scored docs {len(scored)} vs {out['scored_docs']}")
    elif kind == "maud":
        q = R.cell(f"{k}.maud_q", path, "| labeled MAUD questions |", 1)
        ans = R.cell(f"{k}.maud_answered", path, "| answered |", 1, 0)
        cor = R.cell(f"{k}.maud_correct", path, "| correct |", 1, 0)
        acc = R.cell(f"{k}.maud_acc", path, "| correct |", 1, 1)
        L.check(abs(cor / q * 100 - acc) < 0.06, f"{rid}: MAUD micro accuracy {cor}/{q} vs {acc}%")
        out.update(headline=cor / q, maud_questions=q, maud_answered=ans, maud_correct=cor,
                   maud_clean=R.rx(f"{k}.maud_clean", path, r"clean subset[^|]*\| (\d+/\d+ = [\d.]+%)", number=False),
                   metric="MAUD per-question micro accuracy")
    else:
        out["headline"] = overall
        out["metric"] = "overall extraction score"
    return out


def sand032(R: Repo) -> dict:
    L = R.L
    runs = {rid: sand032_run(R, rid) for rid in SAND032}
    # program summary table vs run reports
    for label, rid in [("L0 baseline AWQ", "sand032-l0-baseline"), ("L1 + thinking off", "sand032-l1-nothink"), ("L2 + awq_marlin", "sand032-l2-marlin"), ("**L5 frozen**", "sand032-l5-graphs")]:
        s = R.cell(f"summary.ladder.{rid}.score", SUMMARY, f"| {label}", 1)
        L.check(abs(s - runs[rid]["overall"]) < 1e-4, f"summary ladder {rid} score")
        w = R.cell(f"summary.ladder.{rid}.wall", SUMMARY, f"| {label}", 3)
        L.check(abs(w - runs[rid]["wall"]) < 0.06, f"summary ladder {rid} wall")
    ladder = _ladder_rows(R)
    for r in ladder:
        run = runs[f"sand032-{r['rung']}"]
        L.check(abs(r["score"] - run["overall"]) < 1e-4 and abs(r["wall"] - run["wall"]) < 0.06, f"ladder {r['rung']} vs report")
    spend = R.rx("summary.spend", SUMMARY, r"ledger estimate\): \*\*\$([\d.]+) of the \$[\d.]+ cap\*\* at program close")
    cap = R.rx("summary.cap", SUMMARY, r"ledger estimate\): \*\*\$[\d.]+ of the \$([\d.]+) cap\*\*")
    stage5 = R.rx("summary.spend_stage5", SUMMARY, r"ledger stood at \$([\d.]+) after stages 1–5")
    close = R.rx("summary.spend_close", SUMMARY, r"Ledger at close: \$([\d.]+) cumulative")
    L.check(close == spend, f"summary spend header ${spend} vs ledger at close ${close}")
    L.check(stage5 < spend <= cap, f"summary spend ${stage5} → ${spend} within cap ${cap}")
    incident = R.rx("summary.incident_cost", SUMMARY, r"Fleet stopped; cost \$([\d.]+)")
    for rid, row in [("sand032-s3-corr50", "| correspondence | overall extraction"), ("sand032-s3-insurance50", "| insurance_claim |"),
                     ("sand032-s3-corporate50", "| corporate_record |"), ("sand032-s3-contracts50", "| contract |"),
                     ("sand032-s3-merger50", "| merger_agreement |"), ("sand032-s5-merger50-maud", "| merger (MAUD v1 prompt) |")]:
        v = R.cell(f"summary.sweep.{rid}", SUMMARY, row, 2)
        head = runs[rid]["headline"] * (100 if runs[rid]["kind"] == "maud" else 1)
        L.check(abs(v - head) < (0.06 if runs[rid]["kind"] == "maud" else 1e-3), f"summary sweep {rid}: {v} vs {head}")
        usd = R.cell(f"summary.sweep.{rid}.usd", SUMMARY, row, 6)
        L.check(abs(usd - runs[rid]["usd_per_doc"]) < 3e-6, f"summary sweep {rid} $/doc {usd} vs {runs[rid]['usd_per_doc']}",
                key=f"{rid}.summary_usd", got=usd, want=runs[rid]["usd_per_doc"])
    return {"runs": runs, "ladder": ladder, "spend": spend, "spend_stage5": stage5, "cap": cap, "incident": incident}


L4_USD_PER_HOUR = 0.80  # docs/RUN-COST-DERIVATION.md; every SAND-032 GPU $ uses it
REPLICA_LINE = re.compile(
    r"^- replica `([^`]*)`: requests Δ (\d+) \(cumulative \d+\), measured TTFT mean ([\d.]+) s "
    r"\(vLLM histogram, cumulative\), prefix-cache hit ([\d.]+)%, preemptions (\d+)"
    r"(?:, length-capped finishes \d+, KV usage at scrape ([\d.]+)%)?", re.M)
# Setup header rows of every SAND-032 run report (engine, context / quant, engine flags, modal, dataset, draw):
# (field, regex, group, is-number). Values are strings unless marked numeric.
SETUP_ROWS = [
    ("engine_model", r"\| engine \| `([^`]+)`", 1, False),
    ("vllm", r"\| engine \| `[^`]+`, vLLM `([^`]+)`", 1, False),
    ("max_model_len", r"\| context / quant \| `max_model_len=(\d+)`", 1, True),
    ("quant", r"\| context / quant \| [^|]*quant=`([^`]+)`", 1, False),
    ("prefix_caching", r"\| engine flags \| [^|]*prefix_caching=(\w+)", 1, False),
    ("enforce_eager", r"\| engine flags \| [^|]*enforce_eager=(\w+)", 1, False),
    ("kv_cache_dtype", r"\| engine flags \| [^|]*kv_cache_dtype=`([^`]+)`", 1, False),
    ("thinking", r"\| engine flags \| [^|]*thinking=(\w+)", 1, False),
    ("containers_min", r"max/min containers \d/(\d)", 1, True),
    ("dataset", r"\| dataset \| (\S+) `([^`]+)`, split=(\w+), rev `([0-9a-f]+)`, seed (\d+) \|", 1, False),
    ("dataset_config", r"\| dataset \| (\S+) `([^`]+)`, split=(\w+), rev `([0-9a-f]+)`, seed (\d+) \|", 2, False),
    ("dataset_split", r"\| dataset \| (\S+) `([^`]+)`, split=(\w+), rev `([0-9a-f]+)`, seed (\d+) \|", 3, False),
    ("dataset_rev", r"\| dataset \| (\S+) `([^`]+)`, split=(\w+), rev `([0-9a-f]+)`, seed (\d+) \|", 4, False),
    ("seed", r"\| dataset \| (\S+) `([^`]+)`, split=(\w+), rev `([0-9a-f]+)`, seed (\d+) \|", 5, True),
    ("draw_nesting", r"\| draw \| [^|]*\(nested ([^)]+)\)", 1, False),
]
# The S6 sorter report has a one-line engine row and names the dataset in prose; it records no vLLM version,
# max_model_len, engine flags, split or seed.
SETUP_ROWS_S6 = [
    ("engine_model", r"\| engine \| `([^`]+)`", 1, False),
    ("kv_cache_dtype", r"\| engine \| [^|]*kv `([^`]+)`, `([^`]+)`, graphs", 1, False),
    ("quant", r"\| engine \| [^|]*kv `([^`]+)`, `([^`]+)`, graphs", 2, False),
    ("dataset", r"Public HF `([^`]+)` @ `([0-9a-f]+)`", 1, False),
    ("dataset_rev", r"Public HF `([^`]+)` @ `([0-9a-f]+)`", 2, False),
]
SETUP_FIELDS = [f for f, *_ in SETUP_ROWS]
GPU_SPEC = "../deploy/README.md"  # relative to reports/: the deploy doc's GPU table (a spec, not a run record)


def _setup(R: Repo, k: str, path: str, rows) -> dict:
    out = {f: None for f in SETUP_FIELDS}
    for f, pat, g, num in rows:
        v = R.rx(f"{k}.r.{f}", path, pat, group=g, number=num)
        out[f] = int(v) if num else v
    return out


def _started(replica_id: str):
    """A replica id is the vLLM process start time (epoch seconds) in every SAND-032 report."""
    try:
        return float(replica_id)
    except ValueError:
        return None


def sand032_fleet(R: Repo, runs: dict) -> dict:
    """Every SAND-032 serving export (``serving/SAND-32/sand032-*.serving.json``) against its run report.

    Feeds the GPU economics report: busy-window and billed GPU $, tokens, throughput, client-slot
    occupancy, boot, and the per-replica vLLM ``/metrics`` split. Busy-window GPU $ is
    wall × replicas × L4 rate; billed (a lower bound on the Modal bill) adds the run's cold boot.
    """
    L = R.L
    reports = {
        p.name[: -len("-REPORT.md")].lower(): p.relative_to(R.base).as_posix()
        for pattern in ("SAND-32/*/SAND032-*-REPORT.md", "serving/SAND-32/SAND032-*-REPORT.md")
        for p in sorted(R.base.glob(pattern))
    }
    out = {}
    for sp in sorted((R.base / "serving" / "SAND-32").glob("sand032-*.serving.json")):
        rid = sp.name[: -len(".serving.json")]
        jp, k, path = sp.relative_to(R.base).as_posix(), f"fleet.{rid}", reports.get(rid)
        if path is None:
            raise SourceError(f"{rid}: serving export without a run report")
        doc = R.jload(jp)
        J = {f: R.jkey(f"{k}.{f}", jp, f, doc=doc) for f in (
            "replicas", "concurrency", "n", "wall_seconds", "cold_boot_seconds", "gpu_seconds", "prompt_tokens",
            "completion_tokens", "tokens_per_second", "slot_utilization", "latency_sum_seconds",
            "estimated_gpu_cost_usd", "idle_estimated_usd", "latency_p50_seconds", "latency_p95_seconds")}
        rep, wall = int(J["replicas"]), J["wall_seconds"]
        L.check(abs(J["gpu_seconds"] - (wall + J["cold_boot_seconds"])) < 0.002, f"{rid}: gpu_seconds = wall + cold boot")
        L.check(abs(J["estimated_gpu_cost_usd"] - J["gpu_seconds"] * rep * L4_USD_PER_HOUR / 3600) < 1.5e-6,
                f"{rid}: billed GPU $ = gpu_seconds × replicas × L4 rate")
        L.check(abs(J["slot_utilization"] - J["latency_sum_seconds"] / J["concurrency"] / wall) < 1e-4,
                f"{rid}: slot utilization = Σ latency / concurrency / wall")
        busy = wall * rep * L4_USD_PER_HOUR / 3600
        rec = {"run": rid, "report": path, "replicas": rep, "conc": int(J["concurrency"]), "n": int(J["n"]),
               "wall": wall, "cold_boot": J["cold_boot_seconds"], "gpu_seconds": J["gpu_seconds"],
               "prompt_tokens": int(J["prompt_tokens"]), "completion_tokens": int(J["completion_tokens"]),
               "tps": J["tokens_per_second"], "slot": J["slot_utilization"], "lat_sum": J["latency_sum_seconds"],
               "billed_usd": J["estimated_gpu_cost_usd"], "idle_usd": J["idle_estimated_usd"], "busy_usd": busy,
               "p50": J["latency_p50_seconds"], "p95": J["latency_p95_seconds"],
               "model": R.jkey(f"{k}.model", jp, "model", doc=doc), "gpu": R.jkey(f"{k}.gpu", jp, "gpu", doc=doc)}
        s6 = rid == "sand032-s6-sorter1000"
        rec.update(_setup(R, k, path, SETUP_ROWS_S6 if s6 else SETUP_ROWS))
        L.check(rec["engine_model"] == rec["model"], f"{rid}: report engine model {rec['engine_model']} vs export {rec['model']}")
        if s6:
            ok = R.rx(f"{k}.ok", path, r"\| docs ok / total \| (\d+) / \d+ \|")
            L.check(abs(R.cell(f"{k}.r.wall", path, "| wall s |", 1) - wall) < 0.05, f"{rid}: report wall vs export")
            L.check(abs(R.cell(f"{k}.r.tps", path, "| tok/s |", 1) - J["tokens_per_second"]) < 0.6, f"{rid}: report tok/s")
            L.check(R.rx(f"{k}.r.replicas", path, r"(\d)× L4") == rep, f"{rid}: report replicas")
            L.check(R.cell(f"{k}.r.conc", path, "| concurrency |", 1) == J["concurrency"], f"{rid}: report concurrency")
            usd = R.cell(f"{k}.r.usd", path, "| GPU $/doc |", 1)
            L.check(abs(usd - J["estimated_gpu_cost_usd"] / ok) < 1e-6, f"{rid}: report $/doc is the billed basis")
            L.check(abs(usd - busy / ok) < 1e-6, f"{rid}: report $/doc on the busy-window basis",
                    key=f"{rid}.usd_basis", got=f"{usd:.6f}", want=f"{busy / ok:.6f}", boot=J["cold_boot_seconds"])
            rec.update(ok=int(ok), seqs=int(R.rx(f"{k}.r.seqs", path, r"seqs (\d+)")), max_inputs=None,
                       boot_ready=None, replica_split=[], scaledown=None, score=None)
            out[rid] = rec
            continue
        ok = R.rx(f"{k}.ok", path, r"\| docs ok / total \| \*\*(\d+) / \d+\*\*")
        r_wall = R.cell(f"{k}.r.wall", path, "| wall (runner busy interval) |", 1)
        r_pt = R.cell(f"{k}.r.prompt_tokens", path, "| prompt / completion tokens |", 1, 0)
        r_ct = R.cell(f"{k}.r.completion_tokens", path, "| prompt / completion tokens |", 1, 1)
        r_tps = R.cell(f"{k}.r.tps", path, "| throughput |", 1)
        r_conc = R.cell(f"{k}.r.conc", path, "| concurrency |", 1)
        pat = r"\| GPU \$ over busy wall \(×(\d) L4 @ \$([\d.]+)/h\) \| ([\d.]+) \|"
        r_rep, r_rate, r_busy = (R.rx(f"{k}.r.gpu.{g}", path, pat, group=g) for g in (1, 2, 3))
        L.check(abs(r_wall - wall) < 0.0006, f"{rid}: report wall {r_wall} vs export {wall}")
        L.check(r_pt == J["prompt_tokens"] and r_ct == J["completion_tokens"], f"{rid}: report tokens vs export")
        L.check(abs(r_tps - J["tokens_per_second"]) < 0.06, f"{rid}: report tok/s vs export")
        L.check(r_conc == J["concurrency"] and r_rep == rep, f"{rid}: report concurrency/replicas vs export")
        L.check(r_rate == L4_USD_PER_HOUR, f"{rid}: L4 rate {r_rate}")
        L.check(abs(r_busy - busy) < 1.5e-6, f"{rid}: busy GPU $ {r_busy} = wall × replicas × rate")
        L.check(R.rx(f"{k}.r.containers", path, r"max/min containers (\d)/\d") == rep, f"{rid}: Modal containers = replicas")
        if rid in runs:
            L.check(runs[rid]["gpu_usd"] == r_busy and runs[rid]["wall"] == r_wall, f"{rid}: fleet vs run extract")
        split = []
        for m in REPLICA_LINE.finditer(R.text(path)):
            split.append(L.record(f"{k}.replica.{m.group(1)}", {
                "requests": int(m.group(2)), "ttft": float(m.group(3)), "prefix": float(m.group(4)) / 100,
                "preempt": int(m.group(5)), "started": _started(m.group(1)),
                "kv_scrape": float(m.group(6)) / 100 if m.group(6) is not None else None}, R.name, R.sha, R.rel(path), m.group(0)))
        L.check(len(split) == rep, f"{rid}: {len(split)} replicas observed vs {rep}")
        L.check(sum(s["requests"] for s in split) == J["n"], f"{rid}: replica requests sum to n")
        boot = re.search(r"deploy→engine-ready (\d+) s", R.text(path))
        rec.update(ok=int(ok), seqs=int(R.rx(f"{k}.r.seqs", path, r"max_num_seqs=(\d+)")),
                   max_inputs=int(R.rx(f"{k}.r.max_inputs", path, r"max_inputs=(\d+)")),
                   boot_ready=float(boot.group(1)) if boot else None, replica_split=split,
                   scaledown=R.rx(f"{k}.r.scaledown", path, r"max/min containers \d/\d, scaledown (\d+) s"),
                   score=R.rx(f"{k}.r.score", path, r"\| \*\*overall_extraction_score\*\* \| \*\*([\d.]+)\*\*"))
        if rid in runs:
            L.check(abs(rec["score"] - runs[rid]["overall"]) < 1e-4, f"{rid}: fleet score vs run extract")
        out[rid] = rec
    # Provenance-only figures the GPU report quotes (read back from ``provenance`` by key):
    # the program summary's saturation finding and stage 6–9 date, and the deploy doc's L4 memory spec.
    R.rx("fleet.summary.saturation", SUMMARY, r"(One L4 saturates at around \d+ concurrent sequences for these prompts)\.",
         number=False)
    R.rx("fleet.summary.stages69_date", SUMMARY, r"## 7\. Stages 6–9 \((\d{4}-\d{2}-\d{2})\)", number=False)
    gpu = {r["gpu"] for r in out.values()}
    L.check(len(gpu) == 1, f"SAND-032 exports disagree on the GPU: {gpu}")
    spec_gpu = R.rx("fleet.gpu_spec.gpu", GPU_SPEC, r"\| `MODAL_VLLM_GPU` \| `([^`]+)` \| [\d.]+ GB VRAM \|", number=False)
    L.check({spec_gpu} == gpu, f"deploy spec GPU {spec_gpu} vs exports {gpu}")
    R.rx("fleet.gpu_spec.memory", GPU_SPEC, r"\| `MODAL_VLLM_GPU` \| `[^`]+` \| ([\d.]+ GB) VRAM \|", number=False)
    return out


def _ladder_rows(R: Repo) -> list[dict]:
    lines = R.text(LADDER).splitlines()
    hdr = next(i for i, ln in enumerate(lines) if ln.startswith("| rung |"))
    header = [c.strip() for c in lines[hdr].strip().strip("|").split("|")]
    out = []
    for ln in lines[hdr + 2:]:
        if not ln.startswith("|"):
            break
        c = dict(zip(header, [x.strip() for x in ln.strip().strip("|").split("|")]))
        rung = c["rung"]
        R.L.record(f"ladder.{rung}", ln, R.name, R.sha, R.rel(LADDER), ln)
        out.append({
            "rung": rung, "change": c["change"], "score": fnum(c["score"]), "delta": fnum(c["Δ vs L0 (paired)"]),
            "schema": fnum(c["schema"]), "wall": fnum(c["wall s"]), "p50": fnum(c["p50 s"]), "p95": fnum(c["p95 s"]),
            "tps": fnum(c["tok/s"]), "ttft": fnum(c["TTFT s"]), "prefix": fnum(c["prefix %"]),
            "boot": fnum(c["boot→ready s"]), "usd": fnum(c["$/doc busy"]), "gate": c["gate"].replace("**", ""),
        })
    return out


# ------------------------------------------------------------ eval-environment
API_MODELS = {
    "qwen3-8b": "Qwen3-8B",
    "granite-4.2-8b": "Granite-4.2-8B",
    "deepseek-v4.1-flash": "DeepSeek-V4.1-Flash",
}
API_TASKS = ["correspondence", "insurance claims", "contracts", "merger agreements", "corporate records"]
CLS_REPORTS = [
    "api-comparisons/qwen3-8b/classification/RUN-20-FULL-QWEN3-8B-REPORT.md",
    "api-comparisons/granite-4.2-8b/classification/RUN-20-FULL-GRANITE-4.2-8B-REPORT.md",
    "api-comparisons/granite-4.2-8b/classification/RUN-100-FULL-GRANITE-4.2-8B-REPORT.md",
    "api-comparisons/qwen3.7-flash/classification/RUN-100-FULL-QWEN3.7-FLASH-REPORT.md",
    "api-comparisons/deepseek-v4.1-flash/classification/RUN-100-FULL-DEEPSEEK-V4.1-FLASH-REPORT.md",
]


def eval_env(R: Repo) -> dict:
    L = R.L
    # The log also carries non-run records (prompt promotions: ``record_kind``,
    # ``run_a``/``run_b``) — only eval runs have a ``run_id``.
    log = {r["run_id"]: r for r in R.jload("experiment_log.jsonl") if "run_id" in r}

    def run_fields(key, rid):
        r = log[rid]
        perf = r.get("performance") or {}
        doc = r
        rec = {
            "run": rid, "model": R.jkey(f"{key}.model", "experiment_log.jsonl", "model", doc=doc),
            "n": R.jkey(f"{key}.n", "experiment_log.jsonl", "metrics", "n", doc=doc),
            "errors": R.jkey(f"{key}.errors", "experiment_log.jsonl", "metrics", "errors", doc=doc),
            "wall": R.jkey(f"{key}.wall", "experiment_log.jsonl", "duration_s", doc=doc),
            "p95_ms": R.jkey(f"{key}.p95", "experiment_log.jsonl", "performance", "latency_ms_p95", doc=doc),
            "cost": R.jkey(f"{key}.cost_est", "experiment_log.jsonl", "performance", "cost_usd_est_total", doc=doc),
            "prompt_tokens": perf.get("tokens_prompt_total"), "completion_tokens": perf.get("tokens_completion_total"),
            "revision": doc["dataset"].get("revision", "")[:8], "split": doc["dataset"].get("split"),
            "prompt_lineage": doc.get("prompt_lineage"),
        }
        L.check(rec["prompt_lineage"] == "frozen", f"{rid}: prompt lineage")
        return rec

    ext = {}
    for mdir, label in API_MODELS.items():
        path = f"api-comparisons/{mdir}/README.md"
        for task in API_TASKS:
            row = f"| {task} |"
            rid = R.rx(f"api.{mdir}.{task}.run", path, re.escape(row) + r" `([^`]+)`", number=False)
            score = R.cell(f"api.{mdir}.{task}.score", path, row, 2)
            cost = R.cell(f"api.{mdir}.{task}.readme_cost", path, row, 5)
            rec = run_fields(f"api.{mdir}.{task}", rid)
            s_log = R.jkey(f"api.{mdir}.{task}.score_log", "experiment_log.jsonl", "metrics", "overall_score", doc=log[rid])
            L.check(abs(s_log - score) < 1e-4, f"{rid}: README score vs log")
            L.check(abs((rec["cost"] or 0) - cost) < 1e-5, f"{rid}: README cost vs log")
            rec.update(score=score, task=task, family=label)
            ext.setdefault(task, {})[mdir] = rec
    cls = []
    for path in CLS_REPORTS:
        rid = R.rx(f"cls.{path}.run", path, r"\| run_id \| `([^`]+)`", number=False)
        rec = run_fields(f"cls.{rid}", rid)
        rec["class_acc"] = R.jkey(f"cls.{rid}.class", "experiment_log.jsonl", "metrics", "class_accuracy", doc=log[rid])
        rec["subclass_acc"] = R.jkey(f"cls.{rid}.subclass", "experiment_log.jsonl", "metrics", "subclass_accuracy", doc=log[rid])
        rec["report"] = path
        cls.append(rec)
    master = "api-comparisons/API-LEG-MASTER-REPORT.md"
    L.check(ext["merger agreements"]["qwen3-8b"]["model"] == "qwen/qwen3-8b", "qwen3-8b merger leg model", key="api.qwen_merger_model",
            model=ext["merger agreements"]["qwen3-8b"]["model"])
    superseded = R.rx("api.granite_corr_superseded", master, r"`RUN-20-CORRESPONDENCE-GRANITE-4.2-8B-REPORT.md`: \*\*final\*\* `([^`]+)`; superseded `[^`]+`, `(20260927T044805Z-eval-correspondence)`", number=False)
    ds = next(c for c in cls if "deepseek" in c["model"])
    L.check(ds["wall"] >= ds["p95_ms"] / 1000, "deepseek classification wall vs p95", key="api.deepseek_cls_wall",
            wall=ds["wall"], p95=ds["p95_ms"] / 1000)
    return {"tasks": ext, "classification": cls, "granite_corr_final": superseded}


# Route comparison: the production model's n = 50 API legs, one per specialist task.
ROUTE50 = {
    "correspondence": "correspondence/RUN-50-CORRESPONDENCE-QWEN3.7-FLASH-REPORT.md",
    "insurance claims": "insurance_claims/RUN-50-INSURANCE_CLAIM-QWEN3.7-FLASH-REPORT.md",
    "corporate records": "corporate_records/RUN-50-CORPORATE_RECORD-QWEN3.7-FLASH-REPORT.md",
    "contracts": "contracts/RUN-50-CONTRACT-QWEN3.7-FLASH-REPORT.md",
    "merger agreements": "merger_agreement/RUN-50-MERGER_AGREEMENT-QWEN3.7-FLASH-REPORT.md",
}


def eval_env_route50(R: Repo) -> dict:
    """``qwen/qwen3.7-flash`` n = 50 legs: score and estimated cost from the log, cross-checked against the report."""
    L = R.L
    log = {r["run_id"]: r for r in R.jload("experiment_log.jsonl") if "run_id" in r}
    out = {}
    for task, rel in ROUTE50.items():
        path = f"api-comparisons/qwen3.7-flash/{rel}"
        key = f"route50.{task}"
        rid = R.rx(f"{key}.run", path, r"\| run_id \| `([^`]+)`", number=False)
        doc = log[rid]
        rec = {
            "run": rid, "task": task, "family": "Qwen3.7-Flash",
            "model": R.jkey(f"{key}.model", "experiment_log.jsonl", "model", doc=doc),
            "n": R.jkey(f"{key}.n", "experiment_log.jsonl", "metrics", "n", doc=doc),
            "errors": R.jkey(f"{key}.errors", "experiment_log.jsonl", "metrics", "errors", doc=doc),
            "score": R.jkey(f"{key}.score", "experiment_log.jsonl", "metrics", "overall_score", doc=doc),
            "cost": R.jkey(f"{key}.cost_est", "experiment_log.jsonl", "performance", "cost_usd_est_total", doc=doc),
            "wall": R.jkey(f"{key}.wall", "experiment_log.jsonl", "duration_s", doc=doc),
            "p95_ms": R.jkey(f"{key}.p95", "experiment_log.jsonl", "performance", "latency_ms_p95", doc=doc),
            "prompt_tokens": R.jkey(f"{key}.prompt_tokens", "experiment_log.jsonl", "performance", "tokens_prompt_total", doc=doc),
            "completion_tokens": R.jkey(f"{key}.completion_tokens", "experiment_log.jsonl", "performance",
                                        "tokens_completion_total", doc=doc),
            "revision": doc["dataset"].get("revision", "")[:8], "split": doc["dataset"].get("split"),
            "prompt_lineage": doc.get("prompt_lineage"),
        }
        r_pt = R.rx(f"{key}.report_prompt_tokens", path, r"\| prompt / completion / total tokens \| (\d+) / \d+ / \d+ \|")
        r_ct = R.rx(f"{key}.report_completion_tokens", path, r"\| prompt / completion / total tokens \| \d+ / (\d+) / \d+ \|")
        L.check(r_pt == rec["prompt_tokens"] and r_ct == rec["completion_tokens"], f"{rid}: report tokens vs log")
        rep = R.rx(f"{key}.report_score", path, r"\| overall_score \| ([0-9.]+) \|")
        L.check(abs(rep - rec["score"]) < 1e-4, f"{rid}: report overall vs log")
        L.check(rec["model"] == "qwen/qwen3.7-flash", f"{rid}: model")
        out[task] = rec
    return out


def collapse_signal(rows) -> dict:
    """Per class, over (class, true subclass, predicted subclass, correct) rows whose class was right: subclass accuracy,
    the share of predictions on the single most common predicted subclass, and the most common true subclass's share."""
    from collections import Counter

    out = {}
    for c in CLASSES:
        sel = [r for r in rows if r[0] == c]
        if not sel:
            continue
        pred, true = Counter(r[2] for r in sel).most_common(1)[0], Counter(r[1] for r in sel).most_common(1)[0]
        out[c] = {"n": len(sel), "correct": sum(bool(r[3]) for r in sel), "top_pred": list(pred), "top_true": list(true)}
    return out


SORTER_BINS = [0.0, 0.5, 0.8, 0.9, 0.95, 0.99, 1.0001]
SORTER_BIN_MIN = 5


def sorter_cases(R: Repo, cls: list[dict]) -> dict:
    """Case-level LLM sorter views (n = 100 runs) from the eval-environment viewer snapshot: confusion matrix,
    collapse signal and stated-confidence reliability. Each run's class accuracy is re-derived from its cases
    and checked against the experiment log."""
    L = R.L
    path = "web/data/snapshot.json"
    snap = R.jload(path)
    out = {}
    for rec in cls:
        if rec["n"] != 100:
            continue
        cases = snap["cases"][rec["run"]]
        L.check(len(cases) == rec["n"], f"{rec['run']}: snapshot case rows")
        sc = [c["scores"] for c in cases]
        acc = sum(bool(s.get("class_correct")) for s in sc) / len(sc)
        L.check(abs(acc - rec["class_acc"]) < 1e-9, f"{rec['run']}: class accuracy from cases")
        conf: dict[str, int] = {}
        for s in sc:
            k = f"{s['expected_doc_class']}->{s.get('predicted_doc_class') or 'unknown'}"
            conf[k] = conf.get(k, 0) + 1
        pts = [(float(c["prediction"]["confidence"]), bool(c["scores"].get("class_correct"))) for c in cases
               if isinstance((c.get("prediction") or {}).get("confidence"), (int, float))]
        bins = []
        for lo, hi in zip(SORTER_BINS[:-1], SORTER_BINS[1:]):
            b = [p for p in pts if lo <= p[0] < hi]
            if len(b) >= SORTER_BIN_MIN:
                bins.append({"conf": round(sum(p[0] for p in b) / len(b), 4), "acc": round(sum(p[1] for p in b) / len(b), 4), "n": len(b)})
        nb = sum(b["n"] for b in bins)
        R.L.record(f"sorter.{rec['run']}.cases", len(cases), R.name, R.sha, R.rel(path), f"cases[{rec['run']}]: {len(cases)} rows")
        out[rec["model"]] = {
            "run": rec["run"], "n": len(cases), "confusion": conf, "bins": bins, "n_conf": len(pts),
            "ece": round(sum(b["n"] * abs(b["acc"] - b["conf"]) for b in bins) / nb, 4) if nb else None,
            "collapse": collapse_signal([(s["expected_doc_class"], s.get("expected_subclass"), s.get("predicted_subclass"),
                                          s.get("subclass_correct")) for s in sc if s.get("class_correct")]),
        }
    return out


# ------------------------------------------------------------------ mailroom-ml
MB_EVALS = {
    "armB": "reports/eval_m9a-local-20260927-014429.json",
    "armA": "reports/eval_m9a-local-gpu1-armA-1ep-20260927-025236.json",
    "run3": "reports/eval_run3_20260921.json",
    "plus": "reports/eval_m9a-local-20260927-014429-heldout-plus.json",
}
CLASSES = ["insurance_claim", "correspondence", "contract", "corporate_record", "merger_agreement"]


def per_class(conf: dict) -> dict:
    out = {}
    for c in CLASSES:
        tot = sum(v for k, v in conf.items() if k.startswith(c + "->"))
        out[c] = {"correct": conf.get(f"{c}->{c}", 0), "n": tot}
    return out


def mailroom_ml(R: Repo) -> dict:
    L = R.L
    ev = {}
    for tag, path in MB_EVALS.items():
        d = R.jload(path)
        acc = R.jkey(f"mb.{tag}.acc", path, "doc_type_accuracy", doc=d)
        conf = R.jkey(f"mb.{tag}.confusion", path, "per_stratum_confusion", doc=d)
        pc = per_class(conf)
        n = R.jkey(f"mb.{tag}.n", path, "n_docs", doc=d)
        L.check(sum(v["n"] for v in pc.values()) == n, f"{tag}: confusion total")
        L.check(abs(sum(v["correct"] for v in pc.values()) / n - acc) < 1e-4, f"{tag}: accuracy from confusion")
        rec = {"acc": acc, "subclass": R.jkey(f"mb.{tag}.subclass", path, "subclass_accuracy_conditional", doc=d),
               "n": n, "per_class": pc, "confusion": conf, "sha": d.get("artifact_sha", "")[:12],
               "window_ece": R.jkey(f"mb.{tag}.window_ece", path, "window_calibration", "ece", doc=d)}
        if d.get("head_ece"):
            rec["head_ece"] = R.jkey(f"mb.{tag}.head_ece", path, "head_ece", doc=d)
        if "per_head" in d:
            rec["macro_f1"] = {h: v.get("macro_f1") for h, v in d["per_head"].items()}
        if "fast_path_rate" in d:
            rec["fast_path"] = R.jkey(f"mb.{tag}.fast_path", path, "fast_path_rate", doc=d)
        if "ood" in d:
            rec["ood"] = R.jkey(f"mb.{tag}.ood", path, "ood", "rate", doc=d)
        sr = d.get("selective_risk") or {}
        if sr.get("rows"):
            pick = sr.get("recommended_threshold")
            rec["risk"] = [[r["threshold"], r["coverage"], r["accuracy"], r["n"]] for r in sr["rows"]]
            rec["pick"] = R.jkey(f"mb.{tag}.pick", path, "selective_risk", "recommended_threshold", doc=d)
            row = next((r for r in sr["rows"] if pick is not None and abs(r["threshold"] - pick) < 1e-9), None)
            if row:
                L.check(row["n"] == sr.get("n_at_pick"), f"{tag}: pick row n")
                rec["pick_cov"], rec["pick_acc"], rec["windows"] = row["coverage"], row["accuracy"], round(row["n"] / row["coverage"])
                L.check(abs(sr["coverage"] - row["coverage"]) < 1e-6, f"{tag}: top-level coverage", key=f"mb.{tag}.coverage_field",
                        top=round(sr["coverage"], 4), row=round(row["coverage"], 4), last=round(sr["rows"][-1]["coverage"], 4), pick=pick)
        gates = d.get("recorded_gates") or {}
        rec["gates"] = {g: {"actual": v["actual"], "threshold": v["threshold"], "met": v["met"]} for g, v in gates.items()}
        cohorts = d.get("cohorts") or {}
        rec["cohorts"] = {c: {"acc": v["doc_type_accuracy"], "n": v["n_docs"]} for c, v in cohorts.items()}
        if tag in ("armA", "armB"):
            rec["eda"] = mb_eda(L, tag, path, d, rec)
        ev[tag] = rec
        if tag == "plus":
            base = R.jload(MB_EVALS["armB"])
            canon = {r["filename"]: r for r in base["per_doc"]}
            overlap = [r for r in d["per_doc"] if r["filename"] in canon]
            rec["overlap_n"] = len(overlap)
            rec["overlap_correct_plus"] = sum(bool(r["dt_correct"]) for r in overlap)
            rec["overlap_correct_base"] = sum(bool(canon[r["filename"]]["dt_correct"]) for r in overlap)
            L.check(rec["overlap_correct_plus"] == rec["overlap_correct_base"], "held-out-plus vs canonical on shared docs",
                    key="mb.plus_invalid", n=len(overlap), plus=rec["overlap_correct_plus"], base=rec["overlap_correct_base"],
                    acc=acc)
    cmp = "reports/M9a-COMPARE-ArmA-vs-ArmB-20260927.md"
    L.check(abs(R.cell("mb.cmp.armB", cmp, "| doc_type_accuracy |", 1) - ev["armB"]["acc"]) < 1e-4, "M9a compare arm B")
    L.check(abs(R.cell("mb.cmp.armA", cmp, "| doc_type_accuracy |", 2) - ev["armA"]["acc"]) < 1e-4, "M9a compare arm A")
    return ev


def eval_env_modernbert(R: Repo) -> dict:
    path = "modernbert/held-out-test/eval_full_test_20260927.json"
    d = R.jload(path)
    rec = {"acc": R.jkey("mb.run3_reeval.acc", path, "doc_type_accuracy", doc=d),
           "sha": R.jkey("mb.run3_reeval.sha", path, "artifact_sha", doc=d)[:12],
           "subclass": R.jkey("mb.run3_reeval.subclass", path, "subclass_accuracy_conditional", doc=d)}
    cmp = "modernbert/comparisons/sorter-vs-modernbert-full-test-323.json"
    c = R.jload(cmp)
    rec["sorter"] = {
        "sorter_acc": R.jkey("mb.sorter.acc", cmp, "sorter_api_qwen3_8b", "scores", "accuracy", doc=c),
        "sorter_usd": R.jkey("mb.sorter.usd", cmp, "sorter_api_qwen3_8b", "cost_per_document", doc=c),
        "sorter_lat": R.jkey("mb.sorter.lat", cmp, "sorter_api_qwen3_8b", "e2e_latency_seconds", doc=c),
        "mb_acc": R.jkey("mb.sorter.mb_acc", cmp, "modernbert", "scores", "accuracy", doc=c),
        "mb_usd": R.jkey("mb.sorter.mb_usd", cmp, "modernbert", "cost_per_document", doc=c),
        "mb_lat": R.jkey("mb.sorter.mb_lat", cmp, "modernbert", "e2e_latency_seconds", doc=c),
        "note": c["sorter_api_qwen3_8b"].get("accuracy_source", ""),
    }
    return rec


def mb_eda(L: Ledger, tag: str, path: str, d: dict, rec: dict) -> dict:
    """Per-document EDA + surrogate ALE for a ModernBERT eval (cross-checked against its aggregates)."""
    import math
    from collections import Counter

    import ale

    pdoc = d["per_doc"]
    n = len(pdoc)
    L.check(n == rec["n"], f"{tag}: per_doc rows")
    L.check(abs(sum(r["dt_correct"] for r in pdoc) / n - rec["acc"]) < 1e-4, f"{tag}: per_doc accuracy")

    def grp(pred):
        rows = [r for r in pdoc if pred(r)]
        return {"n": len(rows), "correct": sum(bool(r["dt_correct"]) for r in rows)}

    fp = grp(lambda r: r["fast_path"])
    if "fast_path" in rec:
        L.check(abs(fp["n"] / n - rec["fast_path"]) < 1e-3, f"{tag}: fast-path count vs rate")
    ood = grp(lambda r: r["ood_flag"])
    if "ood" in rec:
        L.check(abs(ood["n"] / n - rec["ood"]) < 1e-3, f"{tag}: OOD count vs rate")
    buckets = [("1 window", 1, 1), ("2–3", 2, 3), ("4–8", 4, 8), ("9+", 9, 99)]
    sub = {}
    for c in CLASSES:
        rows = [r for r in pdoc if r["gt_doc_type"] == c and r["dt_correct"]]
        sub[c] = {"n": len(rows), "correct": sum(bool(r["sc_correct"]) for r in rows)}
    con = [r for r in pdoc if r["gt_doc_type"] == "contract" and r["dt_correct"]]
    pred_c, true_c = Counter(r["pred_subclass"] for r in con), Counter(r["gt_subclass"] for r in con)
    rows = [{"cls": r["gt_doc_type"], "y": 1.0 if r["dt_correct"] else 0.0, "lw": math.log2(r["n_windows"]),
             "ood": 1.0 if r["ood_flag"] else 0.0} for r in pdoc]
    return {
        "fast": fp, "slow": grp(lambda r: not r["fast_path"]), "ood": ood, "in_dist": grp(lambda r: not r["ood_flag"]),
        "windows": [{"label": lab, **grp(lambda r, a=a, b=b: a <= r["n_windows"] <= b)} for lab, a, b in buckets],
        "subclass": sub, "contract_pred": pred_c.most_common(8), "contract_true": true_c.most_common(8), "contract_n": len(con),
        "collapse": collapse_signal([(r["gt_doc_type"], r["gt_subclass"], r["pred_subclass"], r["sc_correct"])
                                     for r in pdoc if r["dt_correct"]]),
        "ale_windows": ale.ale(rows, "y", ["lw", "ood"], "lw", kind="logit", boot=200),
    }
