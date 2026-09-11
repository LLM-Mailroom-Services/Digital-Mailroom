# Modal doc-pipeline job queue — implementation plan (DMR-059)

Status: **plan** (approved → Phase A). Modeled on the Modal docs tutorial
`09_job_queues/doc_ocr_jobs.py` (`modal run doc_ocr_jobs.py`): an App with a
GPU inference Function, a model-cache Volume, a `local_entrypoint` for CLI
kicks, and `modal deploy` + `Function.from_name(...).spawn(...)` as the async
job-queue consumption pattern.

## 1. The example pattern → what it maps to here

| `doc_ocr_jobs.py` | Sandbox equivalent (existing) | Gap |
| --- | --- | --- |
| `modal.App("example-doc-ocr-jobs")` | `sandbox-job` (evals), `sandbox-vllm` (serving) | no **document** queue app |
| `parse_document(bytes)` GPU Function (L40S, retries=3) | `deploy/modal_job.py::run_job` (CPU, spec-locked) | no per-document entry function |
| `marker` models on a Volume (`marker-cache`) | `sandbox-hf-cache` → `/root/.cache/huggingface` | models live on the vLLM side, not per-doc |
| `@app.local_entrypoint` (`modal run …`) | `modal_job.py::main` (prints deploy hint) | add a real doc-submit entrypoint |
| `Function.from_name(...).spawn(doc)` consumer | `job/remote.py::fire` (spec-driven) | add doc-bytes consumer |

The mailroom pipeline's "structured data" step is NOT an OCR model — it is
the **13-node LangGraph pipeline** (`intake → pdf_transcriber/image_extractor
→ sorter → specialists → judge → compile`) talking to the **already-deployed
`sandbox-vllm`** OpenAI-compatible endpoint. So the new app is a CPU-side
document job queue whose LLM is the existing Modal vLLM app; no GPU needed in
the new app itself.

## 2. New file: `deploy/modal_doc_jobs.py` (`sandbox-doc-jobs` app)

Same DNA as `deploy/modal_job.py` (bundled image, Volume + Dict, DMR-057
vendored family), with a document front door:

- **Image** — `modal.Image.debian_slim(python_version="3.12")`
  `.add_local_python_source("mailroom_sandbox")` + `config/`,
  `data/fixtures/`, `vendor/llm-mailroom/src`, `vendor/llm-dojo-scoring/src`
  (DMR-057 — no git pins), `.uv_pip_install(httpx, openai, pydantic, pyyaml,
  python-dotenv, structlog, huggingface_hub, pyarrow, langfuse,
  opentelemetry-sdk, opentelemetry-exporter-otlp-proto-http)` + the
  PDF/image stage deps: `pypdf`, `pdfplumber`, `pillow`, `pytesseract`
  (CPU OCR for scanned pages), `.env({"SANDBOX_ROOT": "/root",
  "DEFAULT_PROVIDER": "vllm", "VLLM_BASE_URL":
  "https://<ws>--sandbox-vllm-serve.modal.run/v1"})`.
- **Volumes / Dicts** — reuse `sandbox-runs` (job state) + new
  `sandbox-doc-inbox` (raw doc bytes, staged per doc id) + `sandbox-doc-state`
  Dict (per-doc progress mirror, same shape as `sandbox-job-state`).
- **Stage A `extract_text(document_id)`** (CPU, `retries=3`): pull bytes
  from the inbox Volume, run the mailroom `pdf_transcriber`/`image_extractor`
  agent surface via the vendored pipeline (text pages + image frames), write
  `text.jsonl` back to the inbox. This is the `parse_document` analog — a
  small deterministic stage the pipeline consumes.
- **Stage B `process_document(document_id)`** (CPU, `timeout=45min`): load
  the extracted text, run the connected mailroom graph through the vLLM
  provider (`DEFAULT_PROVIDER=vllm`), persist the matter record to the inbox
  Volume, mirror progress to the Dict, append the experiment-log record.
  Reuses `mailroom_sandbox.eval.runners`/`job.runner` seams so scoring,
  tracing (OTEL sink from the run lock), and checkpoints stay identical to
  `sandbox-job`.
- **`@app.local_entrypoint`** — `modal run deploy/modal_doc_jobs.py
  --document <path.pdf>` reads a local file, uploads to the inbox, spawns
  both stages, prints the matter record (the `modal run doc_ocr_jobs.py`
  experience). `--list` prints open doc ids from the Dict.
- **Consumer seam** — `modal.Function.from_name("sandbox-doc-jobs",
  "process_document").spawn(document_id)` from any Python (mirrors the
  tutorial's web-app path); CLI wiring follows in Phase C.

## 3. Why this shape (decisions)

- **No GPU in the new app.** The heavy lifting already lives in
  `sandbox-vllm` (L4). doc_ocr uses an L40S because Marker is a vision
  model; our equivalent (pdf_transcriber/image_extractor) runs over the
  vLLM endpoint, so the queue app stays CPU-only and cheap. A future
  marker-style vision stage can add `gpu="l40s"` exactly like the tutorial.
- **Bytes never re-enter the pipeline via memory.** Docs are staged on the
  inbox Volume and referenced by id — spawn payloads stay small, resumes
  re-read from the Volume (same durability argument as `sandbox-runs`).
- **One app, two stages, one Dict.** Extraction and pipeline are separable
  functions so Modal scales them independently and `retries` cover each
  half; the Dict gives external status without polling logs.
- **Bearer discipline.** No `unauthenticated=True`; the vLLM call carries
  `VLLM_API_KEY` from the deploy Secret. Never commit tokens.

## 4. Verification plan (network-free first, live last)

1. `tests/test_modal_doc_jobs.py` — stub `modal` (pattern of
   `tests/test_modal_vllm.py`): pin app name/volumes/Dict names, image
   bundle paths (vendored family present), stage signatures, env contract
   (`DEFAULT_PROVIDER=vllm` forced, `VLLM_BASE_URL` from deploy env),
   local-entrypoint argv handling.
2. `modal run deploy/modal_doc_jobs.py --document data/fixtures/intake/hello.pdf`
   against a **mock** run (no vLLM) — proves extraction + graph wiring end
   to end without GPU spend.
3. Live smoke: `sandbox-vllm` deployed → same command live, 1–3 docs,
   recorded in `reports/experiment_log.jsonl`; state what it costs
   (L4 ≈ $0.80/hr warm, scaledown 15min).
4. Parity + suite (230 passed / 1 skipped) + propagation to fork + parent.

## 5. Phases

- **Phase A (approved plan → code):** `deploy/modal_doc_jobs.py` +
  `tests/test_modal_doc_jobs.py` + this doc + knob rows in
  `config/.env.example`; mock smoke; propagate.
- **Phase B:** live vLLM smoke against the deployed `sandbox-vllm`.
- **Phase C (optional):** CLI wiring — `sandbox doc-jobs submit|status`
  (or fold into `sandbox run` with `job.mode: doc-jobs`), status mirroring,
  record pull-back to the experiment log.

## 6. Open questions for the human

1. Stage A extraction: is `pypdf/pdfplumber + pytesseract` (CPU OCR)
   enough, or do you want a Marker-style GPU vision stage from day one?
2. Should `process_document` run the FULL 13-node graph (incl. judge) or a
   reduced `sorter + specialists + compile` path like the reduced agent
   profile (HUB-015)?
3. CLI: Phase C as its own command family, or fold into `sandbox run`?