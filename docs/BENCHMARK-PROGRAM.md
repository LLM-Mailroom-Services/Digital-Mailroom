# Mailroom benchmark program: how to structure runs after SAND-40

**Card:** SAND-043 (milestone after the SAND-40 AmFam handoff) · **Status:** research and proposal, no spend ·
**Inputs:** SAND-37/39/40 run cards (`reports/SAND-37/`), the public `Lucius-Morningstar/mailroom-dataset`
@ `ed7576b6`, and the external sources listed at the end.

SAND-37 through SAND-40 were controlled posture experiments: one model, one aligned spec, nested
samples, and one variable at a time (GPU count, concurrency, batch size, then the merger † settings).
That design answered "does the fleet scale, and does posture change quality?" It is the wrong design
for the next question, "how good, fast and cheap is the mailroom, and is a change an improvement?"
This document sets out how to answer that question so the numbers survive scrutiny.

## 1. Rules for every reported number

These follow the metric-context method: a number is only meaningful with its definition, its
denominator, its sample size and the population it was measured on.

1. **State the definition next to the number.** "CUAD F1 0.61" is our per-document clause-presence F1
   over labeled documents. ContractEval's 0.641 for GPT-4.1 is a strict span F1. The two are not the
   same metric and cannot be compared as a ranking.
2. **State the denominator.** Report cost per *successful* document, and also per *schema-valid*
   document. Insurance claims is 0.23 schema-valid, so its cost per usable record is about 4× its
   cost per document.
3. **Never pool across classes without a like-for-like line.** The SAND-40 pooled column fell from
   20.7 to 11.9 documents per minute only because the † merger cell (≈ 112k tokens per agreement)
   took 73% of the busy time. With merger excluded, the same fleet ran +24% faster at −19% cost per
   document. Pooled numbers are always reported next to a per-class table.
4. **A benchmark describes a population; it is not a target.** Vendor claims of "95%+ STP" for
   insurance intelligent document processing (IDP) are marketing, measured on clean typed forms
   with vendor-defined fields. They tell us what buyers expect to hear, not what our extraction
   should score.
5. **Lead with the sample-size caveat when it applies.** If a difference is inside the noise
   floor (§3), say so before quoting any benchmark.

## 2. What the corpus supports

| Class | All rows | Test split | Label source | Median source |
| --- | ---: | ---: | --- | --- |
| Insurance claims | 1,100 | 114 | **synthetic (LLM-annotated)** | CMS DE-SynPUF, GNOTHEIA, motor-claims, INSURBIAS |
| Correspondence | 1,000 | 85 | source-native | Enron (dedup) |
| Contracts | 600 | 60 | source-native (CUAD) | CUAD, SEC EDGAR |
| Corporate records | 450 | 47 | source-native | SEC EDGAR |
| Merger agreements | 152 | **17** | source-native (MAUD) | MAUD |

All SAND-37 to SAND-40 draws used `split: all` with seed 42, mixing train and test. Three things
follow from this table:

- **Insurance-claims scores measure agreement with the annotating model, not ground truth.** The
  0.67–0.69 field score is a consistency metric. Report it that way, and do not quote it next to
  source-native classes as if it were accuracy.
- **The merger test split (17 agreements) is too small to rank configurations.** Benchmark merger
  on a fixed 50-agreement panel (the SAND-37/40 agreements) plus the 17 test agreements as a holdout.
  Do not tune on the holdout.
- **The next subset should be the test split.** Its 323 documents have never been tuned against, so
  they give the cleanest benchmark set. Configurations are tuned on train draws and scored once on
  test.

## 3. The noise floor, measured on our own runs

SAND-39 (1×L4) and SAND-37 2×L4 scored the identical 250 documents with identical settings. The
spread of the per-document differences is therefore pure run-to-run noise (sampling, batching
nondeterminism). That spread sets how many documents a comparison needs.

| Class | n paired | Between-document SD | Run-to-run SD of the difference | Paired n to detect Δ = 0.05 | Paired n to detect Δ = 0.03 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Insurance claims (T 0.1) | 50 | 0.069 | 0.027 | 3 | 7 |
| Corporate records (T 0.1) | 50 | 0.249 | 0.077 | 19 | 53 |
| Correspondence (T 0.1) | 50 | 0.218 | 0.082 | 22 | 59 |
| Merger (T 0.7) | 42 | 0.049 | 0.052 | 9 | 24 |
| **Contracts (T 0.7)** | 38 | 0.118 | **0.122** | **47** | **131** |

The sample sizes use 80% power and a two-sided 5% test, paired on the same documents:
n ≈ (2.8 × SD_diff / Δ)².

Three findings follow:

- **Pairing is the single largest saving.** For corporate records, an unpaired comparison needs
  about 390 documents per arm to see Δ = 0.05, while a paired one needs 19. Every comparison should
  run both arms on the same documents. This is the variance-reduction argument in Miller (2024),
  *Adding Error Bars to Evals*.
- **Contracts at temperature 0.7 is as noisy run-to-run as it is document-to-document.** Re-running
  the same contract moves its score as much as switching contracts does. Benchmark mode should run
  contracts at T ≤ 0.2, or average k ≥ 3 samples per document; otherwise contracts comparisons need
  100+ paired documents.
- **n = 100 per class is enough for paired Δ ≥ 0.05 in every class.** It is not enough for Δ = 0.03
  on contracts. Choose n per class from this table rather than using one n for all classes.

Every quality delta should be reported with a 95% interval: a bootstrap over documents, or the
clustered standard error when one document yields several fields or MAUD questions. MAUD answers
are clustered within agreements, so 817 questions are not 817 independent observations.

## 4. External reference points (with their qualifiers)

| Area | Reference | Value | How it differs from our measure |
| --- | --- | --- | --- |
| Serving SLO, 8B model | MLPerf Inference v5.1, Llama 3.1-8B server scenario | TTFT ≤ 2 s, TPOT ≤ 100 ms | Interactive chat SLO, Poisson arrivals, H100-class systems. Our mean TTFT is 2.6–10.8 s at C32 on L4, so we are a batch system and do not meet it. |
| Serving efficiency | DistServe (OSDI '24) goodput | Highest request rate at which ≥ 90% of requests meet both TTFT and TPOT SLOs, per GPU | Per-request. Our unit is a document, which may be several requests (merger † averages 8 per agreement). |
| Serving harness | `vllm bench serve` | Request and output-token throughput; TTFT, TPOT, ITL and E2EL at p50/p99 | Synthetic prompts. Use it to size the engine, not to score extraction. |
| Contracts | ContractEval (2025), CUAD test | GPT-4.1 zero-shot F1 0.641; fine-tuned Qwen3-4B 0.678 (3 seeds) | Strict span F1 per clause type. Ours is clause-presence F1 per document, 0.61 at n = 100, which is a different scale. |
| Merger | LegalBench MAUD tasks (34) | GPT-4 balanced accuracy 47.8% | The relevant excerpt is supplied and questions are multiple-choice. Ours reads the whole agreement end to end: 14.0% micro-accuracy with 69% coverage (†). Retrieval is part of our task, so a lower score is expected. |
| Long-document key information extraction | Kleister NDA / Charity | best F1 0.82 / 0.84 | Long formal documents with fixed field schemas. This is the closest academic analogue to our field score. |
| Generative extraction metric | ANLS* (2024) | Normalized Levenshtein similarity for LLM outputs, including lists and dicts | A candidate replacement for exact field matching. It tolerates paraphrase and is useful for correspondence (0.34). |
| Insurance IDP | Vendor reports | "95%+ STP", "99% field accuracy" | Marketing figures with undisclosed definitions and clean forms. Directional only. |

## 5. Recommended structure for benchmark runs

**5.1 A frozen benchmark set, versioned like code.** `MB-v1`:

- The 323 test-split documents, stratified by class and subclass.
- The 50-agreement merger panel, plus the 17 merger test agreements as a holdout.
- A manifest committed under `config/benchmarks/` with content SHA-256 per document, the dataset
  revision and the per-class n chosen from §3.

Configurations are tuned on train draws and scored on `MB-v1`. A change of set is a new version
(`MB-v2`), never an in-place edit.

**5.2 One scorecard per run, five groups of metrics.**

| Group | Metric | Definition |
| --- | --- | --- |
| Quality | Primary score per class, with a 95% confidence interval | field score, CUAD presence F1 (with span F1 alongside), MAUD accuracy and coverage |
| Reliability | ok rate (Wilson interval), schema-valid rate, length-capped share | the denominator is all documents attempted |
| Throughput | **document goodput** | documents per minute per GPU with p95 document latency ≤ the class SLO (set from SAND-40: 60 s for short classes, 300 s for contracts, 30 min for merger †) |
| Cost | $ per 1,000 ok documents; **$ per 1,000 schema-valid documents** | GPU-time cost at $0.80 per L4-hour, plus the session's metered total |
| Engine | TTFT and TPOT p50/p95, prefix-cache hit rate, preemptions, KV-cache use | from vLLM `/metrics` deltas |

There is no single composite score. The decision rule is: a change ships if quality is
non-inferior (the lower bound of the Δ interval is above −0.02) and it improves cost or goodput, or
if it improves quality at a stated cost.

**5.3 Comparisons are always paired.** Both arms score the same `MB-v1` documents. The card reports
Δ with its interval and the better/worse counts, the format the master card already uses for
merger †.

**5.4 Baselines on every card.**

- **Floor:** an empty or constant prediction, which shows how much of each field score is free.
- **Frozen baseline:** the SAND-40 configuration.
- **Ceiling reference:** one API model run, opt-in only (OpenRouter needs an explicit yes).

**5.5 A broader configuration space, now that the posture questions are closed.** Recommended
sweep order, cheapest information first:

1. **Decode controls on long classes** (merger †, contracts): output cap at 2,048, 3,072 or 6,144;
   repetition penalty; salvage-and-retry (§6). This needs no engine change and attacks the largest
   cost line.
2. **Temperature for contracts:** 0.7 vs 0.2, paired on n = 100, to close the noise problem in §3.
3. **Schema enforcement for insurance claims:** grammar-constrained decoding to lift schema-valid
   from 0.23.
4. **Prompt variants per class** on train draws, scored once on `MB-v1`.
5. **Model swaps** (Qwen3-8B bf16 against AWQ, a 14B on an L40S, an API reference), each with the
   same scorecard.

**5.6 Serving runs separately from quality.** Engine sizing (replicas, `max_num_seqs`, concurrency)
uses `vllm bench serve` style load at fixed prompt lengths taken from `MB-v1` length percentiles,
and reports goodput. Quality runs then use the chosen engine. This prevents the SAND-40 situation,
where a long-document cell distorted the serving numbers.

## 6. Salvage-and-retry for output-cap loops (first SAND-043 workstream)

**Evidence from SAND-40 merger †:**

- 23 of 418 section calls hit the 6,144-token cap.
- vLLM's output-length histogram shows that 82% of requests stop under 1,000 tokens, and that
  almost all requests over 5,000 are cap hits, which means repetition loops.
- Every loop burns a full 6,144-token decode, about 4–7 minutes of a slot at C32, before its one
  re-sample.

**Design:**

1. **Salvage.** On `finish_reason=length`, parse the partial JSON leniently: cut it at the start of
   the repeated n-gram run, close open brackets, and keep every complete field.
2. **Targeted retry.** Re-ask only for the fields still missing from the salvaged object, with a
   short prompt that states the fields already found. Skip the retry when the merge across
   overlapping chunks already covers those fields.
3. **Early stop.** Stream the response and cancel when a repeated n-gram span passes a threshold
   (≈ 200 tokens), instead of waiting for the cap.
4. **Cap.** Lower the output cap to the measured legitimate p99.5 (≈ 2,500–3,000 tokens), with
   salvage as the safety net.

**Acceptance:**

- A paired run on the 50-agreement merger panel shows MAUD accuracy non-inferior to SAND-40 †
  (lower bound of the Δ interval above −0.02).
- Decode tokens wasted on cap hits fall by at least 50%.
- No silent chunk drops: a skipped chunk is counted on the card. Today `extract_chunked` skips an
  unparseable chunk without a trace.

## 7. Other findings from SAND-40 that feed the program

- **Replica imbalance.** At C32 one replica held 16 running plus 7 queued while the other ran 6, and
  the 8 preemptions all landed on the busy replica. Request counts still split 199/219, so this is
  bursty affinity rather than a routing failure. Before the next 2×L4 benchmark, measure it with
  per-replica in-flight sampling and test client connection limits.
- **KV pressure.** About 50,000-character merger sections at C32 drove the 8 preemptions. A
  benchmark of merger † should either cap concurrency for that class or size `max_num_seqs` from
  the section length.
- **Insurance-claims schema** remains the cheapest quality win: content scores 0.67 while 77% of
  outputs fail the strict schema.

## Sources

- MLCommons, [MLPerf Inference 5.1: Benchmarking small LLMs with Llama3.1-8B](https://mlcommons.org/2025/09/small-llm-inference-5-1/); [Llama 2 70B benchmark](https://mlcommons.org/2024/03/mlperf-llama2-70b/); EDN, [MLPerf and the rise of latency-aware LLM benchmarking](https://www.edn.com/mlperf-and-the-rise-of-latency-aware-llm-benchmarking/)
- Zhong et al., [DistServe (OSDI '24)](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin); Hao AI Lab, [Throughput is not all you need](https://haoailab.com/blogs/distserve/)
- vLLM, [`vllm bench serve`](https://docs.vllm.ai/en/latest/cli/bench/serve/)
- Miller, [Adding Error Bars to Evals (arXiv:2411.00640)](https://arxiv.org/abs/2411.00640)
- [ContractEval: clause-level legal risk identification (arXiv:2508.03080)](https://arxiv.org/pdf/2508.03080); [cuad-qlora-vllm](https://github.com/lakshy-606/cuad-qlora-vllm)
- Guha et al., [LegalBench (NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/file/89e44582fd28ddfea1ea4dcb0ebbf4b0-Paper-Datasets_and_Benchmarks.pdf); Wang et al., [MAUD (EMNLP 2023)](https://aclanthology.org/2023.emnlp-main.1019/)
- Graliński et al., [Kleister](https://arxiv.org/pdf/2105.05796); Peer et al., [ANLS*](https://arxiv.org/html/2402.03848v4)
- XBP Global, [IDP for claims processing](https://xbpglobal.com/blog/intelligent-document-processing-for-claims/); Docsumo, [IDP for insurance](https://www.docsumo.com/blog/intelligent-document-processing-insurance) (vendor sources, directional only)
