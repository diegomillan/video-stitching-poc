"""Video validation service for checking video quality and integrity."""
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import os
from dataclasses import dataclass, asdict
import boto3
from botocore.exceptions import ClientError
import ffmpeg


@dataclass
class ValidationResult:
    """Results of video validation."""
    is_valid: bool
    issues: List[str]
    metrics: Dict[str, float]
    timestamp: str
    video_path: str
    duration: float
    frame_count: int
    fps: float
    resolution: Tuple[int, int]
    bitrate: float
    has_audio: bool
    audio_sample_rate: Optional[float]
    audio_channels: Optional[int]
    container_timescale: Optional[int]
    video_timescale: Optional[int]
    container_bitrate: Optional[float]
    stream_bitrate: Optional[float]
    frame_rate_consistency: Optional[float]


class VideoValidator:
    """Validates video files for quality and integrity."""

    # Validation tolerances
    BITRATE_TOLERANCE = 0.2  # 20% tolerance for bitrate differences
    TIMESCALE_TOLERANCE = 0.1  # 10% tolerance for timescale differences
    MIN_FRAME_COUNT = 1  # Minimum number of frames required
    MIN_DURATION = 0.1  # Minimum duration in seconds

    def __init__(self, metrics_bucket: str, region: str = "us-east-1"):
        """
        Initialize the validator.

        Args:
            metrics_bucket: S3 bucket for storing validation metrics
            region: AWS region
        """
        self.metrics_bucket = metrics_bucket
        try:
            self.s3 = boto3.client('s3', region_name=region)
        except Exception as e:
            print(f"Warning: Could not initialize S3 client: {e}")
            self.s3 = None
        self.issues = []

    def validate_video(self, video_path: str) -> ValidationResult:
        """
        Validate a video file for common issues.

        Args:
            video_path: Path to the video file

        Returns:
            ValidationResult containing validation results and metrics
        """
        self.issues = []
        metrics = {}

        try:
            # Get video information using ffmpeg
            probe = ffmpeg.probe(video_path)
            
            # Analyze container and stream properties
            container_info = self._analyze_container(probe)
            video_info = self._analyze_video(probe)
            audio_info = self._analyze_audio(probe)
            
            # Basic video properties
            fps = video_info['fps']
            frame_count = video_info['frame_count']
            width = video_info['width']
            height = video_info['height']
            duration = video_info['duration']
            has_audio = audio_info['has_audio']
            audio_sample_rate = audio_info['sample_rate']
            audio_channels = audio_info['channels']

            # Check for minimum requirements
            if fps <= 0:
                self.issues.append("Invalid frame rate")
            if frame_count < self.MIN_FRAME_COUNT:
                self.issues.append(f"Frame count ({frame_count}) below minimum ({self.MIN_FRAME_COUNT})")
            if width <= 0 or height <= 0:
                self.issues.append("Invalid resolution")
            if duration < self.MIN_DURATION:
                self.issues.append(f"Duration ({duration:.2f}s) below minimum ({self.MIN_DURATION}s)")

            # Check for black frames
            black_frames = self._check_black_frames(video_path)
            if black_frames > 0:
                self.issues.append(f"Found {black_frames} black frames")

            # Check for frozen frames
            frozen_frames = self._check_frozen_frames(video_path)
            if frozen_frames > 0:
                self.issues.append(f"Found {frozen_frames} frozen frames")

            if not has_audio:
                self.issues.append("No audio track found")

            # Calculate bitrate
            file_size = os.path.getsize(video_path)
            bitrate = (file_size * 8) / duration if duration > 0 else 0

            # Check frame rate consistency
            frame_rate_consistency = self._check_frame_rate_consistency(video_path, frame_count, fps)

            # Validate container vs stream properties
            self._validate_container_properties(container_info, fps, bitrate)

            # Store metrics
            metrics.update({
                "fps": fps,
                "frame_count": frame_count,
                "duration": duration,
                "width": width,
                "height": height,
                "bitrate": bitrate,
                "black_frames": black_frames,
                "frozen_frames": frozen_frames,
                "has_audio": has_audio,
                "audio_sample_rate": audio_sample_rate,
                "audio_channels": audio_channels,
                "container_timescale": container_info.get('container_timescale'),
                "video_timescale": container_info.get('video_timescale'),
                "container_bitrate": container_info.get('container_bitrate'),
                "stream_bitrate": container_info.get('stream_bitrate'),
                "frame_rate_consistency": frame_rate_consistency
            })

            # Upload metrics to S3 if client is available
            if self.s3:
                self._upload_metrics(video_path, metrics)

            return self._create_result(
                video_path,
                len(self.issues) == 0,
                metrics,
                duration,
                frame_count,
                fps,
                (width, height),
                bitrate,
                has_audio,
                audio_sample_rate,
                audio_channels,
                container_info.get('container_timescale'),
                container_info.get('video_timescale'),
                container_info.get('container_bitrate'),
                container_info.get('stream_bitrate'),
                frame_rate_consistency
            )

        except Exception as e:
            self.issues.append(f"Validation error: {str(e)}")
            return self._create_result(video_path, False, metrics)

    def _analyze_container(self, probe: Dict) -> Dict:
        """Analyze container-level properties."""
        container_info = {}
        
        try:
            # Get container format
            format_info = probe.get('format', {})
            container_info['container_bitrate'] = float(format_info.get('bit_rate', 0)) / 1000  # Convert to kbps
            
            # Get video stream info
            video_stream = next((s for s in probe.get('streams', []) if s['codec_type'] == 'video'), None)
            if video_stream:
                # Get timescale information
                time_base = video_stream.get('time_base', '1/1000')
                if '/' in time_base:
                    container_info['container_timescale'] = int(time_base.split('/')[1])
                
                r_frame_rate = video_stream.get('r_frame_rate', '0/1')
                if '/' in r_frame_rate:
                    container_info['video_timescale'] = int(r_frame_rate.split('/')[1])
                
                container_info['stream_bitrate'] = float(video_stream.get('bit_rate', 0)) / 1000  # Convert to kbps
                
        except Exception as e:
            print(f"Error analyzing container: {e}")
            
        return container_info

    def _analyze_video(self, probe: Dict) -> Dict:
        """Analyze video stream properties."""
        video_info = {
            'fps': 0.0,
            'frame_count': 0,
            'width': 0,
            'height': 0,
            'duration': 0.0
        }
        
        try:
            # Find video stream
            video_stream = next((s for s in probe.get('streams', []) if s['codec_type'] == 'video'), None)
            if video_stream:
                # Parse frame rate
                fps_str = video_stream.get('r_frame_rate', '0/1')
                if '/' in fps_str:
                    num, den = map(int, fps_str.split('/'))
                    video_info['fps'] = num / den if den != 0 else 0
                
                # Get other properties
                video_info['width'] = int(video_stream.get('width', 0))
                video_info['height'] = int(video_stream.get('height', 0))
                video_info['duration'] = float(video_stream.get('duration', 0))
                video_info['frame_count'] = int(video_stream.get('nb_frames', 0))
                
        except Exception as e:
            print(f"Error analyzing video: {e}")
            
        return video_info

    def _analyze_audio(self, probe: Dict) -> Dict:
        """Analyze audio properties."""
        audio_info = {
            'has_audio': False,
            'sample_rate': 0.0,
            'channels': 0
        }
        
        try:
            # Find audio stream
            audio_stream = next((s for s in probe.get('streams', []) if s['codec_type'] == 'audio'), None)
            if audio_stream:
                audio_info['has_audio'] = True
                audio_info['sample_rate'] = float(audio_stream.get('sample_rate', 0))
                audio_info['channels'] = int(audio_stream.get('channels', 0))
                
        except Exception as e:
            print(f"Error analyzing audio: {e}")
            
        return audio_info

    def _check_black_frames(self, video_path: str) -> int:
        """Check for black frames in the video using ffmpeg."""
        try:
            # Use ffmpeg to extract frames and analyze them
            out, _ = (
                ffmpeg
                .input(video_path)
                .filter('select', 'eq(pict_type,I)')  # Only check I-frames
                .filter('blackdetect', d=0.1, pic_th=0.98)  # Detect black frames
                .output('pipe:', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Count black frame detections
            black_frames = len([line for line in out.decode().split('\n') if 'blackdetect' in line])
            return black_frames
            
        except Exception as e:
            print(f"Error checking black frames: {e}")
            return 0

    def _check_frozen_frames(self, video_path: str) -> int:
        """Check for frozen frames in the video using ffmpeg."""
        try:
            # Use ffmpeg to detect frozen frames
            out, _ = (
                ffmpeg
                .input(video_path)
                .filter('freezedetect', n=0.003, d=2)  # Detect frozen frames
                .output('pipe:', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Count frozen frame detections
            frozen_frames = len([line for line in out.decode().split('\n') if 'freezedetect' in line])
            return frozen_frames
            
        except Exception as e:
            print(f"Error checking frozen frames: {e}")
            return 0

    def _check_frame_rate_consistency(self, video_path: str, total_frames: int, target_fps: float) -> float:
        """Check frame rate consistency using ffmpeg."""
        if total_frames <= 0 or target_fps <= 0:
            return 0.0

        try:
            # Use ffmpeg to analyze frame timestamps
            out, _ = (
                ffmpeg
                .input(video_path)
                .filter('fps=fps=1')  # Sample at 1 fps to get timestamps
                .output('pipe:', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Parse timestamps from ffmpeg output
            timestamps = []
            for line in out.decode().split('\n'):
                if 'pts_time' in line:
                    try:
                        timestamp = float(line.split('pts_time:')[1].split()[0])
                        timestamps.append(timestamp)
                    except (IndexError, ValueError):
                        continue
            
            if not timestamps:
                return 0.0
                
            # Calculate frame intervals
            intervals = np.diff(timestamps)
            expected_interval = 1.0 / target_fps
            
            # Calculate consistency as percentage of frames within acceptable range
            acceptable_range = 0.1  # 10% tolerance
            consistent_frames = np.sum(np.abs(intervals - expected_interval) <= (expected_interval * acceptable_range))
            consistency = (consistent_frames / len(intervals)) * 100

            if consistency < 95:  # Less than 95% consistency
                self.issues.append(f"Frame rate inconsistency detected: {consistency:.1f}% of frames at expected intervals")

            return consistency
            
        except Exception as e:
            print(f"Error checking frame rate consistency: {e}")
            return 0.0

    def _validate_container_properties(self, container_info: Dict, fps: float, calculated_bitrate: float) -> None:
        """Validate container-level properties."""
        # Check timescale mismatch
        container_timescale = container_info.get('container_timescale')
        video_timescale = container_info.get('video_timescale')
        if container_timescale and video_timescale:
            # Calculate relative difference
            timescale_diff = abs(container_timescale - video_timescale) / max(container_timescale, video_timescale)
            if timescale_diff > self.TIMESCALE_TOLERANCE:
                self.issues.append(f"Timescale mismatch: container={container_timescale}, video={video_timescale}")

        # Check bitrate mismatch
        container_bitrate = container_info.get('container_bitrate')
        stream_bitrate = container_info.get('stream_bitrate')
        if container_bitrate and stream_bitrate:
            # Calculate relative difference
            bitrate_diff = abs(container_bitrate - stream_bitrate) / max(container_bitrate, stream_bitrate)
            if bitrate_diff > self.BITRATE_TOLERANCE:
                self.issues.append(f"Bitrate mismatch: container={container_bitrate}kbps, stream={stream_bitrate}kbps")

        # Check calculated vs container bitrate
        if container_bitrate:
            # Calculate relative difference
            bitrate_diff = abs(container_bitrate - calculated_bitrate) / max(container_bitrate, calculated_bitrate)
            if bitrate_diff > self.BITRATE_TOLERANCE:
                self.issues.append(f"Bitrate mismatch: container={container_bitrate}kbps, calculated={calculated_bitrate}kbps")

    def _create_result(
        self,
        video_path: str,
        is_valid: bool,
        metrics: Dict[str, float],
        duration: float = 0,
        frame_count: int = 0,
        fps: float = 0,
        resolution: Tuple[int, int] = (0, 0),
        bitrate: float = 0,
        has_audio: bool = False,
        audio_sample_rate: Optional[float] = None,
        audio_channels: Optional[int] = None,
        container_timescale: Optional[int] = None,
        video_timescale: Optional[int] = None,
        container_bitrate: Optional[float] = None,
        stream_bitrate: Optional[float] = None,
        frame_rate_consistency: Optional[float] = None
    ) -> ValidationResult:
        """Create a ValidationResult object."""
        return ValidationResult(
            is_valid=is_valid,
            issues=self.issues,
            metrics=metrics,
            timestamp=datetime.utcnow().isoformat(),
            video_path=video_path,
            duration=duration,
            frame_count=frame_count,
            fps=fps,
            resolution=resolution,
            bitrate=bitrate,
            has_audio=has_audio,
            audio_sample_rate=audio_sample_rate,
            audio_channels=audio_channels,
            container_timescale=container_timescale,
            video_timescale=video_timescale,
            container_bitrate=container_bitrate,
            stream_bitrate=stream_bitrate,
            frame_rate_consistency=frame_rate_consistency
        )

    def _upload_metrics(self, video_path: str, metrics: Dict[str, float]) -> None:
        """Upload validation metrics to S3."""
        if not self.s3:
            return

        try:
            # Create a unique key for the metrics file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            video_name = os.path.basename(video_path)
            key = f"validation-metrics/{timestamp}_{video_name}.json"

            # Upload metrics
            self.s3.put_object(
                Bucket=self.metrics_bucket,
                Key=key,
                Body=json.dumps(metrics, indent=2),
                ContentType="application/json"
            )
        except ClientError as e:
            print(f"Error uploading metrics: {e}") 