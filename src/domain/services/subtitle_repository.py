from typing import Protocol


class SubtitleRepository(Protocol):
    def get_output_path(self, file_path: str, target_lang: str, replace_original: bool = False) -> str: ...

    def clean_srt_file(self, input_file: str, create_backup: bool = False) -> dict: ...
