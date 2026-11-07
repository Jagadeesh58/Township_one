.PHONY: help setup dev test test-backend test-frontend seed reset-demo build clean

PYTHON ?= python
NPM ?= npm

help:
	@echo "Township One - Development and Operations Automation"
	@echo ""
	@echo "Targets:"
	@echo "  setup       Install backend dependencies and frontend npm packages"
	@echo "  dev         Start development services (backend on :8000, frontend on :5173)"
	@echo "  test        Execute all automated tests (pytest suite + frontend vitest)"
	@echo "  seed        Deterministically seed synthetic township data in safe mode"
	@echo "  reset-demo  Cleanly reset and reseed local demo database with confirmation"
	@echo "  build       Compile frontend production build and verify typecheck"
	@echo "  clean       Remove temporary build artifacts and test caches"

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	cd frontend && $(NPM) ci

dev:
	@echo "Starting Township One services..."
	@echo "Backend API: http://localhost:8000 (docs at /docs)"
	@echo "Frontend UI: http://localhost:5173"
	@echo "Run backend:  uvicorn backend.app.main:app --reload --port 8000"
	@echo "Run frontend: cd frontend && npm run dev"

test: test-backend test-frontend

test-backend:
	$(PYTHON) -m pytest tests/ -v

test-frontend:
	cd frontend && $(NPM) test

seed:
	$(PYTHON) scripts/seed.py --mode safe

reset-demo:
	$(PYTHON) scripts/seed.py --mode reset-demo --confirm-local-demo

build:
	cd frontend && $(NPM) run build

clean:
	@rm -rf .pytest_cache frontend/dist .coverage htmlcov
