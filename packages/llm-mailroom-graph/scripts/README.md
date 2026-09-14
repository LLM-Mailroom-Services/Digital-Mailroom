<div align="center">

# ⚙️ LLM Mailroom Graph Scripts

**Utility scripts for the llm-mailroom-graph package.**

</div>

---

## Purpose

Scripts for generating and maintaining the document graph visualization.

## Usage

```bash
cd packages/llm-mailroom-graph
python3 scripts/regenerate_graph_site.py [NEW_GRAPH.json] [OUT_DIR]
# NEW_GRAPH.json defaults to ./graph.json; OUT_DIR defaults to the package
# root. Set GRAPH_COMMIT=<sha> to stamp the rebuilt pages with a different
# source commit.
```

## Related Files

- `README.md` — Package overview
- `docs/` — Documentation
