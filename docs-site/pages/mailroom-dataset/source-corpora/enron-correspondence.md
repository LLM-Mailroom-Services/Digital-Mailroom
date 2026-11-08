---
description: Correspondence rows from the Enron corpus.
icon: envelope
title: Enron correspondence
---

# Enron correspondence

`correspondence` · **1,000 rows** (30.3%) · 8 strata · train 915 / test 85 · **research use** (CMU Enron Email Dataset; real names).

Canonical card: [`docs/dataset-cards/enron-correspondence.md`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/docs/dataset-cards/enron-correspondence.md) in Mailroom-Corpus-EDA. Some card sections still describe earlier v7 subset sizes; **live v9 counts are 1,000 rows** as below.

## What this block is

Drawn from the **CMU Enron Email Dataset** (Klimt & Yang, 2004) via the family's deduplicated pool [`enron-correspondence-dedup`](https://huggingface.co/datasets/Lucius-Morningstar/enron-correspondence-dedup) (247,523 rows). Labelers live in [Enron-Evaluation-Environment](../../repository-guides/repos/enron-evaluation-environment.md). `metadata.source = cmu_enron_maildir`. Sampling is deterministic (`metadata.sample_method`); v4 drew 110, v6 appended 240, v9 appended +650.

This is the only multi-task subset: **subclass + content topic + intent + sentiment** supervise the same rows.

## Purpose in the mailroom

1. Gold `correspondence` labels, including the hard minority `attorney_demand` (3 rows, zero test — an honest gap).
2. Short, noisy, conversational text for agentic triage (Gmail lane and sorter).
3. Canonical 8-class **intent** vocabulary used family-wide: `analysis`, `meeting_invite`, `notice`, `other`, `payment_demand`, `press_communication`, `request`, `update`.
4. Sentiment and topic heads with evidence strings on `ground_truth`.

## Intent hydration

Intent is **100% hydrated** (1,000/1,000). `intent_source` records the path; the four values are disjoint and sum to 1,000:

| `intent_source` | Rows |
| --------------- | ---: |
| `llm_zero_shot` |  637 |
| `aeslc_join`    |  162 |
| `heuristic`     |  105 |
| `manual`        |   96 |

Source: the `intent_source` column of Hub `mailroom-dataset` `ground_truth`, cross-checked against Mailroom-Corpus-EDA's P2 metrics (2026-09-13). The 25 review-flagged rows come from the same `intent_status` pass. Upstream subject-line source: [`Yale-LILY/aeslc`](https://huggingface.co/datasets/Yale-LILY/aeslc).

v9 added the `heuristic` path for subject-line-hydrated draws (`intent_status = auto_labeled`). 25 rows are flagged for review. Every canonical intent class appears in the 10% test split. AESLC mirrors (`snoop2head/enron_aeslc_emails`, `Yale-LILY/aeslc`) supply provenance and recovered subject lines only — they carry **no** intent annotations.

## Subclass mix

`email` dominates (557). Other subtypes sit in the 53–83 range except `attorney_demand` (3). Full table: [Classes and strata](../classes-and-strata.md#correspondence-1-000-rows-30.3).

Text length (EDA): mean **526 characters**, p50 264, max 26,209 — the short-text pole of the corpus.

## EDA figures 20–22

<figure><img src="https://raw.githubusercontent.com/Exios66/Mailroom-Corpus-EDA/main/reports/figures/20_corr_content_topic.png" alt="Correspondence content-topic distribution"><figcaption><p>Content topic (figure 20).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/Mailroom-Corpus-EDA/main/reports/figures/21_corr_intent.png" alt="Correspondence intent class distribution"><figcaption><p>Intent (figure 21).</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/Exios66/Mailroom-Corpus-EDA/main/reports/figures/22_corr_sentiment.png" alt="Correspondence sentiment distribution"><figcaption><p>Sentiment (figure 22).</p></figcaption></figure>

Table: [`correspondence_topic_intent.csv`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/reports/tables/correspondence_topic_intent.csv). Interactive topic/intent: [`20_corr_topic_intent.html`](https://github.com/Exios66/Mailroom-Corpus-EDA/blob/main/reports/figures_interactive/20_corr_topic_intent.html).

## Attribution and license

Klimt, Bryan, and Yiming Yang. "The Enron Corpus: A New Dataset for Email Classification Research." _ECML 2004_. Canonical distribution: <https://www.cs.cmu.edu/~enron/> (CMU, compute/csce/03-177).

The subject line for each message is joined from the **AESLC** corpus: Zhang & Tetreault, "The Email Dataset Corpus: A New Email Dataset for Natural Language Processing", _ACL 2019_ — used via [`snoop2head/enron_aeslc_emails`](https://huggingface.co/datasets/snoop2head/enron_aeslc_emails). The deduplicated pool this class is drawn from is published as [`Lucius-Morningstar/enron-correspondence-dedup`](https://huggingface.co/datasets/Lucius-Morningstar/enron-correspondence-dedup).

**Binding:** the CMU Enron dataset is **research use only** and contains real personally identifying information of Enron employees. Those terms are inherited by every correspondence row (`metadata.license`). No redistribution of raw PII outside research contexts; no production or consumer use of this subset.

## Caveats

* Subclass / topic / sentiment labels are deterministic lexicon functions, human spot-checked — routing priors, not courtroom gold. Most intent labels come from a constrained LLM pass.
* Language and formatting are early-2000s corporate email.
* `attorney_demand` has three rows and no test split.
