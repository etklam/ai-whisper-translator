import threading
import logging
from dataclasses import dataclass

from src.application.events import ProgressEvent
from src.domain.errors import ExternalServiceError

logger = logging.getLogger(__name__)


@dataclass
class ExecutionSummary:
    total_files: int
    successful_files: int
    failed_files: int


class TranslationCoordinator:
    def __init__(self, subtitle_repo, translation_client, prompt_provider, event_sink=None):
        self.subtitle_repo = subtitle_repo
        self.translation_client = translation_client
        self.prompt_provider = prompt_provider
        self.event_sink = event_sink
        logger.debug(
            "TranslationCoordinator initialized repo=%s client=%s prompt_provider=%s event_sink=%s",
            type(subtitle_repo).__name__,
            type(translation_client).__name__,
            type(prompt_provider).__name__,
            bool(event_sink),
        )

    def run(self, request):
        successful = 0
        failed = 0
        total = len(request.file_paths)
        logger.info(
            "Coordinator run started total_files=%s target_lang=%s model=%s retries=%s",
            total,
            request.target_lang,
            request.model_name,
            request.max_retries,
        )
        for index, file_path in enumerate(request.file_paths, start=1):
            logger.debug("Processing file index=%s/%s path=%s", index, total, file_path)
            system_prompt = self.prompt_provider.get_prompt(use_alt_prompt=request.use_alt_prompt)

            for attempt in range(request.max_retries + 1):
                try:
                    logger.debug("Translate attempt=%s path=%s", attempt + 1, file_path)
                    self.translation_client.translate_text(
                        text=file_path,
                        target_lang=request.target_lang,
                        model_name=request.model_name,
                        system_prompt=system_prompt,
                    )
                    successful += 1
                    logger.debug("File translated successfully path=%s attempt=%s", file_path, attempt + 1)
                    break
                except ExternalServiceError as exc:
                    logger.warning(
                        "External service error path=%s attempt=%s/%s error=%s",
                        file_path,
                        attempt + 1,
                        request.max_retries + 1,
                        exc,
                    )
                    if attempt == request.max_retries:
                        failed += 1
                        logger.error("File failed after retries path=%s", file_path)
                except Exception:
                    failed += 1
                    logger.exception("Unexpected translation failure path=%s", file_path)
                    break

            if self.event_sink:
                self.event_sink(
                    ProgressEvent(
                        current=index,
                        total=total,
                        message=f"Processed {index}/{total}",
                    )
                )
            logger.debug(
                "Progress emitted index=%s/%s successful=%s failed=%s",
                index,
                total,
                successful,
                failed,
            )

        summary = ExecutionSummary(
            total_files=len(request.file_paths),
            successful_files=successful,
            failed_files=failed,
        )
        logger.info(
            "Coordinator run completed total=%s successful=%s failed=%s",
            summary.total_files,
            summary.successful_files,
            summary.failed_files,
        )
        return summary

    def run_async(self, request, callback=None):
        def _run():
            logger.debug("Async run thread started")
            summary = self.run(request)
            if callback:
                logger.debug("Invoking async callback")
                callback(summary)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        logger.debug("Async translation thread launched thread=%s", thread.name)
        return thread
