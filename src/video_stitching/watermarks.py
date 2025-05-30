"""Watermark configurations and implementations for video processing."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import ffmpeg


class WatermarkConfig(ABC):
    """Base class for watermark configurations."""

    @abstractmethod
    def apply(self, stream: ffmpeg.nodes.FilterableStream) -> ffmpeg.nodes.FilterableStream:
        """Apply the watermark to the video stream."""
        pass


class ImageWatermark(WatermarkConfig):
    """Image-based watermark configuration."""

    def __init__(
        self,
        image_path: str,
        x: int = 10,
        y: int = 10,
        alpha: float = 1.0
    ):
        """
        Initialize image watermark.

        Args:
            image_path: Path to the watermark image
            x: X position of the watermark
            y: Y position of the watermark
            alpha: Opacity of the watermark (0.0 to 1.0)
        """
        self.image_path = image_path
        self.x = x
        self.y = y
        self.alpha = alpha

    def apply(self, stream: ffmpeg.nodes.FilterableStream) -> ffmpeg.nodes.FilterableStream:
        """Apply image watermark to the stream."""
        return (
            stream
            .input(self.image_path)
            .filter('overlay', x=self.x, y=self.y, alpha=self.alpha)
        )


class TextWatermark(WatermarkConfig):
    """Text-based watermark configuration."""

    def __init__(
        self,
        text: str,
        x: int = 10,
        y: int = 10,
        fontsize: int = 48,
        fontcolor: str = 'white',
        alpha: float = 0.8,
        boxcolor: str = 'black@0.5'
    ):
        """
        Initialize text watermark.

        Args:
            text: Watermark text
            x: X position of the text
            y: Y position of the text
            fontsize: Size of the font
            fontcolor: Color of the text
            alpha: Opacity of the text (0.0 to 1.0)
            boxcolor: Color of the background box
        """
        self.text = text
        self.x = x
        self.y = y
        self.fontsize = fontsize
        self.fontcolor = fontcolor
        self.alpha = alpha
        self.boxcolor = boxcolor

    def apply(self, stream: ffmpeg.nodes.FilterableStream) -> ffmpeg.nodes.FilterableStream:
        """Apply text watermark to the stream."""
        print(f"Applying text watermark: '{self.text}' at position ({self.x}, {self.y})")
        return stream.filter(
            'drawtext',
            text=self.text,
            x=self.x,
            y=self.y,
            fontsize=self.fontsize,
            fontcolor=self.fontcolor,
            alpha=self.alpha,
            box=1,
            boxcolor=self.boxcolor,
            boxborderw=5,
            font='Arial'
        )


class AnimatedWatermark(WatermarkConfig):
    """Animated watermark configuration with fade in/out."""

    def __init__(
        self,
        image_path: str,
        x: int = 10,
        y: int = 10,
        fade_in_duration: float = 2.0,
        fade_out_duration: float = 2.0,
        display_duration: float = 6.0
    ):
        """
        Initialize animated watermark.

        Args:
            image_path: Path to the watermark image
            x: X position of the watermark
            y: Y position of the watermark
            fade_in_duration: Duration of fade in effect in seconds
            fade_out_duration: Duration of fade out effect in seconds
            display_duration: Duration of full opacity display in seconds
        """
        self.image_path = image_path
        self.x = x
        self.y = y
        self.fade_in_duration = fade_in_duration
        self.fade_out_duration = fade_out_duration
        self.display_duration = display_duration

    def apply(self, stream: ffmpeg.nodes.FilterableStream) -> ffmpeg.nodes.FilterableStream:
        """Apply animated watermark to the stream."""
        # Calculate the alpha expression for fade in/out
        fade_in = f"if(lt(t,{self.fade_in_duration}),t/{self.fade_in_duration}"
        fade_out = f"if(lt(t,{self.fade_in_duration + self.display_duration}),1"
        fade_out_end = f"if(lt(t,{self.fade_in_duration + self.display_duration + self.fade_out_duration}),1-(t-{self.fade_in_duration + self.display_duration})/{self.fade_out_duration},0)"

        alpha_expr = f"{fade_in},{fade_out},{fade_out_end})"

        return (
            stream
            .input(self.image_path)
            .filter('overlay', x=self.x, y=self.y, alpha=alpha_expr)
        )


class NoWatermark(WatermarkConfig):
    """No watermark configuration"""

    def apply(self, stream: ffmpeg.nodes.FilterableStream) -> ffmpeg.nodes.FilterableStream:
        """Return the stream unchanged."""
        return stream
