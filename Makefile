.PHONY: setup clean process process-ts process-mp4 process-ts-mov process-ts-mp4 process-ts-mov-ffmpeg process-ts-mov-watermark process-ts-mov-text process-ts-mov-animated download-samples sync serve simulate lint fix fix-extensions

# Python environment
UV = uv

# Directories
INPUT_DIR = video-input
OUTPUT_DIR = output

setup:
	$(UV) sync

sync:
	$(UV) sync

clean:
	rm -rf $(OUTPUT_DIR)/*
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

process:
	@echo "Processing videos to HLS segments (both TS and MP4 formats)..."
	$(UV) run python -m src.video_stitching.local_processor

process-ts:
	@echo "Processing videos to HLS segments (TS format only)..."
	$(UV) run python -m src.video_stitching.local_processor --format ts

process-mp4:
	@echo "Processing videos to HLS segments (MP4 format only)..."
	$(UV) run python -m src.video_stitching.local_processor --format mp4

process-ts-mov:
	@echo "Processing .mov files to HLS segments (TS format)..."
	$(UV) run python -m src.video_stitching.local_processor --format ts --input-ext .mov

process-ts-mp4:
	@echo "Processing .mp4 files to HLS segments (TS format)..."
	$(UV) run python -m src.video_stitching.local_processor --format ts --input-ext .mp4

process-ts-mov-ffmpeg:
	@echo "Processing .mov files to HLS segments (TS format) using ffmpeg-python..."
	$(UV) run python -m src.video_stitching.local_processor_ffmpeg --format ts --input-ext .mov

process-ts-mov-watermark:
	@echo "Processing .mov files to HLS segments (TS format) with image watermark..."
	$(UV) run python -m src.video_stitching.local_processor_ffmpeg --format ts --input-ext .mov --watermark-type image --watermark-path assets/watermark.png

process-ts-mov-text:
	@echo "Processing .mov files to HLS segments (TS format) with text watermark..."
	$(UV) run python -m src.video_stitching.local_processor_ffmpeg --format ts --input-ext .mov --watermark-type text --watermark-text "WATERMARK" --watermark-x 50 --watermark-y 50

process-ts-mov-animated:
	@echo "Processing .mov files to HLS segments (TS format) with animated watermark..."
	$(UV) run python -m src.video_stitching.local_processor_ffmpeg --format ts --input-ext .mov --watermark-type animated --watermark-path assets/watermark.png

simulate:
	$(UV) run python -m video_stitching.simulate_s3_event

download-samples:
	@echo "Downloading sample videos..."
	curl -L "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4" -o $(INPUT_DIR)/sample1.mp4
	curl -L "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_2MB.mp4" -o $(INPUT_DIR)/sample2.mp4

serve:
	@echo "Starting CORS-enabled server at http://localhost:8000"
	python3 server.py

lint:
	@echo "Running ruff linter..."
	$(UV) run python -m ruff check .

fix:
	@echo "Running ruff fix..."
	$(UV) run python -m ruff check --fix .

fix-extensions:
	@echo "Fixing video file extensions in $(INPUT_DIR)..."
	$(UV) run python -m src.video_stitching.fix_video_extensions

help:
	@echo "Available commands:"
	@echo "  make setup          - Set up the Python virtual environment using uv"
	@echo "  make sync           - Sync dependencies using uv.lock"
	@echo "  make clean          - Clean up generated files"
	@echo "  make process        - Process videos into HLS segments (both TS and MP4 formats)"
	@echo "  make process-ts     - Process videos into HLS segments (TS format only)"
	@echo "  make process-mp4    - Process videos into HLS segments (MP4 format only)"
	@echo "  make process-ts-mov - Process .mov files into HLS segments (TS format)"
	@echo "  make process-ts-mp4 - Process .mp4 files into HLS segments (TS format)"
	@echo "  make process-ts-mov-ffmpeg - Process .mov files into HLS segments (TS format) using ffmpeg-python"
	@echo "  make process-ts-mov-watermark - Process .mov files into HLS segments (TS format) with image watermark"
	@echo "  make process-ts-mov-text - Process .mov files into HLS segments (TS format) with text watermark"
	@echo "  make process-ts-mov-animated - Process .mov files into HLS segments (TS format) with animated watermark"
	@echo "  make simulate       - Simulate S3 events for local testing"
	@echo "  make download-samples - Download sample videos for testing"
	@echo "  make serve          - Start a CORS-enabled server to view the video player"
	@echo "  make lint           - Run ruff linter to check for issues"
	@echo "  make fix            - Run ruff to automatically fix issues"
	@echo "  make fix-extensions - Fix video file extensions in input directory"
	@echo "  make help           - Show this help message"

sam-build:
	@echo "Building SAM application..."
	source ./sam-env.sh && sam build

sam-start:
	@echo "Starting SAM API locally..."
	source ./sam-env.sh && sam local start-api

sam-invoke:
	@echo "Invoking SAM function..."
	source ./sam-env.sh && sam local invoke VideoProcessingFunction -e event.json

test-api:
	@echo "Testing API endpoint..."
	curl -X POST http://localhost:3000/process -H "Content-Type: application/json" -d '{"process_type": "process-ts-mp4"}'
