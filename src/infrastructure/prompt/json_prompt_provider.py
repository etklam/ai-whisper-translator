import json
from pathlib import Path

DEFAULT_PROMPT = "You are a professional translator."


class JsonPromptProvider:
    def __init__(self, prompt_path: str):
        self.prompt_path = Path(prompt_path)

    def get_prompt(self, use_alt_prompt: bool) -> str:
        try:
            data = json.loads(self.prompt_path.read_text(encoding="utf-8"))
            if use_alt_prompt:
                return data.get("alt_prompt", data.get("default_prompt", DEFAULT_PROMPT))
            return data.get("default_prompt", DEFAULT_PROMPT)
        except Exception:
            return DEFAULT_PROMPT
