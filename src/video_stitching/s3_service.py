"""S3 service for handling video chunks and streams."""
import os
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from .config import settings


class S3Service:
    """Service for handling S3 operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
        )

    def get_chunk(self, event_id: str, chunk_name: str) -> Optional[bytes]:
        """
        Download a video chunk from S3.

        Args:
            event_id: The event identifier
            chunk_name: Name of the chunk file

        Returns:
            The chunk data as bytes or None if not found
        """
        try:
            key = f"uploads/{event_id}/{chunk_name}"
            response = self.s3.get_object(
                Bucket=settings.upload_bucket,
                Key=key,
            )
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def upload_stream(self, event_id: str, filename: str, data: bytes) -> str:
        """
        Upload a stream file to S3.

        Args:
            event_id: The event identifier
            filename: Name of the file
            data: File contents as bytes

        Returns:
            The S3 URL of the uploaded file
        """
        key = f"streams/{event_id}/{filename}"
        self.s3.put_object(
            Bucket=settings.stream_bucket,
            Key=key,
            Body=data,
            ContentType="application/vnd.apple.mpegurl" if filename.endswith(".m3u8") else "video/mp4",
        )
        return f"https://{settings.stream_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"

    def list_chunks(self, event_id: str) -> list[str]:
        """
        List all chunks for an event.

        Args:
            event_id: The event identifier

        Returns:
            List of chunk filenames
        """
        response = self.s3.list_objects_v2(
            Bucket=settings.upload_bucket,
            Prefix=f"uploads/{event_id}/",
        )
        return [os.path.basename(obj["Key"]) for obj in response.get("Contents", [])]
