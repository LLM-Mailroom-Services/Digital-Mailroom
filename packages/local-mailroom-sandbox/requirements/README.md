# requirements/ — pip-installable mirrors of pyproject.toml extras.
#
# Source of truth is ALWAYS pyproject.toml. These files exist so operators,
# Docker/CI contexts, and lock export tooling that expect a requirements.txt
# get a complete, pinned-enough list without inventing a second dependency
# graph. Keep them in sync via tests/test_requirements.py.
#
# Install (from package root):
#   pip install -r requirements/base.txt
#   pip install -r requirements/dev.txt          # offline pytest + Hub
#   pip install -r requirements/pipeline.txt     # vendored mailroom live path
#   pip install -r requirements/deploy.txt       # Modal SDK
#   pip install -r requirements/all.txt          # everything
# Or (preferred editable):
#   pip install -e ".[dev,pipeline,deploy]"
