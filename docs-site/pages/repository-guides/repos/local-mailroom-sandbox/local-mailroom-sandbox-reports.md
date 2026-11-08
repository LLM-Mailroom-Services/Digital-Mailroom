---
description: GPU and specialist-grid results.
icon: gauge-high
title: local-mailroom-sandbox reports
---

# Run reports

Measured GPU and specialist-grid results from [Exios66/local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox). Canonical write-ups, cards, and serving JSON live in that repo's `reports/`. Figures from those runs are on [Visuals](local-mailroom-sandbox-visuals.md). Snapshot as of the sandbox `main` tip used to build this page (2026-10).

Parent guide: [local-mailroom-sandbox](./). Dedicated manuals: [Documentation](local-mailroom-sandbox-docs.md).

The interactive hub is [`reports/dashboard/mailroom-reports.html`](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/dashboard/mailroom-reports.html) (tabs: Overview · Specialists · Serving · API models · Modal vs API · Classifier · ML diagnostics · Data quality). Cross-repo markdown + SVG copies are published from that hub into [mailroom-issues/reports](https://github.com/LLM-Mailroom-Services/mailroom-issues/tree/main/reports) and the static site [https://llm-mailroom-services.github.io/mailroom-issues/](https://llm-mailroom-services.github.io/mailroom-issues/).

## SAND-37 — specialist grid score and cost

Qwen3-8B-AWQ on vLLM, NVIDIA L4, Hub `Lucius-Morningstar/mailroom-dataset` @ `ed7576b6` (data commit of tag `v9.1`). Start here: [SAND-37-MASTER-SCORE-COST-CARD.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/SAND-37/SAND-37-MASTER-SCORE-COST-CARD.md). Detail: [SAND-37-MASTER-APPENDIX.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/SAND-37/SAND-37-MASTER-APPENDIX.md). Index: [reports/SAND-37/README.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/SAND-37/README.md).

Key findings from the master card:

1. **2×L4 at C32 raises throughput +99% at +0.4% cost per document** on the same 250 documents (Experiment 2 → 3). Median latency rises ×1.4–1.8. GPU count and client concurrency changed together.
2. **Larger runs cost less per document.** On the four unchanged specialists, n = 100 cuts GPU cost per document by 19% against n = 50 (Experiment 3 → 4). 1 of 400 documents failed (0.25%).
3. **Merger is the quality gap; the † settings narrow it.** On the same 50 agreements, MAUD accuracy rises 0.035 → 0.140 and coverage rises 23% → 69% (35 better, 1 worse). GPU cost per agreement is 4.5×.

**SAND-040 (Experiment 4)** ran on one 32K-window deploy: correspondence, insurance claims and corporate records 100/100 ok, contracts 99/100, merger † 50/50. The † merger cell reads each whole agreement in chunks. Its settings:

* 47,000-character windows with 6,500 characters of overlap;
* the `merger_agreement_specialist_maud_v1` prompt;
* Qwen3 sampling: temperature 0.7, top_p 0.8, top_k 20, presence penalty 1.0;
* a 6,144-token output cap.

So its p50 latency is about 1,044 s, against 92 s for the head-and-tail read. The earlier 64K YaRN validation probes appear only as a matched-document appendix in the master appendix, never in the pooled columns.

| Experiment | Board card | Posture        | GPUs | Concurrency |     Docs / class |
| ---------- | ---------- | -------------- | ---: | ----------: | ---------------: |
| 1          | SAND-037   | 1×L4 C8 n=20   |    1 |           8 |               20 |
| 2          | SAND-039   | 1×L4 C8 n=50   |    1 |           8 |               50 |
| 3          | SAND-037   | 2×L4 C32 n=50  |    2 |          32 |               50 |
| 4          | SAND-040   | 2×L4 C32 n=100 |    2 |          32 | 100 (merger 50†) |

Pooled serving efficiency:

| Metric           |    Exp 1 |    Exp 2 |    Exp 3 |    Exp 4 |
| ---------------- | -------: | -------: | -------: | -------: |
| Error rate       |     3.0% |     2.8% |     2.0% |    0.22% |
| Documents / min  |     8.74 |    10.40 |    20.71 |    11.86 |
| Tokens / s / GPU |      812 |    1,002 |    1,013 |    1,662 |
| GPU $ / document | $0.00153 | $0.00128 | $0.00129 | $0.00225 |

Metered Modal session total across the four experiments: **$3.39** for 1,050 documents (busy-window GPU $1.81, 53% busy share). Per-cell cards: [SAND37\_L4\_cost\_cards.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/SAND-37/SAND37_L4_cost_cards.md) · record: [SAND37\_L4\_cost\_record.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/SAND-37/SAND37_L4_cost_record.md) · reader pack: [READER-REPORT.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/SAND-37/READER-REPORT.md).

Cost against quality, one panel per posture (from the record set):

<figure><img src="https://raw.githubusercontent.com/Exios66/local-mailroom-sandbox/main/reports/SAND-37/figures/record/cost-vs-score.png" alt="SAND-37 record: GPU cost versus extraction score by posture"><figcaption><p>Cost versus extraction score by posture (record set).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/local-mailroom-sandbox/main/reports/SAND-37/figures/cmp-quality.png" alt="SAND-37 posture comparison: extraction quality by specialist"><figcaption><p>SAND-37 quality comparison across 1×L4 and 2×L4 postures (from the master appendix).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/local-mailroom-sandbox/main/reports/SAND-37/figures/cmp-efficiency.png" alt="SAND-37 posture comparison: serving efficiency"><figcaption><p>SAND-37 efficiency comparison (throughput and GPU cost).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/local-mailroom-sandbox/main/reports/SAND-37/figures/cmp-latency-cost.png" alt="SAND-37 latency versus cost"><figcaption><p>SAND-37 latency versus cost.</p></figcaption></figure>

## SAND-045 — chunked ground-truth labeler

This is a labeling job, not a benchmark. `Qwen/Qwen3-14B-AWQ` runs on two L4 replicas (app `sandbox-vllm-gt-labeler`, `mailroom_sandbox.gt_labeler`). It fills unfinished ground-truth fields for Hub tag `v9.1`, in chunks of 40 documents, under a $2 projected cap. Golden CUAD and MAUD labels are never requested. The first live wave labeled the 91 SEC EDGAR EX-10 rows that had no `cuad_clause_labels`. The job accepted 78 as verbatim CUAD maps. It did not accept 13, which were below the quality floor. Journal: [`reports/gt-labeler/`](https://github.com/Exios66/local-mailroom-sandbox/tree/main/reports/gt-labeler).

## SAND-032 — Qwen3-8B-AWQ knob ladder on Modal L4

Program summary: [QWEN3-L4-LADDER-SUMMARY.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/serving/QWEN3-L4-LADDER-SUMMARY.md). Ladder write-up: [SAND032-LADDER.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/serving/SAND-32/SAND032-LADDER.md). App name on those runs is `sandbox-vllm-sand032` (sandbox study app — not this pipeline's `mailroom-vllm`).

Frozen L5 vs L0 baseline (correspondence n=20, 1×L4): **−44% wall, −43% $/doc at equal quality**. Frozen engine: AWQ-marlin, `kv_cache_dtype=fp8`, thinking off, `max_num_seqs=16`, CUDA graphs `[1,2,4,8,16]`. Scale-out correspondence n=100: **2×L4 is 2.06× faster at flat $/doc**.

Largest serving lever: **set `max_inputs` = `max_num_seqs` per container**. Modal fills one container up to `max_inputs` before it routes to the next. A value of 64 instead of 32 turned a 2×L4 fleet into one hot replica.

<figure><img src="https://raw.githubusercontent.com/Exios66/local-mailroom-sandbox/main/reports/serving/figures/sand032-ladder.svg" alt="SAND-032 knob ladder small multiples"><figcaption><p>SAND-032 knob ladder (L0 → frozen L5).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/local-mailroom-sandbox/main/reports/serving/figures/sand032-admission.svg" alt="SAND-032 admission: seqs16 fleet versus seqs32 balanced fleet"><figcaption><p>Admission: seqs16 fleet versus seqs32 balanced fleet.</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/local-mailroom-sandbox/main/reports/serving/figures/sand032-routing.svg" alt="SAND-032 correspondence n=100 wall time by fleet"><figcaption><p>Correspondence n=100 wall time by fleet.</p></figcaption></figure>

## Reports hub and published copies

| Artifact                                                                                                                                         | Role                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| [`reports/README.md`](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/README.md)                                             | How the hub, figures, and mailroom-issues export are built                                                           |
| [`reports/dashboard/mailroom-reports.html`](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/dashboard/mailroom-reports.html) | Built hub (specialist, serving, API, ModernBERT)                                                                     |
| [COST-COMPARISON-MODAL-VS-API.md](https://github.com/LLM-Mailroom-Services/mailroom-issues/blob/main/reports/COST-COMPARISON-MODAL-VS-API.md)    | Modal vs API cost comparison (exported)                                                                              |
| [MODAL-VLLM-GPU-REPORT.md](https://github.com/LLM-Mailroom-Services/mailroom-issues/blob/main/reports/MODAL-VLLM-GPU-REPORT.md)                  | GPU economics (exported)                                                                                             |
| [MASTER-REPORT.md](https://github.com/LLM-Mailroom-Services/mailroom-issues/blob/main/reports/MASTER-REPORT.md)                                  | Master status (exported)                                                                                             |
| GitHub Pages                                                                                                                                     | [https://llm-mailroom-services.github.io/mailroom-issues/](https://llm-mailroom-services.github.io/mailroom-issues/) |

Rebuild (in a sandbox checkout, sibling checkouts for eval-environment + mailroom-ml):

```bash
python reports/dashboard/build_hub.py           # rebuild the page
python reports/dashboard/build_hub.py --check   # fail if stale
```

## Archive and other trees

| Path                                                                                                                                       | What it is                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| [archive/MODAL-RUNS-REPORT.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/archive/MODAL-RUNS-REPORT.md)           | Earlier Modal run write-up                                       |
| [archive/RUN50-MODAL-HF-REPORT.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/archive/RUN50-MODAL-HF-REPORT.md)   | Run-50 Hub report                                                |
| [archive/QWEN-FLASH-COST-REPORT.md](https://github.com/Exios66/local-mailroom-sandbox/blob/main/reports/archive/QWEN-FLASH-COST-REPORT.md) | Qwen Flash cost note                                             |
| [reports/SAND-32/](https://github.com/Exios66/local-mailroom-sandbox/tree/main/reports/SAND-32)                                            | Per-class SAND-032 run folders                                   |
| [reports/modernbert/](https://github.com/Exios66/local-mailroom-sandbox/tree/main/reports/modernbert)                                      | Redirect — canonical ModernBERT reports live in eval-environment (copies here may be stale) |
| [reports/gt-labeler/](https://github.com/Exios66/local-mailroom-sandbox/tree/main/reports/gt-labeler)                                      | SAND-045 labeler journal and checkpoint                          |

## Related

* [Visuals](local-mailroom-sandbox-visuals.md)
* [Documentation](local-mailroom-sandbox-docs.md)
* Pipeline [Modal + vLLM](../../../pipeline-reference-llm-mailroom/deployment/modal-vllm.md) (`mailroom-vllm`, not the sandbox study app)
