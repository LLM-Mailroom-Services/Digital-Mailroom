#!/usr/bin/env python3
"""Regenerate the llm-mailroom-graph site HTMLs (index.html, report.html) from graph.json.

Reconstructs the generator that produced the committed pages: index.html embeds
const DATA/GODS/LAYERS/RELS, report.html embeds rendered stats/gods/communities.
Community names are carried over from the previous graph.json where membership
overlaps (architectural names survive rebuilds), else fall back to a dominant
source-dir label.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# hub#45: derive the artifact paths from THIS script's own location so the
# recipe runs from any checkout — the old hardcoded /tmp/opencode/... paths
# crashed with FileNotFoundError on every other machine. argv overrides stay:
#   python3 scripts/regenerate_graph_site.py [NEW_GRAPH.json] [OUT_DIR]
HERE = Path(__file__).resolve().parent.parent
OLD_GRAPH = HERE / "graph.json"  # committed graph: community-name carryover
NEW_GRAPH = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "graph.json")
INDEX_OLD = HERE / "index.html"
REPORT_OLD = HERE / "report.html"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else HERE)

BUILT = datetime.now(timezone.utc).strftime("%Y-%m-%d")
# The graph's source commit: llm-mailroom pinned tip (v0.7.1, the corpus
# re-pin to GT-closure revision 46a4d3c2). Override with GRAPH_COMMIT when
# rebuilding from a different checkout.
COMMIT = os.environ.get("GRAPH_COMMIT", "2a212e76a62b")
GRAPHIFY_VER = "0.9.53"

old = json.loads(OLD_GRAPH.read_text())
new = json.loads(NEW_GRAPH.read_text())

def node_keys(n: dict) -> dict:
    return n["id"], n.get("label", n["id"]), n.get("file_type", "code"), n.get("source_file", "")

old_members = {}
for n in old["nodes"]:
    old_members.setdefault(n.get("community"), set()).add(node_keys(n))

new_comm_name = {}
for n in new["nodes"]:
    new_comm_name.setdefault(n.get("community"), None)

# name new communities by overlap with old ones
old_names = {n.get("community"): n.get("community_name") for n in old["nodes"] if n.get("community_name")}
for cid, members in sorted(new_comm_name.items()):
    if cid is None:
        continue
    new_ids = {node_keys(n) for n in new["nodes"] if n.get("community") == cid}
    best, best_overlap = None, 0
    for ocid, omembers in old_members.items():
        overlap = len(new_ids & omembers)
        if overlap > best_overlap:
            best, best_overlap = old_names.get(ocid), overlap
    new_comm_name[cid] = best or None

# fallback: dominant source dir
for cid, name in list(new_comm_name.items()):
    if name or cid is None:
        continue
    nodes = [n for n in new["nodes"] if n.get("community") == cid]
    dirs = Counter((n.get("source_file") or "").split("/")[0] for n in nodes)
    dom = dirs.most_common(1)[0][0] if dirs else "misc"
    new_comm_name[cid] = dom.replace("_", " ").title()
    if len(dirs) > 1:
        plural = f" ({len(nodes)})"
        new_comm_name[cid] = f"{dom.replace('_', ' ').title()} {plural}".strip()

# degree map
degree = Counter()
for e in new["links"]:
    degree[e["source"]] += 1
    degree[e["target"]] += 1

layer_of = {}
for n in new["nodes"]:
    sf = n.get("source_file") or ""
    parts = sf.split("/")
    ly = parts[0] if parts else "other"
    layer_of.setdefault(ly, set()).add(n["id"])

# ---- index.html DATA ----
nodes_out = []
for n in new["nodes"]:
    sf = n.get("source_file") or ""
    nodes_out.append({
        "id": n["id"],
        "l": n.get("label", n["id"]),
        "t": n.get("file_type", "code"),
        "sf": sf,
        "ly": sf.split("/")[0] if sf else "other",
        "c": n.get("community", 0),
        "cn": new_comm_name.get(n.get("community")) or "misc",
        "d": degree.get(n["id"], 0),
        "loc": n.get("source_location", ""),
    })

edges_out = []
for e in new["links"]:
    edges_out.append({"f": e["source"], "t": e["target"], "r": e.get("relation", "imports"), "k": (e.get("_origin") or "EXTRACTED").upper()})

labels_out = {str(c): (nm or "misc") for c, nm in sorted(new_comm_name.items()) if c is not None}

DATA = {"nodes": nodes_out, "edges": edges_out, "labels": labels_out}

# ---- GODS (top 10 by degree, code nodes only) ----
gods = []
for nid, d in degree.most_common():
    node = next(n for n in new["nodes"] if n["id"] == nid)
    if node.get("_callable") is not True:
        continue
    gods.append({
        "label": node.get("label", node["id"]),
        "degree": d,
        "id": node["id"],
        "file": node.get("source_file", ""),
    })
    if len(gods) >= 10:
        break

# ---- LAYERS (preserve titles/blurbs from old page; update counts) ----
old_html = INDEX_OLD.read_text()
m_layers = re.search(r"const LAYERS = (\[.*?\]);", old_html, re.S)
old_layers = json.loads(m_layers.group(1)) if m_layers else []
layer_counts = {k: len(v) for k, v in layer_of.items()}
layers = []
for l in old_layers:
    cnt = layer_counts.get(l["id"], 0)
    layers.append({**l, "count": cnt})
for lid, cnt in layer_counts.items():
    if not any(l["id"] == lid for l in layers) and lid:
        layers.append({"id": lid, "title": lid, "blurb": "", "color": "#64748b", "count": cnt})

# ---- RELS ----
rel_cnt = Counter(e.get("relation", "imports") for e in new["links"])
rels = dict(rel_cnt.most_common())

# PIPELINE (13 nodes) kept from old page
m_pipe = re.search(r"const PIPELINE = (\[.*?\]);", old_html, re.S)
pipeline = json.loads(m_pipe.group(1)) if m_pipe else []

# ---- write index.html ----
out = old_html
out = re.sub(r"const DATA = .*?;\n", lambda m: "const DATA = " + json.dumps(DATA, separators=(",", ":")) + ";\n", out, count=1, flags=re.S)
out = re.sub(r"const GODS = .*?;\n", lambda m: "const GODS = " + json.dumps(gods, separators=(",", ":")) + ";\n", out, count=1, flags=re.S)
out = re.sub(r"const LAYERS = .*?;\n", lambda m: "const LAYERS = " + json.dumps(layers, separators=(",", ":")) + ";\n", out, count=1, flags=re.S)
out = re.sub(r"const RELS = .*?;\n", lambda m: "const RELS = " + json.dumps(rels, separators=(",", ":")) + ";\n", out, count=1, flags=re.S)
out = re.sub(r"const PIPELINE = .*?;\n", lambda m: "const PIPELINE = " + json.dumps(pipeline, separators=(",", ":")) + ";\n", out, count=1, flags=re.S)
out = re.sub(r"graph · 7dc57874 · 2026-08-28", f"graph · {COMMIT} · {BUILT}", out)
out = re.sub(r"llm-mailroom@7dc57874", f"llm-mailroom@{COMMIT}", out)
out = re.sub(r"7dc57874cd4206fa6470a887c38b566f2168daf8", "2a212e76a62b98f6eba451ff6f3c5bc96039ae37", out)
out = re.sub(r"commit/7dc57874", f"commit/{COMMIT}", out)
(OUT / "index.html").write_text(out)
print(f"index.html: {len(nodes_out)} nodes, {len(edges_out)} edges, {len(labels_out)} communities, {len(gods)} gods")

# ---- report.html ----
rep = REPORT_OLD.read_text()
n_nodes, n_edges = len(new["nodes"]), len(new["links"])
n_comm = len(set(n.get("community") for n in new["nodes"] if n.get("community") is not None))
n_files = len(set(n.get("source_file") for n in new["nodes"] if n.get("source_file")))

rep = rep.replace("built <b>2026-08-28</b>", f"built <b>{BUILT}</b>")
rep = rep.replace("commit <b>7dc57874</b>", f"commit <b>{COMMIT}</b>")
rep = rep.replace("graphify <b>0.9.50</b>", f"graphify <b>{GRAPHIFY_VER}</b>")
rep = rep.replace('data-count="1730"', f'data-count="{n_nodes}"')
rep = rep.replace('data-count="4181"', f'data-count="{n_edges}"')
rep = rep.replace('data-count="102"', f'data-count="{n_comm}"')
rep = rep.replace('data-count="121"', f'data-count="{n_files}"')
rep = rep.replace("74 shown · 28 thin omitted", f"{min(n_comm, 74)} shown · {max(n_comm - 74, 0)} thin omitted")

# god rows
god_rows = "".join(
    f'<div class="godrow"><div class="godname"><code>{g["label"]}</code></div>'
    f'<div class="godbarwrap"><div class="godbar" data-w="{100.0 * g["degree"] / max(gods[0]["degree"], 1):.1f}"></div>'
    f'<span class="godval">{g["degree"]}</span></div></div>'
    for g in gods
)
rep = re.sub(r'(<section id="gods">.*?<div class="panel">).*?(</div>\s*</section>)', lambda m: m.group(1) + god_rows + m.group(2), rep, count=1, flags=re.S)

# communities list (top 40 by node count, kept filterable)
comms = Counter(n.get("community_name") or new_comm_name.get(n.get("community")) or "misc" for n in new["nodes"])
com_rows = "".join(
    f'<div class="comrow" data-com="{c}"><span class="comname">{c}</span><span class="comcnt">{v} symbols</span></div>'
    for c, v in comms.most_common(60)
)
m_com = re.search(r'(<section id="communities">.*?<div class="complist">).*?(</div>\s*</section>)', rep, flags=re.S)
if m_com:
    inner = m_com.group(0).replace(m_com.group(1), "", 1).replace(m_com.group(2), "", 1)
    if "comrow" not in inner or len(inner) > 5000:
        rep = rep[:m_com.start()] + m_com.group(1) + com_rows + m_com.group(2) + rep[m_com.end():]
    else:
        rep = re.sub(r'(<section id="communities">.*?<div class="complist">).*?(</div>\s*</section>)', lambda m: m.group(1) + com_rows + m.group(2), rep, flags=re.S)

# What changed section — fresh copy with the current commit + stats
wc_arrow = chr(0x2192)
what_changed = (
    '<section id="fresh">\n<h2>What changed</h2>\n<div class="panel note">\n'
    '<p>Rebuilt from <a href="https://github.com/Exios66/llm-mailroom/commit/'
    '2a212e76a62b98f6eba451ff6f3c5bc96039ae37"><code>2a212e76</code></a> '
    '(mailroom v0.7.1 + mailroom-dataset v9 corpus, GT-closure revision '
    '46a4d3c2 + ground truth: pared LLM load, 13-node layered-state pipeline, '
    'Gmail triage + relations clerk auxiliary flows, review-resolve tray, '
    'judge/arbiter lanes, deterministic field scoring, and the '
    'Digital-Mailroom monorepo docs alignment).</p>'
    '<p style="margin-top:.7rem">This build indexes <b>production '
    '<code>src/</code> only</b> (' + str(n_files) + ' files) so the map follows the live '
    'architecture: <code>review_resolve.py</code>, <code>posthoc_gt.py</code>, '
    '<code>agent_eval.py</code>, specialist suites, honesty-gap metadata, and '
    'the 13-node conveyor (human_review pauses with <code>interrupt()</code>). '
    'Tests, notebooks, and <code>.opencode/skills</code> are excluded on purpose.</p>'
    '<p style="margin-top:.7rem">Navigate the <a href="./">architecture map</a> '
    'as <b>layers ' + wc_arrow + ' modules ' + wc_arrow + ' symbols</b>. '
    'The 13-node conveyor strip at the top jumps to <code>intake_node</code>, '
    '<code>classify_node</code>, Lane A/B, Boss, catalog, and archive. '
    'Comments (rationale nodes) are hidden until you uncheck them. '
    'Double-click a symbol to isolate its neighborhood.</p>\n</div>\n</section>'
)
rep = re.sub(r'<section id="fresh">.*?</section>', lambda m: what_changed, rep, count=1, flags=re.S)

# footer stamp
rep = re.sub(
    r'<span>Derived artifact of https://github.com/Exios66/llm-mailroom @ [0-9a-f]{7,40} · graphify [0-9.]+ · local AST, 0 tokens</span>',
    f'<span>Derived artifact of https://github.com/Exios66/llm-mailroom @ {COMMIT} · graphify {GRAPHIFY_VER} · local AST, 0 tokens</span>',
    rep, count=1)
(OUT / "report.html").write_text(rep)
print("report.html regenerated")