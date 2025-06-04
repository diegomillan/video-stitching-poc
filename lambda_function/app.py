"""Lambda function handler for video processing."""
import json
import os
from typing import Dict, Any, Literal
from pathlib import Path
from src.video_stitching.local_processor import LocalVideoProcessor
from src.video_stitching.validation import VideoValidator
import boto3
from botocore.exceptions import ClientError


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for video processing.

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Response dictionary
    """
    try:
        # Initialize services
        s3 = boto3.client('s3')
        validator = VideoValidator(
            metrics_bucket=os.environ['METRICS_BUCKET'],
            region=os.environ.get('AWS_REGION', 'us-east-1')
        )

        # In Lambda container, we're mounted at /var/task
        base_dir = Path('/var/task')

        # Create input and output directories
        input_dir = os.environ.get('INPUT_DIR', str(base_dir / 'video-input'))
        output_dir = os.environ.get('OUTPUT_DIR', '/tmp/output')

        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Handle S3 event
        if 'Records' in event:
            for record in event['Records']:
                if record.get('eventSource') == 'aws:s3':
                    bucket = record['s3']['bucket']['name']
                    key = record['s3']['object']['key']

                    # Download video from S3
                    local_path = os.path.join(input_dir, os.path.basename(key))
                    s3.download_file(bucket, key, local_path)

                    # Validate video
                    validation_result = validator.validate_video(local_path)
                    if not validation_result.is_valid:
                        return {
                            'statusCode': 400,
                            'body': json.dumps({
                                'error': 'Video validation failed',
                                'issues': validation_result.issues,
                                'metrics': validation_result.metrics
                            })
                        }

                    # Process video
                    processor = LocalVideoProcessor(input_dir, output_dir)
                    output_path = processor.process_videos(
                        format='ts',
                        input_ext='.mp4'
                    )

                    # Upload processed video to stream bucket
                    stream_bucket = os.environ['STREAM_BUCKET']
                    stream_key = f"streams/{os.path.basename(key)}"
                    s3.upload_file(output_path, stream_bucket, stream_key)

                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Video processed successfully',
                            'validation': validation_result.metrics,
                            'output_path': f"s3://{stream_bucket}/{stream_key}"
                        })
                    }

        # Handle API Gateway event
        else:
            # Parse request body
            body = json.loads(event.get('body', '{}'))
            process_type = body.get('process_type', 'process')

            # Map process types to format and input extension
            process_config = {
                'process': {'format': 'ts', 'input_ext': '.mp4'},
                'process-ts': {'format': 'ts', 'input_ext': '.mp4'},
                'process-mp4': {'format': 'mp4', 'input_ext': '.mp4'},
                'process-ts-mov': {'format': 'ts', 'input_ext': '.mov'},
                'process-ts-mp4': {'format': 'ts', 'input_ext': '.mp4'}
            }

            if process_type not in process_config:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Invalid process type. Must be one of: {", ".join(process_config.keys())}'
                    })
                }

            # Initialize processor
            processor = LocalVideoProcessor(input_dir, output_dir)

            # Process videos
            output_path = processor.process_videos(
                format=process_config[process_type]['format'],
                input_ext=process_config[process_type]['input_ext']
            )

            # Validate output
            validation_result = validator.validate_video(output_path)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Successfully executed {process_type}',
                    'output_path': output_path,
                    'validation': validation_result.metrics
                })
            }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
