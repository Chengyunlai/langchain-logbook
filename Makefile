# Makefile for langchain-logbook

# Variables
PYTHON ?= python3
UV ?= uv
UV_RUN := $(UV) run --locked --group dev
VENV_DIR := .venv
PROJECT_NAME := langchain-logbook
SITE_BASE ?= /langchain-logbook
SITE_URL ?= https://chengyunlai.github.io/langchain-logbook/
REPOSITORY_URL ?= https://github.com/Chengyunlai/langchain-logbook

# Default target
.DEFAULT_GOAL := help

.PHONY: help
help: ## Display this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: check-python
check-python: ## Check if Python is installed
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo >&2 "Python 3 is required but not installed. Aborting."; exit 1; }
	@echo "Python 3 is installed: $$($(PYTHON) --version)"

.PHONY: check-uv
check-uv: ## Check if uv is installed
	@command -v $(UV) >/dev/null 2>&1 || { echo >&2 "uv is required. Run 'make install-uv' first."; exit 1; }
	@echo "uv is installed: $$($(UV) --version)"

.PHONY: install-uv
install-uv: ## Install uv package manager
	@if ! command -v $(UV) >/dev/null 2>&1; then \
		echo "uv is not installed. Installing it now..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "Please restart your terminal or run 'source \$$HOME/.cargo/env' to use 'uv'."; \
	else \
		echo "uv is already installed: $$($(UV) --version)"; \
	fi

.PHONY: setup
setup: check-python check-uv ## Initialize the locked project environment and .env
	@if [ ! -f .env ]; then \
		cp .env.example .env 2>/dev/null || touch .env; \
		echo "Created .env file. Please edit it with your API keys."; \
	fi
	@$(UV) sync --locked --group dev
	@echo "Setup complete. The environment exactly matches uv.lock."

.PHONY: install
install: check-uv ## Install dependencies exactly as recorded in uv.lock
	@$(UV) sync --locked --group dev
	@echo "Locked dependencies installed."

.PHONY: notebook
notebook: ## Launch Jupyter Notebook
	@echo "Launching Jupyter Notebook..."
	@$(UV_RUN) jupyter notebook --notebook-dir=tutorials

.PHONY: lab
lab: ## Launch Jupyter Lab
	@echo "Launching Jupyter Lab..."
	@$(UV_RUN) jupyter lab --notebook-dir=tutorials

.PHONY: clean
clean: ## Clean up temporary files
	@rm -rf $(VENV_DIR)
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} +
	@echo "Cleanup complete."

.PHONY: check-lock
check-lock: check-uv ## Verify pyproject.toml and uv.lock are synchronized
	@$(UV) lock --check

.PHONY: check-workflows
check-workflows: check-uv ## Verify CI and Pages reuse the canonical release gate
	@$(UV_RUN) python scripts/check_workflows.py --root .

.PHONY: test
test: check-uv ## Run offline tests (external cases are collected and shown as skipped)
	@LANGCHAIN_LOGBOOK_PROFILE=offline $(UV_RUN) pytest -q
	@$(UV_RUN) python scripts/validate_tutorials.py

.PHONY: test-integration
test-integration: check-uv ## Run opt-in external tests; matching API keys are required
	@LANGCHAIN_LOGBOOK_PROFILE=integration $(UV_RUN) pytest -q -m integration

.PHONY: mini-deerflow
mini-deerflow: check-uv ## Run the Mini DeerFlow deterministic offline conversation
	@$(UV_RUN) python -m mini_deerflow

.PHONY: mini-deerflow-eval
mini-deerflow-eval: check-uv ## Run deterministic result, trajectory, and budget evaluation
	@$(UV_RUN) python -m mini_deerflow.eval_demo

.PHONY: mini-deerflow-capstone
mini-deerflow-capstone: check-uv ## Run the offline long-task capstone scenario
	@rm -rf .capstone-demo
	@$(UV_RUN) python -m mini_deerflow.capstone

.PHONY: check-docs
check-docs: check-uv ## Build the documentation site and check generated links
	@cd docs-site && npm ci && SITE_BASE_PATH=$(SITE_BASE) SITE_URL=$(SITE_URL) REPOSITORY_URL=$(REPOSITORY_URL) npm run build
	@$(UV_RUN) python scripts/check_site_links.py --site docs-site/dist --base $(SITE_BASE)
	@$(UV_RUN) python scripts/check_site_contracts.py --site docs-site/dist --base $(SITE_BASE) --repo-root . --repository-url $(REPOSITORY_URL)

.PHONY: check
check: check-lock check-workflows test check-docs ## Run the complete local quality gate
