.PHONY: setup run test-unit test-int test-e2e lint clean

PYTHON := python3
PIP := pip3
UVICORN := uvicorn
PYTEST := pytest
NPM := npm

BACKEND_DIR := backend
FRONTEND_DIR := frontend
APP_MODULE := app.main:app
HOST := 0.0.0.0
PORT := 8000

setup: setup-backend setup-frontend

setup-backend:
	cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt

setup-frontend:
	cd $(FRONTEND_DIR) && $(NPM) install

run: run-backend

run-backend:
	cd $(BACKEND_DIR) && $(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

run-frontend:
	cd $(FRONTEND_DIR) && $(NPM) start

run-all:
	$(MAKE) run-backend &
	$(MAKE) run-frontend

test-unit:
	cd $(BACKEND_DIR) && $(PYTEST) tests/unit -v --tb=short

test-int:
	cd $(BACKEND_DIR) && $(PYTEST) tests/integration -v --tb=short

test-e2e:
	cd $(BACKEND_DIR) && $(PYTEST) tests/e2e -v --tb=short

test-all:
	cd $(BACKEND_DIR) && $(PYTEST) tests/ -v --tb=short

lint: lint-backend lint-frontend

lint-backend:
	cd $(BACKEND_DIR) && ruff check . && mypy app/

lint-frontend:
	cd $(FRONTEND_DIR) && $(NPM) run lint

migrate:
	cd $(BACKEND_DIR) && alembic upgrade head

migrate-down:
	cd $(BACKEND_DIR) && alembic downgrade -1

migrate-create:
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(msg)"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true

help:
	@echo "Available targets:"
	@echo "  setup          - Install all dependencies (backend + frontend)"
	@echo "  setup-backend  - Install Python dependencies"
	@echo "  setup-frontend - Install Node.js dependencies"
	@echo "  run            - Start the backend server (with hot reload)"
	@echo "  run-backend    - Start the FastAPI backend server"
	@echo "  run-frontend   - Start the React frontend dev server"
	@echo "  run-all        - Start both backend and frontend servers"
	@echo "  test-unit      - Run unit tests"
	@echo "  test-int       - Run integration tests"
	@echo "  test-e2e       - Run end-to-end tests"
	@echo "  test-all       - Run all tests"
	@echo "  lint           - Run linters (backend + frontend)"
	@echo "  lint-backend   - Run ruff and mypy on backend"
	@echo "  lint-frontend  - Run ESLint on frontend"
	@echo "  migrate        - Apply all pending database migrations"
	@echo "  migrate-down   - Revert the last database migration"
	@echo "  migrate-create - Create a new migration (usage: make migrate-create msg='description')"
	@echo "  clean          - Remove build artifacts and caches"