.PHONY: help install env ollama-start ollama-models setup build up down logs restart start

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install        Install Homebrew dependencies (brew bundle)"
	@echo "  env            Copy .env.example to .env (skips if .env already exists)"
	@echo "  ollama-start   Start Ollama as a macOS background service"
	@echo "  ollama-models  Pull required Ollama models (llama3.1, nomic-embed-text)"
	@echo "  setup          Run env + install + ollama-start + ollama-models"
	@echo "  build          Build Docker images (docker-compose build)"
	@echo "  up             Start the stack in the background (docker-compose up -d)"
	@echo "  down           Stop and remove containers (docker-compose down)"
	@echo "  logs           Tail all container logs (docker-compose logs -f)"
	@echo "  restart        down then up"
	@echo "  start          Full first-time setup: setup + build + up"

install:
	brew bundle

env:
	@test -f .env && echo ".env already exists, skipping" || (cp .env.example .env && echo "Created .env from .env.example")

ollama-start:
	brew services start ollama

ollama-models:
	ollama pull llama3.1
	ollama pull nomic-embed-text

setup: env install ollama-start ollama-models

build:
	# First build can take 10-20 minutes — Docker pulls Docling, PyTorch, and dependencies
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart: down up

start: setup build up
