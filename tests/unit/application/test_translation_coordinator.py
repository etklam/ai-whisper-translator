from src.application.models import TranslationRequest
from src.application.translation_coordinator import TranslationCoordinator


def test_continues_after_single_file_failure(fake_services):
    coordinator = TranslationCoordinator(**fake_services)
    req = TranslationRequest(
        file_paths=["a.srt", "b.srt"],
        source_lang="英文",
        target_lang="繁體中文",
        model_name="m",
    )
    summary = coordinator.run(req)
    assert summary.total_files == 2
    assert summary.failed_files <= 1
