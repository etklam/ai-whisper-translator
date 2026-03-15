"""ASR Coordinator - Orchestrates audio transcription workflow."""

import logging
import sys
from dataclasses import dataclass
from typing import List, Optional

from src.application.events import ProgressEvent
from src.application.path_validation import ensure_existing_file, ensure_output_file_path
from src.domain.errors import ExternalServiceError


logger = logging.getLogger(__name__)


@dataclass
class ASRRequest:
    """Request for audio transcription."""

    input_path: str
    output_path: str
    model_path: str
    asr_provider: str = "auto"
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
            "ASR run started input=%s output=%s model=%s provider=%s lang=%s gpu=%s backend=%s",
            request.input_path,
            request.output_path,
            request.model_path,
            request.asr_provider,
            request.language,
            request.use_gpu,
            request.gpu_backend,
        )

        # Import transcriber here to avoid import errors if whisper.cpp is not available
        try:
            input_path = ensure_existing_file(request.input_path)
            model_path = ensure_existing_file(request.model_path, allowed_suffixes=(".bin",))
            output_path = ensure_output_file_path(request.output_path)
            from src.infrastructure.asr.providers import create_asr_provider

            for attempt in range(request.max_retries + 1):
                try:
                    logger.debug("ASR attempt=%s/%s", attempt + 1, request.max_retries + 1)

                    logger.debug(
                        "Initializing ASR provider provider=%s model=%s gpu=%s backend=%s",
                        request.asr_provider,
                        str(model_path),
                        request.use_gpu,
                        request.gpu_backend,
                    )
                    provider = create_asr_provider(
                        provider_name=request.asr_provider,
                        platform_name=sys.platform,
                        model_path=str(model_path),
                        use_gpu=request.use_gpu,
                        gpu_backend=request.gpu_backend,
                    )

                    if hasattr(provider, "load_model"):
                        self._emit_event(
                            ProgressEvent(
                                stage="loading_model",
                                current=0,
                                total=100,
                                message="Loading Whisper model...",
                            )
                        )
                        logger.debug("Loading ASR model...")
                        provider.load_model()
                        logger.info("ASR model loaded successfully provider=%s", provider.__class__.__name__)

                    self._emit_event(
                        ProgressEvent(
                            stage="transcribing",
                            current=0,
                            total=100,
                            message="Transcribing audio...",
                        )
                    )

                    language = None if request.language == "auto" else request.language
                    logger.debug("Starting transcription provider=%s language=%s threads=%s",
                                provider.__class__.__name__, language or "auto", request.n_threads)
                    segments = provider.transcribe(
                        input_path=str(input_path),
                        language=language,
                        n_threads=request.n_threads,
                        print_progress=False,
                    )
                    logger.info("Transcription completed segments=%s", len(segments))

                    detected_lang = None
                    if hasattr(provider, "get_detected_language"):
                        detected_lang = provider.get_detected_language()
                    logger.debug("Detected language: %s", detected_lang)

                    self._emit_event(
                        ProgressEvent(
                            stage="saving",
                            current=90,
                            total=100,
                            message="Saving transcription...",
                        )
                    )

                    logger.debug("Saving output format=%s path=%s", request.output_format, output_path)
                    self._save_output(
                        segments=segments,
                        output_path=str(output_path),
                        format=request.output_format,
                        language=detected_lang,
                    )

                    logger.info("ASR transcription successful path=%s", input_path)
                    successful += 1
                    break

                except Exception as exc:
                    logger.warning("ASR attempt %s failed: %s", attempt + 1, exc)
                    if attempt == request.max_retries:
                        failed += 1
                        logger.error("ASR transcription failed after all retries path=%s", input_path)
                        raise ExternalServiceError(f"ASR transcription failed: {exc}") from exc

        except ImportError as exc:
            logger.error("Failed to import ASR provider dependencies: %s", exc)
            raise ExternalServiceError(
                "ASR provider not available. Please install the required runtime dependencies."
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
