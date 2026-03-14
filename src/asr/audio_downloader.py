#!/usr/bin/env python3
"""
Audio downloader module using yt-dlp.
Downloads audio from YouTube and other video platforms.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import yt_dlp

from src.application.path_validation import ensure_output_directory
from src.asr.utils.helpers import sanitize_filename, check_ffmpeg_installed, print_ffmpeg_installation_help
from src.asr.utils.logger import get_logger


class AudioDownloader:
    """
    Downloads audio from video URLs using yt-dlp.
    """

    def __init__(self, output_dir: str = "downloads", cookies_from_browser: Optional[str] = None):
        """
        Initialize the audio downloader.

        Args:
            output_dir: Directory to save downloaded files
            cookies_from_browser: Browser name for yt-dlp cookies loading (e.g. "firefox")
        """
        self.output_dir = ensure_output_directory(output_dir)
        self.cookies_from_browser = cookies_from_browser.strip() if cookies_from_browser else None
        self.logger = get_logger()

    def _apply_cookie_options(self, ydl_opts: dict) -> dict:
        """Add yt-dlp browser-cookie settings when configured."""
        if self.cookies_from_browser:
            ydl_opts["cookiesfrombrowser"] = (self.cookies_from_browser,)
        return ydl_opts

    def _should_retry_after_update(self, error: Exception) -> bool:
        """Return True when a yt-dlp update retry is likely to help."""
        return "Requested format is not available" in str(error)

    def _update_yt_dlp(self) -> bool:
        """Try to update yt-dlp in the active Python environment."""
        self.logger.info("Attempting to update yt-dlp...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.logger.info("yt-dlp update completed")
            return True
        except Exception as e:
            self.logger.warning(f"yt-dlp update failed: {e}")
            return False

    def download_audio(
        self,
        url: str,
        output_filename: Optional[str] = None,
        audio_format: str = "bestaudio/best",
        quality: str = "192",
    ) -> str:
        """
        Download audio from a video URL.

        Args:
            url: Video URL (YouTube, etc.)
            output_filename: Custom output filename (without extension)
            audio_format: Audio format selector
            quality: Audio quality (bitrate in kbps)

        Returns:
            Path to the downloaded audio file

        Raises:
            yt_dlp.utils.DownloadError: If download fails
        """
        self.logger.debug(f"Starting audio download from: {url}")

        # Configure yt-dlp options
        ydl_opts = self._apply_cookie_options({
            "format": audio_format,
            "outtmpl": str(self.output_dir / "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "extract_flat": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }
            ],
        })

        # If custom filename is provided, use it
        if output_filename:
            ydl_opts["outtmpl"] = str(self.output_dir / f"{output_filename}.%(ext)s")
            self.logger.debug(f"Using custom output filename: {output_filename}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to get title
                self.logger.debug("Extracting video information...")
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "audio")
                safe_title = sanitize_filename(title)
                self.logger.debug(f"Video title: {title}, safe filename: {safe_title}")

                # Download the audio
                self.logger.info(f"Downloading audio from: {url}")
                self.logger.info(f"Title: {title}")
                ydl.download([url])

                # Find the downloaded file
                self.logger.debug(f"Searching for downloaded file: {safe_title}.*")
                downloaded_files = list(self.output_dir.glob(f"{safe_title}.*"))
                if downloaded_files:
                    # Prefer mp3 files
                    mp3_files = [f for f in downloaded_files if f.suffix.lower() == ".mp3"]
                    if mp3_files:
                        self.logger.debug(f"Found MP3 file: {mp3_files[0]}")
                        return str(mp3_files[0])
                    self.logger.debug(f"Found file: {downloaded_files[0]}")
                    return str(downloaded_files[0])

                # Fallback: look for any recent audio file
                self.logger.debug("Searching for recent audio files...")
                audio_files = []
                for ext in [".mp3", ".m4a", ".wav", ".webm"]:
                    audio_files.extend(self.output_dir.glob(f"*{ext}"))

                if audio_files:
                    # Return the most recently modified file
                    result = str(max(audio_files, key=lambda p: p.stat().st_mtime))
                    self.logger.debug(f"Found recent audio file: {result}")
                    return result

                self.logger.error("Could not find downloaded audio file")
                raise RuntimeError("Could not find downloaded audio file")

        except yt_dlp.utils.DownloadError as e:
            self.logger.error(f"Download failed: {e}")
            raise RuntimeError(f"Failed to download audio: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during download: {e}")
            raise RuntimeError(f"Unexpected error during download: {e}")

    def download_audio_to_wav(
        self,
        url: str,
        output_filename: Optional[str] = None,
    ) -> str:
        """
        Download audio and convert directly to WAV format.

        Args:
            url: Video URL
            output_filename: Custom output filename (without extension)

        Returns:
            Path to the WAV file
        """
        self.logger.debug(f"Starting WAV audio download from: {url}")

        # Configure yt-dlp options for WAV output
        ydl_opts = self._apply_cookie_options({
            "format": "bestaudio/best",
            "outtmpl": str(self.output_dir / "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }
            ],
        })

        if output_filename:
            ydl_opts["outtmpl"] = str(self.output_dir / f"{output_filename}.%(ext)s")
            self.logger.debug(f"Using custom output filename: {output_filename}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.debug("Extracting video information...")
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "audio")
                safe_title = sanitize_filename(title)
                self.logger.debug(f"Video title: {title}, safe filename: {safe_title}")

                self.logger.info(f"Downloading audio from: {url}")
                self.logger.info(f"Title: {title}")
                ydl.download([url])

                # Find the WAV file
                self.logger.debug(f"Searching for WAV file: {safe_title}.wav")
                wav_files = list(self.output_dir.glob(f"{safe_title}.wav"))
                if wav_files:
                    self.logger.debug(f"Found WAV file: {wav_files[0]}")
                    return str(wav_files[0])

                # Fallback: look for any recent WAV file
                self.logger.debug("Searching for recent WAV files...")
                wav_files = list(self.output_dir.glob("*.wav"))
                if wav_files:
                    result = str(max(wav_files, key=lambda p: p.stat().st_mtime))
                    self.logger.debug(f"Found recent WAV file: {result}")
                    return result

                self.logger.error("Could not find downloaded WAV file")
                raise RuntimeError("Could not find downloaded WAV file")

        except yt_dlp.utils.DownloadError as e:
            self.logger.error(f"Download failed: {e}")
            raise RuntimeError(f"Failed to download audio: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during download: {e}")
            raise RuntimeError(f"Unexpected error during download: {e}")

    def get_video_info(self, url: str) -> dict:
        """
        Get information about a video without downloading.

        Args:
            url: Video URL

        Returns:
            Dictionary with video information
        """
        self.logger.debug(f"Getting video info for: {url}")
        ydl_opts = self._apply_cookie_options({
            "ignoreconfig": True,
            "ignore_no_formats_error": True,
            "quiet": True,
            "no_warnings": True,
        })

        retried_after_update = False
        while True:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    result = {
                        "title": info.get("title", "Unknown"),
                        "duration": info.get("duration", 0),
                        "uploader": info.get("uploader", "Unknown"),
                        "view_count": info.get("view_count", 0),
                        "upload_date": info.get("upload_date", ""),
                    }
                    self.logger.debug(f"Video info retrieved: {result}")
                    return result
            except Exception as e:
                if (
                    not retried_after_update
                    and self._should_retry_after_update(e)
                    and self._update_yt_dlp()
                ):
                    retried_after_update = True
                    self.logger.info("Retrying video info extraction after yt-dlp update")
                    continue
                self.logger.error(f"Failed to get video info: {e}")
                raise RuntimeError(f"Failed to get video info: {e}")


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python audio_downloader.py <URL> [output_filename]")
        sys.exit(1)

    url = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) > 2 else None

    # Check ffmpeg
    if not check_ffmpeg_installed():
        print_ffmpeg_installation_help()

    # Download audio
    downloader = AudioDownloader()
    try:
        # Get video info
        info = downloader.get_video_info(url)
        print(f"\nVideo Information:")
        print(f"  Title: {info['title']}")
        print(f"  Duration: {info['duration']} seconds")
        print(f"  Uploader: {info['uploader']}")

        # Download
        audio_path = downloader.download_audio_to_wav(url, output_filename)
        print(f"\nDownloaded audio to: {audio_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
