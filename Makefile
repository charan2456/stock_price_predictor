.PHONY: install install-dev test lint format serve train scrape docker-build docker-up clean help

PYTHON := python3
PIP := pip

# ─────────────────────────────────────────────
#  Setup
# ─────────────────────────────────────────────

install: ## Install production dependencies
	$(PIP) install -e .

install-dev: ## Install development dependencies
	$(PIP) install -e ".[dev]"
	pre-commit install

# ─────────────────────────────────────────────
#  Data Pipeline
# ─────────────────────────────────────────────

scrape: ## Run full data ingestion pipeline
	$(PYTHON) -m src.data.data_pipeline

scrape-reddit: ## Scrape Reddit sentiment data only
	$(PYTHON) -m src.data.reddit_scraper

scrape-news: ## Scrape financial news only
	$(PYTHON) -m src.data.news_scraper

fetch-market: ## Fetch market data only
	$(PYTHON) -m src.data.market_data

# ─────────────────────────────────────────────
#  Training
# ─────────────────────────────────────────────

train: ## Train ensemble model with MLflow tracking
	$(PYTHON) -m src.models.trainer

train-lstm: ## Train LSTM model only
	$(PYTHON) -m src.models.lstm_model

train-xgb: ## Train XGBoost model only
	$(PYTHON) -m src.models.xgboost_model

# ─────────────────────────────────────────────
#  Serving
# ─────────────────────────────────────────────

serve: ## Start FastAPI prediction server
	$(PYTHON) -m src.serving.app

serve-dev: ## Start FastAPI server with hot reload
	uvicorn src.serving.app:app --reload --host 0.0.0.0 --port 8000

# ─────────────────────────────────────────────
#  Testing & Quality
# ─────────────────────────────────────────────

test: ## Run all tests with coverage
	pytest

test-fast: ## Run tests without coverage
	pytest --no-cov -x

lint: ## Run linter
	ruff check src/ tests/

format: ## Auto-format code
	ruff format src/ tests/

typecheck: ## Run type checker
	mypy src/

quality: lint typecheck test ## Run all quality checks

# ─────────────────────────────────────────────
#  Docker
# ─────────────────────────────────────────────

docker-build: ## Build Docker image
	docker-compose -f docker/docker-compose.yml build

docker-up: ## Start all services
	docker-compose -f docker/docker-compose.yml up -d

docker-down: ## Stop all services
	docker-compose -f docker/docker-compose.yml down

# ─────────────────────────────────────────────
#  MLflow
# ─────────────────────────────────────────────

mlflow-ui: ## Launch MLflow tracking UI
	mlflow ui --port 5000

# ─────────────────────────────────────────────
#  Cleanup
# ─────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# ─────────────────────────────────────────────
#  Help
# ─────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
