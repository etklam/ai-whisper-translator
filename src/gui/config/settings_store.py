import json
import logging
import os
from dataclasses import replace
from pathlib import Path

from src.application.settings_models import AppSettings
from src.infrastructure.asr.providers import resolve_asr_provider


logger = logging.getLogger(__name__)
CONFIG_FILENAME = ".config"


def default_settings_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", CONFIG_FILENAME)
    )


def snapshot_settings(raw_settings: dict) -> AppSettings:
    return AppSettings.from_dict(raw_settings)


def build_default_settings(platform_name: str | None = None) -> dict:
    settings = AppSettings(
        asr_provider=resolve_asr_provider("auto", platform_name or os.sys.platform)
    )
    return settings.to_dict()


def load_settings(path: str) -> tuple[AppSettings, str]:
    config_path = Path(path)
    if not config_path.exists():
        return AppSettings.from_dict(build_default_settings()), ""

    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and not payload.get("asr_provider"):
        payload = {
            **build_default_settings(),
            **payload,
        }
    settings = AppSettings.from_dict(payload if isinstance(payload, dict) else {})
    legacy_api_key = ""
    if isinstance(payload, dict):
        legacy_api_key = str(payload.get("openai_api_key") or "").strip()
    return settings, legacy_api_key


def save_settings(path: str, settings: AppSettings) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(settings.to_dict(), handle, ensure_ascii=True, indent=2, sort_keys=True)


def with_endpoint_default(settings: AppSettings, endpoint: str) -> AppSettings:
    if settings.openai_endpoint:
        return settings
    return replace(settings, openai_endpoint=endpoint)
