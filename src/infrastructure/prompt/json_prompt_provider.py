import json
import logging
from pathlib import Path

DEFAULT_PROMPT = "You are a professional translator."
logger = logging.getLogger(__name__)


class JsonPromptProvider:
    def __init__(self, prompt_path: str):
        self.prompt_path = Path(prompt_path)
        logger.debug("JsonPromptProvider initialized prompt_path=%s", self.prompt_path)

    def get_prompt(self, use_alt_prompt: bool) -> str:
        logger.debug("Loading prompt use_alt_prompt=%s path=%s", use_alt_prompt, self.prompt_path)
        try:
            data = json.loads(self.prompt_path.read_text(encoding="utf-8"))
            if use_alt_prompt:
                prompt = data.get("alt_prompt", data.get("default_prompt", DEFAULT_PROMPT))
                logger.debug("Loaded alt prompt len=%s", len(prompt))
                return prompt
            prompt = data.get("default_prompt", DEFAULT_PROMPT)
            logger.debug("Loaded default prompt len=%s", len(prompt))
            return prompt
        except Exception as exc:
            logger.warning("Prompt load failed path=%s error=%s; using fallback", self.prompt_path, exc)
            return DEFAULT_PROMPT
