.PHONY: help install install-dev test lint format clean run graph health-check

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test         - Run all tests"
	@echo "  lint         - Run linters (ruff, mypy)"
	@echo "  format       - Format code (black, isort)"
	@echo "  clean        - Clean temporary files"
	@echo "  run          - Run the agent (requires APK path)"
	@echo "  graph        - Generate knowledge graph"
	@echo "  health-check - Run KB health check"

# Install dependencies
install:
	pip install -r .agent/scripts/requirements.txt

install-dev: install
	pip install -r requirements-dev.txt
	pre-commit install

# Testing
test:
	pytest

test-cov:
	pytest --cov=.agent/scripts --cov-report=term-missing

# Linting
lint:
	ruff check .
	mypy .

lint-fix:
	ruff check --fix .
	mypy .

# Formatting
format:
	black .
	isort .

# Clean
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf **/__pycache__ **/.pytest_cache **/.mypy_cache **/.ruff_cache
	rm -rf build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Run the agent (requires APK path)
run:
	@echo "Usage: make run APK=/path/to/app.apk"
	@if [ -z "$(APK)" ]; then echo "Error: APK path required"; exit 1; fi
	python .agent/scripts/apk_fingerprint.py "$(APK)"

# Generate knowledge graph
graph:
	python .agent/scripts/graph_generator.py --open

# Health check
health-check:
	@echo "Running KB health check..."
	@echo "This will scan for dead links, orphans, and stale stubs"
