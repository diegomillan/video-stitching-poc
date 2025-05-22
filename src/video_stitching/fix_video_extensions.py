import os
import mimetypes
import magic
from pathlib import Path

def get_video_extension(file_path):
    """Detect the actual video format of a file using python-magic."""
    try:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(str(file_path))

        if mime_type and mime_type.startswith('video/'):
            # Map common MIME types to file extensions
            mime_to_ext = {
                'video/mp4': '.mp4',
                'video/x-matroska': '.mkv',
                'video/quicktime': '.mov',
                'video/x-msvideo': '.avi',
                'video/webm': '.webm',
                'video/x-ms-wmv': '.wmv',
                'video/mpeg': '.mpg',
                'video/x-flv': '.flv'
            }
            return mime_to_ext.get(mime_type, '.mp4')  # Default to .mp4 if unknown
    except Exception as e:
        print(f"Error detecting MIME type for {file_path}: {e}")
    return None

def fix_video_extensions(input_dir):
    """Fix video file extensions in the input directory."""
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Input directory {input_dir} does not exist")
        return

    for file_path in input_path.glob('*'):
        if file_path.is_file():
            # Skip hidden files and files that already have a video extension
            if file_path.name.startswith('.') or file_path.suffix.lower() in ['.mp4', '.mkv', '.mov', '.avi', '.webm', '.wmv', '.mpg', '.flv']:
                continue

            # Get the correct extension
            correct_ext = get_video_extension(file_path)
            if correct_ext:
                new_path = file_path.with_suffix(correct_ext)
                try:
                    file_path.rename(new_path)
                    print(f"Renamed {file_path.name} to {new_path.name}")
                except Exception as e:
                    print(f"Error renaming {file_path.name}: {e}")
            else:
                print(f"Could not determine video format for {file_path.name}")

if __name__ == '__main__':
    input_dir = os.getenv('INPUT_DIR', 'video-input')
    fix_video_extensions(input_dir)
