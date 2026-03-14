from unittest.mock import Mock

from src.application.models import TranslationRequest
from src.application.translation_coordinator import TranslationCoordinator
from src.domain.errors import ExternalServiceError
from src.infrastructure.subtitles.pysrt_subtitle_repository import PysrtSubtitleRepository


def test_retry_once_then_success(tmp_path):
    srt_path = tmp_path / "a.srt"
    srt_path.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:01,000",
                "Hello",
                "",
            ]
        ),
        encoding="utf-8",
    )
    client = Mock()
    client.translate_text.side_effect = [ExternalServiceError("temporary"), "ok"]
    repo = PysrtSubtitleRepository()
    prompt = Mock()
    prompt.get_prompt.return_value = "p"
    coordinator = TranslationCoordinator(
        subtitle_repo=repo,
        translation_client=client,
        prompt_provider=prompt,
        event_sink=Mock(),
    )
    req = TranslationRequest(
        file_paths=[str(srt_path)],
        source_lang="英文",
        target_lang="繁體中文",
        model_name="m",
        max_retries=1,
    )
    summary = coordinator.run(req)
    assert summary.failed_files == 0
    assert client.translate_text.call_count == 2
