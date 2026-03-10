"""ASR (Automatic Speech Recognition) module for whisper.cpp integration."""

from .whisper_transcriber import Transcriber
from .audio_downloader import AudioDownloader

__all__ = [
    "Transcriber",
    "AudioDownloader",
]
