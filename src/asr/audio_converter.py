#!/usr/bin/env python3
"""
Audio converter module.
Converts audio files to the format required by whisper.cpp (16kHz mono PCM float32).
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import soundfile as sf

from src.asr.utils.constants import WHISPER_SAMPLE_RATE
from src.asr.utils.logger import get_logger


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    try:
        import numpy
        import soundfile
        return True
    except ImportError:
        return False


class AudioConverter:
    """
    Converts audio files to whisper.cpp compatible format.
    Required format: 16kHz, mono, PCM float32
    """

    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize the audio converter.

        Args:
            temp_dir: Temporary directory for intermediate files
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger()

    def convert_to_whisper_format(
        self,
        input_path: str,
        output_path: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Convert audio file to whisper.cpp format (16kHz mono float32).

        Args:
            input_path: Path to input audio file
            output_path: Optional path to save converted WAV file

        Returns:
            Tuple of (audio_samples, sample_rate) where audio_samples is a numpy array of float32

        Raises:
            RuntimeError: If conversion fails
        """
        input_path = Path(input_path)
        if not input_path.exists():
            self.logger.error(f"Input file not found: {input_path}")
            raise FileNotFoundError(f"Input file not found: {input_path}")

        self.logger.debug(f"Converting audio to whisper format: {input_path}")

        # First, try to use soundfile to read the audio
        try:
            self.logger.debug("Attempting conversion with soundfile...")
            audio, sr = sf.read(input_path, dtype="float32")
            self.logger.debug(f"Read audio: {len(audio)} samples at {sr} Hz")

            # Handle multi-channel audio - convert to mono by averaging
            if len(audio.shape) > 1:
                self.logger.debug(f"Converting from {audio.shape[1]} channels to mono")
                audio = np.mean(audio, axis=1)

            # Resample if necessary
            if sr != WHISPER_SAMPLE_RATE:
                self.logger.debug(f"Resampling from {sr} Hz to {WHISPER_SAMPLE_RATE} Hz")
                audio = self._resample_audio(audio, sr, WHISPER_SAMPLE_RATE)

            # Save to output path if specified
            if output_path:
                self.logger.debug(f"Saving converted audio to: {output_path}")
                sf.write(output_path, audio, WHISPER_SAMPLE_RATE, subtype="FLOAT")

            self.logger.debug("Audio conversion complete")
            self._log_audio_stats(audio, WHISPER_SAMPLE_RATE, source="soundfile")
            return audio, WHISPER_SAMPLE_RATE

        except Exception as e:
            # Fallback to ffmpeg if soundfile fails
            self.logger.warning(f"soundfile failed, trying ffmpeg: {e}")
            return self._convert_with_ffmpeg(input_path, output_path)

    def _convert_with_ffmpeg(
        self,
        input_path: Path,
        output_path: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Convert audio using ffmpeg.

        Args:
            input_path: Path to input audio file
            output_path: Optional path to save converted WAV file

        Returns:
            Tuple of (audio_samples, sample_rate)
        """
        # Create temporary output file if not specified
        if output_path is None:
            output_path = str(self.temp_dir / f"converted_{input_path.stem}.wav")

        self.logger.debug(f"Converting with ffmpeg to: {output_path}")

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i", str(input_path),  # Input file
            "-ar", str(WHISPER_SAMPLE_RATE),  # Sample rate
            "-ac", "1",  # Mono
            "-f", "wav",  # WAV format
            "-c:a", "pcm_f32le",  # PCM float32 little-endian
            "-y",  # Overwrite output file
            output_path,
        ]

        self.logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")

        try:
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            self.logger.debug("ffmpeg conversion successful, reading output file...")

            # Read the converted file
            audio, sr = sf.read(output_path, dtype="float32")

            # Ensure mono
            if len(audio.shape) > 1:
                self.logger.debug(f"Converting from {audio.shape[1]} channels to mono")
                audio = np.mean(audio, axis=1)

            self.logger.debug(f"ffmpeg conversion complete: {len(audio)} samples at {sr} Hz")
            self._log_audio_stats(audio, sr, source="ffmpeg")
            return audio, sr

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
            self.logger.error(f"ffmpeg conversion failed: {error_msg}")
            raise RuntimeError(f"ffmpeg conversion failed: {error_msg}")
        except Exception as e:
            self.logger.exception(f"Failed to convert audio: {e}")
            raise RuntimeError(f"Failed to convert audio: {e}")

    def _resample_audio(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int,
    ) -> np.ndarray:
        """
        Resample audio to target sample rate.

        Args:
            audio: Input audio array
            orig_sr: Original sample rate
            target_sr: Target sample rate

        Returns:
            Resampled audio array
        """
        self.logger.debug(f"Resampling audio from {orig_sr} Hz to {target_sr} Hz")

        # Calculate the number of samples in the target sample rate
        n_samples = int(len(audio) * target_sr / orig_sr)

        # Use numpy's linear interpolation for resampling
        indices = np.linspace(0, len(audio) - 1, n_samples)
        resampled = np.interp(indices, np.arange(len(audio)), audio)

        self.logger.debug(f"Resampled from {len(audio)} to {len(resampled)} samples")
        return resampled

    def _log_audio_stats(self, audio: np.ndarray, sr: int, source: str) -> None:
        """Log basic audio statistics to help diagnose silent/invalid input."""
        try:
            if audio.size == 0:
                self.logger.warning("Audio stats: empty audio source=%s sr=%s", source, sr)
                return

            finite_mask = np.isfinite(audio)
            if not np.all(finite_mask):
                invalid_count = int(np.size(audio) - np.count_nonzero(finite_mask))
                self.logger.warning("Audio stats: non-finite values detected count=%s source=%s", invalid_count, source)

            audio_min = float(np.min(audio))
            audio_max = float(np.max(audio))
            audio_mean = float(np.mean(audio))
            audio_rms = float(np.sqrt(np.mean(np.square(audio))))
            audio_abs_max = float(np.max(np.abs(audio)))
            zero_ratio = float(np.mean(audio == 0.0))

            self.logger.info(
                "Audio stats source=%s dtype=%s samples=%s sr=%s min=%.6f max=%.6f mean=%.6f rms=%.6f abs_max=%.6f zero_ratio=%.4f",
                source,
                audio.dtype,
                audio.size,
                sr,
                audio_min,
                audio_max,
                audio_mean,
                audio_rms,
                audio_abs_max,
                zero_ratio,
            )

            if audio_abs_max < 1e-4 or audio_rms < 1e-5:
                self.logger.warning(
                    "Audio appears nearly silent source=%s rms=%.6f abs_max=%.6f",
                    source,
                    audio_rms,
                    audio_abs_max,
                )
        except Exception as exc:
            self.logger.warning("Audio stats logging failed source=%s error=%s", source, exc)
