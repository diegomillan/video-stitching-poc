"""Lambda handler for processing video chunks."""
import json
import os
import tempfile
from typing import Any, Dict
import cv2
import numpy as np
from .s3_service import S3Service
from .hls_manager import HLSManager
from .config import settings


def get_event_id(key: str) -> str:
    """
    Extract event ID from S3 key.

    Args:
        key: S3 object key

    Returns:
        Event ID
    """
    return key.split("/")[1]


def process_chunk(event_id: str, chunk_name: str, s3_service: S3Service) -> None:
    """
    Process a single video chunk.

    Args:
        event_id: The event identifier
        chunk_name: Name of the chunk file
        s3_service: S3 service instance
    """
    # Download chunk
    chunk_data = s3_service.get_chunk(event_id, chunk_name)
    if not chunk_data:
        return

    # Save chunk to temporary file
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
        temp_file.write(chunk_data)
        temp_path = temp_file.name

    try:
        # Open video file
        cap = cv2.VideoCapture(temp_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {chunk_name}")

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps

        # Process video frames
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)

        cap.release()

        # Upload processed segment
        segment_name = f"segment_{chunk_name}"
        s3_service.upload_stream(event_id, segment_name, chunk_data)

        # Update HLS manifest
        hls_manager = HLSManager(event_id)
        hls_manager.add_segment(segment_name, duration)
        manifest = hls_manager.get_manifest()
        s3_service.upload_stream(event_id, "playlist.m3u8", manifest.encode())

    finally:
        # Clean up temporary file
        os.unlink(temp_path)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing S3 events.

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Response dictionary
    """
    try:
        # Initialize services
        s3_service = S3Service()

        # Process S3 event
        for record in event["Records"]:
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]

            # Skip if not in upload bucket
            if bucket != settings.upload_bucket:
                continue

            # Process chunk
            event_id = get_event_id(key)
            chunk_name = os.path.basename(key)
            process_chunk(event_id, chunk_name, s3_service)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Processing completed successfully"}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
