# Document Extraction on Low-Cost Cloud GPUs: Speed, Quality and Cost

We ran an open-source language model on rented cloud GPUs to pull structured information out of five kinds of business documents. We varied the hardware and the batch size across four experiments and measured speed, accuracy and cost.

**Data:** every result uses the public Hugging Face dataset `Lucius-Morningstar/mailroom-dataset`. No American Family Insurance data was used or shared.

## Key findings

1. **Adding a second GPU doubles speed at the same cost per document.** On the same 250 documents, moving from 1 GPU to 2 GPUs processed 99% more documents per minute, and GPU cost per document changed by only +0.4%. The trade-off: each document waited 1.4–1.8 times longer for its answer, because more documents shared the GPUs at once. This setup suits batch processing; latency-sensitive use would need different tuning.
2. **Larger batches are cheaper.** On the 2-GPU setup, processing 100 documents of each type instead of 50 cut GPU cost per document by 19% (four document types; merger agreements excluded because their settings changed). 1 of 400 documents failed.
3. **Hardware choice did not change accuracy.** Comparing the same documents across experiments (420 document pairs), the average score change per document type was between -0.017 and +0.023 on a 0–1 scale, and every 95% confidence interval includes zero. Effects smaller than about ±0.04 cannot be ruled out at this sample size.
4. **Merger agreements are the weak spot; reading the whole agreement helps.** These contracts are far longer than the model can read in one pass. Splitting each agreement into overlapping sections and combining the answers raised accuracy from 3.5% to 14.0% and the share of questions answered from 23% to 69%, at 4.5 times the cost per agreement.
5. **The full study cost $3.39 in cloud charges for 1,050 documents** (about 0.32 cents each, all-in), and $0.00 was billed after the provider's free credits.

## What we tested

**The task.** An automated mailroom reads each incoming document and returns its key facts as structured data (for example parties, dates, amounts, and which contract clauses are present). Each of the five document types has its own extraction instructions:

| Document type | What it contains | How accuracy is measured |
| --- | --- | --- |
| Insurance Claims | Insurance claim forms and notices | Extraction score |
| Contracts | Commercial contracts | Clause F1 (CUAD) |
| Corporate Records | Corporate filings and records | Extraction score |
| Correspondence | Business letters and email | Extraction score |
| Merger Agreements | Merger agreements (often 100+ pages) | Question accuracy (MAUD) |

**The model.** Qwen/Qwen3-8B-AWQ: an open-weights model with 8 billion parameters, compressed to 4-bit weights (AWQ) so it fits on a single 24 GB GPU. It ran on vLLM, an open-source model server, on NVIDIA L4 GPUs rented from Modal at $0.80 per GPU-hour.

**The sample.** Documents were drawn at random with a fixed seed (42), so every run is reproducible. Smaller samples are subsets of larger ones, so runs can be compared on the same documents.

## The four experiments

| Experiment | GPUs | Documents processed at once | Documents per type | Total documents |
| --- | ---: | ---: | ---: | ---: |
| Experiment 1 | 1 | 8 | 20 | 100 |
| Experiment 2 | 1 | 8 | 50 | 250 |
| Experiment 3 | 2 | 32 | 50 | 250 |
| Experiment 4 | 2 | 32 | 100 (merger agreements: 50) | 450 |

Experiments 2 and 3 use the identical 250 documents and differ only in GPU count and documents processed at once, so they give the cleanest hardware comparison. Experiment 4 repeats Experiment 3's hardware on twice as many documents and also tests improved settings for merger agreements (described below).

## How to read the numbers

| Term | Meaning |
| --- | --- |
| Token | The unit a language model reads and writes; roughly three-quarters of an English word. |
| Documents per minute | Overall throughput for the run: documents finished ÷ total run time. |
| Tokens per second per GPU | Text processed (read plus written) per second by each GPU; a hardware-efficiency measure. |
| Median time per document | Half of documents finished faster than this, half slower (seconds from submission to answer). |
| GPU cost per document | GPU time the documents actually used × $0.80/hour ÷ documents. Excludes start-up and idle time. |
| Session cost | What the cloud provider metered for the whole session, including start-up, waiting and shut-down. |
| Failed document | The model's answer exceeded the output length limit (8,192 tokens) and was cut off, so no result was returned. |
| Extraction score | 0–1. Average agreement between extracted fields and the dataset's answer key, per document. |
| Clause F1 (CUAD) | 0–1. CUAD is a public set of commercial contracts with lawyer-labeled clause types. F1 balances finding the clauses that are present against flagging clauses that are not. |
| Question accuracy (MAUD) | 0–1. MAUD is a public set of merger agreements with lawyer-written multiple-choice questions. Accuracy is the share of all labeled questions answered correctly; coverage is the share the model answered at all. |
| 95% confidence interval | The range that likely contains the true difference; if it includes zero, the data show no reliable difference. |

The three scores use different scales, so compare them across experiments, not across document types.

## Speed and cost by experiment

| Measure | Experiment 1 | Experiment 2 | Experiment 3 | Experiment 4 |
| --- | ---: | ---: | ---: | ---: |
| Documents per minute | 8.7 | 10.4 | 20.7 | 11.9 |
| Tokens per second per GPU | 812 | 1,002 | 1,013 | 1,662 |
| GPU cost per document | $0.00153 | $0.00128 | $0.00129 | $0.00225 |
| Failed documents | 3 of 100 | 7 of 250 | 5 of 250 | 1 of 450 |

Every failure was an answer cut off at the output length limit, all on contracts or merger agreements (the longest documents).

Experiment 4's cost and throughput include the slower, more thorough merger-agreement settings; the like-for-like batch-size comparison is in Key finding 2.

## Results by document type

Scores by document type (0–1, higher is better):

| Document type | Measure | Experiment 1 | Experiment 2 | Experiment 3 | Experiment 4 |
| --- | --- | ---: | ---: | ---: | ---: |
| Insurance Claims | Extraction score | 0.684 | 0.684 | 0.686 | 0.672 |
| Contracts | Clause F1 (CUAD) | 0.597 | 0.590 | 0.605 | 0.608 |
| Corporate Records | Extraction score | 0.459 | 0.449 | 0.452 | 0.475 |
| Correspondence | Extraction score | 0.327 | 0.345 | 0.334 | 0.341 |
| Merger Agreements | Question accuracy (MAUD) | 0.014 | 0.048 | 0.035 | 0.140* |

\* Experiment 4 uses the improved merger-agreement settings.

Cost per successfully processed document (US dollars):

| Document type | Experiment 1 | Experiment 2 | Experiment 3 | Experiment 4 |
| --- | ---: | ---: | ---: | ---: |
| Insurance Claims | $0.00042 | $0.00039 | $0.00032 | $0.00036 |
| Contracts | $0.00350 | $0.00310 | $0.00284 | $0.00207 |
| Corporate Records | $0.00026 | $0.00032 | $0.00019 | $0.00021 |
| Correspondence | $0.00011 | $0.00018 | $0.00012 | $0.00012 |
| Merger Agreements | $0.00390 | $0.00284 | $0.00329 | $0.01475 |

Median seconds per document:

| Document type | Experiment 1 | Experiment 2 | Experiment 3 | Experiment 4 |
| --- | ---: | ---: | ---: | ---: |
| Insurance Claims | 13 | 14 | 20 | 20 |
| Contracts | 66 | 68 | 103 | 96 |
| Corporate Records | 14 | 13 | 24 | 20 |
| Correspondence | 6 | 7 | 11 | 10 |
| Merger Agreements | 50 | 51 | 92 | 1,044 |

## Merger agreements: what changed

Merger agreements are long: the median agreement in the sample runs to hundreds of thousands of characters, while the standard settings read only the first and last 30,000 characters combined. In Experiment 4 we changed the settings for this document type only, on the same 50 agreements as Experiment 3:

| Setting | Standard (Experiments 1–3) | Improved (Experiment 4) |
| --- | --- | --- |
| What the model reads | Start and end of the agreement; the middle is skipped | The whole agreement, in overlapping sections of about 47,000 characters, with answers combined |
| Instructions | General extraction instructions | Instructions written around the MAUD question set |
| Output length limit | 8,192 tokens | 6,144 tokens, with one retry if an answer is cut off |
| Sampling | temperature 0.7, other sampling at vLLM defaults | temperature 0.7, top_p 0.8, top_k 20, presence_penalty 1.0 |
| Question accuracy | 3.5% | 14.0% |
| Questions answered | 23% | 69% |
| Agreements returning a result | 46 of 50 | 50 of 50 |
| Cost per agreement | $0.0033 | $0.0147 |
| Median time per agreement | 92 s | 1,044 s |

On the 46 agreements scored under both settings, 35 improved and 1 got worse (average change +0.106 on the 0–1 scale). Several settings changed together, so this run does not show which change drove the gain.

## Total cost

GPU cost counts only the time the GPUs spent on documents. Session cost is the provider's metered charge for the whole session, including start-up, waiting between runs and shut-down.

| Experiments | Documents | GPU cost on documents | Session cost | Share of session spent on documents | Session cost per document | Billed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Experiments 1 and 3 | 350 | $0.47 | $1.09 | 44% | $0.0031 | $0.00 |
| Experiment 2 | 250 | $0.32 | $0.49 | 65% | $0.0020 | $0.00 |
| Experiment 4 | 450 | $1.01 | $1.81 | 56% | $0.0040 | $0.00 |
| **All experiments** | 1,050 | $1.81 | $3.39 | 53% | $0.0032 | $0.00 |

Billed is zero because the provider's monthly free credits covered the charges. Session costs exclude short exploratory test deployments run between the main runs.

## Limitations

- **One sample per run.** Each run used one random draw of 20–100 documents per type; small differences between experiments may be noise.
- **Hardware and load changed together.** Going from 1 to 2 GPUs also raised the number of documents processed at once (8 to 32), so the speed gain cannot be split between the two.
- **Some outputs vary between runs.** Contracts and merger agreements are generated with some randomness (temperature 0.7), so repeated runs give slightly different answers.
- **Strict format checks.** Most insurance-claim outputs did not pass strict data-format validation even though their extraction scores are the highest; a system that rejects malformed records would need that fixed first.
- **Public data only.** Results describe this public dataset; performance on other document collections has not been measured.

## Experiment cross-reference

For readers comparing against the project's internal records:

| Experiment | Internal shorthand |
| --- | --- |
| Experiment 1 | 1×L4 C8 n=20 |
| Experiment 2 | 1×L4 C8 n=50 |
| Experiment 3 | 2×L4 C32 n=50 |
| Experiment 4 | 2×L4 C32 n=100 |

Shorthand key: `2×L4` = two NVIDIA L4 GPUs; `C32` = 32 documents processed at once; `n=100` = documents per type. Detailed tables and charts: `SAND-37-MASTER-APPENDIX.md` in the project repository.
