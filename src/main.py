import os
import sys
import tkinter as tk
import logging
import subprocess

# 添加當前目錄到 PATH，以便可以導入模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入自定義模組
from src.application.translation_coordinator import TranslationCoordinator
from src.application.asr_coordinator import ASRCoordinator
from src.gui.app import App
from src.infrastructure.prompt.json_prompt_provider import JsonPromptProvider
from src.infrastructure.runtime.logging_config import configure_logging
from src.infrastructure.subtitles.pysrt_subtitle_repository import PysrtSubtitleRepository
from src.infrastructure.translation.ollama_translation_client import OllamaTranslationClient

logger = logging.getLogger(__name__)


def ensure_yt_dlp():
    """Ensure yt-dlp is installed and up-to-date at startup."""
    try:
        # Try to upgrade yt-dlp
        logger.info("Checking yt-dlp installation...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            logger.info("yt-dlp is up-to-date")
        else:
            logger.warning("yt-dlp upgrade failed: %s", result.stderr)
    except subprocess.TimeoutExpired:
        logger.warning("yt-dlp upgrade timed out")
    except Exception as e:
        logger.warning("Failed to ensure yt-dlp: %s", e)


def build_default_coordinator():
    prompt_path = os.path.join(os.path.dirname(__file__), "translation", "prompts.json")
    logger.debug("Building default coordinator with prompt_path=%s", prompt_path)
    return TranslationCoordinator(
        subtitle_repo=PysrtSubtitleRepository(),
        translation_client=OllamaTranslationClient("http://localhost:11434/v1/chat/completions"),
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

    # Ensure yt-dlp is installed and up-to-date
    ensure_yt_dlp()

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
