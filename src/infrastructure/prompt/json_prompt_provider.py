import json
import logging
from pathlib import Path

DEFAULT_PROMPT = "You are a professional translator."
logger = logging.getLogger(__name__)


class JsonPromptProvider:
    def __init__(self, prompt_path: str):
        self.prompt_path = Path(prompt_path)
        logger.debug("JsonPromptProvider initialized prompt_path=%s", self.prompt_path)

    def get_prompt(self, use_alt_prompt: bool, language: str | None = None) -> str:
        logger.debug(
            "Loading prompt use_alt_prompt=%s language=%s path=%s",
            use_alt_prompt,
            language,
            self.prompt_path,
        )
        try:
            data = json.loads(self.prompt_path.read_text(encoding="utf-8"))
            if use_alt_prompt:
                if language:
                    prompt = data.get(f"alt_prompt_{language}") or data.get("alt_prompt")
                else:
                    prompt = data.get("alt_prompt")
                prompt = prompt or data.get("default_prompt", DEFAULT_PROMPT)
                logger.debug("Loaded alt prompt len=%s", len(prompt))
                return prompt
            if language:
                prompt = data.get(f"default_prompt_{language}") or data.get("default_prompt", DEFAULT_PROMPT)
            else:
                prompt = data.get("default_prompt", DEFAULT_PROMPT)
            logger.debug("Loaded default prompt len=%s", len(prompt))
            return prompt
        except Exception as exc:
            logger.warning("Prompt load failed path=%s error=%s; using fallback", self.prompt_path, exc)
            return DEFAULT_PROMPT
