"""Helper functions for ASR module."""

import os
import re
import shutil
import subprocess
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage."""
    # Replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized or "untitled"


def check_ffmpeg_installed() -> bool:
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def print_ffmpeg_installation_help():
    """Print ffmpeg installation help."""
    print("ERROR: ffmpeg is not installed or not in PATH")
    print("Please install ffmpeg:")
    print("  macOS:   brew install ffmpeg")
    print("  Ubuntu:  sudo apt install ffmpeg")
    print("  Windows: https://ffmpeg.org/download.html")
