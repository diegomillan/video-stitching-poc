import json
import os
from typing import Dict, Any, Literal
from pathlib import Path
from src.video_stitching.local_processor import LocalVideoProcessor

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for video processing
    """
    try:
        # In Lambda container, we're mounted at /var/task
        base_dir = Path('/var/task')

        # Create input and output directories
        input_dir = os.environ.get('INPUT_DIR', str(base_dir / 'video-input'))
        output_dir = os.environ.get('OUTPUT_DIR', '/tmp/output')

        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        process_type = body.get('process_type', 'process')  # Default to full process

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

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully executed {process_type}',
                'output_path': output_path
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
