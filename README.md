# Video Stitching POC

This proof-of-concept demonstrates local video stitching and HLS streaming using Python, OpenCV, FFmpeg, and HLS.js. It is designed for local testing and can be adapted for cloud workflows (e.g., AWS Lambda + S3 triggers).

## How It Works

1. **Input Videos**: Place `.mp4` files in the `video-input` directory.
2. **Processing**: Run `make process` to:
   - Convert each `.mp4` into segments (either `.ts` or `.mp4` format)
   - Generate a `playlist.m3u8` HLS playlist in the `output` directory, referencing all segments in order.
3. **Serving**: Run `make serve` to start a local HTTP server in the `output` directory.
4. **Playback**: Open [http://localhost:8000/player.html](http://localhost:8000/player.html) in your browser to view the stitched video stream using a simple HLS.js-based player.

## Segment Formats

The POC supports two segment formats:

1. **HLS TS Segments** (default):
   ```sh
   make process-ts  # or just make process
   ```
   - Generates `.ts` segments using MPEG-TS container format
   - Best for HLS streaming
   - Compatible with most HLS players

2. **MP4 Segments**:
   ```sh
   make process-mp4
   ```
   - Generates `.mp4` segments
   - Useful for direct MP4 playback or when MP4 segments are required
   - Still works with HLS.js for streaming

## Why Serve the Application?

- **HLS streaming requires HTTP(S)**: Browsers and HLS.js fetch the playlist and video segments over HTTP. Opening `player.html` directly from the filesystem will not work due to browser security restrictions (CORS, file access).
- **Local server**: `make serve` uses Python's built-in HTTP server to serve the playlist, segments, and player page, simulating a real streaming environment.

## Video Scrubbing Support

- **Supported**: The player supports scrubbing (seeking) within the stitched video timeline, as all segments are referenced in the playlist and the playlist is finalized for VOD.
- **How it works**: HLS.js loads the playlist and segments, allowing you to jump to any point in the video after it is loaded.

## Usage

```sh
make clean                # Clean output directory
make download-samples     # Download sample videos to video-input/
make process-ts          # Process videos into HLS segments (TS format)
make process-mp4         # Process videos into MP4 segments
make serve               # Start local HTTP server in output/
```

Then open [http://localhost:8000/player.html](http://localhost:8000/player.html) in your browser.

## Project Structure

- `video-input/` — Place your input `.mp4` files here
- `output/`      — Contains generated segments (`.ts` or `.mp4`), `playlist.m3u8`, and `player.html`
- `src/video_stitching/local_processor.py` — Processes and stitches videos into HLS format
- `output/player.html` — Simple HTML5 player using HLS.js

## Requirements
- Python 3.8+
- FFmpeg (must be installed and available in your PATH)
- [uv](https://github.com/astral-sh/uv) for dependency management

## FAQ

**Q: Why do I need to run a server?**
A: HLS streaming only works over HTTP(S), not from the local filesystem.

**Q: Can I scrub/seek in the video?**
A: Yes, the player supports scrubbing within the stitched video.

**Q: Can I use my own videos?**
A: Yes! Place your `.mp4` files in `video-input/` and run `make process`.

**Q: Which segment format should I use?**
A: Use `.ts` for HLS streaming (default) or `.mp4` if you need MP4 segments for specific requirements.

---

For further improvements, see the TODO section in the code or open an issue. 