from src.application.models import TranslationRequest


def test_translation_request_defaults():
    req = TranslationRequest(
        file_paths=["a.srt"],
        source_lang="英文",
        target_lang="繁體中文",
        model_name="m",
    )
    assert req.max_retries == 1
