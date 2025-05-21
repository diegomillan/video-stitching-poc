.PHONY: setup clean process process-ts process-mp4 download-samples sync serve simulate lint fix

# Python environment
VENV = .venv
PYTHON = $(VENV)/bin/python
UV = uv

# Directories
INPUT_DIR = video-input
OUTPUT_DIR = output

setup: $(VENV)
	$(UV) sync

$(VENV):
	$(UV) venv

sync:
	$(UV) sync

clean:
	rm -rf $(OUTPUT_DIR)/*
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

process: process-ts

process-ts:
	SEGMENT_FORMAT=ts $(PYTHON) -m src.video_stitching.local_processor

process-mp4:
	SEGMENT_FORMAT=mp4 $(PYTHON) -m src.video_stitching.local_processor

simulate: setup
	$(PYTHON) -m video_stitching.simulate_s3_event

download-samples:
	@echo "Downloading sample videos..."
	curl -L "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4" -o $(INPUT_DIR)/sample1.mp4
	curl -L "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_2MB.mp4" -o $(INPUT_DIR)/sample2.mp4

serve:
	@echo "Starting local server at http://localhost:8000"
	cd $(OUTPUT_DIR) && python3 -m http.server 8000

lint:
	@echo "Running ruff linter..."
	$(PYTHON) -m ruff check .

fix:
	@echo "Running ruff fix..."
	$(PYTHON) -m ruff check --fix .

help:
	@echo "Available commands:"
	@echo "  make setup          - Set up the Python virtual environment using uv"
	@echo "  make sync           - Sync dependencies using uv.lock"
	@echo "  make clean          - Clean up generated files"
	@echo "  make process        - Process videos into HLS segments (TS format)"
	@echo "  make process-ts     - Process videos into HLS segments (TS format)"
	@echo "  make process-mp4    - Process videos into MP4 segments"
	@echo "  make simulate       - Simulate S3 events for local testing"
	@echo "  make download-samples - Download sample videos for testing"
	@echo "  make serve          - Start a local server to view the video player"
	@echo "  make lint           - Run ruff linter to check for issues"
	@echo "  make fix            - Run ruff to automatically fix issues"
	@echo "  make help           - Show this help message"