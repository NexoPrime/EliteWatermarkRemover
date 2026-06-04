.PHONY: help install dev test lint format type-check clean run build

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

dev: ## Install dev dependencies
	pip install -e ".[dev]"

test: ## Run tests with coverage
	pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

lint: ## Run linters
	flake8 src/ tests/
	python -m mypy src/ --ignore-missing-imports

format: ## Format code with black and isort
	black src/ tests/
	isort src/ tests/

type-check: ## Run type checking
	python -m mypy src/ --ignore-missing-imports --strict

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

run: ## Run the application
	python run.py

build: ## Build distribution packages
	python -m build

package: ## Compile standalone desktop executable
	pyinstaller --name "EliteWatermarkRemover" \
		--windowed \
		--onefile \
		--icon="assets/app_icon.ico" \
		--add-data="assets:assets" \
		--clean \
		--noconfirm \
		run.py
