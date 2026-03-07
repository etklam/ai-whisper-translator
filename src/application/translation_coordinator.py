import threading
from dataclasses import dataclass

from src.application.events import ProgressEvent
from src.domain.errors import ExternalServiceError


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

    def run(self, request):
        successful = 0
        failed = 0
        total = len(request.file_paths)
        for index, file_path in enumerate(request.file_paths, start=1):
            system_prompt = self.prompt_provider.get_prompt(use_alt_prompt=request.use_alt_prompt)

            for attempt in range(request.max_retries + 1):
                try:
                    self.translation_client.translate_text(
                        text=file_path,
                        target_lang=request.target_lang,
                        model_name=request.model_name,
                        system_prompt=system_prompt,
                    )
                    successful += 1
                    break
                except ExternalServiceError:
                    if attempt == request.max_retries:
                        failed += 1
                except Exception:
                    failed += 1
                    break

            if self.event_sink:
                self.event_sink(
                    ProgressEvent(
                        current=index,
                        total=total,
                        message=f"Processed {index}/{total}",
                    )
                )
        return ExecutionSummary(
            total_files=len(request.file_paths),
            successful_files=successful,
            failed_files=failed,
        )

    def run_async(self, request, callback=None):
        def _run():
            summary = self.run(request)
            if callback:
                callback(summary)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread
