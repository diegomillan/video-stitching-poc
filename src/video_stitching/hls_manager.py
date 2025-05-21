"""HLS manifest manager for handling playlists."""
import m3u8
from typing import List
from .config import settings


class HLSManager:
    """Manager for HLS playlist operations."""

    def __init__(self, event_id: str):
        """
        Initialize HLS manager.

        Args:
            event_id: The event identifier
        """
        self.event_id = event_id
        self.playlist = m3u8.M3U8()
        self.playlist.version = 3
        self.playlist.target_duration = settings.segment_duration
        self.playlist.media_sequence = 0
        self.playlist.is_endlist = False

    def add_segment(self, segment_name: str, duration: float) -> None:
        """
        Add a segment to the playlist.

        Args:
            segment_name: Name of the segment file
            duration: Duration of the segment in seconds
        """
        segment = m3u8.Segment(
            uri=segment_name,
            duration=duration,
        )
        self.playlist.add_segment(segment)

    def get_manifest(self) -> str:
        """
        Get the current manifest as a string.

        Returns:
            The manifest content
        """
        return self.playlist.dumps()

    def finalize(self) -> None:
        """Mark the playlist as complete."""
        self.playlist.is_endlist = True
