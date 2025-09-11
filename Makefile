# Makefile untuk memudahkan penggunaan Docker commands
# Mom Transcript Docker Management

.PHONY: help build run-full run-batch run-hybrid run-live dev clean logs stop test

# Default target
help:
	@echo "Mom Transcript Docker Commands:"
	@echo ""
	@echo "Build Commands:"
	@echo "  make build          - Build Docker image (full profile)"
	@echo "  make build-no-cache - Build Docker image without cache (full profile)"
	@echo "  make build-all      - Build all Docker profiles"
	@echo "  make build-batch    - Build batch transcription profile"
	@echo "  make build-hybrid   - Build hybrid transcription profile"
	@echo "  make build-live     - Build live transcription profile"
	@echo "  make build-dev      - Build development profile"
	@echo ""
	@echo "Run Commands:"
	@echo "  make run-full       - Run full application (API)"
	@echo "  make run-batch      - Run batch transcription mode"
	@echo "  make run-hybrid     - Run hybrid transcription mode"
	@echo "  make run-live       - Run live transcription mode"
	@echo "  make dev            - Run development mode with shell access"
	@echo ""
	@echo "Management Commands:"
	@echo "  make logs           - Show container logs"
	@echo "  make stop           - Stop all running containers"
	@echo "  make clean          - Remove containers and images"
	@echo "  make restart        - Restart services"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make shell          - Access running container shell"
	@echo "  make health         - Check container health"
 	@echo "  make test           - Run test scripts"

# Build commands
build:
	@echo "Building Mom Transcript Docker image (full profile)..."
	docker compose --profile full build

build-no-cache:
	@echo "Building Mom Transcript Docker image (full profile, no cache)..."
	docker compose --profile full build --no-cache

build-all:
	@echo "Building all Mom Transcript Docker profiles..."
	docker compose --profile full --profile batch --profile hybrid --profile live --profile dev build

build-batch:
	@echo "Building batch transcription profile..."
	docker compose --profile batch build

build-hybrid:
	@echo "Building hybrid transcription profile..."
	docker compose --profile hybrid build

build-live:
	@echo "Building live transcription profile..."
	docker compose --profile live build

build-dev:
	@echo "Building development profile..."
	docker compose --profile dev build

# Run commands
run-full:
	@echo "Starting full Mom Transcript application..."
	docker compose --profile full up -d
	@echo "Application available at:"
	@echo "  Backend API: http://localhost:8000"

run-batch:
	@echo "Starting batch transcription mode..."
	docker compose --profile batch up

run-hybrid:
	@echo "Starting hybrid transcription mode..."
	docker compose --profile hybrid up

run-live:
	@echo "Starting live transcription mode..."
	docker compose --profile live up

dev:
	@echo "Starting development mode..."
	docker compose --profile dev up -d
	@echo "Access shell with: make shell"

# Management commands
logs:
	@echo "Showing container logs..."
	docker compose logs -f

stop:
	@echo "Stopping all Mom Transcript containers..."
	docker compose down

clean:
	@echo "Cleaning up containers and images..."
	docker compose down --rmi all --volumes --remove-orphans
restart:
	@echo "Restarting Mom Transcript services..."
	docker compose restart

# Utility commands
shell:
	@echo "Accessing container shell..."
	docker compose exec mom-transcript-dev /bin/bash || \
	docker compose exec mom-transcript /bin/bash

health:
	@echo "Checking container health..."
	docker compose ps
	@echo ""
	@echo "API Health Check:"
	@curl -f http://localhost:8000/health 2>/dev/null && echo "✅ API is healthy" || echo "❌ API is not responding"

# Tests (simple scripts; require local environment prerequisites)
test:
	@echo "Running test scripts (non-interactive)..."
	@echo "Note: tests/test_whisper_command.py requires whisper.cpp + audio in output/batch/recordings"
	@echo ""
	python3 tests/test_hybrid.py || true
	python3 tests/test_whisper_command.py || true
	@echo ""
	@echo "Interactive test (optional): python3 tests/test_batch_stop.py"

# Production commands
prod-build:
	@echo "Building production image..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-up:
	@echo "Starting production services..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Quick setup for new users
setup:
	@echo "Setting up Mom Transcript for first time..."
	@echo "1. Building Docker image..."
	@make build
	@echo "2. Creating necessary directories..."
	@mkdir -p output/{batch,hybrid,live} output/.transient
	@echo "3. Setup complete! Use 'make run-full' to start the application."
