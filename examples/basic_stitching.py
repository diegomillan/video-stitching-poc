"""Basic example of video stitching."""
import cv2
import numpy as np
from video_stitching.stitcher import VideoStitcher


def main():
    """Run a basic example of video stitching."""
    # Create sample images (in a real scenario, these would be video frames)
    img1 = cv2.imread("sample1.jpg")
    img2 = cv2.imread("sample2.jpg")

    if img1 is None or img2 is None:
        print("Error: Could not load sample images")
        return

    # Initialize the stitcher
    stitcher = VideoStitcher()

    try:
        # Stitch the images
        result = stitcher.stitch_images([img1, img2])

        # Display the result
        cv2.imshow("Stitched Result", result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    except Exception as e:
        print(f"Error during stitching: {e}")


if __name__ == "__main__":
    main() 
