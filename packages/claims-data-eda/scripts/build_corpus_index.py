#!/usr/bin/env python3
"""Normalize the DE-SynPUF Sample-1 CSVs into unified JSONL indexes.

Outputs (gitignored, regenerable):
  data/cms/beneficiaries.jsonl.gz  one row per beneficiary (static demographics,
                                   per-year chronic-condition flags + reimbursements)
  data/cms/index.jsonl.gz          one row per claim event (inpatient, outpatient,
                                   carrier claim with embedded service lines) or
                                   prescription drug event

Rows are COMPACT: null/empty fields are dropped and beneficiary demographics are
NOT embedded per claim (116k-row lookup lives in beneficiaries.jsonl.gz; join at
render time). Streams are gzip level 1 -- the full 11.2M-event corpus stays
under ~1 GB. Row order is deterministic; dates are ISO yyyy-mm-dd, amounts float.

Usage:
    python scripts/build_corpus_index.py [--limit N]   # smoke test with --limit
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from pathlib import Path
from typing import Any, Iterator

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw"
OUT = REPO / "data" / "cms"

YEARS = [2008, 2009, 2010]

BENE_FILES = {
    2008: "DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv",
    2009: "DE1_0_2009_Beneficiary_Summary_File_Sample_1.csv",
    2010: "DE1_0_2010_Beneficiary_Summary_File_Sample_1.csv",
}
INPATIENT_FILE = "DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv"
OUTPATIENT_FILE = "DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv"
CARRIER_FILES = [
    "DE1_0_2008_to_2010_Carrier_Claims_Sample_1A.csv",
    "DE1_0_2008_to_2010_Carrier_Claims_Sample_1B.csv",
]
PDE_FILE = "DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_1.csv"

CC_KEYS = [
    "ALZHDMTA", "CHF", "CHRNKIDN", "CNCR", "COPD", "DEPRESSN",
    "DIABETES", "ISCHMCHT", "OSTEOPRS", "RA_OA", "STRKETIA",
]

STATIC_FIELDS = ["BENE_SEX_IDENT_CD", "BENE_RACE_CD", "BENE_ESRD_IND", "SP_STATE_CODE", "BENE_COUNTY_CD"]
YEARLY_MONEY = ["MEDREIMB_IP", "BENRES_IP", "PPPYMT_IP", "MEDREIMB_OP", "BENRES_OP", "PPPYMT_OP",
                "MEDREIMB_CAR", "BENRES_CAR", "PPPYMT_CAR"]


def jopen(path: Path, mode: str = "rt"):
    """Open .gz or plain JSONL transparently (read or write-text)."""
    if str(path).endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8", compresslevel=1)
    return open(path, mode, encoding="utf-8")


def compact(obj: Any) -> Any:
    """Recursively drop None values and empty containers (dicts/lists/strings)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            v = compact(v)
            if v is None or v == [] or v == {} or v == "":
                continue
            out[k] = v
        return out
    if isinstance(obj, list):
        return [compact(v) for v in obj]
    return obj


def _valid_ymd(y: int, mo: int, d: int) -> bool:
    """1-12 month and calendar-correct day (leap-year aware)."""
    import calendar

    return 1 <= mo <= 12 and 1 <= d <= calendar.monthrange(y, mo)[1]


def iso_date(raw: str | None) -> str | None:
    """Normalize a date string to ISO YYYY-MM-DD, or None for garbage.

    hub#58: the old code returned any non-8-digit string unchanged ('N/A',
    '1/1/2010') and did no month/day range validation on 8-digit strings
    ('20101332' -> '2010-13-32'), so downstream `int(...[:4])` raised
    ValueError on garbage and the sibling bene age computation silently
    swallowed it. Month 1-12 and calendar-correct day are validated; garbage
    returns None.
    """
    if not raw or not raw.strip():
        return None
    s = raw.strip()
    if len(s) == 8 and s.isdigit():
        y, mo, d = int(s[:4]), int(s[4:6]), int(s[6:8])
        if _valid_ymd(y, mo, d):
            return f"{y}-{mo:02d}-{d:02d}"
        return None
    # tolerate already-ISO dates; anything else is not machine-parseable
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            y, mo, d = int(s[:4]), int(s[5:7]), int(s[8:10])
            if _valid_ymd(y, mo, d):
                return s
        except ValueError:
            return None
        return None
    return None


def to_float(raw: str | None) -> float | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        return float(str(raw).strip())
    except ValueError:
        return None


def to_int(raw: str | None) -> int | None:
    v = to_float(raw)
    return int(v) if v is not None else None


def collect_codes(row: dict, prefix: str) -> list[str]:
    out = []
    for k in sorted(row):
        if k.startswith(prefix) and row.get(k, "").strip():
            out.append(row[k].strip())
    return out


def read_csv(path: Path) -> Iterator[dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            yield {k.strip('"'): (v or "").strip() for k, v in row.items()}


# ---------------------------------------------------------------- beneficiaries

def build_beneficiaries(limit: int | None = None) -> dict[str, dict]:
    """Merge the three yearly summary files into one record per beneficiary."""
    bene: dict[str, dict] = {}
    for year in YEARS:
        n = 0
        for row in read_csv(RAW / BENE_FILES[year]):
            bid = row["DESYNPUF_ID"]
            rec = bene.setdefault(bid, {
                "bene_id": bid,
                "birth_dt": iso_date(row.get("BENE_BIRTH_DT")),
                "death_dt": iso_date(row.get("BENE_DEATH_DT")),
                **{f.lower(): row.get(f) for f in STATIC_FIELDS},
                "years": {},
            })
            # death date can first appear in any later year file
            dd = iso_date(row.get("BENE_DEATH_DT"))
            if dd and not rec["death_dt"]:
                rec["death_dt"] = dd
            rec["years"][year] = {
                "cc": {k: to_int(row.get(f"SP_{k}")) for k in CC_KEYS},
                "money": {m: to_float(row.get(m)) for m in YEARLY_MONEY},
                "hi_mons": to_int(row.get("BENE_HI_CVRAGE_TOT_MONS")),
                "smi_mons": to_int(row.get("BENE_SMI_CVRAGE_TOT_MONS")),
                "hmo_mons": to_int(row.get("BENE_HMO_CVRAGE_TOT_MONS")),
                "plan_mos": to_int(row.get("PLAN_CVRG_MOS_NUM")),
            }
            n += 1
            if limit and n >= limit:
                break
        print(f"  bene {year}: {n:,} rows", flush=True)
    return bene


def bene_snapshot(rec: dict, year: int | None) -> dict:
    """Static demographics + chronic flags for the service year (nearest fallback)."""
    yearly = rec["years"]
    if not yearly:
        return {}
    if year is None:
        y = max(yearly)
    else:
        y = year
        while y not in yearly and y <= max(YEARS):
            y += 1
        while y not in yearly and y >= min(YEARS):
            y -= 1
    cc = yearly[y]["cc"] if y in yearly else {}
    age = None
    if rec["birth_dt"]:
        try:
            by = int(rec["birth_dt"][:4])
            ref_year = year if year is not None else y
            age = max(ref_year - by, 0)
        except ValueError:
            # hub#58: an unparseable birth date left bene_age silently None —
            # surface it so the data gap is observable, not hidden.
            print(f"  !! unparseable birth_dt {rec.get('birth_dt')!r} "
                  f"for record {rec.get('record_id')} — bene_age left None", flush=True)
    return {
        "bene_sex": {"1": "M", "2": "F"}.get(rec.get("bene_sex_ident_cd"), "U"),
        "bene_race_cd": to_int(rec.get("bene_race_cd")),
        "bene_state": to_int(rec.get("sp_state_code")),
        "bene_county": to_int(rec.get("bene_county_cd")),
        "esrd_ind": rec.get("bene_esrd_ind") or None,
        "bene_death_dt": rec["death_dt"],
        "bene_age": age,
        "chronic_conditions": cc,
    }


# ---------------------------------------------------------------- claim events

def claim_event(row: dict, claim_type: str, src: str) -> dict:
    seg = to_int(row.get("SEGMENT")) if claim_type != "carrier" else to_int(row.get("CLM_SEGMENT_NUM"))
    ev = {
        "record_id": f"{claim_type}:{row['CLM_ID']}" + (f":{seg}" if seg is not None else ""),
        "record_type": "claim",
        "claim_type": claim_type,
        "bene_id": row["DESYNPUF_ID"],
        "clm_id": row["CLM_ID"],
        "segment": seg,
        "year": None,
        "from_dt": iso_date(row.get("CLM_FROM_DT")),
        "thru_dt": iso_date(row.get("CLM_THRU_DT")),
        "admit_dt": iso_date(row.get("CLM_ADMSN_DT")),
        "discharge_dt": iso_date(row.get("NCH_BENE_DSCHRG_DT")),
        "payment_amt": to_float(row.get("CLM_PMT_AMT")),
        "primary_payer_amt": to_float(row.get("NCH_PRMRY_PYR_CLM_PD_AMT")),
        "prvdr_num": row.get("PRVDR_NUM") or None,
        "provider_npis": sorted({row[c] for c in ("AT_PHYSN_NPI", "OP_PHYSN_NPI", "OT_PHYSN_NPI")
                                 if row.get(c, "").strip()}),
        "diagnosis_codes": collect_codes(row, "ICD9_DGNS_CD_"),
        "admitting_dx": row.get("ADMTNG_ICD9_DGNS_CD") or None,
        "procedure_codes": collect_codes(row, "ICD9_PRCDR_CD_"),
        "hcpcs_codes": collect_codes(row, "HCPCS_CD_"),
        "drg_cd": row.get("CLM_DRG_CD") or None,
        "utilization_days": to_int(row.get("CLM_UTLZTN_DAY_CNT")),
        "source_file": src,
    }
    if claim_type == "inpatient":
        ev.update({
            "deductible_amt": to_float(row.get("NCH_BENE_IP_DDCTBL_AMT")),
            "coinsurance_amt": to_float(row.get("NCH_BENE_PTA_COINSRNC_LBLTY_AM")),
            "pass_thru_per_diem_amt": to_float(row.get("CLM_PASS_THRU_PER_DIEM_AMT")),
            "blood_deductible_amt": to_float(row.get("NCH_BENE_BLOOD_DDCTBL_LBLTY_AM")),
        })
    elif claim_type == "outpatient":
        ev.update({
            "ptb_deductible_amt": to_float(row.get("NCH_BENE_PTB_DDCTBL_AMT")),
            "ptb_coinsurance_amt": to_float(row.get("NCH_BENE_PTB_COINSRNC_AMT")),
            "blood_deductible_amt": to_float(row.get("NCH_BENE_BLOOD_DDCTBL_LBLTY_AM")),
        })
    if ev["from_dt"]:
        ev["year"] = int(ev["from_dt"][:4])
    return ev


def carrier_claim_event(row: dict, src: str) -> dict:
    """Carrier rows are CLAIM-level with up to 13 embedded line slots (wide format).

    Payments exist only per-line (LINE_NCH_PMT_AMT_*), so payment_amt is the
    sum over populated lines; lines are kept as structured sub-records.
    """
    lines = []
    for i in range(1, 14):
        hcpcs = row.get(f"HCPCS_CD_{i}", "").strip()
        pmt = to_float(row.get(f"LINE_NCH_PMT_AMT_{i}"))
        allowed = to_float(row.get(f"LINE_ALOWD_CHRG_AMT_{i}"))
        coins = to_float(row.get(f"LINE_COINSRNC_AMT_{i}"))
        ded = to_float(row.get(f"LINE_BENE_PTB_DDCTBL_AMT_{i}"))
        if not any([hcpcs, pmt, allowed]):
            continue
        lines.append({
            "line_num": i,
            "hcpcs": hcpcs or None,
            "payment_amt": pmt,
            "allowed_charge_amt": allowed,
            "coinsurance_amt": coins,
            "deductible_amt": ded,
        })
    ev = {
        "record_id": f"carrier:{row['CLM_ID']}",
        "record_type": "claim",
        "claim_type": "carrier",
        "bene_id": row["DESYNPUF_ID"],
        "clm_id": row["CLM_ID"],
        "segment": None,
        "year": None,
        "from_dt": iso_date(row.get("CLM_FROM_DT")),
        "thru_dt": iso_date(row.get("CLM_THRU_DT")),
        "admit_dt": None,
        "discharge_dt": None,
        "payment_amt": sum(l["payment_amt"] or 0.0 for l in lines) or None,
        "bene_primary_payer_amt": sum(
            to_float(row.get(f"LINE_BENE_PRMRY_PYR_PD_AMT_{i}")) or 0.0 for i in range(1, 14)
        ) or None,
        "prvdr_num": None,
        "provider_npis": sorted({row[f"PRF_PHYSN_NPI_{i}"] for i in range(1, 14)
                                 if row.get(f"PRF_PHYSN_NPI_{i}", "").strip()}),
        "diagnosis_codes": collect_codes(row, "ICD9_DGNS_CD_"),
        "admitting_dx": None,
        "procedure_codes": [],
        "hcpcs_codes": [l["hcpcs"] for l in lines if l["hcpcs"]],
        "drg_cd": None,
        "utilization_days": None,
        "lines": lines,
        "source_file": src,
    }
    if ev["from_dt"]:
        ev["year"] = int(ev["from_dt"][:4])
    return ev


def pde_event(row: dict, src: str) -> dict:
    svc = iso_date(row.get("SRVC_DT"))
    return {
        "record_id": f"pde:{row['PDE_ID']}",
        "record_type": "pde",
        "claim_type": "pde",
        "bene_id": row["DESYNPUF_ID"],
        "pde_id": row["PDE_ID"],
        "segment": None,
        "year": int(svc[:4]) if svc else None,
        "service_dt": svc,
        "ndc": row.get("PROD_SRVC_ID") or None,
        "qty_dispensed": to_float(row.get("QTY_DSPNSD_NUM")),
        "days_supply": to_int(row.get("DAYS_SUPLY_NUM")),
        "drug_cost_amt": to_float(row.get("TOT_RX_CST_AMT")),
        "patient_pay_amt": to_float(row.get("PTNT_PAY_AMT")),
        "source_file": src,
    }


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None, help="rows per input file (smoke test)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print("[1/3] beneficiaries ...", flush=True)
    bene = build_beneficiaries(args.limit)
    bene_path = OUT / "beneficiaries.jsonl.gz"
    with jopen(bene_path, "wt") as fh:
        for bid in sorted(bene):
            fh.write(json.dumps(compact(bene[bid]), sort_keys=True) + "\n")
    print(f"  wrote {len(bene):,} beneficiaries -> {bene_path}", flush=True)

    def emit(path: Path, rows: Iterator[dict]) -> int:
        n = 0
        with jopen(path, "at") as fh:
            for r in rows:
                fh.write(json.dumps(compact(r), sort_keys=True) + "\n")
                n += 1
                if args.limit and n >= args.limit:
                    break
        return n

    print("[2/3] claims ...", flush=True)
    index_path = OUT / "index.jsonl.gz"
    index_path.unlink(missing_ok=True)  # truncate
    total = 0
    for label, files, fn in (
        ("inpatient", [INPATIENT_FILE], lambda r, s: claim_event(r, "inpatient", s)),
        ("outpatient", [OUTPATIENT_FILE], lambda r, s: claim_event(r, "outpatient", s)),
        ("carrier", CARRIER_FILES, carrier_claim_event),
    ):
        for fname in files:
            fpath = RAW / fname
            if not fpath.exists():
                print(f"  !! missing {fname} (skipped)", flush=True)
                continue
            n = emit(index_path, (fn(r, fname) for r in read_csv(fpath)))
            print(f"  {label}: {n:,} events from {fname}", flush=True)
            total += n

    pde_path = RAW / PDE_FILE
    if pde_path.exists():
        n = emit(index_path, (pde_event(r, PDE_FILE) for r in read_csv(pde_path)))
        print(f"  pde: {n:,} events from {PDE_FILE}", flush=True)
        total += n
    else:
        print(f"  !! missing {PDE_FILE}", flush=True)

    print(f"[3/3] wrote {total:,} claim events -> {index_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
