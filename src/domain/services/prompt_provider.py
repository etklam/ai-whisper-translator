from typing import Protocol


class PromptProvider(Protocol):
    def get_prompt(self, use_alt_prompt: bool, language: str | None = None) -> str: ...
