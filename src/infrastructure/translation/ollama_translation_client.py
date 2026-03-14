import json
import logging
import os
import urllib.request
import urllib.error

from src.application.endpoint_policy import build_models_endpoint, validate_openai_endpoint
from src.domain.errors import ExternalServiceError
from src.infrastructure.runtime.logging_config import redact_endpoint

logger = logging.getLogger(__name__)


class OllamaTranslationClient:
    def __init__(self, endpoint: str | None = None, api_key: str | None = None, timeout: int = 30):
        resolution = validate_openai_endpoint(
            endpoint
            or os.getenv("OPENAI_COMPAT_ENDPOINT")
            or os.getenv("OLLAMA_ENDPOINT")
            or None
        )
        self.endpoint = resolution.endpoint
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OLLAMA_API_KEY", "")
        self.timeout = timeout
        logger.debug(
            "OllamaTranslationClient initialized endpoint=%s timeout=%s local=%s",
            redact_endpoint(self.endpoint),
            self.timeout,
            resolution.is_local,
        )

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        return validate_openai_endpoint(endpoint).endpoint

    @staticmethod
    def build_models_endpoint(endpoint: str | None) -> str:
        return build_models_endpoint(endpoint)

    def translate_text(
        self,
        text: str,
        target_lang: str,
        model_name: str,
        system_prompt: str,
        source_lang: str | None = None,
    ) -> str:
        logger.debug(
            "Sending translation request endpoint=%s model=%s target_lang=%s text_len=%s prompt_len=%s",
            redact_endpoint(self.endpoint),
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
        logger.debug("Request payload: model=%s messages_count=%s", model_name, len(payload["messages"]))
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        try:
            logger.debug("Sending HTTP request to OpenAI-compatible endpoint")
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                logger.debug("OpenAI-compatible response received")
                result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"].strip()
                logger.debug("Translation response parsed content_len=%s", len(content))
                logger.info("Translation successful input_len=%s output_len=%s", len(text), len(content))
                return content
        except urllib.error.HTTPError as exc:
            logger.error("HTTP error from OpenAI-compatible endpoint status=%s reason=%s", exc.code, exc.reason)
            raise ExternalServiceError(f"Ollama HTTP error {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            logger.error("URL error connecting to OpenAI-compatible endpoint error=%s", exc.reason)
            raise ExternalServiceError(f"Cannot connect to Ollama: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON response from OpenAI-compatible endpoint error=%s", exc)
            raise ExternalServiceError("Invalid response from Ollama") from exc
        except KeyError as exc:
            logger.error("Unexpected response structure from OpenAI-compatible endpoint missing_key=%s", exc)
            raise ExternalServiceError("Unexpected response format from Ollama") from exc
        except Exception as exc:
            logger.error("Translation request failed error=%s", exc)
            raise ExternalServiceError(str(exc)) from exc
