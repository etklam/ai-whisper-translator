#!/usr/bin/env python3
"""
Transcription module.
Orchestrates the audio transcription process using whisper.cpp.
"""

import ctypes
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np

from src.asr.whisper_wrapper import (
    WhisperWrapper,
    WhisperSegment,
    WhisperSamplingStrategy,
)
from src.asr.audio_converter import AudioConverter
from src.asr.utils.logger import get_logger


class Transcriber:
    """
    Transcribes audio files using whisper.cpp.
    """

    def __init__(
        self,
        model_path: str,
        library_path: Optional[str] = None,
        use_gpu: bool = False,
        gpu_backend: str = "auto",
        fallback_to_cpu: bool = True,
    ):
        """
        Initialize the transcriber.

        Args:
            model_path: Path to the whisper model (.ggml file)
            library_path: Path to libwhisper library (optional)
            use_gpu: Whether to use GPU acceleration
        """
        self.logger = get_logger()
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            self.logger.error(f"Model file not found: {model_path}")
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self.wrapper = WhisperWrapper(library_path=library_path)
        self.use_gpu = use_gpu
        self.requested_gpu_backend = gpu_backend
        self.fallback_to_cpu = fallback_to_cpu
        self.used_fallback = False
        self.runtime_use_gpu = use_gpu
        self.ctx = None
        self.logger.debug(
            f"Transcriber initialized with model: {model_path}, GPU: {use_gpu}, backend: {gpu_backend}"
        )

    def load_model(self):
        """Load the whisper model."""
        self.logger.info(
            f"Loading model from: {self.model_path} (requested_backend={self.requested_gpu_backend})"
        )
        try:
            self.ctx = self.wrapper.init_context(str(self.model_path), use_gpu=self.use_gpu)
            self.runtime_use_gpu = self.use_gpu
        except Exception as e:
            if self.use_gpu and self.fallback_to_cpu:
                self.logger.warning(f"GPU init failed, fallback to CPU: {e}")
                self.ctx = self.wrapper.init_context(str(self.model_path), use_gpu=False)
                self.runtime_use_gpu = False
                self.used_fallback = True
            else:
                raise
        self.logger.info("Model loaded successfully")
        self.logger.debug(f"Whisper version: {self.wrapper.get_version()}")
        self.logger.debug(f"System info: {self.wrapper.get_system_info()}")

    def transcribe_file(
        self,
        audio_path: str,
        language: Optional[str] = None,
        n_threads: int = 4,
        translate: bool = False,
        no_timestamps: bool = False,
        print_progress: bool = True,
    ) -> List[WhisperSegment]:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es', 'auto')
            n_threads: Number of threads to use
            translate: Whether to translate to English
            no_timestamps: Whether to disable timestamps
            print_progress: Whether to print progress

        Returns:
            List of WhisperSegment objects
        """
        if self.ctx is None:
            self.load_model()

        # Convert audio to whisper format
        self.logger.info(f"Processing audio: {audio_path}")
        converter = AudioConverter()
        audio_samples, sr = converter.convert_to_whisper_format(audio_path)

        self.logger.info(f"Audio info: {len(audio_samples)} samples at {sr} Hz")
        self.logger.info(f"Duration: {len(audio_samples) / sr:.2f} seconds")

        # Get transcription parameters
        params = self.wrapper.get_full_params(
            strategy=WhisperSamplingStrategy.WHISPER_SAMPLING_GREEDY,
            language=language,
            n_threads=n_threads,
            translate=translate,
            no_timestamps=no_timestamps,
            print_progress=print_progress,
        )

        # Convert numpy array to ctypes array
        audio_array = (ctypes.c_float * len(audio_samples))(*audio_samples)

        # Transcribe
        self.logger.info("Transcribing...")
        self.logger.debug(f"Language: {language}, Threads: {n_threads}, Translate: {translate}")
        segments = self.wrapper.transcribe(
            self.ctx,
            audio_array,
            len(audio_samples),
            params,
        )

        # Get detected language
        detected_lang = self.wrapper.get_detected_language(self.ctx)
        if detected_lang:
            self.logger.info(f"Detected language: {detected_lang}")

        # Print timings
        self.logger.debug("Performance timings:")
        self.wrapper.print_timings(self.ctx)

        return segments

    def close(self):
        """Free the whisper context."""
        if self.ctx is not None:
            self.logger.debug("Freeing whisper context")
            self.wrapper.free_context(self.ctx)
            self.ctx = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class OutputFormatter:
    """Formats transcription output in various formats."""

    @staticmethod
    def format_text(segments: List[WhisperSegment]) -> str:
        """
        Format segments as plain text.

        Args:
            segments: List of WhisperSegment objects

        Returns:
            Plain text string with each segment on a new line
        """
        return "\n".join(segment.text.strip() for segment in segments)

    @staticmethod
    def format_json(
        segments: List[WhisperSegment],
        language: Optional[str] = None,
    ) -> str:
        """
        Format segments as JSON.

        Args:
            segments: List of WhisperSegment objects
            language: Detected language code

        Returns:
            JSON string
        """
        data = {
            "language": language,
            "segments": [],
        }

        for segment in segments:
            data["segments"].append({
                "text": segment.text,
                "start": segment.start,
                "end": segment.end,
                "no_speech_prob": segment.no_speech_prob,
            })

        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def format_srt(segments: List[WhisperSegment]) -> str:
        """
        Format segments as SRT subtitles.

        Args:
            segments: List of WhisperSegment objects

        Returns:
            SRT formatted string
        """
        srt_lines = []

        for i, segment in enumerate(segments, start=1):
            # Convert milliseconds to SRT timestamp format (HH:MM:SS,mmm)
            start_time = segment.start
            end_time = segment.end

            start_srt = OutputFormatter._ms_to_srt_timestamp(start_time)
            end_srt = OutputFormatter._ms_to_srt_timestamp(end_time)

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_srt} --> {end_srt}")
            srt_lines.append(segment.text.strip())
            srt_lines.append("")  # Empty line between segments

        return "\n".join(srt_lines)

    @staticmethod
    def _ms_to_srt_timestamp(ms: int) -> str:
        """
        Convert milliseconds to SRT timestamp format.

        Args:
            ms: Milliseconds

        Returns:
            SRT timestamp string (HH:MM:SS,mmm)
        """
        total_seconds = ms / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int(ms % 1000)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    @staticmethod
    def format_verbose(segments: List[WhisperSegment]) -> str:
        """
        Format segments with timestamps.

        Args:
            segments: List of WhisperSegment objects

        Returns:
            Formatted string with timestamps
        """
        output = []
        for segment in segments:
            start_time = segment.start / 1000  # Convert to seconds
            end_time = segment.end / 1000
            output.append(f"[{start_time:.2f}s - {end_time:.2f}s] {segment.text}")

        return "\n".join(output)


def save_output(
    segments: List[WhisperSegment],
    output_path: str,
    format: str = "txt",
    language: Optional[str] = None,
):
    """
    Save transcription to a file.

    Args:
        segments: List of WhisperSegment objects
        output_path: Path to output file
        format: Output format (txt, json, srt, verbose)
        language: Detected language code
    """
    logger = get_logger()
    logger.debug(f"Saving output to: {output_path}, format: {format}")

    formatter = OutputFormatter()

    if format == "txt":
        content = formatter.format_text(segments)
    elif format == "json":
        content = formatter.format_json(segments, language)
    elif format == "srt":
        content = formatter.format_srt(segments)
    elif format == "verbose":
        content = formatter.format_verbose(segments)
    else:
        logger.error(f"Unknown format: {format}")
        raise ValueError(f"Unknown format: {format}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Output saved to: {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python transcriber.py <model_path> <audio_path> [language]")
        sys.exit(1)

    model_path = sys.argv[1]
    audio_path = sys.argv[2]
    language = sys.argv[3] if len(sys.argv) > 3 else None

    # Transcribe
    with Transcriber(model_path) as transcriber:
        segments = transcriber.transcribe_file(audio_path, language=language)

        # Print results
        print("\nTranscription:")
        print("=" * 60)
        for segment in segments:
            print(segment.text)
        print("=" * 60)
