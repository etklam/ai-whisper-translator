from typing import Protocol


class TranslationClient(Protocol):
    def translate_text(self, text: str, target_lang: str, model_name: str, system_prompt: str) -> str: ...
