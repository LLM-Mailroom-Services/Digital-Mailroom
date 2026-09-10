# Fixture attribution

Text fixtures in this directory are **copied from**
[`Exios66/llm-mailroom`](https://github.com/Exios66/llm-mailroom) `v0.6.0`
(`src/tests/fixtures/` and `docs/examples/sources/`). They are original
synthetic documents written for that repo unless noted.

The full 22-sample PDF pilot (CUAD / Atticus, CC BY 4.0) is **not** vendored
here (binary, multi-MB). Pull it from the mailroom checkout:

```bash
sandbox fetch-deps
# then copy vendor/llm-mailroom/docs/examples/samples/
```

See mailroom `docs/examples/samples/ATTRIBUTION.md` for CUAD license terms.

Tiny HF JSONL under `hf/` is a **synthetic** one-doc-per-class slice matching
the `Lucius-Morningstar/mailroom-corpus` schema (not Hub content). Use
`sandbox datasets pull` for real Hub rows.

Tiny PDF/PNG under `intake/` are original sandbox fixtures (ASCII PDF + 1×1 PNG)
for offline transcriber / image-extractor wiring tests, not the CUAD pilot.

`serving/local_vs_api.json` is a **synthetic** timing pair for the dojo
`get_suite("local_vs_api")` smoke (Ollama vs OpenRouter identity). Values are
not live measurements; GPU/KV fields are local-only.
