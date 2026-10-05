# Offline sandbox Jupyter notebooks
#
# 01 — activate profile, dotenv, compose/Dockerfile checklist
# 02 — load / clean / prepare fixture corpora → data/runtime/prepared/
# 03 — smoke the prepared datasets with mock evals (no live LLM required)
#
# Host:
#   pip install -e ".[dev,notebooks]"
#   jupyter lab notebooks/
#
# Docker (recommended offline path):
#   sandbox up --compose-profile jupyter
#   open http://127.0.0.1:8888/lab
#
# See docs/setting-up/docker-offline.md and deploy/README.md.
