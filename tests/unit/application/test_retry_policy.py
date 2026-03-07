from unittest.mock import Mock

from src.application.models import TranslationRequest
from src.application.translation_coordinator import TranslationCoordinator
from src.domain.errors import ExternalServiceError


def test_retry_once_then_success():
    client = Mock()
    client.translate_text.side_effect = [ExternalServiceError("temporary"), "ok"]
    repo = Mock()
    prompt = Mock()
    prompt.get_prompt.return_value = "p"
    coordinator = TranslationCoordinator(
        subtitle_repo=repo,
        translation_client=client,
        prompt_provider=prompt,
        event_sink=Mock(),
    )
    req = TranslationRequest(
        file_paths=["a.srt"],
        source_lang="英文",
        target_lang="繁體中文",
        model_name="m",
        max_retries=1,
    )
    summary = coordinator.run(req)
    assert summary.failed_files == 0
    assert client.translate_text.call_count == 2
