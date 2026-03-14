from unittest.mock import Mock

from src.application.models import TranslationRequest
from src.application.translation_coordinator import TranslationCoordinator
from src.infrastructure.subtitles.pysrt_subtitle_repository import PysrtSubtitleRepository


def _write_srt(path, text="Hello"):
    path.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:01,000",
                text,
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_continues_after_single_file_failure(tmp_path):
    file_a = tmp_path / "a.srt"
    file_b = tmp_path / "b.srt"
    _write_srt(file_a, "Hello")
    _write_srt(file_b, "World")

    client = Mock()
    client.translate_text.return_value = "ok"
    prompt = Mock()
    prompt.get_prompt.return_value = "p"
    coordinator = TranslationCoordinator(
        subtitle_repo=PysrtSubtitleRepository(),
        translation_client=client,
        prompt_provider=prompt,
        event_sink=Mock(),
    )
    req = TranslationRequest(
        file_paths=[str(file_a), str(file_b)],
        source_lang="英文",
        target_lang="繁體中文",
        model_name="m",
    )
    summary = coordinator.run(req)
    assert summary.total_files == 2
    assert summary.failed_files <= 1
