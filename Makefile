.PHONY: help setup install shell test lint format type build clean build-kg

help:
	@echo "FTreeKG Development Commands"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make setup          Install dependencies with Poetry"
	@echo "  make shell          Activate Poetry shell"
	@echo "  make install        Install in editable mode"
	@echo "  make test           Run pytest suite"
	@echo "  make lint           Lint with ruff"
	@echo "  make format         Format with ruff"
	@echo "  make type           Type check with ty"
	@echo "  make build-kg       Build PyCodeKG + DocKG indices"
	@echo "  make clean          Remove build artifacts"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

setup:
	@./scripts/setup.sh

install:
	poetry install

shell:
	poetry shell

test:
	poetry run pytest tests -v --cov=ftree_kg

lint:
	poetry run ruff check src tests conftest.py

format:
	poetry run ruff format src tests conftest.py

type:
	poetry run ty check src

build-kg:
	@echo "Building PyCodeKG index..."
	poetry run pycodekg build --repo .
	@echo "Building DocKG index..."
	poetry run dockg build --repo .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pycodekg -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .dockg -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .filetreekg -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info
	@echo "✓ Cleaned build artifacts"

all: setup test lint type
	@echo "✅ All checks passed!"
