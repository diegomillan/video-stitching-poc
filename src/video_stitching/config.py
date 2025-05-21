"""Configuration settings for the video stitching service."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    # AWS Settings
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    upload_bucket: str = Field(..., env="UPLOAD_BUCKET")
    stream_bucket: str = Field(..., env="STREAM_BUCKET")

    # HLS Settings
    segment_duration: int = Field(default=10, env="SEGMENT_DURATION")
    playlist_window: int = Field(default=60, env="PLAYLIST_WINDOW")

    # Processing Settings
    max_concurrent_events: int = Field(default=10, env="MAX_CONCURRENT_EVENTS")

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True


settings = Settings()
