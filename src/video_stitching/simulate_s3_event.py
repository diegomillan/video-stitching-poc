"""Simulate S3 events for local testing."""
import json
import os
from pathlib import Path
from .lambda_handler import lambda_handler


def simulate_s3_event(file_path: str, bucket_name: str = "test-bucket") -> None:
    """
    Simulate an S3 event for a file upload.

    Args:
        file_path: Path to the uploaded file
        bucket_name: Name of the S3 bucket
    """
    # Create S3 event structure
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": bucket_name
                    },
                    "object": {
                        "key": f"uploads/test-event/{os.path.basename(file_path)}"
                    }
                }
            }
        ]
    }

    # Process the event
    response = lambda_handler(event, None)
    print(f"Event processing response: {json.dumps(response, indent=2)}")


def main():
    """Run the S3 event simulator."""
    input_dir = Path("video-input")
    for video_file in input_dir.glob("*.mp4"):
        print(f"\nProcessing {video_file.name}...")
        simulate_s3_event(str(video_file))


if __name__ == "__main__":
    main()
