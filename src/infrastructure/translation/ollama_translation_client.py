import json
import logging
import urllib.request

from src.domain.errors import ExternalServiceError

logger = logging.getLogger(__name__)


class OllamaTranslationClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        logger.debug("OllamaTranslationClient initialized endpoint=%s", endpoint)

    def translate_text(self, text: str, target_lang: str, model_name: str, system_prompt: str) -> str:
        logger.debug(
            "Sending translation request endpoint=%s model=%s target_lang=%s text_len=%s prompt_len=%s",
            self.endpoint,
            model_name,
            target_lang,
            len(text),
            len(system_prompt),
        )
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Translate the following text to {target_lang}:\n{text}"},
            ],
            "stream": False,
            "temperature": 0.1,
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"].strip()
                logger.debug("Translation response parsed content_len=%s", len(content))
                return content
        except Exception as exc:
            logger.error("Translation request failed error=%s", exc)
            raise ExternalServiceError(str(exc)) from exc
