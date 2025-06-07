# Deepthought Development Makefile

.PHONY: test test-fast test-integration test-coverage clean install-dev lint format

# Test commands
test:
	pytest

test-fast:
	pytest -m "not slow and not integration"

test-integration:
	pytest -m integration

test-hardware:
	pytest -m hardware

test-coverage:
	pytest --cov=deepthought --cov-report=html --cov-report=term-missing

# Development setup
install-dev:
	pip install -e .
	pip install pytest pytest-asyncio pytest-cov black flake8 mypy

# Code quality
lint:
	flake8 deepthought/
	mypy deepthought/ --ignore-missing-imports

format:
	black deepthought/

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/

# Version management
version-beta:
	python -c "
import sys
sys.path.insert(0, '.')
from deepthought.version import get_version
print(f'Current version: {get_version()}')
"

# Documentation
docs:
	@echo "Documentation generation not yet implemented"

# Development workflow
dev-setup: install-dev
	@echo "Development environment ready!"
	@echo "Run 'make test-fast' for quick tests"
	@echo "Run 'make test' for full test suite"