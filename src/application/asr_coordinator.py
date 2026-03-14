"""ASR Coordinator - Orchestrates audio transcription workflow."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.application.events import ProgressEvent
from src.domain.errors import ExternalServiceError


logger = logging.getLogger(__name__)


@dataclass
class ASRRequest:
    """Request for audio transcription."""

    input_path: str
    output_path: str
    model_path: str
    language: Optional[str] = None
    use_gpu: bool = False
    gpu_backend: str = "auto"
    n_threads: int = 4
    output_format: str = "srt"
    max_retries: int = 1


@dataclass
class ASRSummary:
    """Summary of ASR operation."""

    total_files: int
    successful_files: int
    failed_files: int


class ASRCoordinator:
    """Coordinates ASR transcription workflow."""

    def __init__(self, event_sink=None):
        """
        Initialize ASR coordinator.

        Args:
            event_sink: Optional callback for progress events
        """
        self.event_sink = event_sink
        logger.debug("ASRCoordinator initialized with event_sink=%s", bool(event_sink))

    def run(self, request: ASRRequest) -> ASRSummary:
        """
        Execute ASR transcription.

        Args:
            request: ASR request parameters

        Returns:
            ASRSummary with operation statistics
        """
        successful = 0
        failed = 0
        total = 1  # Single file for now

        logger.info(
            "ASR run started input=%s output=%s model=%s lang=%s gpu=%s backend=%s",
            request.input_path,
            request.output_path,
            request.model_path,
            request.language,
            request.use_gpu,
            request.gpu_backend,
        )

        # Import transcriber here to avoid import errors if whisper.cpp is not available
        try:
            from src.asr.whisper_transcriber import Transcriber

            for attempt in range(request.max_retries + 1):
                try:
                    logger.debug("ASR attempt=%s/%s", attempt + 1, request.max_retries + 1)

                    # Initialize transcriber
                    logger.debug("Initializing transcriber model=%s gpu=%s backend=%s",
                                request.model_path, request.use_gpu, request.gpu_backend)
                    with Transcriber(
                        model_path=request.model_path,
                        use_gpu=request.use_gpu,
                        gpu_backend=request.gpu_backend,
                    ) as transcriber:
                        # Load model
                        self._emit_event(
                            ProgressEvent(
                                stage="loading_model",
                                current=0,
                                total=100,
                                message="Loading Whisper model...",
                            )
                        )
                        logger.debug("Loading Whisper model...")
                        transcriber.load_model()
                        logger.info("Whisper model loaded successfully, runtime_gpu=%s fallback=%s",
                                   transcriber.runtime_use_gpu, transcriber.used_fallback)

                        # Transcribe
                        self._emit_event(
                            ProgressEvent(
                                stage="transcribing",
                                current=0,
                                total=100,
                                message="Transcribing audio...",
                            )
                        )

                        language = None if request.language == "auto" else request.language
                        logger.debug("Starting transcription language=%s threads=%s",
                                    language or "auto", request.n_threads)
                        segments = transcriber.transcribe_file(
                            audio_path=request.input_path,
                            language=language,
                            n_threads=request.n_threads,
                            print_progress=False,
                        )
                        logger.info("Transcription completed segments=%s", len(segments))

                        # Get detected language
                        detected_lang = transcriber.wrapper.get_detected_language(transcriber.ctx)
                        logger.debug("Detected language: %s", detected_lang)

                        # Format and save output
                        self._emit_event(
                            ProgressEvent(
                                stage="saving",
                                current=90,
                                total=100,
                                message="Saving transcription...",
                            )
                        )

                        logger.debug("Saving output format=%s path=%s", request.output_format, request.output_path)
                        self._save_output(
                            segments=segments,
                            output_path=request.output_path,
                            format=request.output_format,
                            language=detected_lang,
                        )

                        logger.info("ASR transcription successful path=%s", request.input_path)
                        successful += 1
                        break

                except Exception as exc:
                    logger.warning("ASR attempt %s failed: %s", attempt + 1, exc)
                    if attempt == request.max_retries:
                        failed += 1
                        logger.error("ASR transcription failed after all retries path=%s", request.input_path)
                        raise ExternalServiceError(f"ASR transcription failed: {exc}") from exc

        except ImportError as exc:
            logger.error("Failed to import Transcriber: %s", exc)
            raise ExternalServiceError(
                "Whisper transcriber not available. Please install whisper.cpp library."
            ) from exc

        # Emit completion event
        self._emit_event(
            ProgressEvent(
                stage="complete",
                current=100,
                total=100,
                message="ASR transcription complete!",
            )
        )

        return ASRSummary(total_files=total, successful_files=successful, failed_files=failed)

    def _save_output(self, segments, output_path: str, format: str, language: str):
        """Save transcription output to file."""
        from src.asr.whisper_transcriber import save_output

        save_output(
            segments=segments,
            output_path=output_path,
            format=format,
            language=language,
        )

    def _emit_event(self, event: ProgressEvent):
        """Emit progress event if sink is configured."""
        if self.event_sink:
            self.event_sink(event)
