#!/usr/bin/env python3
"""Build the pipeline-ready insurance_claim sample from the DE-SynPUF index.

Produces data/cms/pipeline.jsonl -- one row per rendered EOB document in the
flat streamer-dump shape consumed by llm-entity-extraction eval runners
(`expected="insurance_claim"`, `expected_subclass` = claim subtype, GT fields
aligned to llm-mailroom's InsuranceClaimExtraction schema).

Sampling is deterministic and stratified:
  strata  = claim_type x service-year x cost band (bands cut at p33/p66 of the
            corpus-wide per-type payment distributions reported by the EDA)
  budget  = --n split equally across claim types, allocated within type by
            observed stratum weight; every NON-EMPTY stratum keeps >= 1 row
            (coverage contract, exit code 2 on violation); the high-cost band
            holds a >= 15% floor so the heavy tail is always represented.

Beneficiary demographics are joined from beneficiaries.jsonl.gz at render time.

Usage:
    python scripts/build_pipeline_dump.py [--n 400] [--seed 42] [--dry-run]
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
import zlib
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from build_corpus_index import YEARS, jopen  # noqa: E402
from render_eob import pipeline_row  # noqa: E402

CMS_DIR = REPO / "data" / "cms"
STATS_PATH = REPO / "reports" / "eda" / "corpus_stats.json"
OUT_PATH = CMS_DIR / "pipeline.jsonl"

TYPES = ("inpatient", "outpatient", "carrier", "pde")


class Reservoir:
    def __init__(self, k: int, seed: int):
        self.k, self.n, self.rng = k, 0, random.Random(seed)
        self.items: list[dict] = []

    def add(self, row: dict) -> None:
        self.n += 1
        if len(self.items) < self.k:
            self.items.append(row)
        else:
            j = self.rng.randint(0, self.n - 1)
            if j < self.k:
                self.items[j] = row


def load_bene_lookup() -> dict[str, dict]:
    lookup = {}
    with jopen(CMS_DIR / "beneficiaries.jsonl.gz") as fh:
        for line in fh:
            b = json.loads(line)
            lookup[b["bene_id"]] = b
    return lookup


def join_beneficiary(e: dict, bene: dict | None) -> dict:
    """Attach demographics/CC flags for the service year (mirrors index enrichment)."""
    if bene is None:
        e.setdefault("chronic_conditions", {})
        return e
    yearly = {int(k): v for k, v in (bene.get("years") or {}).items()}
    y = e.get("year")
    if y not in yearly:
        candidates = sorted(yearly, key=lambda v: abs(v - (y if y else 0)))
        y = candidates[0] if candidates else None
    yd = yearly.get(y, {})
    cc = {k: v for k, v in (yd.get("cc") or {}).items() if v == 1}
    e["chronic_conditions"] = cc
    e["bene_sex"] = {"1": "M", "2": "F"}.get(bene.get("bene_sex_ident_cd"), "U")
    e["bene_state"] = bene.get("sp_state_code")
    e["bene_county"] = bene.get("bene_county_cd")
    birth = bene.get("birth_dt")
    if birth and e.get("year"):
        try:
            e["bene_age"] = max(e["year"] - int(birth[:4]), 0)
        except ValueError:
            pass
    return e


def cost_of(e: dict) -> float | None:
    v = e.get("drug_cost_amt") if e["claim_type"] == "pde" else e.get("payment_amt")
    return v if isinstance(v, (int, float)) and v > 0 else None


def band_of(value: float | None, cuts: tuple[float, float]) -> str:
    if value is None:
        return "none"
    if value <= cuts[0]:
        return "low"
    if value <= cuts[1]:
        return "mid"
    return "high"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=400, help="total documents to emit")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="plan quotas without writing")
    args = ap.parse_args()

    if not STATS_PATH.exists():
        print("!! reports/eda/corpus_stats.json missing -- run scripts/eda/explore_cms.py first", flush=True)
        return 1
    pct = json.loads(STATS_PATH.read_text())["cost_percentiles"]
    cuts = {t: (pct[t]["33"], pct[t]["66"]) for t in TYPES}

    # ---- pass 1: per-stratum reservoirs -------------------------------
    pools: dict[tuple, Reservoir] = {}
    with jopen(CMS_DIR / "index.jsonl.gz") as fh:
        for line in fh:
            e = json.loads(line)
            t = e["claim_type"]
            key = (t, e.get("year") or 0, band_of(cost_of(e), cuts[t]))
            r = pools.get(key)
            if r is None:
                r = pools[key] = Reservoir(k=250, seed=args.seed + zlib.crc32(str(key).encode()) % 10000)
            r.add(e)

    print(f"{len(pools)} non-empty strata:")
    for key in sorted(pools, key=str):
        t, y, b = key
        print(f"  {t:<11} {y} {b:<5} ~{pools[key].n:>9,} events")

    # ---- quota allocation ---------------------------------------------
    rng = random.Random(args.seed)
    present_types = sorted({k[0] for k in pools})
    budget = {t: args.n // len(present_types) for t in present_types}
    leftover = args.n - sum(budget.values())
    for t in present_types[:leftover]:
        budget[t] += 1

    selection: list[dict] = []
    chosen_ids: set[str] = set()
    for t in present_types:
        strata = [k for k in pools if k[0] == t]
        weights = {k: pools[k].n for k in strata}
        total_w = sum(weights.values())
        hi_floor = max(int(budget[t] * 0.15), 1)

        alloc: dict[tuple, int] = {k: 1 for k in strata}
        remaining = budget[t] - len(strata)
        if remaining < 0:
            # more strata than budget: keep one per stratum anyway (contract),
            # prioritizing high band first
            order = sorted(strata, key=lambda k: (k[2] != "high", -weights[k]))
            alloc = {k: 0 for k in strata}
            for k in order[:budget[t]]:
                alloc[k] = 1
            remaining = 0
        else:
            for k in strata:
                alloc[k] += int(round(budget[t] * weights[k] / total_w)) - 1
            # fix rounding drift
            drift = budget[t] - sum(alloc.values())
            step = 1 if drift > 0 else -1
            i = 0
            while drift != 0 and strata:
                k = strata[i % len(strata)]
                if step > 0 or alloc[k] > 1:
                    alloc[k] += step
                    drift -= step
                i += 1

        # enforce high-band floor by shifting surplus from other bands
        hi_keys = [k for k in strata if k[2] == "high"]
        hi_alloc = sum(alloc[k] for k in hi_keys)
        if hi_keys and hi_alloc < hi_floor:
            need = hi_floor - hi_alloc
            for k in sorted((x for x in strata if x[2] != "high"),
                            key=lambda x: -alloc[x]):
                take = min(need, alloc[k] - 1)
                if take > 0:
                    alloc[k] -= take
                    alloc[next(x for x in hi_keys)] += take
                    need -= take
                if need == 0:
                    break

        for k in sorted(strata, key=str):
            res = pools[k]
            take = min(alloc[k], len(res.items))
            picks = res.items if take >= len(res.items) else rng.sample(res.items, take)
            for e in picks:
                rid = e["record_id"]
                if rid not in chosen_ids:
                    chosen_ids.add(rid)
                    selection.append(e)

    if len(selection) != len(chosen_ids):
        print(f"!! duplicate record_ids collapsed ({len(selection)} -> {len(chosen_ids)})", flush=True)

    # ---- coverage contract --------------------------------------------
    got_types = {e["claim_type"] for e in selection}
    missing = set(present_types) - got_types
    if missing:
        print(f"!! COVERAGE CONTRACT VIOLATION: strata types {sorted(missing)} missing from sample",
              file=sys.stderr)
        return 2
    got_years = {e.get("year") for e in selection}
    print(f"\nselected {len(selection)} docs across types={sorted(got_types)} "
          f"years={sorted(y for y in got_years if y)}")

    if args.dry_run:
        print("DRY RUN: no output written")
        return 0

    # ---- pass 2: fetch selected rows in stream order -------------------
    wanted = chosen_ids
    fetched: dict[str, dict] = {}
    with jopen(CMS_DIR / "index.jsonl.gz") as fh:
        for line in fh:
            if not wanted:
                break
            e = json.loads(line)
            if e["record_id"] in wanted:
                fetched[e["record_id"]] = e
                wanted.discard(e["record_id"])
    if wanted:
        print(f"!! {len(wanted)} selected ids not found on refetch (reservoir race?) -- aborting",
              file=sys.stderr)
        return 3

    # ---- join + render --------------------------------------------------
    bene = load_bene_lookup()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_written = 0
    with OUT_PATH.open("w") as out:
        for e in selection:
            row = join_beneficiary(fetched[e["record_id"]], bene.get(e["bene_id"]))
            out.write(json.dumps(pipeline_row(row), sort_keys=True) + "\n")
            n_written += 1

    dist = defaultdict(int)
    with OUT_PATH.open() as fh:
        for line in fh:
            dist[json.loads(line)["expected_subclass"]] += 1
    print(f"wrote {n_written:,} rows -> {OUT_PATH}")
    print("distribution:", dict(sorted(dist.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
