import json
import logging
import os
import re
import urllib.request
import urllib.error

from src.domain.errors import ExternalServiceError

logger = logging.getLogger(__name__)


class LibreTranslateClient:
    def __init__(self, endpoint: str | None = None, api_key: str | None = None, timeout: int = 30):
        self.endpoint = endpoint or os.getenv("LIBRETRANSLATE_ENDPOINT", "https://libretranslate.com/translate")
        self.api_key = api_key or os.getenv("LIBRETRANSLATE_API_KEY", "")
        self.timeout = timeout
        logger.debug("LibreTranslateClient initialized endpoint=%s timeout=%s", self.endpoint, self.timeout)

    def translate_text(
        self,
        text: str,
        target_lang: str,
        model_name: str | None = None,
        system_prompt: str | None = None,
        source_lang: str | None = None,
    ) -> str:
        if not text or not text.strip():
            return text

        source_code = self._resolve_lang_code(source_lang, allow_auto=False)
        target_code = self._resolve_lang_code(target_lang, allow_auto=False)

        payload = {
            "q": text,
            "source": source_code,
            "target": target_code,
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                translated = result.get("translatedText", "").strip()
                if not translated:
                    raise ExternalServiceError("LibreTranslate returned empty translation")
                return translated
        except urllib.error.HTTPError as exc:
            raise ExternalServiceError(f"LibreTranslate HTTP error {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ExternalServiceError(f"Cannot connect to LibreTranslate: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ExternalServiceError("Invalid response from LibreTranslate") from exc
        except Exception as exc:
            raise ExternalServiceError(str(exc)) from exc

    def _resolve_lang_code(self, label: str | None, allow_auto: bool) -> str:
        if label is None:
            if allow_auto:
                return "auto"
            raise ExternalServiceError("Source language is required for LibreTranslate")

        normalized = label.strip()
        if allow_auto and normalized.lower() in {"auto", "auto detect", "自動偵測", "自动检测"}:
            return "auto"
        if normalized.lower() in {"auto", "auto detect", "自動偵測", "自动检测"}:
            raise ExternalServiceError("LibreTranslate does not support auto-detect in this app")

        # Pass through if it's already a language code
        if re.fullmatch(r"[a-z]{2}(-[A-Z]{2})?", normalized):
            return normalized

        mapping = {
            "英文": "en",
            "English": "en",
            "日文": "ja",
            "Japanese": "ja",
            "韓文": "ko",
            "韩文": "ko",
            "Korean": "ko",
            "法文": "fr",
            "French": "fr",
            "德文": "de",
            "German": "de",
            "西班牙文": "es",
            "Spanish": "es",
            "義大利文": "it",
            "意大利文": "it",
            "Italian": "it",
            "葡萄牙文": "pt",
            "Portuguese": "pt",
            "俄文": "ru",
            "Russian": "ru",
            "阿拉伯文": "ar",
            "Arabic": "ar",
            "印地文": "hi",
            "Hindi": "hi",
            "印尼文": "id",
            "Indonesian": "id",
            "越南文": "vi",
            "Vietnamese": "vi",
            "泰文": "th",
            "Thai": "th",
            "馬來文": "ms",
            "马来文": "ms",
            "Malay": "ms",
            "繁體中文": "zh-TW",
            "繁体中文": "zh-TW",
            "Traditional Chinese": "zh-TW",
            "簡體中文": "zh",
            "简体中文": "zh",
            "Simplified Chinese": "zh",
        }

        resolved = mapping.get(normalized)
        if not resolved:
            raise ExternalServiceError(f"Unsupported language selection: {label}")
        return resolved
