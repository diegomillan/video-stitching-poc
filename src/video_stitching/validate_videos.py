"""Script to validate videos in the input directory."""
import argparse
import json
from pathlib import Path
from typing import List
from .validation import VideoValidator


def validate_videos(input_dir: str, output_file: str = None) -> None:
    """
    Validate all videos in the input directory.

    Args:
        input_dir: Directory containing videos to validate
        output_file: Optional JSON file to save validation results
    """
    # Initialize validator with a dummy bucket (not used in local mode)
    validator = VideoValidator(metrics_bucket="local-validation")
    
    # Get all video files
    input_path = Path(input_dir)
    video_files = list(input_path.glob("*.mp4")) + list(input_path.glob("*.mov"))
    
    if not video_files:
        print(f"No video files found in {input_dir}")
        return

    # Validate each video
    results = {}
    for video_file in video_files:
        print(f"\nValidating {video_file.name}...")
        result = validator.validate_video(str(video_file))
        
        # Print validation results
        print(f"Valid: {result.is_valid}")
        if result.issues:
            print("Issues found:")
            for issue in result.issues:
                print(f"  - {issue}")
        
        print("\nMetrics:")
        for key, value in result.metrics.items():
            print(f"  {key}: {value}")
        
        # Store results
        results[video_file.name] = {
            "is_valid": result.is_valid,
            "issues": result.issues,
            "metrics": result.metrics
        }

    # Save results to file if specified
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nValidation results saved to {output_file}")


def main():
    """Run the validation script."""
    parser = argparse.ArgumentParser(description="Validate videos in the input directory")
    parser.add_argument('--input-dir', default='video-input',
                      help='Directory containing videos to validate')
    parser.add_argument('--output-file',
                      help='JSON file to save validation results')
    args = parser.parse_args()

    validate_videos(args.input_dir, args.output_file)


if __name__ == "__main__":
    main()