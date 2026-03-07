import os
import sys
import tkinter as tk
import logging

# 添加當前目錄到 PATH，以便可以導入模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入自定義模組
from src.application.translation_coordinator import TranslationCoordinator
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
        translation_client=OllamaTranslationClient("http://localhost:11434/v1/chat/completions"),
        prompt_provider=JsonPromptProvider(prompt_path),
        event_sink=None,
    )

def main():
    """程式主入口點"""
    develop_mode = configure_logging()
    logger.info("Application startup")
    logger.debug("Develop mode=%s", develop_mode)

    coordinator = build_default_coordinator()
    app = App(coordinator=coordinator)
    coordinator.event_sink = app.on_coordinator_event
    logger.debug("Coordinator event sink bound to GUI app")
    logger.info("Entering GUI main loop")
    app.mainloop()
    logger.info("Application shutdown")
    return 0

if __name__ == "__main__":
    sys.exit(main())
