<div align="center">

# 🔗 llm-mailroom-graph

**Interactive knowledge graph of [llm-mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) — the 13-node LangGraph pipeline with Gmail triage and relations clerk auxiliary flows, visualized as a walkable architecture map.**

[![Python 3.11+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Extractor](https://img.shields.io/badge/extractor-graphify%200.9.53-orange)](https://github.com/nicholasgasior/graphify)
[![Live Site](https://img.shields.io/badge/live-site-blue)](https://LLM-Mailroom-Services.github.io/llm-mailroom-graph/)
[![Contributor](https://img.shields.io/badge/contributor-Exios66-blue)](https://github.com/Exios66)

**Live site:** [llm-mailroom-graph](https://LLM-Mailroom-Services.github.io/llm-mailroom-graph/)

</div>

---

## How to Read It

<div align="center">

| Page | What it is |
|:---|:---|
| [Architecture map](./index.html) | Default view. Three zoom levels: **layers → modules → symbols**. Conveyor strip jumps to the 13 LangGraph nodes. |
| [Module tree](./tree.html) | Filesystem collapsible tree of the same graph. |
| [Report](./report.html) | God nodes, communities, bridges, suggested questions. |
| [Classic vis](./graph.html) | Graphify's stock force-directed canvas, if you want the hairball. |
| [GRAPH_REPORT.md](./GRAPH_REPORT.md) | Machine-written audit trail. |

</div>

## Corpus

| Metric | Value |
|:---|:---|
| **Included** | `src/agents`, `graph`, `pipeline`, `api`, `storage`, `observability`, `llm`, `schemas`, `langchain_agents`, `legalbench`, `scripts` |
| **Excluded** | `src/tests`, `notebooks`, `.opencode/skills` (vendored assistant tools), docs |
| **Extractor** | graphify 0.9.53, `--code-only` AST, 0 LLM tokens |
| **Code symbols** | 1,905 |
| **Edges** | 4,557 |
| **Communities** | 104 |
| **Source files** | 130 |

## Rebuild

```bash
git clone https://github.com/Exios66/llm-mailroom.git /tmp/llm-mailroom
# copy the .graphifyignore from this repo's last rebuild notes
uv tool install graphifyy
graphify extract /tmp/llm-mailroom --code-only --force --resolution 0.4 --exclude-hubs 99
graphify cluster-only /tmp/llm-mailroom --no-label --no-viz --resolution 0.4 --exclude-hubs 99
graphify tree --graph /tmp/llm-mailroom/graphify-out/graph.json --output tree.html --label llm-mailroom
```

Then regenerate `index.html` / `report.html` from `graph.json`:

```bash
graphify export html --graph /tmp/llm-mailroom/graphify-out/graph.json → graph.html
python3 scripts/regenerate_graph_site.py /tmp/llm-mailroom/graphify-out/graph.json . → index.html + report.html
```

---

<div align="center">

**[llm-mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)** ·
**[llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction)** ·
**[llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring)**

<sub>Built by the governed evaluation family under <a href="https://github.com/Exios66">@Exios66</a> · 2026</sub>

</div>
