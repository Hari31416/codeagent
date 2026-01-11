SHELL := /bin/bash

# Configuration
BACKEND_DIR = backend
FRONTEND_DIR = frontend
LOGS_DIR = logs
BACKEND_PORT = 8011
FRONTEND_PORT = 5170

.PHONY: help setup backend-setup frontend-setup start backend-start frontend-start frontend-preview stop backend-stop frontend-stop logs-dir up

up:
	docker compose -f docker-compose.infra.yml up -d

down:
	docker compose -f docker-compose.infra.yml down

help:
	@echo "Available commands:"
	@echo "  make setup            - Install dependencies for backend and frontend"
	@echo "  make start            - Start both backend and frontend"
	@echo "  make stop             - Stop both backend and frontend"
	@echo "  make backend-setup    - Install backend dependencies (using uv)"
	@echo "  make frontend-setup   - Install frontend dependencies (using pnpm)"
	@echo "  make backend-start    - Start backend server"
	@echo "  make frontend-start   - Start frontend dev server"
	@echo "  make frontend-preview - Start frontend preview server (production build)"
	@echo "  make backend-stop     - Stop backend server"
	@echo "  make frontend-stop    - Stop frontend server"
	@echo "  make up               - Start infrastructure (docker)"
	@echo "  make down             - Stop infrastructure (docker)"

logs-dir:
	@mkdir -p $(LOGS_DIR)

setup: backend-setup frontend-setup

backend-setup:
	@echo "Setting up backend..."
	cd $(BACKEND_DIR) && uv sync

frontend-setup:
	@echo "Setting up frontend..."
	cd $(FRONTEND_DIR) && pnpm install

start: up logs-dir backend-start frontend-start

backend-start: logs-dir
	@echo "Starting backend..."
	@nohup bash -c "cd $(BACKEND_DIR) && uv run uvicorn app:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload > ../$(LOGS_DIR)/backend.log 2>&1" & \
	echo "Backend starting on port $(BACKEND_PORT)... (logs in $(LOGS_DIR)/backend.log)"

frontend-start: logs-dir
	@echo "Starting frontend..."
	@nohup bash -c "cd $(FRONTEND_DIR) && pnpm run dev -- --port $(FRONTEND_PORT) > ../$(LOGS_DIR)/frontend.log 2>&1" & \
	echo "Frontend starting on port $(FRONTEND_PORT)... (logs in $(LOGS_DIR)/frontend.log)"

frontend-preview: logs-dir
	@echo "Building and starting frontend preview..."
	@cd $(FRONTEND_DIR) && pnpm run build
	@nohup bash -c "cd $(FRONTEND_DIR) && pnpm run preview > ../$(LOGS_DIR)/frontend-preview.log 2>&1" & \
	echo "Frontend preview starting... (logs in $(LOGS_DIR)/frontend-preview.log)"

stop: backend-stop frontend-stop down

backend-stop:
	@echo "Stopping backend on port $(BACKEND_PORT)..."
	@-lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || echo "Backend not running"

frontend-stop:
	@echo "Stopping frontend on port $(FRONTEND_PORT)..."
	@-lsof -ti:$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || echo "Frontend not running"

restart: stop start