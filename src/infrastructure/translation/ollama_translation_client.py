import json
import logging
import urllib.request
import urllib.error

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
        logger.debug("Request payload: model=%s messages_count=%s", model_name, len(payload["messages"]))
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            logger.debug("Sending HTTP request to Ollama...")
            with urllib.request.urlopen(req, timeout=30) as response:
                logger.debug("Ollama response received")
                result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"].strip()
                logger.debug("Translation response parsed content_len=%s", len(content))
                logger.info("Translation successful input_len=%s output_len=%s", len(text), len(content))
                return content
        except urllib.error.HTTPError as exc:
            logger.error("HTTP error from Ollama status=%s reason=%s", exc.code, exc.reason)
            raise ExternalServiceError(f"Ollama HTTP error {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            logger.error("URL error connecting to Ollama error=%s", exc.reason)
            raise ExternalServiceError(f"Cannot connect to Ollama: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON response from Ollama error=%s", exc)
            raise ExternalServiceError("Invalid response from Ollama") from exc
        except KeyError as exc:
            logger.error("Unexpected response structure from Ollama missing_key=%s", exc)
            raise ExternalServiceError("Unexpected response format from Ollama") from exc
        except Exception as exc:
            logger.error("Translation request failed error=%s", exc)
            raise ExternalServiceError(str(exc)) from exc
