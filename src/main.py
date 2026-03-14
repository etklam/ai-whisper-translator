import os
import sys
import logging

from src.application.dependency_health import check_yt_dlp
from src.application.translation_coordinator import TranslationCoordinator
from src.application.asr_coordinator import ASRCoordinator
from src.gui.app import App
from src.infrastructure.prompt.json_prompt_provider import JsonPromptProvider
from src.infrastructure.runtime.logging_config import configure_logging
from src.infrastructure.subtitles.pysrt_subtitle_repository import PysrtSubtitleRepository
from src.infrastructure.translation.ollama_translation_client import OllamaTranslationClient

logger = logging.getLogger(__name__)


def build_default_coordinator():
    prompt_path = os.path.join(os.path.dirname(__file__), "translation", "prompts.json")
    logger.debug("Building default coordinator with prompt_path=%s", prompt_path)
    return TranslationCoordinator(
        subtitle_repo=PysrtSubtitleRepository(),
        translation_client=OllamaTranslationClient(),
        prompt_provider=JsonPromptProvider(prompt_path),
        event_sink=None,
    )


def build_asr_coordinator():
    logger.debug("Building ASR coordinator")
    return ASRCoordinator(event_sink=None)

def main():
    """程式主入口點"""
    develop_mode = configure_logging()
    logger.info("Application startup")
    logger.debug("Develop mode=%s", develop_mode)
    yt_dlp_status = check_yt_dlp()
    logger.info("Dependency check name=%s available=%s detail=%s", yt_dlp_status.name, yt_dlp_status.available, yt_dlp_status.detail)

    coordinator = build_default_coordinator()
    asr_coordinator = build_asr_coordinator()
    app = App(coordinator=coordinator, asr_coordinator=asr_coordinator)
    coordinator.event_sink = app.on_coordinator_event
    asr_coordinator.event_sink = app.on_asr_event
    logger.debug("Coordinators event sink bound to GUI app")
    logger.info("Entering GUI main loop")
    app.mainloop()
    logger.info("Application shutdown")
    return 0

if __name__ == "__main__":
    sys.exit(main())
