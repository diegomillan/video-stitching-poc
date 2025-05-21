"""Video stitching module for proof of concept."""
from typing import List
import cv2
import numpy as np


class VideoStitcher:
    """A simple video stitching class for proof of concept."""

    def __init__(self):
        """Initialize the video stitcher."""
        self.stitcher = cv2.Stitcher_create()

    def stitch_images(self, images: List[np.ndarray]) -> np.ndarray:
        """
        Stitch multiple images together.

        Args:
            images: List of numpy arrays representing images

        Returns:
            Stitched image as numpy array
        """
        if not images:
            raise ValueError("No images provided for stitching")

        status, stitched = self.stitcher.stitch(images)

        if status != cv2.Stitcher_OK:
            raise RuntimeError(f"Stitching failed with status: {status}")

        return stitched

    def stitch_video_frames(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        Stitch multiple video frames together.

        Args:
            frames: List of numpy arrays representing video frames

        Returns:
            Stitched frame as numpy array
        """
        return self.stitch_images(frames)
