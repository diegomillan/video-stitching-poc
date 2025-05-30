"""Local video processing script using ffmpeg-python."""
import os
import json
from pathlib import Path
from typing import List, Literal, Optional
import ffmpeg
from .watermarks import WatermarkConfig, NoWatermark


class LocalVideoProcessor:
    """Process videos locally using ffmpeg-python."""

    def __init__(self, input_dir: str, output_dir: str, watermark: Optional[WatermarkConfig] = None):
        """
        Initialize the processor.

        Args:
            input_dir: Directory containing input videos
            output_dir: Directory for output files
            watermark: Optional watermark configuration
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.watermark = watermark or NoWatermark()

    def get_video_files(self, extension: str) -> List[Path]:
        """
        Get all video files from input directory with specific extension.

        Args:
            extension: File extension to filter by (e.g., '.mp4' or '.mov')

        Returns:
            List of video file paths
        """
        return sorted(self.input_dir.glob(f"*{extension}"))

    def process_videos(self, format: Literal["ts", "mp4"] = "ts", input_ext: Literal[".mp4", ".mov"] = ".mp4") -> str:
        """
        Process all videos in the input directory with specific extension.

        Args:
            format: Output format ("ts" or "mp4")
            input_ext: Input file extension (".mp4" or ".mov")

        Returns:
            Path to the output playlist
        """
        video_files = self.get_video_files(input_ext)
        if not video_files:
            raise ValueError(f"No {input_ext} files found in input directory")

        print(f"Found {len(video_files)} video files: {[f.name for f in video_files]}")

        # Create a concat file for all input videos
        concat_file = self.output_dir / f"concat_list_{input_ext[1:]}.txt"
        with open(concat_file, "w") as f:
            for vf in video_files:
                f.write(f"file '{vf.resolve()}'\n")

        print(f"Created concat file at: {concat_file}")

        # Set output format specific parameters
        if format == "ts":
            segment_type = "mpegts"
            segment_ext = "ts"
            segment_filename = f"segment_{input_ext[1:]}_%03d.ts"
        else:
            segment_type = "fmp4"
            segment_ext = "m4s"
            segment_filename = f"segment_{input_ext[1:]}_%03d.m4s"

        # Process videos into segments
        playlist_path = self.output_dir / f"playlist_{format}_{input_ext[1:]}.m3u8"

        try:
            # Create the base ffmpeg command
            stream = ffmpeg.input(str(concat_file), f='concat', safe=0)
            
            # Split into video and audio streams
            video = stream.video
            audio = stream.audio
            
            # Apply watermark to video stream
            if isinstance(self.watermark, NoWatermark):
                video = video
            else:
                video = self.watermark.apply(video)
            
            # Combine video and audio back together
            stream = ffmpeg.output(
                video,
                audio,
                str(playlist_path),
                vcodec='libx264',  # Video codec
                acodec='aac',      # Audio codec
                video_bitrate='2M',
                audio_bitrate='128k',
                preset='fast',
                profile='high',
                level='3.0',
                maxrate='2M',
                bufsize='4M',
                g='60',
                sc_threshold='0',
                keyint_min='60',
                hls_time='6',
                hls_list_size='0',
                hls_segment_type=segment_type,
                hls_flags='independent_segments',
                hls_segment_filename=str(self.output_dir / segment_filename),
                hls_playlist_type='vod',
                f='hls'
            ).overwrite_output()

            print("FFmpeg command:", ' '.join(stream.compile()))

            # Run the command
            stdout, stderr = stream.run(capture_stdout=True, capture_stderr=True)
            print("FFmpeg stdout:", stdout.decode())
            print("FFmpeg stderr:", stderr.decode())

        except ffmpeg.Error as e:
            print("FFmpeg stdout:", e.stdout.decode() if e.stdout else "No stdout")
            print("FFmpeg stderr:", e.stderr.decode() if e.stderr else "No stderr")
            raise RuntimeError(f"FFmpeg command failed: {e.stderr.decode() if e.stderr else str(e)}")

        return str(playlist_path)


def main():
    """Run the local processor."""
    import argparse
    from .watermarks import ImageWatermark, TextWatermark, AnimatedWatermark, NoWatermark

    parser = argparse.ArgumentParser()
    parser.add_argument('--format', choices=['ts', 'mp4'], default='ts',
                      help='Output format (ts or mp4)')
    parser.add_argument('--input-ext', choices=['.mp4', '.mov'], default='.mp4',
                      help='Input file extension (.mp4 or .mov)')
    parser.add_argument('--watermark-type', choices=['none', 'image', 'text', 'animated'], default='none',
                      help='Type of watermark to apply')
    parser.add_argument('--watermark-path', help='Path to watermark image (for image or animated watermark)')
    parser.add_argument('--watermark-text', help='Text for text watermark')
    parser.add_argument('--watermark-x', type=int, default=10, help='X position of watermark')
    parser.add_argument('--watermark-y', type=int, default=10, help='Y position of watermark')
    args = parser.parse_args()

    # Create watermark configuration based on arguments
    watermark = NoWatermark()
    if args.watermark_type == 'image' and args.watermark_path:
        watermark = ImageWatermark(args.watermark_path, args.watermark_x, args.watermark_y)
    elif args.watermark_type == 'text' and args.watermark_text:
        watermark = TextWatermark(args.watermark_text, args.watermark_x, args.watermark_y)
    elif args.watermark_type == 'animated' and args.watermark_path:
        watermark = AnimatedWatermark(args.watermark_path, args.watermark_x, args.watermark_y)

    processor = LocalVideoProcessor("video-input", "output", watermark)
    try:
        output_path = processor.process_videos(args.format, args.input_ext)
        print(f"Processing complete. Output saved to: {output_path}")
    except Exception as e:
        print(f"Error processing videos: {e}")


if __name__ == "__main__":
    main()
