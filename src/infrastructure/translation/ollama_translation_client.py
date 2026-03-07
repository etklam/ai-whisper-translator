import json
import urllib.request

from src.domain.errors import ExternalServiceError


class OllamaTranslationClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def translate_text(self, text: str, target_lang: str, model_name: str, system_prompt: str) -> str:
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
                return result["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise ExternalServiceError(str(exc)) from exc
