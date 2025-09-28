# Makefile for the Image Upload Service
# This file provides a convenient set of commands for common development tasks.

# Use bash for all shell commands and ensure the virtual environment is activated.
SHELL := /bin/bash
VENV_ACTIVATE := source .venv/bin/activate;

# Get the API URL once and reuse it. The script is designed to be idempotent.
# The `| cat` prevents make from trying to interpret the output as a makefile.
API_URL := $(shell ./scripts/get_api_url.sh | cat)

# Phony targets are not files. This prevents make from getting confused if a file
# with the same name as a target exists.
.PHONY: help install run-local stop-local deploy-local get-url test coverage view-coverage clean check-prereqs api-upload api-list api-download api-delete

help:
	@echo "Available commands:"
	@echo "  install       - Create a virtual environment and install dependencies."
	@echo "  run-local     - Start the LocalStack container."
	@echo "  stop-local    - Stop the LocalStack container and remove volumes."
	@echo "  check-prereqs - Verify that required tools (Docker, SAM CLI) are installed."
	@echo "  deploy-local  - Build and deploy the SAM application to LocalStack."
	@echo "  get-url       - Get the deployed API Gateway URL from LocalStack."
	@echo "  test          - Run the unit test suite."
	@echo "  coverage      - Run unit tests and generate a code coverage report."
	@echo "  view-coverage - Generate and open the HTML coverage report in a browser."
	@echo "  clean         - Remove build artifacts, cache files, and the virtual environment."
	@echo ""
	@echo "API Interaction Commands (Examples):"
	@echo "  make api-upload FILE=\"./path/to/image.jpg\" DESC=\"A sunset\" TAGS=\"nature,sky\""
	@echo "  make api-list"
	@echo "  make api-list TYPE=image/jpeg"
	@echo "  make api-list TAGS=nature"
	@echo "  make api-list ID=<image-id>"
	@echo "  make api-download ID=<image-id> OUT=\"downloaded.jpg\""
	@echo "  make api-delete ID=<image-id>"

check-prereqs:
	@echo "Checking for required command-line tools..."
	@for tool in docker docker-compose sam python3; do \
		if ! command -v $$tool &> /dev/null; then \
			echo "Error: '$$tool' is not installed or not in your PATH. Please install it and try again."; \
			exit 1; \
		fi \
	done
	@echo "All required tools are available."
	
install:
	@make check-prereqs
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Installing dependencies...";
	@$(VENV_ACTIVATE) pip install -r requirements.txt; \
	$(VENV_ACTIVATE) pip install -r requirements-dev.txt;
	@echo "Installation complete."

run-local: check-prereqs
	@echo "Starting LocalStack container in the background..."
	@docker-compose -f localstack-docker-compose.yml up -d

stop-local: check-prereqs
	@echo "Stopping LocalStack container and removing volumes..."
	@docker-compose -f localstack-docker-compose.yml down --volumes

deploy-local: install
	@# The 'install' target already runs 'check-prereqs'
	@echo "Building the SAM application..."
	@$(VENV_ACTIVATE) sam build
	@echo "Deploying to LocalStack..."
	@$(VENV_ACTIVATE) sam deploy --no-confirm-changeset --config-env local

get-url:
	@echo "API Gateway URL: $(API_URL)"

test: install
	@echo "Running unit tests..."
	@$(VENV_ACTIVATE) pytest

coverage: test
	@echo "Generating code coverage report..."
	@$(VENV_ACTIVATE) pytest --cov=src --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

view-coverage: coverage
	@echo "Opening coverage report in browser..."
	@# Use python's built-in webbrowser module for cross-platform compatibility
	@$(VENV_ACTIVATE) python -m webbrowser -t "htmlcov/index.html"

api-upload:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter is required."; \
		echo "Usage: make api-upload FILE=/path/to/your/image.jpg [DESC=\"A description\"] [TAGS=\"tag1,tag2\"]"; \
		exit 1; \
	fi
	@if [ ! -f "$(FILE)" ]; then \
		echo "Error: File not found at '$(FILE)'. Please provide a valid path."; \
		exit 1; \
	fi
	@if [ -z "$(API_URL)" ]; then echo "Error: Could not get API URL. Is the stack deployed?"; exit 1; fi; \
	echo "Uploading $(FILE) to $(API_URL)/images..."; \
	$(VENV_ACTIVATE) curl -sf -X POST \
		-F "file=@$(FILE)" \
		$(if $(DESC),-F "description=$(DESC)",) \
		$(if $(TAGS),-F "tags=$(TAGS)",) \
		$(API_URL)/images | python -m json.tool;

api-list:
	@if [ -z "$(API_URL)" ]; then echo "Error: Could not get API URL. Is the stack deployed?"; exit 1; fi
	@{ \
		PARAMS=""; \
		if [ ! -z "$(ID)" ]; then PARAMS="imageId=$(ID)"; fi; \
		if [ ! -z "$(TYPE)" ]; then PARAMS="$${PARAMS:+$${PARAMS}&}contentType=$(TYPE)"; fi; \
		if [ ! -z "$(TAGS)" ]; then PARAMS="$${PARAMS:+$${PARAMS}&}tags=$(TAGS)"; fi; \
		FULL_URL="$(API_URL)/images"; \
		if [ ! -z "$$PARAMS" ]; then FULL_URL="$$FULL_URL?$$PARAMS"; fi; \
		echo "Listing images from $$FULL_URL..."; \
		$(VENV_ACTIVATE) curl -s "$$FULL_URL" | python -m json.tool; \
	}

api-download:
	@if [ -z "$(ID)" ] || [ -z "$(OUT)" ]; then \
		echo "Error: ID and OUT parameters are required."; \
		echo "Usage: make api-download ID=<image-id> OUT=<filename.jpg>"; \
		exit 1; \
	fi
	@if [ -z "$(API_URL)" ]; then \
		echo "Error: Could not get API URL. Is the stack deployed?"; \
		exit 1; \
	fi; \
	echo "Downloading image $(ID) to $(OUT)..."; \
	HTTP_STATUS=$$(curl -s -L -w "%{http_code}" -o $(OUT) "$(API_URL)/images/$(ID)"); \
	if [ $$HTTP_STATUS -ge 400 ]; then \
		echo "Error: Download failed. Received HTTP status $$HTTP_STATUS."; \
		echo "Response body:"; \
		cat $(OUT); \
		rm $(OUT); \
		exit 1; \
	else \
		echo "Download complete."; \
	fi

api-delete:
	@if [ -z "$(ID)" ]; then \
		echo "Error: ID parameter is required."; \
		echo "Usage: make api-delete ID=<image-id-to-delete>"; \
		exit 1; \
	fi
	@if [ -z "$(API_URL)" ]; then echo "Error: Could not get API URL. Is the stack deployed?"; exit 1; fi; \
	echo "Deleting image $(ID) from $(API_URL)/images/$(ID)..."; \
	$(VENV_ACTIVATE) curl -s -X DELETE $(API_URL)/images/$(ID) | python -m json.tool;

clean:
	@echo "Cleaning up project..."
	@rm -rf .venv .aws-sam __pycache__ .pytest_cache .coverage htmlcov
	@find . -type d -name "__pycache__" -exec rm -rf {} +