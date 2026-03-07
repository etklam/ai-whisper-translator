import os
import sys
import tkinter as tk

# 添加當前目錄到 PATH，以便可以導入模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入自定義模組
from src.application.translation_coordinator import TranslationCoordinator
from src.gui.app import App
from src.infrastructure.prompt.json_prompt_provider import JsonPromptProvider
from src.infrastructure.subtitles.pysrt_subtitle_repository import PysrtSubtitleRepository
from src.infrastructure.translation.ollama_translation_client import OllamaTranslationClient


def build_default_coordinator():
    prompt_path = os.path.join(os.path.dirname(__file__), "translation", "prompts.json")
    return TranslationCoordinator(
        subtitle_repo=PysrtSubtitleRepository(),
        translation_client=OllamaTranslationClient("http://localhost:11434/v1/chat/completions"),
        prompt_provider=JsonPromptProvider(prompt_path),
        event_sink=None,
    )

def main():
    """程式主入口點"""
    coordinator = build_default_coordinator()
    app = App(coordinator=coordinator)
    coordinator.event_sink = app.on_coordinator_event
    app.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
