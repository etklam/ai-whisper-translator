from src.infrastructure.subtitles.pysrt_subtitle_repository import PysrtSubtitleRepository


def test_get_language_suffix_traditional_chinese():
    repo = PysrtSubtitleRepository()
    output = repo.get_output_path("movie.srt", "繁體中文", replace_original=False)
    assert output.endswith(".zh_tw.srt")
