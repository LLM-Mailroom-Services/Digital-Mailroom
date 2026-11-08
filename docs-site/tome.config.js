/** @type {import('@tomehq/core').TomeConfig} */
export default {
  title: "The Digital Mailroom",
  name: "The Digital Mailroom",
  search: {
    provider: "local",
  },
  api: {
    spec: "./openapi.yaml",
    playground: true,
  },
  navigation: [
  {
    "group": "The Digital Mailroom",
    "pages": [
      "README"
    ]
  },
  {
    "group": "Start here",
    "pages": [
      "start-here/overview",
      "start-here/getting-started",
      "start-here/glossary"
    ]
  },
  {
    "group": "The pipeline in depth",
    "pages": [
      "the-pipeline-in-depth/running",
      "the-pipeline-in-depth/flowchart",
      "the-pipeline-in-depth/extraction-schemas",
      "the-pipeline-in-depth/scoring-and-metrics"
    ]
  },
  {
    "group": "How it fits together",
    "pages": [
      "how-it-fits-together/architecture",
      "how-it-fits-together/data-and-corpora",
      "how-it-fits-together/governance",
      "how-it-fits-together/repo-index"
    ]
  },
  {
    "group": "Mailroom dataset",
    "pages": [
      "mailroom-dataset/mailroom-dataset",
      "mailroom-dataset/classes-and-strata",
      "mailroom-dataset/configs",
      "mailroom-dataset/hub-resources",
      "mailroom-dataset/source-corpora/README",
      "mailroom-dataset/source-corpora/cuad-contracts",
      "mailroom-dataset/source-corpora/maud-merger-agreements",
      "mailroom-dataset/source-corpora/edgar-corporate-records",
      "mailroom-dataset/source-corpora/enron-correspondence",
      "mailroom-dataset/source-corpora/cms-insurance-claims",
      "mailroom-dataset/eda-reports",
      "mailroom-dataset/visualizations"
    ]
  },
  {
    "group": "Experiment reports",
    "pages": [
      "experiment-reports/experiment-reports",
      "repository-guides/repos/local-mailroom-sandbox/local-mailroom-sandbox-reports",
      "experiment-reports/eval-environment-reports",
    ]
  },
  {
    "group": "Repository guides",
    "pages": [
      "repository-guides/repos/README",
      "repository-guides/repos/digital-mailroom",
      "repository-guides/repos/mailroom-issues",
      "repository-guides/repos/llm-mailroom",
      "repository-guides/repos/llm-dojo-scoring",
      "repository-guides/repos/llm-entity-extraction",
      "repository-guides/repos/eval-environment",
      "repository-guides/repos/mailroom-ml",
      "repository-guides/repos/mailroom-reloaded",
      "repository-guides/repos/local-mailroom-sandbox/README",
      "repository-guides/repos/local-mailroom-sandbox/local-mailroom-sandbox-docs",
      "repository-guides/repos/local-mailroom-sandbox/local-mailroom-sandbox-visuals",
      "repository-guides/repos/the-mailroom",
      "repository-guides/repos/agent-mailroom",
      "repository-guides/repos/llm-mailroom-graph",
      "repository-guides/repos/mailroom-corpus-eda",
      "repository-guides/repos/enron-evaluation-environment",
      "repository-guides/repos/claims-data-eda",
      "repository-guides/repos/atticus-investigation"
    ]
  },
  {
    "group": "Pipeline reference (llm-mailroom)",
    "pages": [
      "pipeline-reference-llm-mailroom/architecture",
      "pipeline-reference-llm-mailroom/agents",
      "pipeline-reference-llm-mailroom/decision-reviewer",
      "pipeline-reference-llm-mailroom/configuration",
      "pipeline-reference-llm-mailroom/api",
      "pipeline-reference-llm-mailroom/gmail-intake",
      "pipeline-reference-llm-mailroom/deployment/README",
      "pipeline-reference-llm-mailroom/deployment/docker-deployment",
      "pipeline-reference-llm-mailroom/deployment/modal-vllm",
      "pipeline-reference-llm-mailroom/deployment/litellm-gateway",
      "pipeline-reference-llm-mailroom/deployment/llamafiles",
      "pipeline-reference-llm-mailroom/deployment/langfuse",
      "pipeline-reference-llm-mailroom/deployment/phoenix",
      "pipeline-reference-llm-mailroom/deployment/postgres",
      "pipeline-reference-llm-mailroom/operational-procedure",
      "pipeline-reference-llm-mailroom/local-models",
      "pipeline-reference-llm-mailroom/testing",
      "pipeline-reference-llm-mailroom/sister-repos"
    ]
  },
  {
    "group": "API reference",
    "pages": [
      "api-reference/README",
      "api-reference/health",
      "api-reference/ingest",
      "api-reference/review",
      "api-reference/documents",
      "api-reference/audit",
      "api-reference/ops",
      "api-reference/relations"
    ]
  },
  {
    "group": "Changelog",
    "pages": [
      "changelog/README",
      "changelog/unreleased",
      "changelog/2026/v0-8-0",
      "changelog/2026/v0-7-1",
      "changelog/2026/v0-7-0",
      "changelog/2026/v0-6-0",
      "changelog/2026/v0-5-0",
      "changelog/2026/v0-4-1",
      "changelog/2026/v0-4-0",
      "changelog/2026/v0-3-2",
      "changelog/2026/v0-3-1",
      "changelog/2026/v0-3-0",
      "changelog/2026/released-backlog-v0-4-0-v0-6-0-era",
      "changelog/2026/0-2-2",
      "changelog/2026/0-2-1",
      "changelog/2026/0-2-0",
      "changelog/2026/0-1-0"
    ]
  },
  {
    "group": "About this site",
    "pages": [
      "about-this-site/maintaining"
    ]
  }
],
};
