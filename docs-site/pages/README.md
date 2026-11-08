---
description: 'One place to learn the Mailroom: the pipeline and every repository around it.'
icon: house
layout:
  width: default
  tableOfContents:
    visible: true
title: LLM-MAILROOM
---

# LLM-MAILROOM

This site is the one place to learn the Mailroom: the `llm-mailroom` pipeline and every repository built around it.

> **Migrated to Tome — 2026-11-08.** This site is a migration of the GitBook site at <https://mailroom-inc.gitbook.io/the-digital-mailroom/> (source: [`Exios66/mailroom-documentation`](https://github.com/Exios66/mailroom-documentation)). Content was transferred as published, with GitBook blocks converted to Tome equivalents and the API reference rebuilt from the checked-in OpenAPI spec. Current pins as of 2026-11-08: llm-mailroom **v0.9.3** (released 2026-11-07), llm-dojo-scoring **v0.28.1**, Digital-Mailroom hub **v0.10.0**, dataset code revision **v9.1**, Hub dataset tag **v9.3**. A full freshness sweep ran 2026-11-08 and re-dated every version claim on the site to these pins (see `MIGRATION-NOTES.md` in the site repo).

The Mailroom reads legal and business documents. It identifies the type of each document and extracts the important fields. Then it files the document in an archive with a tamper-evident audit trail. A team of specialist LLM agents does the work, one LangGraph state machine per document. More than a dozen repositories support the pipeline. They include a scoring library, an evaluation harness, corpus builders, and a local sandbox. They also include visualizers, an ML classifier, and the monorepo that connects them.

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody>
<tr><td><h3><i class="fa-compass" style="color:$primary;">:compass:</i></h3></td><td><strong>Understand the Mailroom</strong></td><td>What it is and which repository does what.</td><td><a href="start-here/overview.md">overview</a></td></tr>
<tr><td><h3><i class="fa-rocket" style="color:$primary;">:rocket:</i></h3></td><td><strong>Get running in ten minutes</strong></td><td>Seven paths. Each works without paid keys.</td><td><a href="start-here/getting-started.md">getting-started</a></td></tr>
<tr><td><h3><i class="fa-play" style="color:$primary;">:play:</i></h3></td><td><strong>Run, evaluate or audit</strong></td><td>Push documents through the pipeline.</td><td><a href="the-pipeline-in-depth/running.md">running</a></td></tr>
<tr><td><h3><i class="fa-diagram-project" style="color:$primary;">:diagram-project:</i></h3></td><td><strong>See every node</strong></td><td>The full flowchart with routing conditions.</td><td><a href="the-pipeline-in-depth/flowchart.md">flowchart</a></td></tr>
<tr><td><h3><i class="fa-book" style="color:$primary;">:book:</i></h3></td><td><strong>Look up a key, agent or route</strong></td><td>The pipeline reference.</td><td><a href="pipeline-reference-llm-mailroom/architecture.md">architecture</a></td></tr>
<tr><td><h3><i class="fa-server" style="color:$primary;">:server:</i></h3></td><td><strong>Deploy</strong></td><td>Docker, Modal and more.</td><td><a href="pipeline-reference-llm-mailroom/deployment/README.md">README</a></td></tr>
<tr><td><h3><i class="fa-sitemap" style="color:$primary;">:sitemap:</i></h3></td><td><strong>See how repositories connect</strong></td><td>Data, prompts, scores and traces.</td><td><a href="how-it-fits-together/architecture.md">architecture</a></td></tr>
<tr><td><h3><i class="fa-layer-group" style="color:$primary;">:layer-group:</i></h3></td><td><strong>Read the dataset</strong></td><td>Classes, strata, EDA reports and figures.</td><td><a href="mailroom-dataset/mailroom-dataset.md">mailroom-dataset</a></td></tr>
<tr><td><h3><i class="fa-books" style="color:$primary;">:books:</i></h3></td><td><strong>Work on one repository</strong></td><td>One guide for each repository.</td><td><a href="repository-guides/repos/README.md">README</a></td></tr>
<tr><td><h3><i class="fa-clock-rotate-left" style="color:$primary;">:clock-rotate-left:</i></h3></td><td><strong>See what changed</strong></td><td>Release notes, by version.</td><td><a href="changelog/README.md">README</a></td></tr>
<tr><td><h3><i class="fa-brackets-curly" style="color:$primary;">:brackets-curly:</i></h3></td><td><strong>Call the API</strong></td><td>Interactive endpoint reference, rendered from OpenAPI.</td><td><a href="api-reference/README.md">README</a></td></tr>
<tr><td><h3><i class="fa-flask" style="color:$primary;">:flask:</i></h3></td><td><strong>Read the results</strong></td><td>Measured GPU, API and classifier results, with figures.</td><td><a href="experiment-reports/experiment-reports.md">experiment-reports</a></td></tr>
</tbody></table>

Install the pipeline (release v0.9.3, as of 2026-11-08). The last command starts the API, which embeds the inbox watcher:

```bash
git clone https://github.com/Exios66/llm-mailroom.git
cd llm-mailroom
pip install -e ".[dev]"
PYTHONPATH=src python -m api.main
```

<figure><img src="https://raw.githubusercontent.com/LLM-Mailroom-Services/Digital-Mailroom/main/packages/llm-mailroom/docs/.gitbook/assets/banner.png" alt="Mailroom — a great horned owl postal worker sorting wax-sealed legal documents into bins by lamplight"><figcaption><p>The LLM-Mailroom masthead: the night-shift owl at the sorting desk.</p></figcaption></figure>

## From inbox to archive

The happy path costs two LLM generations. Everything else is procedural, gated, or a human's call.

| Stop         | What happens                                                                                                                                                                                                                                                                                                                        |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Intake**   | The watcher claims the upload by atomic rename into `processing/`, transcribes it, and cleans it. Nothing is ever truncated.                                                                                                                                                                                                        |
| **Classify** | The sorter picks one of five classes. At `0.97` or above it goes straight on. Between `0.88` and `0.97` it gets one re-classification pass, then a second-opinion reviewer agent (Lane A). Below `0.88` it retries, then goes to human review. Contracts, merger agreements and insurance claims use stricter per-class thresholds (`0.98` and `0.90`) because a wrong auto-pass costs more there. |
| **Extract**  | The class specialist fills its schema. Guardrails check the JSON before anything moves forward.                                                                                                                                                                                                                                     |
| **Verify**   | Extractions in the ambiguous confidence band get a judge, then an arbiter. Conflicts go to the boss agent or a human. See the [Pipeline flowchart](the-pipeline-in-depth/flowchart.md).                                                                                                                                             |
| **Archive**  | A procedural report, a catalog row in SQLite, and an archive entry sealed into the hash-chained audit log.                                                                                                                                                                                                                          |

## What ships with it

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody>
<tr><td><h3><i class="fa-file-contract" style="color:$primary;">:file-contract:</i></h3></td><td><strong>Five document classes</strong></td><td>Contracts, merger agreements, corporate records, correspondence and insurance claims. Each has its own specialist.</td><td><a href="mailroom-dataset/classes-and-strata.md">classes-and-strata</a></td></tr>
<tr><td><h3><i class="fa-plug" style="color:$primary;">:plug:</i></h3></td><td><strong>Any model provider</strong></td><td>OpenRouter, Ollama or vLLM. Agents ask for a role. `taxonomy.yaml` picks the model.</td><td><a href="pipeline-reference-llm-mailroom/local-models.md">local-models</a></td></tr>
<tr><td><h3><i class="fa-eye" style="color:$primary;">:eye:</i></h3></td><td><strong>Traced end to end</strong></td><td>Langfuse, Braintrust or a local Arize Phoenix. The pipeline runs with none of them.</td><td><a href="pipeline-reference-llm-mailroom/deployment/langfuse.md">langfuse</a></td></tr>
<tr><td><h3><i class="fa-chart-line" style="color:$primary;">:chart-line:</i></h3></td><td><strong>Evaluation built in</strong></td><td>A 23-sample pilot, deterministic field scoring, LLM judges and a LegalBench harness.</td><td><a href="the-pipeline-in-depth/scoring-and-metrics.md">scoring-and-metrics</a></td></tr>
</tbody></table>

## Meet Fumi

<figure><img src="https://raw.githubusercontent.com/LLM-Mailroom-Services/Digital-Mailroom/main/packages/llm-mailroom/docs/.gitbook/assets/fumi.gif" alt="Fumi in her postal uniform while Hermes the owl blinks on her shoulder" width="192"><figcaption><p>Fumi (文, "letter") is the mailroom's head maid. She wears a USPS-style carrier uniform, a mini cap, and a leather satchel. Hermes checks postmarks from her shoulder.</p></figcaption></figure>

<figure><img src="https://raw.githubusercontent.com/LLM-Mailroom-Services/Digital-Mailroom/main/packages/llm-mailroom/docs/.gitbook/assets/hoot-icon.png" alt="Hermes, the pixel owl on Fumi's shoulder" width="96"><figcaption><p>Hermes is the pixel owl on Fumi's shoulder and the night-shift owl's junior colleague on the banner.</p></figcaption></figure>
