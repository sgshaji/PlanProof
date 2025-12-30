.PHONY: help install install-dev setup test test-unit test-integration coverage lint format clean run migrate migrate-create db-init db-reset docker-build docker-up docker-down docs

# Default target
help:
	@echo "PlanProof - Available Make Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install          - Install production dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo "  make setup            - Complete initial setup (venv + deps + db)"
	@echo ""
	@echo "Development:"
	@echo "  make run              - Start Streamlit UI"
	@echo "  make format           - Format code with Black"
	@echo "  make lint             - Run linters (Ruff + MyPy)"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make coverage         - Run tests with coverage report"
	@echo ""
	@echo "Database:"
	@echo "  make db-init          - Initialize database and run migrations"
	@echo "  make migrate          - Run pending migrations"
	@echo "  make migrate-create   - Create new migration (MSG='description')"
	@echo "  make db-reset         - Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     - Build Docker image"
	@echo "  make docker-up        - Start services with docker-compose"
	@echo "  make docker-down      - Stop and remove containers"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            - Remove cache files and artifacts"
	@echo "  make docs             - Generate documentation"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

setup: install-dev db-init
	@echo "✓ Setup complete! Run 'make run' to start the application"

# Development
run:
	python run_ui.py

format:
	black planproof/ tests/ scripts/ --line-length 100
	@echo "✓ Code formatted"

lint:
	@echo "Running Ruff..."
	ruff check planproof/ tests/ scripts/
	@echo "Running MyPy..."
	mypy planproof/ --ignore-missing-imports
	@echo "✓ Linting complete"

# Testing
test:
	pytest -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v -m "not slow"

coverage:
	pytest --cov=planproof --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "✓ Coverage report generated in htmlcov/"

# Database
db-init:
	@echo "Initializing database..."
	alembic upgrade head
	@echo "✓ Database initialized"

migrate:
	alembic upgrade head

migrate-create:
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG required. Usage: make migrate-create MSG='description'"; \
		exit 1; \
	fi
	alembic revision --autogenerate -m "$(MSG)"

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ]
	alembic downgrade base
	alembic upgrade head
	@echo "✓ Database reset complete"

# Docker
docker-build:
	docker build -t planproof:latest .

docker-up:
	docker-compose up -d
	@echo "✓ Services started. Access UI at http://localhost:8501"

docker-down:
	docker-compose down

# Utilities
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage dist/ build/
	@echo "✓ Cleaned cache files and artifacts"

docs:
	@echo "Documentation is in docs/ folder"
	@echo "View README.md for quick start"

# Quality checks (run before commit)
check: format lint test
	@echo "✓ All checks passed!"
