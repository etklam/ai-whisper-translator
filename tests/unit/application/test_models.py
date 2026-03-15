from src.application.settings_models import AppSettings
from src.application.models import TranslationRequest


def test_translation_request_defaults():
    req = TranslationRequest(
        file_paths=["a.srt"],
        source_lang="英文",
        target_lang="繁體中文",
        model_name="m",
    )
    assert req.max_retries == 1


def test_app_settings_preserves_asr_provider():
    settings = AppSettings.from_dict({"asr_provider": "const_me"})
    assert settings.asr_provider == "const_me"
