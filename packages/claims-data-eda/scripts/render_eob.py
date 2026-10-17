#!/usr/bin/env python3
"""Deterministic EOB-style document renderer for DE-SynPUF claim events.

Turns a normalized index.jsonl row (see build_corpus_index.py) into a
plain-text Medicare Summary Notice / pharmacy statement that:

  * contains EVERY ground-truth value verbatim (so the mailroom field
    scorer's factuality audit can verify extraction against source text),
  * is a pure function of the input row (byte-identical on rebuild),
  * carries no real PHI (the corpus is synthetic; beneficiary names are
    deterministic pseudonyms derived from DESYNPUF_ID).

GT mapping targets llm-mailroom's InsuranceClaimExtraction schema:
  claim_number, policy_number, insurer, insured_party, claim_type,
  date_of_loss, date_filed, claimed_amount, adjuster, damages_description,
  coverage_determination, denial_reasons, supporting_documents
"""

from __future__ import annotations

import hashlib

INSURER = "CMS Medicare"

CC_LABELS = {
    "ALZHDMTA": "Alzheimer's/dementia", "CHF": "congestive heart failure",
    "CHRNKIDN": "chronic kidney disease", "CNCR": "cancer", "COPD": "COPD",
    "DEPRESSN": "depression", "DIABETES": "diabetes", "ISCHMCHT": "ischemic heart disease",
    "OSTEOPRS": "osteoporosis", "RA_OA": "arthritis", "STRKETIA": "stroke/TIA",
}

_GIVEN = ["JAMES", "MARY", "ROBERT", "PATRICIA", "JOHN", "JENNIFER", "MICHAEL", "LINDA",
          "DAVID", "ELIZABETH", "WILLIAM", "BARBARA", "RICHARD", "SUSAN", "JOSEPH", "JESSICA",
          "THOMAS", "SARAH", "CHARLES", "KAREN", "CHRISTOPHER", "NANCY", "DANIEL", "LISA",
          "MATTHEW", "BETTY", "ANTHONY", "MARGARET", "MARK", "SANDRA", "DONALD", "ASHLEY",
          "STEVEN", "KIMBERLY", "PAUL", "EMILY", "ANDREW", "DONNA", "JOSHUA", "MICHELLE"]
_FAMILY = ["SMITH", "JOHNSON", "WILLIAMS", "BROWN", "JONES", "GARCIA", "MILLER", "DAVIS",
           "RODRIGUEZ", "MARTINEZ", "HERNANDEZ", "LOPEZ", "GONZALEZ", "WILSON", "ANDERSON",
           "THOMAS", "TAYLOR", "MOORE", "JACKSON", "MARTIN", "LEE", "PEREZ", "THOMPSON",
           "WHITE", "HARRIS", "SANCHEZ", "CLARK", "RAMIREZ", "LEWIS", "ROBINSON", "WALKER",
           "YOUNG", "ALLEN", "KING", "WRIGHT", "SCOTT", "TORRES", "NGUYEN", "HILL", "FLORES"]


def insured_pseudonym(bene_id: str) -> str:
    """Deterministic patient name derived from the synthetic beneficiary id."""
    h = hashlib.sha256(bene_id.encode()).digest()
    return f"{_FAMILY[h[0] % len(_FAMILY)]}, {_GIVEN[h[1] % len(_GIVEN)]}"


def money(x: float | int | None) -> str:
    if x is None:
        return "N/A"
    return f"${x:,.2f}"


def _bene_block(e: dict) -> str:
    lines = [
        "BENEFICIARY / INSURED",
        f"  Insured party:            {insured_pseudonym(e['bene_id'])}",
        f"  Policy number:            {e['policy_number']}",
        f"  Age:                      {e.get('bene_age') if e.get('bene_age') is not None else 'N/A'}",
        f"  Sex:                      {e.get('bene_sex') or 'N/A'}",
        f"  State/County (SSA):       {e.get('bene_state') or 'N/A'} / {e.get('bene_county') or 'N/A'}",
    ]
    cc = [CC_LABELS[k] for k, v in (e.get("chronic_conditions") or {}).items() if v == 1]
    if cc:
        lines.append(f"  Flagged chronic cond.:    {', '.join(cc)}")
    return "\n".join(lines) + "\n"


def render_inpatient(e: dict) -> str:
    dx = ", ".join(e.get("diagnosis_codes", [])) or "not reported"
    pr = ", ".join(e.get("procedure_codes", [])) or "none reported"
    npi = ", ".join(e.get("provider_npis", [])) or "not reported"
    los = e.get("utilization_days")
    parts = [
        "=" * 74,
        "MEDICARE SUMMARY NOTICE -- INPATIENT STAY (Part A)",
        f"Notice ID: {e['claim_number']}",
        "=" * 74,
        "",
        f"Insurer:                  {INSURER}",
        f"Line of business:         health",
        "",
        _bene_block(e),
        "",
        "STAY DETAILS",
        f"  Claim period start:       {e.get('from_dt') or 'N/A'}",
        f"  Claim period end:         {e.get('thru_dt') or 'N/A'}",
        f"  Admission date:           {e.get('admit_dt') or 'N/A'}",
        f"  Discharge date:           {e.get('discharge_dt') or 'N/A'}",
        f"  Covered days:             {los if los is not None else 'N/A'}",
        f"  Facility provider number: {e.get('prvdr_num') or 'N/A'}",
        f"  Attending/treating NPIs:  {npi}",
        f"  MS-DRG:                   {e.get('drg_cd') or 'N/A'}",
        "",
        "DIAGNOSES (ICD-9-CM)",
        f"  Principal & secondary:    {dx}",
        "",
        "PROCEDURES (ICD-9-CM)",
        f"  Performed:                {pr}",
        "",
        "ADJUDICATION SUMMARY",
        f"  Claim total paid by Medicare: {money(e.get('claimed_amount'))}",
        f"  Beneficiary deductible:       {money(e.get('deductible_amt'))}",
        f"  Beneficiary coinsurance:      {money(e.get('coinsurance_amt'))}",
        f"  Blood deductible:             {money(e.get('blood_deductible_amt'))}",
        f"  Primary payer paid:           {money(e.get('primary_payer_amt'))}",
        "",
        "COVERAGE DETERMINATION: APPROVED - this claim has been adjudicated and paid.",
        "  Stated outcome (verbatim): approved",
        "",
    ]
    return "\n".join(parts)


def render_outpatient(e: dict) -> str:
    dx = ", ".join(e.get("diagnosis_codes", [])) or "not reported"
    hcpcs = ", ".join(e.get("hcpcs_codes", [])) or "none reported"
    pr = ", ".join(e.get("procedure_codes", [])) or "none reported"
    npi = ", ".join(e.get("provider_npis", [])) or "not reported"
    parts = [
        "=" * 74,
        "MEDICARE SUMMARY NOTICE -- OUTPATIENT SERVICES (Part B)",
        f"Notice ID: {e['claim_number']}",
        "=" * 74,
        "",
        f"Insurer:                  {INSURER}",
        f"Line of business:         health",
        "",
        _bene_block(e),
        "",
        "SERVICE DETAILS",
        f"  Service start date:       {e.get('from_dt') or 'N/A'}",
        f"  Service end date:         {e.get('thru_dt') or 'N/A'}",
        f"  Facility provider number: {e.get('prvdr_num') or 'N/A'}",
        f"  Treating NPIs:            {npi}",
        "",
        "BILLING CODES",
        f"  Diagnoses (ICD-9):        {dx}",
        f"  Procedures (ICD-9):       {pr}",
        f"  Services (HCPCS):         {hcpcs}",
        "",
        "ADJUDICATION SUMMARY",
        f"  Claim total paid by Medicare: {money(e.get('claimed_amount'))}",
        f"  Part B deductible:            {money(e.get('ptb_deductible_amt'))}",
        f"  Part B coinsurance:           {money(e.get('ptb_coinsurance_amt'))}",
        f"  Primary payer paid:           {money(e.get('primary_payer_amt'))}",
        "",
        "COVERAGE DETERMINATION: APPROVED - this claim has been adjudicated and paid.",
        "  Stated outcome (verbatim): approved",
        "",
    ]
    return "\n".join(parts)


def render_carrier(e: dict) -> str:
    dx = ", ".join(e.get("diagnosis_codes", [])) or "not reported"
    npis = e.get("provider_npis", [])
    primary_npi = npis[0] if npis else "not reported"
    lines = e.get("lines") or []
    line_rows = []
    for i, l in enumerate(lines, 1):
        line_rows.append(
            f"  {i:>2}. HCPCS {l.get('hcpcs') or '----'}   "
            f"allowed {money(l.get('allowed_charge_amt'))}   "
            f"paid {money(l.get('payment_amt'))}   "
            f"(coins {money(l.get('coinsurance_amt'))}, ded {money(l.get('deductible_amt'))})"
        )
    if not line_rows:
        line_rows.append("  (no itemized lines reported)")
    parts = [
        "=" * 74,
        "MEDICARE SUMMARY NOTICE -- PHYSICIAN/SUPPLIER CLAIM (Part B)",
        f"Notice ID: {e['claim_number']}",
        "=" * 74,
        "",
        f"Insurer:                  {INSURER}",
        f"Line of business:         health",
        "",
        _bene_block(e),
        "",
        "SERVICE DETAILS",
        f"  Service start date:       {e.get('from_dt') or 'N/A'}",
        f"  Service end date:         {e.get('thru_dt') or 'N/A'}",
        f"  Performing physician NPI: {primary_npi}",
        "",
        "DIAGNOSES (ICD-9-CM)",
        f"  Reported:                 {dx}",
        "",
        f"ITEMIZED SERVICE LINES ({len(lines)})",
        *line_rows,
        "",
        "ADJUDICATION SUMMARY",
        f"  Claim total paid by Medicare: {money(e.get('claimed_amount'))}",
        "",
        "COVERAGE DETERMINATION: APPROVED - this claim has been adjudicated and paid.",
        "  Stated outcome (verbatim): approved",
        "",
    ]
    return "\n".join(parts)


def render_pde(e: dict) -> str:
    parts = [
        "=" * 74,
        "MEDICARE PRESCRIPTION DRUG BENEFIT -- PHARMACY STATEMENT (Part D)",
        f"Fill Reference: {e['claim_number']}",
        "=" * 74,
        "",
        f"Insurer:                  {INSURER} Part D",
        f"Line of business:         health",
        "",
        _bene_block(e),
        "",
        "PRESCRIPTION DETAILS",
        f"  Date of service:          {e.get('service_dt') or 'N/A'}",
        f"  Drug product (NDC):       {e.get('ndc') or 'N/A'}",
        f"  Quantity dispensed:       {e.get('qty_dispensed') if e.get('qty_dispensed') is not None else 'N/A'}",
        f"  Days supply:              {e.get('days_supply') if e.get('days_supply') is not None else 'N/A'}",
        "",
        "COST SHARE",
        f"  Total drug cost:          {money(e.get('drug_cost_amt'))}",
        f"  Patient pay amount:       {money(e.get('patient_pay_amt'))}",
        "",
        "COVERAGE DETERMINATION: APPROVED - this fill was covered under the plan.",
        "  Stated outcome (verbatim): approved",
        "",
    ]
    return "\n".join(parts)


RENDERERS = {
    "inpatient": render_inpatient,
    "outpatient": render_outpatient,
    "carrier": render_carrier,
    "pde": render_pde,
}


def gt_fields(e: dict) -> dict:
    """Ground-truth extraction target aligned with InsuranceClaimExtraction."""
    subtype = e["claim_type"]
    if subtype == "pde":
        date_of_loss = e.get("service_dt")
        date_filed = e.get("service_dt")
        claimed = e.get("drug_cost_amt")
        damages = (
            f"Pharmacy fill of prescription drug product NDC {e.get('ndc')} "
            f"({e.get('qty_dispensed') if e.get('qty_dispensed') is not None else '?'} units, "
            f"{e.get('days_supply') if e.get('days_supply') is not None else '?'}-day supply) "
            f"on {date_of_loss}."
        )
    else:
        date_of_loss = e.get("from_dt")
        date_filed = e.get("thru_dt") or e.get("discharge_dt")
        claimed = e.get("payment_amt")
        if subtype == "inpatient":
            damages = (
                f"Inpatient hospital stay from {date_of_loss} to {date_filed} "
                f"({e.get('utilization_days') if e.get('utilization_days') is not None else '?'} covered days), "
                f"MS-DRG {e.get('drg_cd')}. Principal diagnoses (ICD-9): "
                f"{', '.join((e.get('diagnosis_codes') or ['unspecified'])[:5])}."
            )
        elif subtype == "outpatient":
            damages = (
                f"Outpatient facility services on {date_of_loss}; diagnoses (ICD-9): "
                f"{', '.join((e.get('diagnosis_codes') or ['unspecified'])[:5])}; services (HCPCS): "
                f"{', '.join((e.get('hcpcs_codes') or ['none'])[:6])}."
            )
        else:  # carrier
            damages = (
                f"Physician/supplier professional services {date_of_loss} to {date_filed}; "
                f"diagnoses (ICD-9): {', '.join((e.get('diagnosis_codes') or ['unspecified'])[:5])}; "
                f"{len(e.get('lines') or [])} billed service lines."
            )
    supporting = []
    if e.get("prvdr_num"):
        supporting.append(f"facility provider {e['prvdr_num']}")
    for n in (e.get("provider_npis") or [])[:2]:
        supporting.append(f"provider NPI {n}")
    if subtype == "pde":
        supporting.append(f"NDC {e.get('ndc')}")
    elif e.get("hcpcs_codes"):
        supporting.append(f"HCPCS detail ({len(e['hcpcs_codes'])} codes)")
    return {
        "claim_number": e["claim_number"],
        "policy_number": e["policy_number"],
        "insurer": INSURER,
        "insured_party": insured_pseudonym(e["policy_number"]),
        "claim_type": "health",
        "date_of_loss": date_of_loss,
        "date_filed": date_filed,
        "claimed_amount": claimed,
        "adjuster": None,
        "damages_description": damages,
        "coverage_determination": "approved",
        "denial_reasons": [],
        "supporting_documents": supporting,
    }


def render(e: dict) -> tuple[str, dict]:
    """Returns (doc_text, ground_truth). Pure function of `e`."""
    etype = e["claim_type"]
    if etype not in RENDERERS:
        raise ValueError(f"unknown claim_type {etype!r}")
    ev = dict(e)
    # normalize GT-facing fields onto the row copy
    ev["policy_number"] = e["bene_id"]
    ev["claim_number"] = e.get("clm_id") or e.get("pde_id")
    ev["claimed_amount"] = e.get("drug_cost_amt") if etype == "pde" else e.get("payment_amt")
    doc = RENDERERS[etype](ev)
    gt = gt_fields(ev)
    # verbatim contract: every scalar GT value must occur in the document text
    for key in ("claim_number", "policy_number", "insurer", "insured_party", "claim_type"):
        assert gt[key] in doc, f"verbatim contract violated for {key}"
    if gt["claimed_amount"] is not None:
        assert money(gt["claimed_amount"]) in doc, "verbatim contract violated for claimed_amount"
    for d in (gt["date_of_loss"], gt["date_filed"]):
        if d:
            assert d in doc, f"verbatim contract violated for date {d}"
    return doc, gt


def pipeline_row(e: dict, source_dataset: str = "cms-de-synpuf-2008-2010-sample1") -> dict:
    """Flat streamer-dump shape consumed by the mailroom eval runners."""
    doc, gt = render(e)
    meta = {
        "record_id": e["record_id"],
        "claim_subtype": e["claim_type"],
        "year": e.get("year"),
        "provider_npis": e.get("provider_npis"),
        "prvdr_num": e.get("prvdr_num"),
        "diagnosis_codes": e.get("diagnosis_codes"),
        "hcpcs_codes": e.get("hcpcs_codes"),
        "procedure_codes": e.get("procedure_codes"),
        "source_dataset": source_dataset,
    }
    if e["claim_type"] == "pde":
        meta.update({"ndc": e.get("ndc"), "days_supply": e.get("days_supply"),
                     "qty_dispensed": e.get("qty_dispensed")})
    return {
        "filename": f"{e['record_id']}.txt",
        "doc_text": doc,
        "prompt": "",
        "expected": "insurance_claim",
        "expected_subclass": e["claim_type"],
        "metadata": {**meta, "ground_truth": gt},
    }
