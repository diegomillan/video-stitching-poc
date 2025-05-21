"""Local video processing script for testing."""
import os
import subprocess
import json
from pathlib import Path
from typing import List, Literal
import m3u8


class LocalVideoProcessor:
    """Process videos locally for testing."""

    def __init__(self, input_dir: str, output_dir: str, segment_format: Literal["ts", "mp4"] = "ts"):
        """
        Initialize the processor.

        Args:
            input_dir: Directory containing input videos
            output_dir: Directory for output files
            segment_format: Format for output segments ("ts" or "mp4")
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.segment_format = segment_format
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize HLS playlist with best practices
        self.playlist = m3u8.M3U8()
        self.playlist.version = 7  # Using version 7 for better compatibility and features
        self.playlist.target_duration = 4  # 4-second segments for better streaming
        self.playlist.media_sequence = 0
        self.playlist.is_endlist = True  # VOD mode
        self.playlist.is_independent_segments = True  # Each segment can be decoded independently

    def get_video_files(self) -> List[Path]:
        """
        Get all video files from input directory.

        Returns:
            List of video file paths
        """
        return sorted(self.input_dir.glob("*.mp4"))

    def get_video_info(self, video_path: Path):
        """
        Use ffprobe to get video duration, width, height, and fps.
        """
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height,r_frame_rate,duration", "-of", "json", str(video_path)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        info = json.loads(result.stdout)
        stream = info["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        # r_frame_rate is like '30/1'
        fps_parts = stream["r_frame_rate"].split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1])
        # duration may be in stream or format
        duration = float(stream.get("duration", 0))
        if not duration:
            # fallback to format duration
            cmd2 = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
            ]
            result2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            duration = float(result2.stdout.strip())
        return width, height, fps, duration

    def process_videos(self) -> str:
        """
        Process all videos in the input directory.

        Returns:
            Path to the output playlist
        """
        video_files = self.get_video_files()
        if not video_files:
            raise ValueError("No video files found in input directory")

        # Process each video file
        for i, video_file in enumerate(video_files):
            width, height, fps, duration = self.get_video_info(video_file)

            # Create output segment file
            segment_name = f"segment_{i:03d}.{self.segment_format}"
            segment_path = self.output_dir / segment_name

            # Use FFmpeg to convert to desired format with optimized settings
            if self.segment_format == "ts":
                ffmpeg_cmd = (
                    f'ffmpeg -y -i "{video_file}" '
                    f'-c:v libx264 -preset fast -profile:v high -level 3.0 '
                    f'-b:v 2M -maxrate 2M -bufsize 4M '
                    f'-g {int(fps * 2)} '
                    f'-sc_threshold 0 '
                    f'-keyint_min {int(fps * 2)} '
                    f'-hls_time 4 '
                    f'-hls_list_size 0 '
                    f'-hls_segment_type mpegts '
                    f'-hls_flags independent_segments '
                    f'-f mpegts "{segment_path}"'
                )
            else:
                ffmpeg_cmd = (
                    f'ffmpeg -y -i "{video_file}" '
                    f'-c:v libx264 -preset fast -profile:v high -level 3.0 '
                    f'-b:v 2M -maxrate 2M -bufsize 4M '
                    f'-g {int(fps * 2)} '
                    f'-sc_threshold 0 '
                    f'-keyint_min {int(fps * 2)} '
                    f'-movflags +faststart "{segment_path}"'
                )

            os.system(ffmpeg_cmd)

            # Add segment to playlist
            segment = m3u8.Segment(
                uri=segment_name,
                duration=duration
            )
            # Add preload hint for the next segment if available
            if i < len(video_files) - 1:
                next_segment = f"segment_{(i + 1):03d}.{self.segment_format}"
                segment.preload_hint = m3u8.PreloadHint(
                    uri=next_segment,
                    type="PART",
                    base_uri=""
                )
            self.playlist.add_segment(segment)

        # Write playlist
        playlist_path = self.output_dir / "playlist.m3u8"
        with open(playlist_path, 'w') as f:
            f.write(self.playlist.dumps())

        return str(playlist_path)


def main():
    """Run the local processor."""
    # Get segment format from environment variable or default to "ts"
    segment_format = os.getenv("SEGMENT_FORMAT", "ts")
    if segment_format not in ["ts", "mp4"]:
        print(f"Warning: Invalid segment format '{segment_format}'. Using 'ts' instead.")
        segment_format = "ts"

    processor = LocalVideoProcessor("video-input", "output", segment_format=segment_format)
    try:
        output_path = processor.process_videos()
        print(f"Processing complete. Output saved to: {output_path}")
        print(f"Segment format: {segment_format}")
    except Exception as e:
        print(f"Error processing videos: {e}")


if __name__ == "__main__":
    main()
