#!/usr/bin/env python3
"""Build the hub's data-flow map, retaining both pipeline and sandbox traces.

Run this file to regenerate constellation.svg; --check checks bytes read-only.
Label backings are painted after animation and nodes. Runtime-free, deterministic,
standard-library artwork; the standalone repos own their separate shared kit.
"""
import argparse
from html import escape
from pathlib import Path

NODES = [
    ('eda',40,70,240,'mailroom-corpus-eda','EDA + centralized HF uploads','virtual member · no build','#38bdf8',False),
    ('hf',410,70,240,'HF Hub','mailroom-dataset · v9','external · pinned tag','#facc15',True),
    ('sandbox',210,260,240,'local-mailroom-sandbox','offline/local + Modal/vLLM GPU','testing harness','#a78bfa',False),
    ('pipeline',650,260,240,'llm-mailroom','13-node LangGraph pipeline','FastAPI producer','#22c55e',False),
    ('dojo',435,470,240,'llm-dojo-scoring','ALL scoring engine + metrics','error analysis & interpretation','#f59e0b',False),
    ('langfuse',990,400,200,'Langfuse','external · trace store','','#f472b6',True),
    ('viz',980,150,240,'The-Mailroom','pixel-art visualizer','shared by pipeline + sandbox','#f472b6',False),
]
EDGES = [
    ('e1','publishes','M280 118 H410','#38bdf8',345,108,80),
    ('e2','pinned pull','M500 166 C470 210 400 220 360 260','#38bdf8',400,212,92),
    ('e3','pinned pull','M560 166 C620 210 700 220 740 260','#38bdf8',700,212,92),
    ('e4','executes','M450 308 H650','#a78bfa',550,296,78),
    ('e5','scores with','M360 356 C390 420 440 450 480 470','#f59e0b',375,426,90),
    ('e6','scores with','M740 356 C700 420 650 450 610 470','#f59e0b',700,426,90),
    ('e7','traces','M890 320 C940 340 950 410 990 430','#f472b6',947,396,60),
    ('e8','feeds','M1080 400 V246','#f472b6',1110,322,48),
    ('e9','sandbox traces','M210 356 C200 680 1000 680 1080 496','#f472b6',640,645,128),
]


def text(x, y, label, size=12, color='#94a3b8', weight=400, extra=''):
    """Draw an escaped text node with no downloaded fonts."""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}"{extra}>{escape(label)}</text>'


def build():
    """Render all static labels above decorative particles and pulse outlines."""
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720" role="img" aria-labelledby="t d" font-family="ui-sans-serif,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">',
         '<title id="t">The Mailroom constellation</title><desc id="d">Corpus EDA publishes the pinned dataset; sandbox and pipeline pull it, the sandbox executes the pipeline, and both score with Dojo. Both send traces to Langfuse, which feeds The-Mailroom.</desc>',
         '<defs><linearGradient id="bg" x2="0" y2="1"><stop stop-color="#0b1220"/><stop offset="1" stop-color="#140f2e"/></linearGradient><filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter></defs>',
         '<style>@media(prefers-reduced-motion:reduce){.motion{display:none}}</style>',
         '<rect width="1280" height="720" rx="24" fill="url(#bg)"/>',
         text(40,44,'THE CONSTELLATION · HOW DATA MOVES',13,'#8b9bb4',700,' letter-spacing="3"')]
    for eid,_,path,color,_,_,_ in EDGES:
        dash=' stroke-dasharray="6 6"' if color=='#f472b6' else ''
        out.append(f'<path id="{eid}" d="{path}" fill="none" stroke="{color}" stroke-width="2.2"{dash}/>')
    for i,(eid,_,_,color,_,_,_) in enumerate(EDGES):
        out.append(f'<circle class="motion" r="5" fill="{color}" filter="url(#soft)"><animateMotion dur="{1.4+i*.2:.1f}s" begin="{i*.2:.1f}s" repeatCount="indefinite"><mpath href="#{eid}"/></animateMotion></circle>')
    out.append('<rect class="motion" x="650" y="260" width="240" height="96" rx="14" fill="none" stroke="#22c55e"><animate attributeName="stroke-width" values="2;9;2" dur="2.4s" repeatCount="indefinite"/></rect>')
    for key,x,y,w,name,line1,line2,color,external in NODES:
        dash=' stroke-dasharray="7 5"' if external else ''
        out.append(f'<g data-node="{key}"><rect x="{x}" y="{y}" width="{w}" height="96" rx="14" fill="#0f172a" stroke="{color}" stroke-width="2"{dash}/>')
        out.append(text(x+16,y+34,name,16,'#e2e8f0',700));out.append(text(x+16,y+58,line1))
        if line2:out.append(text(x+16,y+78,line2,12,'#64748b'))
        out.append('</g>')
    for eid,label,_,_,x,y,w in EDGES:
        out.append(f'<g data-edge-label="{eid}" transform="translate({x} {y})"><rect data-callout-box="" x="{-w/2}" y="-16" width="{w}" height="32" rx="8" fill="#10142a"/>'+text(0,4.5,label,13,extra=' text-anchor="middle" font-style="italic"')+'</g>')
    for y,label,dash in [(620,'workspace member',''),(646,'external service',' stroke-dasharray="4 3"')]:
        out.append(f'<rect x="40" y="{y-11}" width="16" height="12" rx="3" fill="none" stroke="#e2e8f0"{dash}/>'+text(64,y,label))
    return '\n'.join(out)+'\n</svg>\n'


def main():
    """Write the SVG or refuse generated drift without changing files."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    path=Path(__file__).with_name('constellation.svg');content=build()
    if args.check:
        if path.read_text()!=content:parser.exit(1,'constellation.svg drift\n')
    else:path.write_text(content)
    print('Constellation SVG matches' if args.check else 'Constellation SVG written')


if __name__=='__main__':main()
