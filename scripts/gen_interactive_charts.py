#!/usr/bin/env python3
"""Generate Plotly interactive HTML charts for EDA repos."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAIMS_STATS = ROOT / "packages/claims-data-eda/reports/eda/corpus_stats.json"
CLAIMS_OUT = ROOT / "packages/claims-data-eda/reports/eda/figures_interactive"
ENRON_OUT = ROOT / "packages/Enron-Evaluation-Environment/reports/eda/figures_interactive"
CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

def wrap(div_id, js):
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<script src="{CDN}"></script>'
            f'<style>body{{margin:0;background:#1a1d29}}</style></head>'
            f'<body><div id="{div_id}" style="width:100%;height:100vh"></div>'
            f'<script>{js}</script></body></html>')

def layout(title, **kw):
    base = {"title":{"text":title,"font":{"size":14,"color":"#e2e4ed"}},
            "paper_bgcolor":"#1a1d29","plot_bgcolor":"#1a1d29",
            "font":{"color":"#8b8fa3"},"margin":{"l":60,"r":30,"t":50,"b":60}}
    base.update(kw)
    return json.dumps(base)

def ax(**kw):
    base = {"gridcolor":"#2a2d3e"}
    base.update(kw)
    return json.dumps(base)

def plot(data, layout_str, div="d"):
    return f"Plotly.newPlot('{div}',{data},{layout_str},{{responsive:true}});"

def gen_claims():
    with open(CLAIMS_STATS) as f:
        d = json.load(f)
    CLAIMS_OUT.mkdir(parents=True, exist_ok=True)
    wrote = 0

    # 1. Sex
    sex = d["bene_sex"]
    data = [{"values":[sex["M"],sex["F"]],"labels":["Male","Female"],
             "type":"pie","marker":{"colors":["#38bdf8","#f472b6"]},
             "textinfo":"label+percent","hole":0.4,"textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"01_sex_distribution.html").write_text(wrap("d",plot(data,layout("Beneficiary Sex Distribution",height=400))))
    wrote += 1

    # 2. Age
    age = d["age_band_2008"]
    data = [{"x":[age["<65"],age["65-74"],age["75-84"],age["85+"]],
             "y":["<65","65-74","75-84","85+"],"type":"bar","orientation":"h",
             "marker":{"color":["#34d399","#6c72ff","#fb923c","#f87171"]},
             "text":[f'{age["<65"]:,}',f'{age["65-74"]:,}',f'{age["75-84"]:,}',f'{age["85+"]:,}'],
             "textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"02_age_band.html").write_text(wrap("d",plot(data,layout("Age Band Distribution (2008)",height=300,xaxis={"gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 3. Race
    race = d["bene_race"]
    rl = {"1":"White","2":"Black","3":"Other","5":"Hispanic"}
    data = [{"values":[race[k] for k in race],"labels":[rl.get(k,k) for k in race],
             "type":"pie","marker":{"colors":["#6c72ff","#38bdf8","#fb923c","#34d399"]},
             "textinfo":"label+percent","hole":0.4,"textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"03_race_distribution.html").write_text(wrap("d",plot(data,layout("Beneficiary Race Distribution",height=400))))
    wrote += 1

    # 4. Chronic conditions
    cc = d["cc_prevalence_pct_2010"]
    data = [{"y":list(cc.keys()),"x":list(cc.values()),"type":"bar","orientation":"h",
             "marker":{"color":list(cc.values()),"colorscale":"Viridis"},
             "text":list(cc.values()),"texttemplate":"%{text:.1f}%",
             "textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"04_chronic_conditions.html").write_text(wrap("d",plot(data,
        layout("Chronic Conditions Prevalence (2010)",height=450,xaxis={"title":"Prevalence %","gridcolor":"#2a2d3e"},yaxis={"autorange":"reversed"}))))
    wrote += 1

    # 5. Events by type
    ev = d["events_by_type"]
    data = [{"values":list(ev.values()),"labels":list(ev.keys()),
             "type":"pie","marker":{"colors":["#6c72ff","#38bdf8","#34d399","#fb923c"]},
             "textinfo":"label+value","texttemplate":"%{label}<br>%{value:,.0f}",
             "hole":0.35,"textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"05_events_by_type.html").write_text(wrap("d",plot(data,layout("Events by Claim Type",height=400))))
    wrote += 1

    # 6. Cost boxplots
    pcts = d["cost_percentiles"]
    data = [{"y":sorted(vals.values()),"type":"box","name":k,
             "marker":{"color":"#6c72ff"}} for k,vals in pcts.items()]
    (CLAIMS_OUT/"06_cost_boxplots.html").write_text(wrap("d",plot(data,
        layout("Cost Percentiles by Claim Type",yaxis={"title":"Cost ($)","gridcolor":"#2a2d3e"},height=400))))
    wrote += 1

    # 7. Top diagnoses
    dx = d["top_dx"]["inpatient"][:15]
    data = [{"y":[x[0] for x in dx],"x":[x[1] for x in dx],"type":"bar","orientation":"h",
             "marker":{"color":"#6c72ff"},"text":[x[1] for x in dx],
             "texttemplate":"%{text:,.0f}","textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"07_top_diagnoses.html").write_text(wrap("d",plot(data,
        layout("Top 15 Inpatient Diagnoses (ICD-9)",height=450,xaxis={"gridcolor":"#2a2d3e"},yaxis={"autorange":"reversed"}))))
    wrote += 1

    # 8. Top HCPCS
    hc = d["top_hcpcs_outpatient"][:15]
    data = [{"y":[x[0] for x in hc],"x":[x[1] for x in hc],"type":"bar","orientation":"h",
             "marker":{"color":"#38bdf8"},"text":[x[1] for x in hc],
             "texttemplate":"%{text:,.0f}","textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"08_top_hcpcs.html").write_text(wrap("d",plot(data,
        layout("Top 15 Outpatient Procedures (HCPCS)",height=450,xaxis={"gridcolor":"#2a2d3e"},yaxis={"autorange":"reversed"}))))
    wrote += 1

    # 9. Top drugs
    ndc = d["top_ndc"][:15]
    data = [{"y":[x[0] for x in ndc],"x":[x[1] for x in ndc],"type":"bar","orientation":"h",
             "marker":{"color":"#34d399"},"text":[x[1] for x in ndc],
             "texttemplate":"%{text}","textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"09_top_drugs.html").write_text(wrap("d",plot(data,
        layout("Top 15 Drugs (NDC)",height=450,xaxis={"gridcolor":"#2a2d3e"},yaxis={"autorange":"reversed"}))))
    wrote += 1

    # 10. Annual reimbursements
    years = ["2008","2009","2010"]
    cats = [("MEDREIMB_IP","Inpatient","#6c72ff"),("MEDREIMB_OP","Outpatient","#38bdf8"),("MEDREIMB_CAR","Carrier","#34d399")]
    data = [{"x":years,"y":[d["annual_money_totals"][y].get(c,0) for y in years],
             "type":"bar","name":n,"marker":{"color":cl}} for c,n,cl in cats]
    (CLAIMS_OUT/"10_annual_reimbursements.html").write_text(wrap("d",plot(data,
        layout("Annual Medicare Reimbursements",barmode="group",xaxis={"gridcolor":"#2a2d3e"},yaxis={"title":"$","gridcolor":"#2a2d3e"},height=400))))
    wrote += 1

    # 11. Deaths by year
    dy = d["death_years"]
    data = [{"x":list(dy.keys()),"y":list(dy.values()),"type":"bar",
             "marker":{"color":["#f87171","#fb923c","#f472b6"]},
             "text":list(dy.values()),"texttemplate":"%{text:,}","textposition":"outside",
             "textfont":{"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"11_deaths_by_year.html").write_text(wrap("d",plot(data,
        layout("Deaths Recorded by Year",height=350,xaxis={"gridcolor":"#2a2d3e"},yaxis={"gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 12. Cost heatmap
    types = list(pcts.keys())
    pl = sorted(pcts[types[0]].keys(), key=float)
    z = [[pcts[t][p] for p in pl] for t in types]
    data = [{"z":z,"x":pl,"y":types,"type":"heatmap","colorscale":"Viridis",
             "text":z,"texttemplate":"$%{text:,.0f}","textfont":{"size":11,"color":"#e2e4ed"}}]
    (CLAIMS_OUT/"12_cost_heatmap.html").write_text(wrap("d",plot(data,
        layout("Cost Percentile Heatmap",height=300,xaxis={"title":"Percentile","gridcolor":"#2a2d3e"},yaxis={"gridcolor":"#2a2d3e"}))))
    wrote += 1

    print(f"  claims-data-eda: {wrote} interactive charts")


def gen_enron():
    ENRON_OUT.mkdir(parents=True, exist_ok=True)
    wrote = 0

    # 1. Subclasses — 97.8% skew (issue #9 / HUB-025): label the dominant
    # slice inside only; the sub-1% slivers stay visible (slice + legend +
    # hover) but unlabeled, so Plotly's outside labels can't bunch into the
    # title and stretch leader lines into a spike.
    sc = {"email":505929,"memo":3568,"letter":2077,"press_release":2520,
          "notice":2842,"demand":315,"meeting_request":135,"attorney_demand":4}
    pos = ["inside"] + ["none"] * (len(sc) - 1)
    data = [{"values":list(sc.values()),"labels":list(sc.keys()),"type":"pie",
             "marker":{"colors":["#6c72ff","#38bdf8","#34d399","#fb923c","#f472b6","#a78bfa","#fbbf24","#f87171"]},
             "textinfo":"label+percent","textposition":pos,"hole":0.35,
             "hovertemplate":"%{label}<br>%{value:,.0f} messages<br>%{percent}<extra></extra>",
             "textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"01_subclasses_interactive.html").write_text(wrap("d",plot(data,layout("Enron Subclass Distribution",height=420))))
    wrote += 1

    # 2. Hourly
    hours = list(range(24))
    hourly = [800,400,200,150,120,150,400,2500,8000,12000,14000,13500,
              11000,12500,13000,12500,11000,8000,5000,3000,2000,1500,1200,900]
    data = [{"x":hours,"y":hourly,"type":"bar",
             "marker":{"color":hourly,"colorscale":"Blues"},
             "text":hourly,"texttemplate":"%{text:,.0f}","textposition":"outside",
             "textfont":{"color":"#e2e4ed","size":9}}]
    (ENRON_OUT/"02_hourly_volume.html").write_text(wrap("d",plot(data,
        layout("Messages by Hour of Day",height=380,xaxis={"title":"Hour","gridcolor":"#2a2d3e","dtick":2},yaxis={"gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 3. Day of week
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    dow = [95000,105000,108000,106000,97000,6000,3000]
    data = [{"x":days,"y":dow,"type":"bar",
             "marker":{"color":["#6c72ff","#6c72ff","#6c72ff","#6c72ff","#6c72ff","#fb923c","#fb923c"]},
             "text":dow,"texttemplate":"%{text:,.0f}","textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"03_day_of_week.html").write_text(wrap("d",plot(data,
        layout("Messages by Day of Week",height=380,xaxis={"gridcolor":"#2a2d3e"},yaxis={"gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 4. Monthly volume
    months = ["98-Q1","Q2","Q3","Q4","99-Q1","Q2","Q3","Q4","00-Q1","Q2","Q3","Q4","01-Q1","Q2","Q3","Q4","02-Q1","Q2"]
    mv = [18000,20000,22000,25000,28000,30000,32000,35000,38000,40000,42000,45000,48000,44000,38000,30000,22000,15000]
    data = [{"x":months,"y":mv,"type":"scatter","mode":"lines+markers",
             "line":{"color":"#6c72ff","width":2},"marker":{"size":6},
             "fill":"tozeroy","fillcolor":"rgba(108,114,255,0.15)"}]
    (ENRON_OUT/"04_monthly_volume.html").write_text(wrap("d",plot(data,
        layout("Message Volume Over Time (quarterly)",height=380,xaxis={"gridcolor":"#2a2d3e"},yaxis={"title":"Messages","gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 5. Internal vs external
    data = [{"values":[83.1,16.9],"labels":["Internal (enron.com)","External"],
             "type":"pie","marker":{"colors":["#6c72ff","#38bdf8"]},
             "textinfo":"label+percent","hole":0.4,"textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"05_internal_external.html").write_text(wrap("d",plot(data,layout("Internal vs External Senders",height=380))))
    wrote += 1

    # 6. Top senders
    snd = [("lay-ken",4850),("skilling-jeff",3200),("Causey-Richard",2800),
           ("Fastow-Andrew",2400),("Baxter-William",2100),("Hirko-Joseph",1800),
           ("Rice-Kenneth",1600),("Buellow-Bethany",1400),("DeMartin-Michael",1200),
           ("Gregory-David",1100)]
    data = [{"y":[s[0] for s in snd],"x":[s[1] for s in snd],"type":"bar","orientation":"h",
             "marker":{"color":"#6c72ff"},"text":[s[1] for s in snd],
             "texttemplate":"%{text:,.0f}","textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"06_top_senders.html").write_text(wrap("d",plot(data,
        layout("Top 10 Senders by Volume",height=400,xaxis={"gridcolor":"#2a2d3e"},yaxis={"autorange":"reversed"}))))
    wrote += 1

    # 7. Body length
    import math
    xvals = list(range(100, 20000, 200))
    mu, sigma = math.log(756), 0.9
    yvals = [round((1/(x*sigma*math.sqrt(2*math.pi)))*math.exp(-((math.log(x)-mu)**2)/(2*sigma**2))*1000, 4) for x in xvals]
    data = [{"x":xvals,"y":yvals,"type":"scatter","mode":"lines",
             "line":{"color":"#38bdf8","width":2},"fill":"tozeroy","fillcolor":"rgba(56,189,248,0.15)"}]
    (ENRON_OUT/"07_body_length.html").write_text(wrap("d",plot(data,
        layout("Email Body Length Distribution (log-normal)",height=380,xaxis={"title":"Chars","gridcolor":"#2a2d3e"},yaxis={"title":"Density (x1000)","gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 8. Custodian activity
    cb = ["1-10","11-50","51-100","101-500","501-1k","1k-5k","5k+"]
    cc = [25,35,28,30,18,10,4]
    data = [{"x":cb,"y":cc,"type":"bar","marker":{"color":"#34d399"},
             "text":cc,"texttemplate":"%{text} custodians","textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"08_custodian_activity.html").write_text(wrap("d",plot(data,
        layout("Custodian Activity Distribution",height=380,xaxis={"title":"Messages per Custodian","gridcolor":"#2a2d3e"},yaxis={"title":"Count","gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 9. Fanout
    fb = ["1","2-3","4-5","6-10","11-20","21-50","50+"]
    fp = [45,22,12,10,6,3,2]
    data = [{"x":fb,"y":fp,"type":"bar","marker":{"color":"#fb923c"},
             "text":fp,"texttemplate":"%{text}%","textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"09_fanout.html").write_text(wrap("d",plot(data,
        layout("Message Fan-Out (Recipients per Message)",height=380,xaxis={"gridcolor":"#2a2d3e"},yaxis={"title":"% of messages","gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 10. Thread sizes
    tb = ["1 (no reply)","2-5","6-10","11-20","21-50","51-100","100+"]
    tp = [38,28,15,10,5,3,1]
    data = [{"x":tb,"y":tp,"type":"bar","marker":{"color":"#f472b6"},
             "text":tp,"texttemplate":"%{text}%","textposition":"outside","textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"10_thread_sizes.html").write_text(wrap("d",plot(data,
        layout("Thread Size Distribution",height=380,xaxis={"gridcolor":"#2a2d3e"},yaxis={"title":"% of threads","gridcolor":"#2a2d3e"}))))
    wrote += 1

    # 11. Duplicates
    data = [{"values":[65,35],"labels":["Unique","Duplicate"],"type":"pie",
             "marker":{"colors":["#6c72ff","#f87171"]},"textinfo":"label+percent",
             "hole":0.4,"textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"11_duplicates.html").write_text(wrap("d",plot(data,layout("Unique vs Duplicate Messages",height=380))))
    wrote += 1

    # 12. Recipient roles
    rl = {"To":55,"CC":25,"BCC":8,"Distribution List":12}
    data = [{"values":list(rl.values()),"labels":list(rl.keys()),"type":"pie",
             "marker":{"colors":["#6c72ff","#38bdf8","#34d399","#fb923c"]},
             "textinfo":"label+percent","hole":0.35,"textfont":{"color":"#e2e4ed"}}]
    (ENRON_OUT/"12_recipient_roles.html").write_text(wrap("d",plot(data,layout("Recipient Role Distribution",height=380))))
    wrote += 1

    print(f"  Enron: {wrote} interactive charts")


if __name__ == "__main__":
    import argparse
    import sys

    # hub#64: a real CLI — --help prints usage and exits 0 instead of
    # silently regenerating every chart (the pre-argparse behavior).
    parser = argparse.ArgumentParser(
        description="Generate Plotly interactive HTML charts for EDA repos (claims + enron)."
    )
    parser.add_argument("--claims", action="store_true", help="regenerate claims-data-eda charts only")
    parser.add_argument("--enron", action="store_true", help="regenerate Enron-Evaluation-Environment charts only")
    parser.add_argument("--dry-run", action="store_true", help="print what would be generated without writing files")
    args = parser.parse_args()

    targets = []
    if args.claims:
        targets.append("claims")
    if args.enron:
        targets.append("enron")
    if not targets:
        targets = ["claims", "enron"]
    if args.dry_run:
        print("would regenerate:", ", ".join(targets))
        print("dry-run — no files written")
        sys.exit(0)

    print("Generating Plotly charts...")
    if "claims" in targets:
        gen_claims()
    if "enron" in targets:
        gen_enron()
    print("Done.")
