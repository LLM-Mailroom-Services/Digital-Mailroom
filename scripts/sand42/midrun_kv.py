#!/usr/bin/env python3
"""Mid-run vLLM /metrics — sample, then fold into the run cards.

WHY THIS EXISTS
---------------
The cards' KV/queue readings come from ``sandbox run scrape-metrics --label before|after``,
which fire at a run's two DRAINED edges. ``vllm:kv_cache_usage_perc`` gauges the live
sequences in a cache vLLM pre-allocates at startup, so at either edge it is 0 by
construction — every one of the 58 preserved readings in the SAND-042 tree is 0.0, and a
re-run under the same two-edge design reproduces 0.0. A mid-run sample is the only real
source, and re-running cells to get one is not required: this samples the LIVE fleet.

    .venv/bin/python scripts/sand42/midrun_kv.py sample --cell 2l4-c32 [--gap 30]
    .venv/bin/python scripts/sand42/midrun_kv.py fold   --cell 2l4-c32

``sample``  polls the root ``/metrics`` (unauthenticated; one GET reaches ONE replica, so
            it takes several attempts per tick and groups by process_start_time_seconds,
            exactly as the CLI scraper does) and appends to
            ``data/runtime/<cell>.midrun.jsonl``. It self-terminates after 5 empty ticks.
``fold``    attributes every sample to the run whose beacon window
            (``~/.mailroom/jobs/<run_id>.json``: started_at..finished_at) contains it and
            writes ``data/runtime/runs/<run_id>/vllm_metrics_mid.json``, which the
            cards read. Same artifact name/shape a live
            ``sandbox run scrape-metrics --label mid`` writes, so either producer is
            readable by the same code. Nothing is fabricated: a run with no samples gets
            no file.
"""
from __future__ import annotations

import json
import pathlib
import re
import statistics
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))
RUNS = REPO / "data" / "runtime" / "runs"
JOBS = pathlib.Path.home() / ".mailroom" / "jobs"
def default_url() -> str:
    """The /metrics URL for the config's engine, resolved the way the CLI scraper does.

    Reusing ``spec.engine_base_url`` is what keeps this working for an app-scoped fleet
    (``sandbox-vllm-a``) and for a tunneled/local base, instead of hardcoding one
    modal.run hostname.
    """
    from mailroom_sandbox.job import spec as spec_mod

    base = spec_mod.engine_base_url(spec_mod.load_run_spec(config_path())).rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return f"{base}/metrics"


def config_path() -> str:
    return _CONFIG[0]


_CONFIG = ["config/runs/sand42-50-correspondence-specialist-awq-2l4-c32.yaml"]
DEFAULT_URL = "https://exios66--sandbox-vllm-serve.modal.run/metrics"
ATTEMPTS = 8          # enough to hit both replicas through Modal's round-robin
WANT = (
    "vllm:kv_cache_usage_perc",
    "vllm:num_requests_running",
    "vllm:num_requests_waiting",
    "vllm:num_preemptions_total",
    "vllm:gpu_cache_usage_perc",
)


def _key(cell: str) -> str:
    return cell.replace("l4-c", "L4-c").upper().replace("L4-C", "L4-c")


def out_path(cell: str) -> pathlib.Path:
    return REPO / "data" / "runtime" / f"{cell}.midrun.jsonl"


# ── sample ────────────────────────────────────────────────────────────────────


def tick(url: str) -> dict[str, dict[str, float]]:
    import httpx

    reps: dict[str, dict[str, float]] = {}
    for _ in range(ATTEMPTS):
        try:
            text = httpx.get(url, timeout=10.0).text
        except Exception:  # noqa: BLE001 — the fleet may be gone mid-tick
            continue
        key, vals = None, {}
        for line in text.splitlines():
            m = re.match(r"^process_start_time_seconds(?:\{[^}]*\})?\s+(\S+)$", line)
            if m:
                key = m.group(1)
                continue
            m = re.match(r"^([a-zA-Z0-9_:]+)(?:\{[^}]*\})?\s+(\S+)$", line)
            if not m or m.group(1) not in WANT:
                continue
            try:
                vals[m.group(1)] = float(m.group(2))
            except ValueError:
                continue
        if key and vals:
            vals["t"] = time.time()
            reps[key] = vals          # latest scrape wins, as the CLI scraper does
        time.sleep(0.25)
    return reps


def sample(cell: str, gap: int, url: str) -> int:
    out = out_path(cell)
    print(f"[midrun] sampling {url} every {gap}s -> {out}", flush=True)
    n = empty = 0
    while True:
        reps = tick(url)
        if not reps:
            empty += 1
            if empty >= 5:
                print("[midrun] 5 empty ticks — fleet is down, stopping")
                return 0
            time.sleep(gap)
            continue
        empty = 0
        with out.open("a") as fh:
            for rid, vals in reps.items():
                fh.write(json.dumps({"replica": rid, **vals}) + "\n")
        n += 1
        kv = max(v.get("vllm:kv_cache_usage_perc", 0.0) for v in reps.values())
        run = max(v.get("vllm:num_requests_running", 0.0) for v in reps.values())
        wait = max(v.get("vllm:num_requests_waiting", 0.0) for v in reps.values())
        print(f"[midrun] t={n:>3} replicas={len(reps)} kv_max={kv:.3f} "
              f"running_max={run:.0f} waiting_max={wait:.0f}", flush=True)
        time.sleep(gap)


# ── fold ──────────────────────────────────────────────────────────────────────


def _window(run_id: str) -> tuple[float, float] | None:
    p = JOBS / f"{run_id}.json"
    if not p.is_file():
        return None
    d = json.loads(p.read_text())
    start = d.get("started_at")
    end = d.get("finished_at") or time.time()
    if not start:
        return None
    return float(start), float(end)


def _stats(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {}
    return {
        "min": round(min(vals), 4),
        "median": round(statistics.median(vals), 4),
        "max": round(max(vals), 4),
        "n": len(vals),
    }


def fold(cell: str) -> int:
    src = out_path(cell)
    if not src.is_file():
        print(f"[midrun] no samples at {src} — nothing to fold")
        return 1
    rows = [json.loads(x) for x in src.read_text().splitlines() if x.strip()]
    written = 0
    # `sand42-*-awq-<cell>`: the five `sand42-50-<class>-specialist-awq-<cell>` runs AND the
    # noise-floor leg (`sand42-noisefloor-correspondence-awq-<cell>`), which rides the same
    # fleet and samples into the same cell file.
    for run_dir in sorted(RUNS.glob(f"sand42-*-awq-{cell}")):
        run_id = run_dir.name
        win = _window(run_id)
        if not win:
            print(f"  {run_id}: no beacon window — skipped")
            continue
        lo, hi = win
        mine = [r for r in rows if lo <= float(r.get("t", 0)) <= hi]
        if not mine:
            print(f"  {run_id}: no samples inside its window — skipped")
            continue
        per: dict[str, dict[str, list[float]]] = {}
        for r in mine:
            rid = str(r.get("replica"))
            for fam in WANT:
                if fam in r:
                    per.setdefault(rid, {}).setdefault(fam, []).append(float(r[fam]))
        reps = {rid: {fam: _stats(v) for fam, v in fams.items()} for rid, fams in per.items()}
        cell_max = {
            fam: round(max(v[fam]["max"] for v in reps.values()), 4)
            for fam in WANT
            if any(fam in v for v in reps.values())
        }
        # `replicas` is the LATEST sample per replica in the shape a live
        # `sandbox run scrape-metrics --label mid` writes, so both producers of this
        # artifact are readable by the same code; `cell_max`/`replica_sample_stats` carry
        # the series the sampler actually has and a single probe cannot.
        latest: dict[str, dict[str, float | None]] = {}
        for r in sorted(mine, key=lambda x: float(x.get("t", 0))):
            latest[str(r.get("replica"))] = {
                "kv_cache_usage_perc": r.get("vllm:kv_cache_usage_perc"),
                "num_requests_running": r.get("vllm:num_requests_running"),
                "num_requests_waiting": r.get("vllm:num_requests_waiting"),
                "preemptions": r.get("vllm:num_preemptions_total"),
            }
        doc = {
            "schema": "sandbox.midrun-kv/v1",
            "run_id": run_id,
            "at": max(float(r.get("t", 0)) for r in mine),
            "coverage": f"replicas observed: {len(latest)} of {len(latest)}",
            "source": ("mid-run /metrics sample (root endpoint, unauthenticated); the "
                       "before/after scrapes fire at the run's drained edges and read 0"),
            "window": {"start": lo, "end": hi},
            "samples": len(mine),
            "replicas": latest,
            "cell_max": cell_max,
            "replica_sample_stats": reps,
        }
        (run_dir / "vllm_metrics_mid.json").write_text(
            json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
        written += 1
        print(f"  {run_id}: {len(mine)} samples, {len(reps)} replicas, "
              f"kv_max={cell_max.get('vllm:kv_cache_usage_perc', 0) * 100:.1f}% "
              f"running_max={cell_max.get('vllm:num_requests_running', 0):.0f} "
              f"waiting_max={cell_max.get('vllm:num_requests_waiting', 0):.0f}")
    print(f"[midrun] wrote {written} per-run file(s)")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in {"sample", "fold"}:
        print(__doc__)
        return 2
    verb, rest = args[0], args[1:]
    cell = "2l4-c32"
    gap, url, cfg = 30, "", ""
    for i, a in enumerate(rest):
        if a == "--cell":
            cell = rest[i + 1]
        elif a == "--gap":
            gap = int(rest[i + 1])
        elif a == "--url":
            url = rest[i + 1]
        elif a == "--config":
            cfg = rest[i + 1]
    if cfg:
        _CONFIG[0] = cfg
    if verb == "sample":
        return sample(cell, gap, url or default_url())
    return fold(cell)


if __name__ == "__main__":
    raise SystemExit(main())
